"""Shared structured-output parse → validate → bounded repair flow."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from app.services.json_utils import extract_json_from_text, safe_get_message_text
from app.services.llm import invoke_with_fallback

logger = logging.getLogger(__name__)


class StructuredOutputError(Exception):
    """Raised when parse/validate/repair all fail within bounds."""

    def __init__(self, message: str, *, errors: list[str] | None = None):
        super().__init__(message)
        self.errors = errors or []


def parse_json_payload(raw: str | Any) -> dict | list:
    """Primary parser: LangChain message or text → JSON via extract_json_from_text."""
    if not isinstance(raw, str):
        raw = safe_get_message_text(raw)
    try:
        return extract_json_from_text(raw or "")
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise StructuredOutputError(
            "invalid_json", errors=[str(exc)[:200]]
        ) from exc


def invoke_json_with_repair(
    *,
    messages: list[dict],
    schema_hint: str,
    validate: Callable[[dict | list], tuple[Any, list[str]]],
    run_id: str | None = None,
    call_name: str = "structured_llm",
    preferred_provider: str | None = None,
    stage: str | None = None,
    max_repairs: int = 1,
) -> Any:
    """Call model, parse JSON, validate; on failure attempt bounded structure-only repair.

    ``validate`` returns ``(value, errors)``. Empty ``errors`` means success.
    Safe coercions inside ``validate`` are allowed; this helper does not invent facts.
    """
    response = invoke_with_fallback(
        messages,
        run_id=run_id,
        call_name=call_name,
        preferred_provider=preferred_provider,
        stage=stage,
    )
    try:
        data = parse_json_payload(response)
    except StructuredOutputError:
        data = None
        errors = ["invalid_json"]
    else:
        value, errors = validate(data)
        if not errors:
            return value

    repairs = 0
    last_errors = errors
    last_raw = data
    while repairs < max_repairs:
        repairs += 1
        repair_messages = list(messages) + [
            {
                "role": "user",
                "content": (
                    "Your previous output failed validation. Correct STRUCTURE only. "
                    "Do not add unsupported facts or new source IDs.\n\n"
                    f"Required schema:\n{schema_hint}\n\n"
                    f"Validation errors:\n{json.dumps(last_errors)}\n\n"
                    f"Invalid output:\n{json.dumps(last_raw, default=str)[:4000]}\n\n"
                    "Return corrected JSON only."
                ),
            }
        ]
        try:
            response = invoke_with_fallback(
                repair_messages,
                run_id=run_id,
                call_name=f"{call_name}_repair_{repairs}",
                preferred_provider=preferred_provider,
                stage=stage,
            )
            data = parse_json_payload(response)
            value, errors = validate(data)
            if not errors:
                logger.info("%s: repair %d succeeded", call_name, repairs)
                return value
            last_errors = errors
            last_raw = data
        except Exception as exc:
            last_errors = [f"repair_failed:{type(exc).__name__}"]
            logger.warning("%s: repair %d failed [%s]", call_name, repairs, type(exc).__name__)

    raise StructuredOutputError(
        f"{call_name}: validation failed after {max_repairs} repair(s)",
        errors=last_errors,
    )
