import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.logging import get_logger
from app.graph.workflow import run_research_graph
from app.schemas.research import ReportType, ResearchRequest, ResearchResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/api/research", tags=["research"])

_REAL_MODE_MISSING_KEYS_MSG = (
    "Real research mode requires TAVILY_API_KEY and at least one LLM key."
)


def _check_real_mode_keys() -> None:
    if not settings.is_real_research_enabled:
        return
    if not settings.has_tavily_key or not (settings.has_groq_key or settings.has_gemini_key):
        raise HTTPException(status_code=400, detail=_REAL_MODE_MISSING_KEYS_MSG)

_STREAM_DELAY_SECONDS = 0.25


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


async def _research_stream_events(
    request: ResearchRequest,
) -> AsyncIterator[str]:
    try:
        _check_real_mode_keys()
    except HTTPException as exc:
        yield f"event: error\ndata: {json.dumps({'detail': exc.detail})}\n\n"
        return
    try:
        final_state = await run_research_graph(request)
    except Exception:
        logger.exception("Research stream workflow failed")
        yield (
            "event: error\n"
            f"data: {json.dumps({'detail': 'Research workflow failed'})}\n\n"
        )
        return

    for progress in final_state.get("progress_events", []):
        payload = progress.model_dump(by_alias=True, mode="json")
        yield f"event: progress\ndata: {json.dumps(payload)}\n\n"
        await asyncio.sleep(_STREAM_DELAY_SECONDS)

    report = final_state.get("final_report")
    if report is None:
        yield (
            "event: error\n"
            f"data: {json.dumps({'detail': 'No report generated'})}\n\n"
        )
        return

    report_payload = report.model_dump(by_alias=True, mode="json")
    yield f"event: final_report\ndata: {json.dumps(report_payload)}\n\n"


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
