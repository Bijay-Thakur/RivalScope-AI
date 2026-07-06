import uuid
from typing import cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.graph import nodes
from app.graph.constants import TOTAL_STEPS
from app.graph.state import RivalScopeState
from app.core.logging import write_run_log
from app.observability.metrics import compute_run_metrics
from app.schemas.research import ResearchRequest


def build_research_graph() -> CompiledStateGraph:
    builder = StateGraph(RivalScopeState)

    builder.add_node("normalize_input", nodes.normalize_input)
    builder.add_node("create_research_plan", nodes.create_research_plan)
    builder.add_node("company_profile_track", nodes.company_profile_track)
    builder.add_node("product_track", nodes.product_track)
    builder.add_node("pricing_track", nodes.pricing_track)
    builder.add_node("news_track", nodes.news_track)
    builder.add_node("fact_checker_stub", nodes.fact_checker_stub)
    builder.add_node("report_generator", nodes.report_generator)

    builder.add_edge(START, "normalize_input")
    builder.add_edge("normalize_input", "create_research_plan")
    builder.add_edge("create_research_plan", "company_profile_track")
    builder.add_edge("create_research_plan", "product_track")
    builder.add_edge("create_research_plan", "pricing_track")
    builder.add_edge("create_research_plan", "news_track")
    builder.add_edge("company_profile_track", "fact_checker_stub")
    builder.add_edge("product_track", "fact_checker_stub")
    builder.add_edge("pricing_track", "fact_checker_stub")
    builder.add_edge("news_track", "fact_checker_stub")
    builder.add_edge("fact_checker_stub", "report_generator")
    builder.add_edge("report_generator", END)

    return builder.compile()


def _request_payload(request: ResearchRequest) -> dict:
    return {
        "ourCompany": request.our_company,
        "competitor": request.competitor,
        "market": request.market,
        "reportType": request.report_type.value,
    }


async def run_research_graph(request: ResearchRequest) -> RivalScopeState:
    graph = build_research_graph()
    initial_state: RivalScopeState = {
        "run_id": str(uuid.uuid4()),
        "request": request,
        "current_step": "pending",
        "progress_events": [],
        "research_plan": [],
        "evidence": [],
        "sources": [],
        "verified_claims": [],
        "final_report": None,
        "errors": [],
    }
    run_id = initial_state["run_id"]

    write_run_log(
        run_id,
        "run_started",
        {"request": _request_payload(request)},
    )

    try:
        final_state = await graph.ainvoke(initial_state)
        state = cast(RivalScopeState, final_state)
        final_report = state.get("final_report")
        write_run_log(
            run_id,
            "graph_completed",
            {
                "current_step": state.get("current_step"),
                "progress_event_count": len(state.get("progress_events", [])),
                "evidence_count": len(state.get("evidence", [])),
                "verified_claim_count": len(state.get("verified_claims", [])),
                "confidence_score": (
                    final_report.confidence_score if final_report is not None else None
                ),
            },
        )
        write_run_log(
            run_id,
            "run_metrics",
            compute_run_metrics(state),
        )
        return state
    except Exception as exc:
        write_run_log(
            run_id,
            "run_failed",
            {
                "error": str(exc),
                "request": _request_payload(request),
            },
        )
        raise


async def run_workflow(research_input: ResearchRequest) -> RivalScopeState:
    """Backward-compatible entry point used by the API and tests."""
    state = await run_research_graph(research_input)
    if state.get("final_report") is None:
        raise RuntimeError("Research workflow did not produce a report")
    return state


def total_steps() -> int:
    return TOTAL_STEPS
