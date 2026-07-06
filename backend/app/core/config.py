import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"

    groq_api_key: str | None = None
    google_api_key: str | None = None
    gemini_api_key: str | None = None
    tavily_api_key: str | None = None

    llm_provider: str = "groq"
    groq_model: str = "llama-3.1-8b-instant"
    gemini_model: str = "gemini-2.5-flash"

    research_mode: str = "mock"

    # Step 1 — symmetric research + full-page extraction
    extract_top_n: int = 3  # top-N ranked URLs per (track, company) sent to TavilyExtract
    extract_max_chars: int = 6000  # cap merged full-page content per result

    # Step 4 Part A — LLM reliability/cost guards
    groq_max_payload_chars: int = 16000  # est. prompt size above this -> skip Groq (avoids 413), go straight to Gemini
    max_context_chars: int = 50000  # safety cap on assembled two-sided context; trims lowest-cred evidence first

    # Phase 2 — grounding eval + tracing
    judge_model: str = "gemini-2.5-pro"  # stronger tier than gemini_model (flash) to reduce self-eval bias
    eval_max_concurrency: int = 3

    langsmith_tracing: bool = False
    langsmith_api_key: str | None = None
    langsmith_project: str = "rivalscope-ai"

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def is_real_research_enabled(self) -> bool:
        return self.research_mode.lower() == "real"

    @property
    def has_groq_key(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def has_gemini_key(self) -> bool:
        return bool(self.google_api_key) or bool(self.gemini_api_key)

    @property
    def has_tavily_key(self) -> bool:
        return bool(self.tavily_api_key)

    @property
    def primary_llm_provider(self) -> str:
        return self.llm_provider.lower().strip()


settings = Settings()

if settings.langsmith_tracing:
    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)
    if settings.langsmith_api_key:
        os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
