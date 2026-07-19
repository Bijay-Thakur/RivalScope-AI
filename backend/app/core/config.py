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
    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    groq_api_key: str | None = None
    google_api_key: str | None = None
    gemini_api_key: str | None = None
    tavily_api_key: str | None = None

    llm_provider: str = "groq"
    groq_model: str = "llama-3.1-8b-instant"
    gemini_model: str = "gemini-2.5-flash"

    # Per-step LLM routing (search/extract always Tavily).
    # Convention: Groq = low-effort / mock / initial; Gemini = high-effort real synthesis.
    fact_checker_provider: str = "groq"
    comparison_provider: str = "gemini"
    report_provider: str = "gemini"

    research_mode: str = "mock"

    # Step 1 — symmetric research + full-page extraction
    extract_top_n: int = 2  # top-N URLs per (track, company) → TavilyExtract (2 cuts latency)
    extract_max_chars: int = 6000  # cap merged full-page content per result
    max_results_per_query: int = 2  # Tavily hits per query (was hard-coded 3)

    # Step 4 Part A — LLM reliability/cost guards
    groq_max_payload_chars: int = 16000  # est. prompt size above this -> skip Groq (avoids 413), go straight to Gemini
    max_context_chars: int = 50000  # safety cap on assembled two-sided context; trims lowest-cred evidence first
    llm_request_timeout_seconds: float = 60.0
    llm_max_retries: int = 2  # same-provider retries for transient/rate-limit errors

    # Phase 2 — grounding eval + tracing
    judge_model: str = "gemini-2.5-flash"  # use flash; pro often has zero quota on free/paid tiers
    judge_use_groq: bool = False  # set JUDGE_USE_GROQ=true to skip Gemini judge when quota exhausted
    eval_max_concurrency: int = 2
    judge_max_concurrency: int = 1  # serial judge calls avoid Gemini 429 storms during --mode full

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
