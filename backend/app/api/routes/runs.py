"""Run history API — persisted research runs and their tool-use traces."""
import asyncio

from fastapi import APIRouter, HTTPException, Query

from app.core.logging import get_logger
from app.db import repository

logger = get_logger(__name__)

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("")
async def list_runs(limit: int = Query(50, ge=1, le=200)) -> dict:
    runs = await asyncio.to_thread(repository.list_runs, limit)
    return {"runs": runs}


@router.get("/{run_id}")
async def get_run(run_id: str) -> dict:
    run = await asyncio.to_thread(repository.get_run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}/traces")
async def get_run_traces(run_id: str) -> dict:
    traces = await asyncio.to_thread(repository.get_traces, run_id)
    return {"runId": run_id, "traces": traces}


@router.delete("/{run_id}")
async def delete_run(run_id: str) -> dict:
    await asyncio.to_thread(repository.delete_run, run_id)
    return {"status": "deleted", "runId": run_id}
