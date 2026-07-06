import pytest

from app.core.config import settings
from app.graph.constants import TOTAL_STEPS
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


async def test_run_research_graph_produces_report():
    request = ResearchRequest(
        **_BASE_REQUEST,
        report_type=ReportType.SALES_BATTLECARD,
    )
    state = await run_research_graph(request)

    assert state["final_report"] is not None
    assert len(state["research_plan"]) >= 4
    assert len(state["evidence"]) > 0
    assert state["final_report"].confidence_score is not None


async def test_mock_graph_produces_four_research_tasks():
    request = ResearchRequest(**_BASE_REQUEST, report_type=ReportType.QUICK_BRIEF)
    state = await run_research_graph(request)

    tracks = {t.track for t in state["research_plan"]}
    assert tracks == {"company_profile", "product_features", "pricing", "recent_news"}


async def test_mock_graph_populates_sources_and_evidence():
    request = ResearchRequest(**_BASE_REQUEST, report_type=ReportType.DEEP_RESEARCH)
    state = await run_research_graph(request)

    assert len(state["sources"]) > 0
    assert len(state["evidence"]) > 0
    # Verify every evidence item references an existing source id.
    source_ids = {s.id for s in state["sources"]}
    for item in state["evidence"]:
        assert item.source_id in source_ids


async def test_mock_graph_produces_verified_claims():
    request = ResearchRequest(**_BASE_REQUEST, report_type=ReportType.QUICK_BRIEF)
    state = await run_research_graph(request)

    assert len(state["verified_claims"]) > 0
    for claim in state["verified_claims"]:
        assert claim.verification_status == "mock_verified"
        assert 0.0 <= claim.confidence_score <= 1.0


async def test_mock_report_has_required_fields():
    request = ResearchRequest(**_BASE_REQUEST, report_type=ReportType.SALES_BATTLECARD)
    state = await run_research_graph(request)

    report = state["final_report"]
    assert report.company_snapshot
    assert report.product_positioning
    assert isinstance(report.feature_comparison, list)
    assert report.pricing_intelligence
    assert isinstance(report.strengths, list)
    assert isinstance(report.weaknesses, list)
    assert report.sales_battlecard is not None


async def test_parallel_tracks_append_without_loss_or_duplication():
    """Regression: workflow.py used to slice list-deltas by comparing against a stale
    base state, which could duplicate or drop items from parallel track branches."""
    request = ResearchRequest(**_BASE_REQUEST, report_type=ReportType.DEEP_RESEARCH)
    state = await run_research_graph(request)

    assert len(state["progress_events"]) == TOTAL_STEPS
    assert len(state["progress_events"]) == len({(e.step, e.name) for e in state["progress_events"]})

    # exactly one mock source/evidence item per track (4 tracks) — no dupes, no loss.
    assert len(state["sources"]) == 4
    assert len(state["evidence"]) == 4
    assert len(state["sources"]) == len({s.id for s in state["sources"]})


async def test_comparison_agent_node_populates_matrix():
    request = ResearchRequest(**_BASE_REQUEST, report_type=ReportType.QUICK_BRIEF)
    state = await run_research_graph(request)

    matrix = state["comparison_matrix"]
    assert matrix is not None
    assert len(matrix.rows) >= 1
    # matrix attached to final report on the wire.
    assert state["final_report"].comparison_matrix is not None


async def test_comparison_agent_runs_between_fact_checker_and_report():
    from app.graph.constants import PROGRESS_STEP_LABELS

    fc = PROGRESS_STEP_LABELS.index("fact_checker_stub")
    cmp_ = PROGRESS_STEP_LABELS.index("comparison_agent")
    rpt = PROGRESS_STEP_LABELS.index("report_generator")
    assert fc < cmp_ < rpt

    request = ResearchRequest(**_BASE_REQUEST, report_type=ReportType.QUICK_BRIEF)
    state = await run_research_graph(request)
    names = [e.name for e in sorted(state["progress_events"], key=lambda e: e.step)]
    assert names.index("fact_checker_stub") < names.index("comparison_agent") < names.index("report_generator")


async def test_feature_comparison_from_matrix_in_mock_report():
    request = ResearchRequest(**_BASE_REQUEST, report_type=ReportType.QUICK_BRIEF)
    state = await run_research_graph(request)
    report = state["final_report"]
    # mock report's featureComparison stays its own list; matrix is attached separately.
    assert report.comparison_matrix is not None
    assert len(report.comparison_matrix.rows) >= 1
