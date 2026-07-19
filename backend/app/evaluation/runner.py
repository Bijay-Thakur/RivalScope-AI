import asyncio
import logging
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
from app.observability.tracing import traceable
from app.schemas.report import CompetitorReport
from app.schemas.research import ReportType, ResearchRequest

logger = logging.getLogger(__name__)

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
        source_text = (item.raw_text or src.snippet or "").strip()
        if not source_text:
            # Honest: cited source has no text to judge against.
            verdicts[i] = ClaimVerdict(
                claim=item.claim,
                source_id=item.source_id,
                self_confidence=item.confidence,
                verdict=Verdict.CITATION_INVALID,
                rationale="empty source text (raw_text and snippet both empty)",
                judge_confidence=1.0,
            )
            continue
        judge_idx.append(i)
        judge_items.append(
            {
                "claim": item.claim,
                "source_title": src.title,
                "source_url": src.url,
                "source_text": source_text,
            }
        )

    if judge_items:
        judged = await judge_claims(
            judge_items, model=judge_model, max_concurrency=concurrency
        )
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
    """Return grounded fraction over successfully judged cells; None if none judged."""
    matrix = report.comparison_matrix
    if matrix is None or not matrix.rows:
        return None

    source_map = {s.id: s for s in report.sources}
    # Prefer full extract text from evidence citing that source (not just snippet).
    raw_by_source: dict[str, str] = {}
    for ev in report.evidence:
        text = (ev.raw_text or "").strip()
        if text and (
            ev.source_id not in raw_by_source
            or len(text) > len(raw_by_source[ev.source_id])
        ):
            raw_by_source[ev.source_id] = text

    def _src_text(ids: list[str]) -> str:
        chunks: list[str] = []
        for i in ids:
            if i not in source_map:
                continue
            body = raw_by_source.get(i) or source_map[i].snippet or source_map[i].title
            if body:
                chunks.append(body)
        return "\n".join(chunks)

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
    ok = [(v, r, c) for v, r, c in judged if v != Verdict.ERROR]
    if not ok:
        return None
    grounded = sum(1 for verdict, _, _ in ok if verdict in _GROUNDED)
    return grounded / len(ok)


@traceable(run_type="chain", name="benchmark_task")
async def _run_single_task(
    task: BenchmarkTask,
    *,
    experiment_name: str,
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
        score.grounding_rate = gm["grounding_rate"]  # type: ignore[assignment]
        score.hallucination_rate = gm["hallucination_rate"]  # type: ignore[assignment]
        score.n_claims_total = int(gm["n_claims_total"] or 0)
        score.n_judged_ok = int(gm["n_judged_ok"] or 0)
        score.n_judge_errors = int(gm["n_judge_errors"] or 0)
        score.n_citation_invalid = int(gm["n_citation_invalid"] or 0)
        score.comparison_grounding = await _comparison_grounding(
            final_report, judge_model, judge_concurrency
        )
        extra_notes: list[str] = [
            f"{'Contradicted' if v.verdict == Verdict.CONTRADICTED else 'Unsupported'} claim: {v.claim[:80]}"
            for v in verdicts
            if v.verdict in {Verdict.CONTRADICTED, Verdict.UNSUPPORTED}
        ]
        if score.n_judge_errors:
            extra_notes.append(
                f"Judge errors: {score.n_judge_errors}/{score.n_claims_total} claims"
            )
        if score.n_judged_ok == 0 and score.n_claims_total > 0:
            extra_notes.append(
                "GROUNDING UNRELIABLE: judge produced 0 valid verdicts"
            )
        score.failure_notes = score.failure_notes + extra_notes

    return score


def _avg(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    if not present:
        return None
    return sum(present) / len(present)


@traceable(run_type="chain", name="evaluation_experiment")
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
    judge_concurrency = settings.judge_max_concurrency
    semaphore = asyncio.Semaphore(task_concurrency)

    async def _bounded(task: BenchmarkTask) -> TaskScore:
        async with semaphore:
            return await _run_single_task(
                task,
                experiment_name=experiment_name,
                mode=mode,
                judge_model=judge_model,
                judge_concurrency=judge_concurrency,
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
            langsmith_tracing=settings.langsmith_tracing,
            langsmith_project=settings.langsmith_project if settings.langsmith_tracing else None,
            total_tasks=0,
            average_score=0.0,
            average_latency_seconds=0.0,
            average_source_count=0.0,
            task_scores=[],
        )

    n_claims_total = sum(s.n_claims_total or 0 for s in task_scores)
    n_judged_ok = sum(s.n_judged_ok or 0 for s in task_scores)
    n_judge_errors = sum(s.n_judge_errors or 0 for s in task_scores)
    n_citation_invalid = sum(s.n_citation_invalid or 0 for s in task_scores)
    grounding_unreliable = mode == FULL and (
        n_judge_errors > 0 or (n_claims_total > 0 and n_judged_ok == 0)
    )
    if grounding_unreliable:
        logger.error(
            "GROUNDING UNRELIABLE: judge produced %d valid verdicts / %d errors "
            "(claims_total=%d citation_invalid=%d)",
            n_judged_ok,
            n_judge_errors,
            n_claims_total,
            n_citation_invalid,
        )

    return ExperimentResult(
        experiment_name=experiment_name,
        model_provider=settings.primary_llm_provider,
        research_mode=settings.research_mode,
        eval_mode=mode,
        judge_model=judge_model if mode == FULL else None,
        langsmith_tracing=settings.langsmith_tracing,
        langsmith_project=settings.langsmith_project if settings.langsmith_tracing else None,
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
        n_claims_total=n_claims_total,
        n_judged_ok=n_judged_ok,
        n_judge_errors=n_judge_errors,
        n_citation_invalid=n_citation_invalid,
        grounding_unreliable=grounding_unreliable,
        task_scores=task_scores,
    )
