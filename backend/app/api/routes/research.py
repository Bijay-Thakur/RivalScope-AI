import json
import time
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.logging import get_logger, write_run_log
from app.graph.constants import PROGRESS_STEP_LABELS
from app.graph.workflow import (
    _request_payload,
    build_research_graph,
    initial_state_for,
    log_graph_completed,
    persist_run,
    run_research_graph,
)
from app.observability import trace_buffer
from app.schemas.research import ReportType, ResearchRequest, ResearchResponse

logger = get_logger(__name__)

_STEP_INDEX = {name: i + 1 for i, name in enumerate(PROGRESS_STEP_LABELS)}

router = APIRouter(prefix="/api/research", tags=["research"])

_REAL_MODE_MISSING_KEYS_MSG = (
    "Real research mode requires TAVILY_API_KEY and at least one LLM key."
)


def _check_real_mode_keys() -> None:
    if not settings.is_real_research_enabled:
        return
    if not settings.has_tavily_key or not (settings.has_groq_key or settings.has_gemini_key):
        raise HTTPException(status_code=400, detail=_REAL_MODE_MISSING_KEYS_MSG)

@router.post("", response_model=ResearchResponse)
async def create_research(payload: ResearchRequest) -> ResearchResponse:
    _check_real_mode_keys()
    logger.info(
        "Research request: %s vs %s (%s)",
        payload.our_company,
        payload.competitor,
        payload.market,
    )
    try:
        final_state = await run_research_graph(payload)
    except Exception as exc:
        logger.exception("Research workflow failed")
        raise HTTPException(status_code=500, detail="Research workflow failed") from exc

    report = final_state.get("final_report")
    if report is None:
        raise HTTPException(status_code=500, detail="No report generated")

    return ResearchResponse(report=report)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _first_message(event: dict) -> str:
    """Pull the node's emitted progress message out of its on_chain_end output delta."""
    output = (event.get("data") or {}).get("output")
    if isinstance(output, dict):
        events = output.get("progress_events") or []
        if events:
            msg = getattr(events[0], "message", None)
            if isinstance(msg, str):
                return msg
    return ""


def _chunk_text(event: dict) -> str:
    """Best-effort token delta from an on_chat_model_stream event."""
    chunk = (event.get("data") or {}).get("chunk")
    content = getattr(chunk, "content", None)
    if isinstance(content, str):
        return content
    if isinstance(content, list):  # some providers return content parts
        parts = [p.get("text", "") if isinstance(p, dict) else str(p) for p in content]
        return "".join(parts)
    return ""


async def _research_stream_events(
    request: ResearchRequest,
) -> AsyncIterator[str]:
    try:
        _check_real_mode_keys()
    except HTTPException as exc:
        yield _sse("error", {"detail": exc.detail})
        return

    graph = build_research_graph()
    state = initial_state_for(request)
    run_id = state["run_id"]
    write_run_log(run_id, "run_started", {"request": _request_payload(request)})
    started = time.perf_counter()

    root_run_id: str | None = None
    final_state: Any = None
    emitted_traces = 0

    def _drain_traces() -> list[str]:
        """Emit any tool-use traces recorded since the last drain (near-live)."""
        nonlocal emitted_traces
        out: list[str] = []
        buffered = trace_buffer.get(run_id)
        while emitted_traces < len(buffered):
            out.append(_sse("trace", buffered[emitted_traces]))
            emitted_traces += 1
        return out

    try:
        # Real-time: emit events AS nodes execute (no post-hoc replay, no artificial delay).
        async for ev in graph.astream_events(state, version="v2"):
            etype = ev.get("event")
            name = ev.get("name")

            if root_run_id is None and etype == "on_chain_start":
                root_run_id = ev.get("run_id")
            if etype == "on_chain_end" and ev.get("run_id") == root_run_id:
                final_state = (ev.get("data") or {}).get("output")

            if name in _STEP_INDEX:
                step = _STEP_INDEX[name]
                if etype == "on_chain_start":
                    yield _sse(
                        "agent_status",
                        {"runId": run_id, "step": step, "name": name, "status": "working"},
                    )
                elif etype == "on_chain_end":
                    yield _sse(
                        "agent_status",
                        {
                            "runId": run_id,
                            "step": step,
                            "name": name,
                            "status": "done",
                            "message": _first_message(ev),
                        },
                    )
            elif etype == "on_chat_model_stream":
                # Best-effort token streaming — never let its absence/failure break status.
                try:
                    node = (ev.get("metadata") or {}).get("langgraph_node")
                    if node in _STEP_INDEX:
                        delta = _chunk_text(ev)
                        if delta:
                            yield _sse(
                                "token",
                                {"step": _STEP_INDEX[node], "node": node, "delta": delta},
                            )
                except Exception:  # pragma: no cover — defensive
                    pass

            # Flush any tool-use traces (Tavily search/extract, LLM calls) recorded so far.
            for chunk in _drain_traces():
                yield chunk
    except Exception:
        logger.exception("Research stream workflow failed")
        trace_buffer.pop(run_id)
        write_run_log(
            run_id,
            "run_failed",
            {"error": "stream failed", "request": _request_payload(request)},
        )
        yield _sse("error", {"detail": "Research workflow failed"})
        return

    # Final flush of any straggler traces before we close out the run.
    for chunk in _drain_traces():
        yield chunk

    duration_ms = (time.perf_counter() - started) * 1000.0
    traces = trace_buffer.pop(run_id)

    report = final_state.get("final_report") if isinstance(final_state, dict) else None
    if report is None:
        if isinstance(final_state, dict):
            persist_run(run_id, request, final_state, traces, status="failed", duration_ms=duration_ms)
        yield _sse("error", {"detail": "No report generated"})
        return

    try:
        log_graph_completed(run_id, final_state)
    except Exception:  # pragma: no cover — logging must never break the stream
        logger.warning("graph_completed logging failed for run %s", run_id)

    persist_run(run_id, request, final_state, traces, status="completed", duration_ms=duration_ms)

    yield _sse("final_report", report.model_dump(by_alias=True, mode="json"))


@router.get("/stream")
async def stream_research(
    our_company: str = Query(...),
    competitor: str = Query(...),
    market: str = Query(...),
    report_type: ReportType = Query(...),
) -> StreamingResponse:
    logger.info(
        "Research stream: %s vs %s (%s)",
        our_company,
        competitor,
        market,
    )
    request = ResearchRequest(
        our_company=our_company,
        competitor=competitor,
        market=market,
        report_type=report_type,
    )
    return StreamingResponse(
        _research_stream_events(request),
        media_type="text/event-stream",
    )
