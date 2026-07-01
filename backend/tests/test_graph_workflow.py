import pytest

from app.core.config import settings
from app.graph.workflow import run_research_graph
from app.schemas.research import ReportType, ResearchRequest

_BASE_REQUEST = dict(
    our_company="ClickUp",
    competitor="Notion",
    market="Project management / docs",
)


@pytest.fixture(autouse=True)
def force_mock_mode(monkeypatch):
    """Ensure all graph tests run in mock mode regardless of .env."""
    monkeypatch.setattr(settings, "research_mode", "mock")


def test_run_research_graph_produces_report():
    request = ResearchRequest(
        **_BASE_REQUEST,
        report_type=ReportType.SALES_BATTLECARD,
    )
    state = run_research_graph(request)

    assert state["final_report"] is not None
    assert len(state["research_plan"]) >= 4
    assert len(state["evidence"]) > 0
    assert state["final_report"].confidence_score is not None


def test_mock_graph_produces_four_research_tasks():
    request = ResearchRequest(**_BASE_REQUEST, report_type=ReportType.QUICK_BRIEF)
    state = run_research_graph(request)

    tracks = {t.track for t in state["research_plan"]}
    assert tracks == {"company_profile", "product_features", "pricing", "recent_news"}


def test_mock_graph_populates_sources_and_evidence():
    request = ResearchRequest(**_BASE_REQUEST, report_type=ReportType.DEEP_RESEARCH)
    state = run_research_graph(request)

    assert len(state["sources"]) > 0
    assert len(state["evidence"]) > 0
    # Verify every evidence item references an existing source id.
    source_ids = {s.id for s in state["sources"]}
    for item in state["evidence"]:
        assert item.source_id in source_ids


def test_mock_graph_produces_verified_claims():
    request = ResearchRequest(**_BASE_REQUEST, report_type=ReportType.QUICK_BRIEF)
    state = run_research_graph(request)

    assert len(state["verified_claims"]) > 0
    for claim in state["verified_claims"]:
        assert claim.verification_status == "mock_verified"
        assert 0.0 <= claim.confidence_score <= 1.0


def test_mock_report_has_required_fields():
    request = ResearchRequest(**_BASE_REQUEST, report_type=ReportType.SALES_BATTLECARD)
    state = run_research_graph(request)

    report = state["final_report"]
    assert report.company_snapshot
    assert report.product_positioning
    assert isinstance(report.feature_comparison, list)
    assert report.pricing_intelligence
    assert isinstance(report.strengths, list)
    assert isinstance(report.weaknesses, list)
    assert report.sales_battlecard is not None
