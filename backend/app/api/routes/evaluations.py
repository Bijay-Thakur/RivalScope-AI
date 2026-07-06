"""Evaluation API — run the grounding/quality benchmark and persist results."""
import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.db import repository
from app.evaluation.runner import run_evaluation

logger = get_logger(__name__)

router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])


class RunEvaluationRequest(BaseModel):
    experiment_name: str = Field(default="dashboard_run", alias="experimentName")
    max_tasks: int | None = Field(default=3, alias="maxTasks", ge=1, le=50)
    mode: str = Field(default="structural")  # "structural" | "full"

    model_config = {"populate_by_name": True}


@router.get("")
async def list_evaluations(limit: int = 25) -> dict:
    evals = await asyncio.to_thread(repository.list_evaluations, limit)
    return {"evaluations": evals}


@router.post("/run")
async def run_evaluation_endpoint(payload: RunEvaluationRequest) -> dict:
    if payload.mode not in {"structural", "full"}:
        raise HTTPException(status_code=400, detail="mode must be 'structural' or 'full'")

    logger.info(
        "Running evaluation '%s' (mode=%s, max_tasks=%s)",
        payload.experiment_name, payload.mode, payload.max_tasks,
    )
    try:
        result = await run_evaluation(
            experiment_name=payload.experiment_name,
            max_tasks=payload.max_tasks,
            mode=payload.mode,
        )
    except Exception as exc:
        logger.exception("Evaluation run failed")
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {type(exc).__name__}") from exc

    result_dict = result.model_dump()
    eval_id = await asyncio.to_thread(repository.save_evaluation, result_dict)
    return {"id": eval_id, "result": result_dict}
