"""Config API — surfaces provider settings for the Settings screen.

Never returns secret values — only which providers are configured (booleans)
plus non-sensitive model/mode selections.
"""
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
def get_config() -> dict:
    return {
        "researchMode": settings.research_mode,
        "isRealResearchEnabled": settings.is_real_research_enabled,
        "llmProvider": settings.primary_llm_provider,
        "llmFallback": "gemini" if settings.primary_llm_provider == "groq" else "groq",
        "groqModel": settings.groq_model,
        "geminiModel": settings.gemini_model,
        "judgeModel": settings.judge_model,
        "searchProvider": "tavily",
        "database": "sqlite",
        "providers": {
            "tavily": settings.has_tavily_key,
            "groq": settings.has_groq_key,
            "gemini": settings.has_gemini_key,
        },
        "tracing": {
            "langsmithEnabled": settings.langsmith_tracing,
            "langsmithProject": settings.langsmith_project,
            "toolTraceBuffer": True,
        },
        "extractTopN": settings.extract_top_n,
        "maxContextChars": settings.max_context_chars,
    }
