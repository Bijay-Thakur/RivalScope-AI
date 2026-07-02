import time

from app.core.config import settings
from app.evaluation.loader import load_benchmark_tasks
from app.evaluation.schemas import BenchmarkTask, ExperimentResult, TaskScore
from app.evaluation.scorers import score_report
from app.graph.workflow import run_research_graph
from app.schemas.research import ReportType, ResearchRequest


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


def _run_single_task(task: BenchmarkTask) -> TaskScore:
    request = _benchmark_task_to_request(task)
    started_at = time.perf_counter()

    try:
        state = run_research_graph(request)
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
    return score_report(
        task,
        final_report,
        latency_seconds=latency_seconds,
        warnings_count=warnings_count,
    )


def run_evaluation(
    experiment_name: str = "phase4_baseline",
    max_tasks: int | None = None,
) -> ExperimentResult:
    tasks = load_benchmark_tasks()
    if max_tasks is not None:
        tasks = tasks[:max_tasks]

    task_scores = [_run_single_task(task) for task in tasks]
    total_tasks = len(task_scores)

    if total_tasks == 0:
        return ExperimentResult(
            experiment_name=experiment_name,
            model_provider=settings.primary_llm_provider,
            research_mode=settings.research_mode,
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
        total_tasks=total_tasks,
        average_score=sum(score.overall_score for score in task_scores) / total_tasks,
        average_latency_seconds=sum(
            score.latency_seconds for score in task_scores
        )
        / total_tasks,
        average_source_count=sum(score.source_count for score in task_scores)
        / total_tasks,
        task_scores=task_scores,
    )
