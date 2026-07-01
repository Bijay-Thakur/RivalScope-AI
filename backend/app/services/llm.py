import logging

from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

from app.core.config import settings

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
        )

    if provider == "gemini" and settings.has_groq_key:
        return ChatGroq(
            model=settings.groq_model,
            temperature=temperature,
            api_key=settings.groq_api_key,
        )

    return None


def invoke_with_fallback(messages, temperature: float = 0.1):
    provider_label = settings.primary_llm_provider
    primary = get_primary_llm(temperature)

    try:
        result = primary.invoke(messages)
        logger.info("LLM call succeeded (provider: %s)", provider_label)
        return result
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
        return result
    except Exception as fallback_error:
        raise RuntimeError(
            f"Both primary provider '{provider_label}' and fallback provider '{fallback_label}' failed."
        ) from fallback_error
