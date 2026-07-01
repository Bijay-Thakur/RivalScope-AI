"""Unit tests for LLM factory and search service.

No external API calls are made — all tests monkeypatch settings to
ensure keys are absent or present with fake values, verifying that
services raise clear errors before any network activity.
"""

import pytest

from app.core.config import settings
from app.services.llm import get_primary_llm
from app.services.search import search_web


def _clear_llm_keys(monkeypatch) -> None:
    monkeypatch.setattr(settings, "groq_api_key", None)
    monkeypatch.setattr(settings, "google_api_key", None)
    monkeypatch.setattr(settings, "gemini_api_key", None)


class TestLLMFactory:
    def test_groq_raises_when_key_missing(self, monkeypatch):
        monkeypatch.setattr(settings, "llm_provider", "groq")
        _clear_llm_keys(monkeypatch)

        with pytest.raises((ValueError, RuntimeError), match="GROQ_API_KEY"):
            get_primary_llm()

    def test_gemini_raises_when_both_gemini_keys_missing(self, monkeypatch):
        monkeypatch.setattr(settings, "llm_provider", "gemini")
        _clear_llm_keys(monkeypatch)

        with pytest.raises((ValueError, RuntimeError), match="GOOGLE_API_KEY|GEMINI_API_KEY"):
            get_primary_llm()

    def test_unsupported_provider_raises(self, monkeypatch):
        monkeypatch.setattr(settings, "llm_provider", "openai")

        with pytest.raises((ValueError, RuntimeError), match="[Uu]nsupported"):
            get_primary_llm()

    def test_no_llm_instantiated_at_import_time(self):
        # Importing the module must not raise even when no keys are present.
        import app.services.llm  # noqa: F401


class TestSearchService:
    def test_search_web_raises_when_tavily_key_missing(self, monkeypatch):
        monkeypatch.setattr(settings, "tavily_api_key", None)

        with pytest.raises((ValueError, RuntimeError), match="TAVILY_API_KEY"):
            search_web("test query")

    def test_extract_urls_raises_when_tavily_key_missing(self, monkeypatch):
        from app.services.search import extract_urls

        monkeypatch.setattr(settings, "tavily_api_key", None)

        with pytest.raises((ValueError, RuntimeError), match="TAVILY_API_KEY"):
            extract_urls(["https://example.com"])

    def test_extract_urls_returns_empty_for_no_input(self):
        from app.services.search import extract_urls

        # Should short-circuit before checking the key.
        assert extract_urls([]) == []

    def test_dedupe_urls_removes_duplicates(self):
        from app.services.search import dedupe_urls

        results = [
            {"url": "https://a.com", "title": "A"},
            {"url": "https://b.com", "title": "B"},
            {"url": "https://a.com", "title": "A dup"},
        ]
        deduped = dedupe_urls(results)
        assert len(deduped) == 2
        assert deduped[0]["url"] == "https://a.com"
        assert deduped[1]["url"] == "https://b.com"

    def test_dedupe_urls_skips_empty_urls(self):
        from app.services.search import dedupe_urls

        results = [
            {"url": "", "title": "No URL"},
            {"url": "   ", "title": "Whitespace URL"},
            {"url": "https://valid.com", "title": "Valid"},
        ]
        deduped = dedupe_urls(results)
        assert len(deduped) == 1
        assert deduped[0]["url"] == "https://valid.com"
