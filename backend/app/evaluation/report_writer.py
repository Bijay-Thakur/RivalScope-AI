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
    "evidence_count",
    "source_count",
    "latency_seconds",
    "warnings_count",
    "failure_notes",
)


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

    lines = [
        f"# Experiment Summary: {result.experiment_name}",
        "",
        "## Overview",
        "",
        f"- **Experiment name:** {result.experiment_name}",
        f"- **Model provider:** {result.model_provider}",
        f"- **Research mode:** {result.research_mode}",
        f"- **Total tasks:** {result.total_tasks}",
        f"- **Average score:** {result.average_score:.4f}",
        f"- **Average latency (s):** {result.average_latency_seconds:.2f}",
        f"- **Average source count:** {result.average_source_count:.2f}",
        "",
        "## Task Scores",
        "",
        "| Task ID | Overall | Completion | Sections | Sources | Citations | Evidence | Sources | Latency (s) | Warnings |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

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
