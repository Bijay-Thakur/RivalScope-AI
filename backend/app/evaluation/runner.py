import asyncio
import time

from app.core.config import settings
from app.evaluation.judge import judge_claims
from app.evaluation.loader import load_benchmark_tasks
from app.evaluation.schemas import (
    BenchmarkTask,
    ClaimVerdict,
    ExperimentResult,
    TaskScore,
    Verdict,
)
from app.evaluation.scorers import grounding_metrics, score_report
from app.graph.workflow import run_research_graph
from app.schemas.report import CompetitorReport
from app.schemas.research import ReportType, ResearchRequest

STRUCTURAL = "structural"
FULL = "full"

_GROUNDED = {Verdict.SUPPORTED, Verdict.PARTIAL}


def _benchmark_task_to_request(task: BenchmarkTask) -> ResearchRequest:
    return ResearchRequest(
        our_company=task.our_company,
        competitor=task.competitor,
        market=task.market,
        report_type=ReportType(task.report_type),
    )


def _failed_task_score(
    task: BenchmarkTask,
    latency_seconds: float,
    warnings_count: int,
    failure_notes: list[str],
) -> TaskScore:
    return TaskScore(
        task_id=task.id,
        task_completion=0.0,
        section_coverage=0.0,
        source_coverage=0.0,
        citation_integrity=0.0,
        evidence_count=0,
        source_count=0,
        latency_seconds=latency_seconds,
        warnings_count=warnings_count,
        overall_score=0.0,
        failure_notes=failure_notes,
    )


# ---------------------------------------------------------------------------
# Grounding (LLM-judge) — only invoked in --mode full
# ---------------------------------------------------------------------------

async def _evidence_verdicts(
    report: CompetitorReport, judge_model: str, concurrency: int
) -> list[ClaimVerdict]:
    source_map = {s.id: s for s in report.sources}
    verdicts: list[ClaimVerdict | None] = [None] * len(report.evidence)
    judge_idx: list[int] = []
    judge_items: list[dict] = []

    for i, item in enumerate(report.evidence):
        src = source_map.get(item.source_id)
        if src is None:
            verdicts[i] = ClaimVerdict(
                claim=item.claim,
                source_id=item.source_id,
                self_confidence=item.confidence,
                verdict=Verdict.CITATION_INVALID,
                rationale="source_id not found among report sources",
                judge_confidence=1.0,
            )
            continue
        judge_idx.append(i)
        judge_items.append(
            {
                "claim": item.claim,
                "source_title": src.title,
                "source_url": src.url,
                "source_text": item.raw_text or src.snippet or "",
            }
        )

    judged = await judge_claims(judge_items, model=judge_model, max_concurrency=concurrency)
    for idx, (verdict, rationale, jc) in zip(judge_idx, judged):
        item = report.evidence[idx]
        verdicts[idx] = ClaimVerdict(
            claim=item.claim,
            source_id=item.source_id,
            self_confidence=item.confidence,
            verdict=verdict,
            rationale=rationale,
            judge_confidence=jc,
        )
    return [v for v in verdicts if v is not None]


async def _comparison_grounding(
    report: CompetitorReport, judge_model: str, concurrency: int
) -> float | None:
    matrix = report.comparison_matrix
    if matrix is None or not matrix.rows:
        return None

    source_map = {s.id: s for s in report.sources}

    def _src_text(ids: list[str]) -> str:
        return "\n".join(
            source_map[i].snippet or source_map[i].title
            for i in ids
            if i in source_map and (source_map[i].snippet or source_map[i].title)
        )

    items: list[dict] = []
    for row in matrix.rows:
        for value, ids in (
            (row.our_value, row.our_source_ids),
            (row.competitor_value, row.competitor_source_ids),
        ):
            text = _src_text(ids)
            if not value or "not found in available sources" in value.lower() or not text:
                continue
            items.append(
                {"claim": value, "source_title": row.dimension, "source_url": "", "source_text": text}
            )

    if not items:
        return None

    judged = await judge_claims(items, model=judge_model, max_concurrency=concurrency)
    grounded = sum(1 for verdict, _, _ in judged if verdict in _GROUNDED)
    return grounded / len(judged)


async def _run_single_task(
    task: BenchmarkTask,
    *,
    mode: str,
    judge_model: str,
    judge_concurrency: int,
) -> TaskScore:
    request = _benchmark_task_to_request(task)
    started_at = time.perf_counter()

    try:
        state = await run_research_graph(request)
    except Exception as exc:
        latency_seconds = time.perf_counter() - started_at
        return _failed_task_score(
            task,
            latency_seconds=latency_seconds,
            warnings_count=0,
            failure_notes=[f"Research graph failed: {exc}"],
        )

    latency_seconds = time.perf_counter() - started_at
    final_report = state.get("final_report")
    errors = list(state.get("errors", []))
    warnings_count = len(errors)

    if final_report is None:
        return _failed_task_score(
            task,
            latency_seconds=latency_seconds,
            warnings_count=warnings_count,
            failure_notes=["No final report produced", *errors],
        )

    warnings_count += len(final_report.warnings)
    score = score_report(
        task,
        final_report,
        latency_seconds=latency_seconds,
        warnings_count=warnings_count,
    )

    if mode == FULL:
        verdicts = await _evidence_verdicts(final_report, judge_model, judge_concurrency)
        gm = grounding_metrics(verdicts)
        score.grounding_rate = gm["grounding_rate"]
        score.hallucination_rate = gm["hallucination_rate"]
        score.comparison_grounding = await _comparison_grounding(
            final_report, judge_model, judge_concurrency
        )
        score.failure_notes = score.failure_notes + [
            f"Contradicted claim: {v.claim[:80]}"
            for v in verdicts
            if v.verdict == Verdict.CONTRADICTED
        ]

    return score


def _avg(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    if not present:
        return None
    return sum(present) / len(present)


async def run_evaluation(
    experiment_name: str = "phase4_baseline",
    max_tasks: int | None = None,
    *,
    mode: str = STRUCTURAL,
    dataset_path: str | None = None,
    task_concurrency: int = 2,
) -> ExperimentResult:
    tasks = load_benchmark_tasks(dataset_path)
    if max_tasks is not None:
        tasks = tasks[:max_tasks]

    judge_model = settings.judge_model
    judge_concurrency = settings.eval_max_concurrency
    semaphore = asyncio.Semaphore(task_concurrency)

    async def _bounded(task: BenchmarkTask) -> TaskScore:
        async with semaphore:
            return await _run_single_task(
                task, mode=mode, judge_model=judge_model, judge_concurrency=judge_concurrency
            )

    task_scores = list(await asyncio.gather(*(_bounded(t) for t in tasks)))
    total_tasks = len(task_scores)

    if total_tasks == 0:
        return ExperimentResult(
            experiment_name=experiment_name,
            model_provider=settings.primary_llm_provider,
            research_mode=settings.research_mode,
            eval_mode=mode,
            judge_model=judge_model if mode == FULL else None,
            total_tasks=0,
            average_score=0.0,
            average_latency_seconds=0.0,
            average_source_count=0.0,
            task_scores=[],
        )

    return ExperimentResult(
        experiment_name=experiment_name,
        model_provider=settings.primary_llm_provider,
        research_mode=settings.research_mode,
        eval_mode=mode,
        judge_model=judge_model if mode == FULL else None,
        total_tasks=total_tasks,
        average_score=sum(s.overall_score for s in task_scores) / total_tasks,
        average_latency_seconds=sum(s.latency_seconds for s in task_scores) / total_tasks,
        average_source_count=sum(s.source_count for s in task_scores) / total_tasks,
        avg_comparison_two_sidedness=_avg([s.comparison_two_sidedness for s in task_scores]),
        avg_comparison_citation_validity=_avg(
            [s.comparison_citation_validity for s in task_scores]
        ),
        avg_grounding_rate=_avg([s.grounding_rate for s in task_scores]),
        avg_hallucination_rate=_avg([s.hallucination_rate for s in task_scores]),
        avg_comparison_grounding=_avg([s.comparison_grounding for s in task_scores]),
        task_scores=task_scores,
    )
