"""Centralized LLM execution: stage temps, timeout, bounded retry, Groq↔Gemini fallback."""

from __future__ import annotations

import logging
import time

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.observability import trace_buffer

logger = logging.getLogger(__name__)

# Stage-specific defaults (application policy; agents should pass stage=...).
STAGE_TEMPERATURES: dict[str, float] = {
    "research_planner": 0.0,
    "evidence_extractor": 0.0,
    "claim_generator": 0.0,
    "fact_checker": 0.0,
    "comparison_agent": 0.1,
    "report_generator": 0.1,
    "grounding_verifier": 0.0,
}


class LLMErrorKind:
    PROVIDER = "provider_network"
    RATE_LIMIT = "rate_limit"
    INVALID_JSON = "invalid_json"
    SCHEMA = "schema_validation"
    GROUNDING = "grounding_validation"
    CONFIG = "configuration"


def classify_llm_error(exc: Exception) -> str:
    text = str(exc).upper()
    name = type(exc).__name__.lower()
    if "api key" in text.lower() or "auth" in name or "401" in text or "403" in text:
        return LLMErrorKind.CONFIG
    if "429" in text or "RATE" in text or "RESOURCE_EXHAUSTED" in text:
        return LLMErrorKind.RATE_LIMIT
    if "timeout" in text.lower() or "timed out" in text.lower():
        return LLMErrorKind.PROVIDER
    return LLMErrorKind.PROVIDER


def _active_gemini_key() -> str | None:
    return settings.google_api_key or settings.gemini_api_key


def get_llm(provider: str, temperature: float = 0.1):
    name = provider.lower().strip()
    timeout = float(settings.llm_request_timeout_seconds)
    if name == "groq":
        if not settings.has_groq_key:
            raise ValueError("GROQ_API_KEY is not set.")
        return ChatGroq(
            model=settings.groq_model,
            temperature=temperature,
            api_key=settings.groq_api_key,
            timeout=timeout,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
    if name == "gemini":
        if not settings.has_gemini_key:
            raise ValueError(
                "Neither GOOGLE_API_KEY nor GEMINI_API_KEY is set."
            )
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            temperature=temperature,
            google_api_key=_active_gemini_key(),
            streaming=True,
            timeout=timeout,
        )
    raise ValueError(f"Unsupported provider '{provider}'. Use 'groq' or 'gemini'.")


def get_primary_llm(temperature: float = 0.1):
    return get_llm(settings.primary_llm_provider, temperature)


def resolve_step_provider(configured: str) -> str:
    """Mock → Groq; real → honor per-step config."""
    wanted = (configured or "groq").lower().strip()
    if wanted not in {"groq", "gemini"}:
        wanted = "groq"

    if not settings.is_real_research_enabled:
        if settings.has_groq_key:
            return "groq"
        if settings.has_gemini_key:
            return "gemini"
        return wanted

    if wanted == "groq" and not settings.has_groq_key and settings.has_gemini_key:
        return "gemini"
    if wanted == "gemini" and not settings.has_gemini_key and settings.has_groq_key:
        return "groq"
    return wanted


def get_fallback_llm(temperature: float = 0.1):
    provider = settings.primary_llm_provider
    if provider == "groq" and settings.has_gemini_key:
        return get_llm("gemini", temperature)
    if provider == "gemini" and settings.has_groq_key:
        return get_llm("groq", temperature)
    return None


def _estimate_payload_chars(messages) -> int:
    total = 0
    for m in messages:
        content = m.get("content") if isinstance(m, dict) else getattr(m, "content", "")
        total += len(content or "")
    return total


def _other_provider(provider: str) -> str:
    return "gemini" if provider == "groq" else "groq"


def _has_provider(provider: str) -> bool:
    return settings.has_groq_key if provider == "groq" else settings.has_gemini_key


def _invoke_once(provider: str, messages, temperature: float):
    return get_llm(provider, temperature).invoke(messages)


def _invoke_with_retries(provider: str, messages, temperature: float):
    """Bounded same-provider retries for transient/rate-limit errors only."""
    attempts = max(1, int(settings.llm_max_retries) + 1)
    last_exc: Exception | None = None
    for attempt in range(attempts):
        t0 = time.perf_counter()
        try:
            result = _invoke_once(provider, messages, temperature)
            logger.info(
                "llm_ok provider=%s attempt=%d latency_ms=%.0f",
                provider,
                attempt + 1,
                (time.perf_counter() - t0) * 1000,
            )
            return result
        except Exception as exc:
            last_exc = exc
            kind = classify_llm_error(exc)
            logger.warning(
                "llm_fail provider=%s attempt=%d kind=%s err=%s",
                provider,
                attempt + 1,
                kind,
                type(exc).__name__,
            )
            if kind == LLMErrorKind.CONFIG:
                raise
            if attempt < attempts - 1 and kind in {
                LLMErrorKind.RATE_LIMIT,
                LLMErrorKind.PROVIDER,
            }:
                delay = min(20.0, 2.0 ** attempt)
                time.sleep(delay)
                continue
            raise
    raise last_exc if last_exc else RuntimeError("llm invoke failed")


def invoke_with_fallback(
    messages,
    temperature: float | None = None,
    *,
    run_id: str | None = None,
    call_name: str = "llm_call",
    track: str | None = None,
    preferred_provider: str | None = None,
    stage: str | None = None,
):
    """Invoke LLM with stage temperature, timeout, retries, cross-provider fallback."""
    if temperature is None:
        temperature = STAGE_TEMPERATURES.get(stage or "", 0.1)

    payload_chars = _estimate_payload_chars(messages)
    with trace_buffer.trace_call(
        run_id,
        kind=trace_buffer.KIND_LLM,
        name=call_name,
        track=track,
        summary=f"{call_name}: {payload_chars:,} char prompt",
        detail={"promptChars": payload_chars, "stage": stage},
    ) as span:
        provider, result = _invoke_with_fallback_inner(
            messages,
            temperature,
            payload_chars,
            preferred_provider=preferred_provider,
        )
        span["summary"] = f"{call_name} → answered via {provider}"
        span["detail"]["provider"] = provider
        return result


def _invoke_with_fallback_inner(
    messages,
    temperature: float,
    payload_chars: int,
    *,
    preferred_provider: str | None = None,
):
    primary_label = (preferred_provider or settings.primary_llm_provider).lower().strip()
    if primary_label not in {"groq", "gemini"}:
        primary_label = settings.primary_llm_provider

    if primary_label == "groq" and settings.has_gemini_key:
        if payload_chars > settings.groq_max_payload_chars:
            logger.info(
                "LLM route: skip Groq (payload %d > %d) -> gemini.",
                payload_chars,
                settings.groq_max_payload_chars,
            )
            try:
                result = _invoke_with_retries("gemini", messages, temperature)
                return "gemini (oversize route)", result
            except Exception as large_error:
                raise RuntimeError(
                    "Oversize payload routed to gemini and it failed."
                ) from large_error

    if not _has_provider(primary_label):
        alt = _other_provider(primary_label)
        if _has_provider(alt):
            logger.warning(
                "Preferred provider %s unavailable — using %s.",
                primary_label,
                alt,
            )
            primary_label = alt
        else:
            raise ValueError(f"No LLM API key configured for '{primary_label}'.")

    try:
        result = _invoke_with_retries(primary_label, messages, temperature)
        return primary_label, result
    except Exception as primary_error:
        if classify_llm_error(primary_error) == LLMErrorKind.CONFIG:
            raise
        logger.warning(
            "Preferred LLM (%s) failed [%s]. Trying fallback.",
            primary_label,
            type(primary_error).__name__,
        )

    fallback_label = _other_provider(primary_label)
    if not _has_provider(fallback_label):
        raise RuntimeError(
            f"Primary LLM provider '{primary_label}' failed and no fallback is configured."
        ) from primary_error

    try:
        result = _invoke_with_retries(fallback_label, messages, temperature)
        return f"{fallback_label} (fallback)", result
    except Exception as fallback_error:
        raise RuntimeError(
            f"Both primary provider '{primary_label}' and fallback provider "
            f"'{fallback_label}' failed."
        ) from fallback_error
