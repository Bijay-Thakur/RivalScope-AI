import csv
import json
from collections import Counter
from pathlib import Path

from app.evaluation.failure_analysis import generate_failure_mode_report
from app.evaluation.schemas import ExperimentResult

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = BACKEND_DIR.parent
DEFAULT_OUTPUT_DIR = "backend/eval_results"

TASK_SCORE_CSV_FIELDS = (
    "task_id",
    "overall_score",
    "task_completion",
    "section_coverage",
    "source_coverage",
    "citation_integrity",
    "comparison_two_sidedness",
    "comparison_citation_validity",
    "grounding_rate",
    "hallucination_rate",
    "comparison_grounding",
    "evidence_count",
    "source_count",
    "latency_seconds",
    "warnings_count",
    "failure_notes",
)


def _fmt(value: float | None) -> str:
    return f"{value:.4f}" if value is not None else ""


def _resolve_output_dir(output_dir: str) -> Path:
    path = Path(output_dir)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _safe_experiment_filename(experiment_name: str) -> str:
    sanitized = experiment_name.strip().replace("/", "_").replace("\\", "_")
    return sanitized or "experiment"


def _write_json(result: ExperimentResult, output_path: Path) -> Path:
    json_path = output_path / f"{_safe_experiment_filename(result.experiment_name)}.json"
    json_path.write_text(
        json.dumps(result.model_dump(), indent=2),
        encoding="utf-8",
    )
    return json_path


def _write_csv(result: ExperimentResult, output_path: Path) -> Path:
    csv_path = output_path / f"{_safe_experiment_filename(result.experiment_name)}.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=TASK_SCORE_CSV_FIELDS)
        writer.writeheader()
        for task_score in result.task_scores:
            writer.writerow(
                {
                    "task_id": task_score.task_id,
                    "overall_score": f"{task_score.overall_score:.4f}",
                    "task_completion": f"{task_score.task_completion:.4f}",
                    "section_coverage": f"{task_score.section_coverage:.4f}",
                    "source_coverage": f"{task_score.source_coverage:.4f}",
                    "citation_integrity": f"{task_score.citation_integrity:.4f}",
                    "comparison_two_sidedness": _fmt(task_score.comparison_two_sidedness),
                    "comparison_citation_validity": _fmt(task_score.comparison_citation_validity),
                    "grounding_rate": _fmt(task_score.grounding_rate),
                    "hallucination_rate": _fmt(task_score.hallucination_rate),
                    "comparison_grounding": _fmt(task_score.comparison_grounding),
                    "evidence_count": task_score.evidence_count,
                    "source_count": task_score.source_count,
                    "latency_seconds": f"{task_score.latency_seconds:.2f}",
                    "warnings_count": task_score.warnings_count,
                    "failure_notes": " | ".join(task_score.failure_notes),
                }
            )
    return csv_path


def _top_failure_notes(result: ExperimentResult, limit: int = 10) -> list[tuple[str, int]]:
    counts = Counter(
        note
        for task_score in result.task_scores
        for note in task_score.failure_notes
        if note.strip()
    )
    return counts.most_common(limit)


def _write_markdown_summary(result: ExperimentResult, output_path: Path) -> Path:
    summary_path = (
        output_path / f"{_safe_experiment_filename(result.experiment_name)}_summary.md"
    )

    def _pct(value: float | None) -> str:
        if value is None:
            return "n/a"
        return f"{value:.1%}"

    lines = [
        f"# Experiment Summary: {result.experiment_name}",
        "",
        "## Overview",
        "",
        f"- **Experiment name:** {result.experiment_name}",
        f"- **Model provider:** {result.model_provider}",
        f"- **Research mode:** {result.research_mode}",
        f"- **Eval mode:** {result.eval_mode}",
        f"- **Judge model:** {result.judge_model or 'n/a (structural mode)'}",
        f"- **LangSmith tracing:** {'on' if result.langsmith_tracing else 'off'}",
        f"- **LangSmith project:** {result.langsmith_project or 'n/a'}",
        f"- **Total tasks:** {result.total_tasks}",
        f"- **Average score:** {result.average_score:.4f}",
        f"- **Average latency (s):** {result.average_latency_seconds:.2f}",
        f"- **Average source count:** {result.average_source_count:.2f}",
        "",
    ]

    if result.eval_mode == "full":
        lines.extend(
            [
                "## Judge Observability",
                "",
                f"- **n_claims_total:** {result.n_claims_total}",
                f"- **n_judged_ok:** {result.n_judged_ok}",
                f"- **n_judge_errors:** {result.n_judge_errors}",
                f"- **n_citation_invalid:** {result.n_citation_invalid}",
                "",
            ]
        )
        if result.grounding_unreliable:
            lines.extend(
                [
                    "> **GROUNDING UNRELIABLE:** judge produced "
                    f"{result.n_judged_ok} valid verdicts / {result.n_judge_errors} errors "
                    f"(claims_total={result.n_claims_total}). "
                    "Do NOT treat grounding_rate=0 as a clean result.",
                    "",
                ]
            )

    lines.extend(
        [
            "## Observability",
            "",
            "When LangSmith tracing is enabled (`LANGSMITH_TRACING=true` in `backend/.env`), "
            "each benchmark task appears as a trace in the LangSmith project above. "
            "Open [smith.langchain.com](https://smith.langchain.com) → **Traces** and filter by "
            f"project `{result.langsmith_project or 'rivalscope-ai'}`.",
            "",
            "Trace hierarchy per task:",
            "",
            "- `evaluation_experiment` — full benchmark run",
            "- `benchmark_task` — single competitor pair",
            "- `research_graph` — LangGraph workflow",
            "- Graph nodes: `normalize_input`, `create_research_plan`, `company_profile_track`, "
            "`product_track`, `pricing_track`, `news_track`, `fact_checker_stub`, "
            "`comparison_agent`, `report_generator`",
            "- Tools: `search_web`, `extract_urls` (real mode)",
            "- LLM spans: `fact_checker_llm`, `comparison_agent_llm`, `report_generator_llm`",
            "",
            "## Headline Metrics",
            "",
            f"- **Comparison two-sidedness:** {_pct(result.avg_comparison_two_sidedness)} "
            "(share of matrix rows with BOTH sides filled — measures the one-sided bug)",
            f"- **Comparison citation validity:** {_pct(result.avg_comparison_citation_validity)}",
            f"- **Claim grounding rate:** {_pct(result.avg_grounding_rate)}",
            f"- **Hallucination rate:** {_pct(result.avg_hallucination_rate)}",
            f"- **Comparison grounding:** {_pct(result.avg_comparison_grounding)}",
            "",
            "## Task Scores",
            "",
            "| Task ID | Overall | Completion | Sections | Sources | Citations | Evidence | Sources | Latency (s) | Warnings |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for task_score in result.task_scores:
        lines.append(
            "| {task_id} | {overall:.4f} | {completion:.4f} | {sections:.4f} | "
            "{sources_cov:.4f} | {citations:.4f} | {evidence} | {sources} | "
            "{latency:.2f} | {warnings} |".format(
                task_id=task_score.task_id,
                overall=task_score.overall_score,
                completion=task_score.task_completion,
                sections=task_score.section_coverage,
                sources_cov=task_score.source_coverage,
                citations=task_score.citation_integrity,
                evidence=task_score.evidence_count,
                sources=task_score.source_count,
                latency=task_score.latency_seconds,
                warnings=task_score.warnings_count,
            )
        )

    lines.extend(["", "## Top Failure Notes", ""])

    top_notes = _top_failure_notes(result)
    if top_notes:
        for note, count in top_notes:
            lines.append(f"- ({count}) {note}")
    else:
        lines.append("- None")

    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_path


def write_experiment_results(
    result: ExperimentResult,
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> dict[str, str]:
    output_path = _resolve_output_dir(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    json_path = _write_json(result, output_path)
    csv_path = _write_csv(result, output_path)
    markdown_path = _write_markdown_summary(result, output_path)
    failure_modes_path = generate_failure_mode_report(
        result,
        str(
            output_path
            / f"{_safe_experiment_filename(result.experiment_name)}_failure_modes.md"
        ),
    )

    return {
        "json": str(json_path),
        "csv": str(csv_path),
        "markdown": str(markdown_path),
        "failure_modes": failure_modes_path,
    }
