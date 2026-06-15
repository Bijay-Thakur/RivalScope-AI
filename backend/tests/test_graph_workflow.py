from app.graph.workflow import run_research_graph
from app.schemas.research import ReportType, ResearchRequest


def test_run_research_graph_produces_report():
    request = ResearchRequest(
        our_company="ClickUp",
        competitor="Notion",
        market="Project management / docs",
        report_type=ReportType.SALES_BATTLECARD,
    )

    state = run_research_graph(request)

    assert state["final_report"] is not None
    assert len(state["research_plan"]) >= 4
    assert len(state["evidence"]) > 0
    assert state["final_report"].confidence_score is not None
