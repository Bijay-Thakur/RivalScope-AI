"""Unified report writer surfaces headline metrics. No API, tmp output."""

from app.evaluation.report_writer import write_experiment_results
from app.evaluation.schemas import ExperimentResult, TaskScore


def _task_score(task_id: str) -> TaskScore:
    return TaskScore(
        task_id=task_id,
        task_completion=1.0,
        section_coverage=1.0,
        source_coverage=1.0,
        citation_integrity=1.0,
        evidence_count=4,
        source_count=4,
        latency_seconds=12.0,
        warnings_count=0,
        overall_score=0.95,
        failure_notes=["One-sided comparison row: 'Pricing'"],
        comparison_two_sidedness=0.5,
        comparison_citation_validity=1.0,
        advantage_distribution={"our": 1, "parity": 1},
        grounding_rate=0.8,
        hallucination_rate=0.1,
        comparison_grounding=0.75,
    )


def _result() -> ExperimentResult:
    scores = [_task_score("task-001"), _task_score("task-002")]
    return ExperimentResult(
        experiment_name="unit_writer",
        model_provider="groq",
        research_mode="mock",
        eval_mode="full",
        judge_model="gemini-2.5-pro",
        total_tasks=2,
        average_score=0.95,
        average_latency_seconds=12.0,
        average_source_count=4.0,
        avg_comparison_two_sidedness=0.5,
        avg_comparison_citation_validity=1.0,
        avg_grounding_rate=0.8,
        avg_hallucination_rate=0.1,
        avg_comparison_grounding=0.75,
        task_scores=scores,
    )


def test_unified_md_contains_headline_metrics(tmp_path):
    paths = write_experiment_results(_result(), output_dir=str(tmp_path))

    md = open(paths["markdown"], encoding="utf-8").read()
    assert "Headline Metrics" in md
    assert "Observability" in md
    assert "LangSmith tracing" in md
    assert "Comparison two-sidedness" in md
    assert "Hallucination rate" in md
    assert "Claim grounding rate" in md
    assert "Judge Observability" in md

    csv_text = open(paths["csv"], encoding="utf-8").read()
    assert "comparison_two_sidedness" in csv_text
    assert "grounding_rate" in csv_text

    # failure analysis surfaces the comparison-matrix failure mode
    fm = open(paths["failure_modes"], encoding="utf-8").read()
    assert "Comparison Matrix Issues" in fm
    assert "One-sided comparison row" in fm


def test_md_loud_warning_when_grounding_unreliable(tmp_path):
    result = _result()
    result.grounding_unreliable = True
    result.n_judged_ok = 0
    result.n_judge_errors = 10
    result.n_claims_total = 10
    result.avg_grounding_rate = None
    paths = write_experiment_results(result, output_dir=str(tmp_path))
    md = open(paths["markdown"], encoding="utf-8").read()
    assert "GROUNDING UNRELIABLE" in md
    assert "n/a" in md  # null grounding rendered as n/a
