import time
import uuid
from typing import cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.graph import nodes
from app.graph.constants import TOTAL_STEPS
from app.graph.state import RivalScopeState
from app.core.logging import get_logger, write_run_log
from app.db import repository
from app.observability import trace_buffer
from app.observability.metrics import compute_run_metrics
from app.observability.tracing import traceable
from app.schemas.research import ResearchRequest

logger = get_logger(__name__)


def build_research_graph() -> CompiledStateGraph:
    builder = StateGraph(RivalScopeState)

    builder.add_node("normalize_input", nodes.normalize_input)
    builder.add_node("create_research_plan", nodes.create_research_plan)
    builder.add_node("company_profile_track", nodes.company_profile_track)
    builder.add_node("product_track", nodes.product_track)
    builder.add_node("pricing_track", nodes.pricing_track)
    builder.add_node("news_track", nodes.news_track)
    builder.add_node("fact_checker_stub", nodes.fact_checker_stub)
    builder.add_node("comparison_agent", nodes.comparison_agent)
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
    builder.add_edge("fact_checker_stub", "comparison_agent")
    builder.add_edge("comparison_agent", "report_generator")
    builder.add_edge("report_generator", END)

    return builder.compile()


def _request_payload(request: ResearchRequest) -> dict:
    return {
        "ourCompany": request.our_company,
        "competitor": request.competitor,
        "market": request.market,
        "reportType": request.report_type.value,
    }


def log_graph_completed(run_id: str, state: RivalScopeState) -> None:
    """Emit graph_completed + run_metrics logs. Shared by sync + streaming paths."""
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
    write_run_log(run_id, "run_metrics", compute_run_metrics(state))


def initial_state_for(request: ResearchRequest) -> RivalScopeState:
    """Fresh graph state. Shared by the sync (ainvoke) + streaming (astream_events) paths."""
    run_id = str(uuid.uuid4())
    trace_buffer.start_run(run_id)
    return {
        "run_id": run_id,
        "request": request,
        "current_step": "pending",
        "progress_events": [],
        "research_plan": [],
        "evidence": [],
        "sources": [],
        "verified_claims": [],
        "comparison_matrix": None,
        "final_report": None,
        "errors": [],
        "traces": [],
    }


def persist_run(
    run_id: str,
    request: ResearchRequest,
    state: RivalScopeState,
    traces: list[dict],
    *,
    status: str,
    duration_ms: float | None = None,
) -> None:
    """Best-effort persistence of a run + its tool-use traces to SQLite. Shared by
    the sync and streaming paths; never raises into the request path."""
    try:
        metrics = compute_run_metrics(state)
        report = state.get("final_report")
        report_json = (
            report.model_dump(by_alias=True, mode="json") if report is not None else None
        )
        repository.save_run(
            run_id=run_id,
            our_company=request.our_company,
            competitor=request.competitor,
            market=request.market,
            report_type=request.report_type.value,
            status=status,
            research_mode=metrics.get("research_mode"),
            confidence_score=metrics.get("confidence_score"),
            source_count=metrics.get("source_count", 0),
            evidence_count=metrics.get("evidence_count", 0),
            verified_claim_count=metrics.get("verified_claim_count", 0),
            warning_count=metrics.get("warning_count", 0),
            duration_ms=duration_ms,
            report_json=report_json,
        )
        repository.save_traces(run_id, traces)
    except Exception:
        logger.exception("Failed to persist run %s", run_id)


@traceable(run_type="chain", name="research_graph")
async def run_research_graph(request: ResearchRequest) -> RivalScopeState:
    graph = build_research_graph()
    initial_state = initial_state_for(request)
    run_id = initial_state["run_id"]
    started = time.perf_counter()

    write_run_log(
        run_id,
        "run_started",
        {"request": _request_payload(request)},
    )

    try:
        final_state = await graph.ainvoke(initial_state)
        state = cast(RivalScopeState, final_state)
        duration_ms = (time.perf_counter() - started) * 1000.0
        traces = trace_buffer.pop(run_id)
        state["traces"] = traces
        log_graph_completed(run_id, state)
        persist_run(
            run_id, request, state, traces,
            status="completed" if state.get("final_report") is not None else "failed",
            duration_ms=duration_ms,
        )
        return state
    except Exception as exc:
        trace_buffer.pop(run_id)
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
