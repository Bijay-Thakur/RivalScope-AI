import logging

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings
from app.observability import trace_buffer

logger = logging.getLogger(__name__)


def _active_gemini_key() -> str | None:
    """Return whichever Gemini key the user configured, preferring GOOGLE_API_KEY."""
    return settings.google_api_key or settings.gemini_api_key


def get_primary_llm(temperature: float = 0.1):
    provider = settings.primary_llm_provider

    if provider == "groq":
        if not settings.has_groq_key:
            raise ValueError(
                "LLM_PROVIDER is 'groq' but GROQ_API_KEY is not set."
            )
        return ChatGroq(
            model=settings.groq_model,
            temperature=temperature,
            api_key=settings.groq_api_key,
            # every prompt in this app demands JSON-only output — force it so small
            # instruct models (e.g. llama-3.1-8b) don't wrap/truncate it into prose.
            model_kwargs={"response_format": {"type": "json_object"}},
        )

    if provider == "gemini":
        if not settings.has_gemini_key:
            raise ValueError(
                "LLM_PROVIDER is 'gemini' but neither GOOGLE_API_KEY nor GEMINI_API_KEY is set."
            )
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            temperature=temperature,
            google_api_key=_active_gemini_key(),
            # stream internally so astream_events surfaces on_chat_model_stream token deltas;
            # .invoke still returns the fully aggregated result (sync/eval path unaffected).
            streaming=True,
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER '{settings.llm_provider}'. "
        "Supported values: 'groq', 'gemini'."
    )


def get_fallback_llm(temperature: float = 0.1):
    provider = settings.primary_llm_provider

    if provider == "groq" and settings.has_gemini_key:
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            temperature=temperature,
            google_api_key=_active_gemini_key(),
            streaming=True,  # token deltas for astream_events; aggregated on .invoke
        )

    if provider == "gemini" and settings.has_groq_key:
        return ChatGroq(
            model=settings.groq_model,
            temperature=temperature,
            api_key=settings.groq_api_key,
            # every prompt in this app demands JSON-only output — force it so small
            # instruct models (e.g. llama-3.1-8b) don't wrap/truncate it into prose.
            model_kwargs={"response_format": {"type": "json_object"}},
        )

    return None


def _estimate_payload_chars(messages) -> int:
    total = 0
    for m in messages:
        content = m.get("content") if isinstance(m, dict) else getattr(m, "content", "")
        total += len(content or "")
    return total


def invoke_with_fallback(
    messages,
    temperature: float = 0.1,
    *,
    run_id: str | None = None,
    call_name: str = "llm_call",
    track: str | None = None,
):
    payload_chars = _estimate_payload_chars(messages)
    with trace_buffer.trace_call(
        run_id,
        kind=trace_buffer.KIND_LLM,
        name=call_name,
        track=track,
        summary=f"{call_name}: {payload_chars:,} char prompt",
        detail={"promptChars": payload_chars},
    ) as span:
        provider, result = _invoke_with_fallback_inner(messages, temperature, payload_chars)
        span["summary"] = f"{call_name} \u2192 answered via {provider}"
        span["detail"]["provider"] = provider
        return result


def _invoke_with_fallback_inner(messages, temperature: float, payload_chars: int):
    """Returns (provider_used_label, result). Raises on total failure."""
    provider_label = settings.primary_llm_provider

    # Payload-aware routing: skip Groq entirely when the prompt is too big for it
    # (avoids a guaranteed 413 round-trip) and go straight to the large model.
    if provider_label == "groq" and settings.has_gemini_key:
        if payload_chars > settings.groq_max_payload_chars:
            large = get_fallback_llm(temperature)  # gemini when primary is groq
            if large is not None:
                logger.info(
                    "LLM route: skip Groq (payload %d > %d) -> gemini.",
                    payload_chars,
                    settings.groq_max_payload_chars,
                )
                try:
                    result = large.invoke(messages)
                    logger.info("LLM call succeeded (route: oversize-direct, provider: gemini)")
                    return "gemini (oversize route)", result
                except Exception as large_error:
                    raise RuntimeError(
                        "Oversize payload routed to gemini and it failed."
                    ) from large_error

    primary = get_primary_llm(temperature)

    try:
        result = primary.invoke(messages)
        logger.info("LLM call succeeded (route: primary-first, provider: %s)", provider_label)
        return provider_label, result
    except Exception as primary_error:
        logger.warning(
            "Primary LLM (%s) failed [%s]. Trying fallback.",
            provider_label,
            type(primary_error).__name__,
        )

    fallback = get_fallback_llm(temperature)
    if fallback is None:
        raise RuntimeError(
            f"Primary LLM provider '{provider_label}' failed and no fallback is configured."
        ) from primary_error

    fallback_label = "gemini" if provider_label == "groq" else "groq"
    try:
        result = fallback.invoke(messages)
        logger.info("LLM call succeeded (fallback provider: %s)", fallback_label)
        return f"{fallback_label} (fallback)", result
    except Exception as fallback_error:
        raise RuntimeError(
            f"Both primary provider '{provider_label}' and fallback provider '{fallback_label}' failed."
        ) from fallback_error
