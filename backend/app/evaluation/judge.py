"""LLM-as-judge grounding (ported from evals/). Reference-free faithfulness:
does the cited SOURCE TEXT support the CLAIM? Tries settings.judge_model first,
then falls back to settings.gemini_model when Pro quota/auth fails."""

import asyncio
import logging
import re
import time

from pydantic import BaseModel, Field

from app.core.config import settings
from app.evaluation.schemas import Verdict
from app.observability.tracing import traceable

logger = logging.getLogger(__name__)

_JUDGE_SYSTEM_PROMPT = (
    "You are a strict grounding judge. Given a CLAIM and the SOURCE TEXT it cites, "
    "decide ONLY from the source text whether it supports the claim.\n"
    "SUPPORTED = fully entailed by the source text.\n"
    "PARTIAL = source text partly supports it.\n"
    "UNSUPPORTED = source text is silent on the claim.\n"
    "CONTRADICTED = source text states the opposite.\n"
    "Ignore all outside knowledge — judge the given text only, nothing else. "
    "Keep rationale to one terse sentence."
)


class _JudgeVerdict(BaseModel):
    verdict: str = Field(description="one of: supported, partial, unsupported, contradicted")
    rationale: str
    judge_confidence: float = Field(ge=0.0, le=1.0)


def _active_gemini_key() -> str | None:
    return settings.google_api_key or settings.gemini_api_key


def judge_model_candidates(preferred: str | None = None) -> list[str]:
    """Ordered backends for judge calls.

    Default: Gemini primary -> Gemini fallback -> Groq.
    JUDGE_USE_GROQ=true: Groq primary -> Gemini models as fallback.
    """
    primary = preferred or settings.judge_model
    gemini_fallback = settings.gemini_model
    gemini_models: list[str] = []
    for name in (primary, gemini_fallback):
        if name and name not in gemini_models:
            gemini_models.append(name)

    if settings.judge_use_groq and settings.has_groq_key:
        out = [f"groq:{settings.groq_model}"]
        out.extend(gemini_models)
        return out

    out = list(gemini_models)
    if settings.has_groq_key:
        out.append(f"groq:{settings.groq_model}")
    return out


async def _invoke_judge_groq(messages: list[dict], model: str) -> _JudgeVerdict:
    from langchain_groq import ChatGroq

    if not settings.has_groq_key:
        raise ValueError("Groq API key not configured for judge fallback.")

    llm = ChatGroq(
        model=model,
        temperature=0.0,
        api_key=settings.groq_api_key,
    )
    structured = llm.with_structured_output(_JudgeVerdict)
    return await structured.ainvoke(messages)


def _get_judge_llm(model: str):
    from langchain_google_genai import ChatGoogleGenerativeAI

    api_key = _active_gemini_key()
    if not api_key:
        raise ValueError(
            "Gemini API key required for --mode full. Set GOOGLE_API_KEY or GEMINI_API_KEY."
        )

    llm = ChatGoogleGenerativeAI(
        model=model,
        temperature=0.0,
        google_api_key=api_key,
    )
    return llm.with_structured_output(_JudgeVerdict)


async def _invoke_judge(messages: list[dict], model: str) -> _JudgeVerdict:
    llm = _get_judge_llm(model)
    return await llm.ainvoke(messages)


def _is_rate_limit_error(exc: Exception) -> bool:
    text = str(exc).upper()
    return "429" in text or "RESOURCE_EXHAUSTED" in text or "RATE" in text


def _is_hard_quota_block(exc: Exception) -> bool:
    """Daily/per-model quota is zero — retries will not help."""
    text = str(exc).lower()
    return "limit: 0" in text or "limit:0" in text


def _retry_delay_seconds(exc: Exception, attempt: int) -> float:
    text = str(exc)
    match = re.search(r"retry in ([0-9.]+)s", text, re.IGNORECASE)
    if match:
        return float(match.group(1)) + 1.0
    match = re.search(r"try again in ([0-9.]+)s", text, re.IGNORECASE)
    if match:
        return float(match.group(1)) + 1.0
    match = re.search(r"Please try again in ([0-9.]+)m", text, re.IGNORECASE)
    if match:
        return float(match.group(1)) * 60.0 + 1.0
    return 22.0 * (attempt + 1)


async def _invoke_judge_with_retry(messages: list[dict], model: str) -> _JudgeVerdict:
    max_attempts = 4
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await _invoke_judge(messages, model)
        except Exception as exc:
            last_exc = exc
            if _is_hard_quota_block(exc):
                raise
            if _is_rate_limit_error(exc) and attempt < max_attempts - 1:
                delay = _retry_delay_seconds(exc, attempt)
                logger.info(
                    "judge rate-limited on %s (attempt %d/%d) — sleeping %.0fs.",
                    model,
                    attempt + 1,
                    max_attempts,
                    delay,
                )
                await asyncio.sleep(delay)
                continue
            raise
    raise last_exc if last_exc else RuntimeError("judge invoke failed")


async def _invoke_judge_groq_with_retry(messages: list[dict], model: str) -> _JudgeVerdict:
    max_attempts = 4
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await _invoke_judge_groq(messages, model)
        except Exception as exc:
            last_exc = exc
            if _is_rate_limit_error(exc) and attempt < max_attempts - 1:
                delay = min(_retry_delay_seconds(exc, attempt), 60.0)
                logger.info(
                    "judge groq rate-limited on %s (attempt %d/%d) — sleeping %.0fs.",
                    model,
                    attempt + 1,
                    max_attempts,
                    delay,
                )
                await asyncio.sleep(delay)
                continue
            raise
    raise last_exc if last_exc else RuntimeError("judge groq invoke failed")


# Cap judge context. 4k keeps claim-relevant sentences without blowing Groq TPM.
_JUDGE_SOURCE_TEXT_MAX_CHARS = 4000


@traceable(run_type="llm", name="judge_claim")
async def judge_claim(
    claim: str,
    source_title: str,
    source_url: str,
    source_text: str,
    model: str,
) -> tuple[Verdict, str, float]:
    clipped = (source_text or "").strip()
    if len(clipped) > _JUDGE_SOURCE_TEXT_MAX_CHARS:
        clipped = clipped[:_JUDGE_SOURCE_TEXT_MAX_CHARS] + "\n…[truncated]"
    user_message = (
        f"CLAIM: {claim}\n\n"
        f"SOURCE TITLE: {source_title}\n"
        f"SOURCE URL: {source_url}\n"
        f"SOURCE TEXT:\n{clipped or '(empty)'}"
    )
    messages = [
        {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    candidates = judge_model_candidates(model)
    last_exc: Exception | None = None
    t0 = time.perf_counter()

    for idx, candidate in enumerate(candidates):
        try:
            if candidate.startswith("groq:"):
                groq_model = candidate.split(":", 1)[1]
                result = await _invoke_judge_groq_with_retry(messages, groq_model)
            else:
                result = await _invoke_judge_with_retry(messages, candidate)
            latency_ms = (time.perf_counter() - t0) * 1000
            if idx > 0:
                logger.info(
                    "judge_claim succeeded via fallback model %s (primary %s unavailable) "
                    "latency_ms=%.0f.",
                    candidate,
                    candidates[0],
                    latency_ms,
                )
            else:
                logger.info(
                    "judge_claim ok model=%s latency_ms=%.0f verdict=%s",
                    candidate,
                    latency_ms,
                    result.verdict,
                )
            verdict = Verdict(result.verdict.strip().lower())
            return verdict, result.rationale, result.judge_confidence
        except Exception as exc:
            last_exc = exc
            if idx < len(candidates) - 1:
                logger.warning(
                    "judge_claim model %s failed [%s]: %s — trying fallback %s.",
                    candidate,
                    type(exc).__name__,
                    _short_error(exc),
                    candidates[idx + 1],
                )
            else:
                latency_ms = (time.perf_counter() - t0) * 1000
                logger.error(
                    "judge_claim FAILED all models %s [%s]: %s latency_ms=%.0f — "
                    "recording ERROR (not unsupported).",
                    candidates,
                    type(exc).__name__,
                    _short_error(exc),
                    latency_ms,
                )

    err_name = type(last_exc).__name__ if last_exc else "unknown"
    return (
        Verdict.ERROR,
        f"Judge error: {err_name}: {_short_error(last_exc) if last_exc else 'unknown'}",
        0.0,
    )


def _short_error(exc: Exception, limit: int = 180) -> str:
    text = str(exc).replace("\n", " ")
    return text[:limit] + ("…" if len(text) > limit else "")


async def judge_claims(
    items: list[dict],
    model: str,
    max_concurrency: int = 3,
) -> list[tuple[Verdict, str, float]]:
    if not items:
        return []

    semaphore = asyncio.Semaphore(max_concurrency)

    async def _bounded(item: dict) -> tuple[Verdict, str, float]:
        async with semaphore:
            return await judge_claim(
                claim=item["claim"],
                source_title=item["source_title"],
                source_url=item["source_url"],
                source_text=item["source_text"],
                model=model,
            )

    return await asyncio.gather(*(_bounded(item) for item in items))
