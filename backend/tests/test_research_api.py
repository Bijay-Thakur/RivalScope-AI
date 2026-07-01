import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)

_VALID_PAYLOAD = {
    "ourCompany": "ClickUp",
    "competitor": "Notion",
    "market": "Project management / docs",
    "reportType": "sales_battlecard",
}


@pytest.fixture(autouse=True)
def force_mock_mode(monkeypatch):
    """Default all API tests to mock mode so no external keys are required."""
    monkeypatch.setattr(settings, "research_mode", "mock")


class TestHealthCheck:
    def test_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "rivalscope-api"


class TestCreateResearch:
    def test_mock_mode_returns_200(self):
        response = client.post("/api/research/", json=_VALID_PAYLOAD)
        assert response.status_code == 200

    def test_mock_mode_report_has_required_fields(self):
        response = client.post("/api/research/", json=_VALID_PAYLOAD)
        report = response.json()["report"]

        assert "companySnapshot" in report
        assert report["companySnapshot"]
        assert "salesBattlecard" in report
        assert report["salesBattlecard"]
        assert "sources" in report
        assert len(report["sources"]) > 0
        assert "evidence" in report
        assert len(report["evidence"]) > 0
        assert "confidenceScore" in report

    def test_mock_mode_sources_have_required_fields(self):
        response = client.post("/api/research/", json=_VALID_PAYLOAD)
        sources = response.json()["report"]["sources"]

        for source in sources:
            assert "id" in source
            assert "title" in source
            assert "url" in source
            assert "sourceType" in source
            assert "credibilityScore" in source

    def test_missing_required_field_returns_422(self):
        bad_payload = {k: v for k, v in _VALID_PAYLOAD.items() if k != "competitor"}
        response = client.post("/api/research/", json=bad_payload)
        assert response.status_code == 422

    def test_invalid_report_type_returns_422(self):
        payload = {**_VALID_PAYLOAD, "reportType": "nonexistent_type"}
        response = client.post("/api/research/", json=payload)
        assert response.status_code == 422


def _set_no_keys(monkeypatch) -> None:
    """Clear all API key fields so tests are environment-independent."""
    monkeypatch.setattr(settings, "tavily_api_key", None)
    monkeypatch.setattr(settings, "groq_api_key", None)
    monkeypatch.setattr(settings, "google_api_key", None)
    monkeypatch.setattr(settings, "gemini_api_key", None)


class TestRealModeKeyValidation:
    def test_real_mode_without_any_keys_returns_400(self, monkeypatch):
        monkeypatch.setattr(settings, "research_mode", "real")
        _set_no_keys(monkeypatch)

        response = client.post("/api/research/", json=_VALID_PAYLOAD)

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "Real research mode" in detail
        assert "TAVILY_API_KEY" in detail

    def test_real_mode_with_tavily_only_returns_400(self, monkeypatch):
        """Tavily alone is not enough — an LLM key is also required."""
        monkeypatch.setattr(settings, "research_mode", "real")
        _set_no_keys(monkeypatch)
        monkeypatch.setattr(settings, "tavily_api_key", "tvly-fake")

        response = client.post("/api/research/", json=_VALID_PAYLOAD)

        assert response.status_code == 400

    def test_real_mode_with_llm_key_only_returns_400(self, monkeypatch):
        """An LLM key alone is not enough — Tavily is also required."""
        monkeypatch.setattr(settings, "research_mode", "real")
        _set_no_keys(monkeypatch)
        monkeypatch.setattr(settings, "groq_api_key", "gsk_fake")

        response = client.post("/api/research/", json=_VALID_PAYLOAD)

        assert response.status_code == 400

    def test_real_mode_with_gemini_key_and_no_tavily_returns_400(self, monkeypatch):
        """GEMINI_API_KEY satisfies LLM requirement but Tavily is still needed."""
        monkeypatch.setattr(settings, "research_mode", "real")
        _set_no_keys(monkeypatch)
        monkeypatch.setattr(settings, "gemini_api_key", "ai-fake")

        response = client.post("/api/research/", json=_VALID_PAYLOAD)

        assert response.status_code == 400

    def test_error_message_does_not_expose_key_values(self, monkeypatch):
        monkeypatch.setattr(settings, "research_mode", "real")
        _set_no_keys(monkeypatch)

        response = client.post("/api/research/", json=_VALID_PAYLOAD)

        detail = response.json()["detail"]
        assert "tvly-" not in detail
        assert "gsk_" not in detail
        assert "ai-fake" not in detail
