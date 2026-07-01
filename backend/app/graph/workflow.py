import uuid
from typing import Any, cast

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.graph import nodes
from app.graph.constants import TOTAL_STEPS
from app.graph.state import RivalScopeState
from app.core.logging import write_run_log
from app.schemas.research import ResearchRequest

_LIST_DELTA_FIELDS = ("progress_events", "sources", "evidence", "errors", "verified_claims")


def _list_delta(state: RivalScopeState, patch: dict[str, Any], field: str) -> list[Any]:
    updated = patch.get(field)
    if updated is None:
        return []
    base_len = len(state.get(field, []))
    if len(updated) <= base_len:
        return list(updated)
    return list(updated[base_len:])


def _as_graph_update(
    state: RivalScopeState,
    patch: dict[str, Any],
) -> dict[str, Any]:
    """Return partial state with list fields as deltas for LangGraph reducers."""
    result = {
        key: value
        for key, value in patch.items()
        if key not in _LIST_DELTA_FIELDS
    }
    for field in _LIST_DELTA_FIELDS:
        delta = _list_delta(state, patch, field)
        if delta:
            result[field] = delta
    return result


def _wrap_node(node_fn):
    def wrapped(state: RivalScopeState) -> dict[str, Any]:
        return _as_graph_update(state, node_fn(state))

    return wrapped


def build_research_graph() -> CompiledStateGraph:
    builder = StateGraph(RivalScopeState)

    builder.add_node("normalize_input", _wrap_node(nodes.normalize_input))
    builder.add_node("create_research_plan", _wrap_node(nodes.create_research_plan))
    builder.add_node("company_profile_track", _wrap_node(nodes.company_profile_track))
    builder.add_node("product_track", _wrap_node(nodes.product_track))
    builder.add_node("pricing_track", _wrap_node(nodes.pricing_track))
    builder.add_node("news_track", _wrap_node(nodes.news_track))
    builder.add_node("fact_checker_stub", _wrap_node(nodes.fact_checker_stub))
    builder.add_node("report_generator", _wrap_node(nodes.report_generator))

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


def run_research_graph(request: ResearchRequest) -> RivalScopeState:
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
        final_state = graph.invoke(initial_state)
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


def run_workflow(research_input: ResearchRequest) -> RivalScopeState:
    """Backward-compatible entry point used by the API and tests."""
    state = run_research_graph(research_input)
    if state.get("final_report") is None:
        raise RuntimeError("Research workflow did not produce a report")
    return state


def total_steps() -> int:
    return TOTAL_STEPS
