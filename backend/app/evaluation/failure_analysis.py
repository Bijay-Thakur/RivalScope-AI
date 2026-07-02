from collections import Counter
from pathlib import Path

from app.evaluation.schemas import ExperimentResult, TaskScore

_EFFICIENCY_THRESHOLDS = (
    (30, "excellent"),
    (60, "acceptable"),
    (120, "slow"),
)
_LOW_SCORE_THRESHOLD = 0.8
_WEAK_DIMENSION_THRESHOLD = 0.85


def _latency_bucket(latency_seconds: float) -> str:
    if latency_seconds <= 30:
        return "excellent (<=30s)"
    if latency_seconds <= 60:
        return "acceptable (31-60s)"
    if latency_seconds <= 120:
        return "slow (61-120s)"
    return "very slow (>120s)"


def _efficiency_score(latency_seconds: float) -> float:
    if latency_seconds <= 30:
        return 1.0
    if latency_seconds <= 60:
        return 0.7
    if latency_seconds <= 120:
        return 0.4
    return 0.1


def _average_dimension(result: ExperimentResult, field: str) -> float:
    if not result.task_scores:
        return 0.0
    return sum(getattr(score, field) for score in result.task_scores) / len(
        result.task_scores
    )


def _weakest_dimension(result: ExperimentResult) -> tuple[str, float]:
    dimensions = {
        "task_completion": _average_dimension(result, "task_completion"),
        "section_coverage": _average_dimension(result, "section_coverage"),
        "source_coverage": _average_dimension(result, "source_coverage"),
        "citation_integrity": _average_dimension(result, "citation_integrity"),
    }
    name, value = min(dimensions.items(), key=lambda item: item[1])
    return name, value


def _common_failure_notes(
    result: ExperimentResult,
    limit: int = 15,
) -> list[tuple[str, int]]:
    counts = Counter(
        note
        for task_score in result.task_scores
        for note in task_score.failure_notes
        if note.strip()
    )
    return counts.most_common(limit)


def _source_coverage_weaknesses(result: ExperimentResult) -> list[str]:
    weaknesses: list[str] = []
    for task_score in sorted(result.task_scores, key=lambda score: score.source_coverage):
        if task_score.source_coverage >= _WEAK_DIMENSION_THRESHOLD:
            continue
        missing_types = [
            note
            for note in task_score.failure_notes
            if "Expected source type" in note
        ]
        detail = (
            "; ".join(missing_types)
            if missing_types
            else "Low source-type coverage without specific notes"
        )
        weaknesses.append(
            f"- **{task_score.task_id}** — coverage {task_score.source_coverage:.2f}, "
            f"{task_score.source_count} source(s). {detail}"
        )
    return weaknesses


def _citation_integrity_issues(result: ExperimentResult) -> list[str]:
    issues: list[str] = []
    for task_score in sorted(result.task_scores, key=lambda score: score.citation_integrity):
        if task_score.citation_integrity >= 1.0:
            continue
        citation_notes = [
            note
            for note in task_score.failure_notes
            if any(
                keyword in note.lower()
                for keyword in ("source_id", "url", "evidence", "source '")
            )
        ]
        detail = (
            "; ".join(citation_notes)
            if citation_notes
            else "Citation integrity below perfect with no detailed notes"
        )
        issues.append(
            f"- **{task_score.task_id}** — integrity {task_score.citation_integrity:.2f}. "
            f"{detail}"
        )
    return issues


def _latency_issues(result: ExperimentResult) -> list[str]:
    issues: list[str] = []
    for task_score in sorted(
        result.task_scores,
        key=lambda score: score.latency_seconds,
        reverse=True,
    ):
        if task_score.latency_seconds <= 30:
            continue
        issues.append(
            f"- **{task_score.task_id}** — {task_score.latency_seconds:.2f}s "
            f"({_latency_bucket(task_score.latency_seconds)}), "
            f"efficiency score {_efficiency_score(task_score.latency_seconds):.1f}"
        )
    return issues


def _recommended_fixes(
    result: ExperimentResult,
    weakest_dimension: str,
    common_notes: list[tuple[str, int]],
) -> list[str]:
    fixes: list[str] = []

    if weakest_dimension == "source_coverage":
        fixes.append(
            "Expand track-specific query templates and source-type detection to "
            "capture company, pricing, docs, and news pages more reliably."
        )
    elif weakest_dimension == "citation_integrity":
        fixes.append(
            "Tighten evidence-to-source linking in the evidence builder and reject "
            "items that reference missing sources or URLs before report generation."
        )
    elif weakest_dimension == "section_coverage":
        fixes.append(
            "Add post-generation validation that fills or flags empty required "
            "sections before returning the final report."
        )
    elif weakest_dimension == "task_completion":
        fixes.append(
            "Strengthen report schema enforcement and fallback synthesis so major "
            "report fields are always populated from collected evidence."
        )

    note_text = " ".join(note for note, _count in common_notes).lower()
    if "expected source type" in note_text:
        fixes.append(
            "Improve URL/title heuristics in `detect_source_type` and add "
            "track-level source_type overrides for pricing and news queries."
        )
    if "missing or empty url" in note_text or "source_id" in note_text:
        fixes.append(
            "Filter search results without valid URLs before evidence creation "
            "and add a pre-report citation audit step."
        )
    if "missing or empty" in note_text and "section" in note_text:
        fixes.append(
            "Map benchmark expected sections to report fields and add targeted "
            "prompt instructions for consistently empty sections."
        )
    if result.average_latency_seconds > 60:
        fixes.append(
            "Reduce `max_results_per_query`, parallelize tracks carefully, and "
            "cache repeated search queries across benchmark tasks."
        )
    if any(score.overall_score == 0.0 for score in result.task_scores):
        fixes.append(
            "Add preflight key validation and clearer per-task error recovery so "
            "failed graph runs still return partial scores where possible."
        )
    if result.average_score >= 0.9 and not common_notes:
        fixes.append(
            "Current failure modes are minor — focus next phase on fact-level "
            "accuracy scoring and LLM-as-judge evaluation."
        )
    if not fixes:
        fixes.append(
            "Review lowest-scoring tasks manually and add targeted benchmark "
            "cases for any category that underperformed."
        )

    deduped: list[str] = []
    for fix in fixes:
        if fix not in deduped:
            deduped.append(fix)
    return deduped


def generate_failure_mode_report(result: ExperimentResult, output_path: str) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    weakest_dimension, weakest_value = _weakest_dimension(result)
    common_notes = _common_failure_notes(result)
    lowest_tasks = sorted(result.task_scores, key=lambda score: score.overall_score)[:5]
    source_weaknesses = _source_coverage_weaknesses(result)
    citation_issues = _citation_integrity_issues(result)
    latency_issues = _latency_issues(result)
    recommendations = _recommended_fixes(result, weakest_dimension, common_notes)

    failed_task_count = sum(
        1 for score in result.task_scores if score.overall_score < _LOW_SCORE_THRESHOLD
    )

    lines = [
        f"# Failure Mode Report: {result.experiment_name}",
        "",
        "## 1. Executive Summary",
        "",
        f"This experiment ran **{result.total_tasks}** task(s) in "
        f"**{result.research_mode}** mode using **{result.model_provider}**.",
        f"The average overall score was **{result.average_score:.4f}** with mean latency "
        f"of **{result.average_latency_seconds:.2f}s** and "
        f"**{result.average_source_count:.2f}** sources per task.",
        "",
        f"- Tasks below {_LOW_SCORE_THRESHOLD:.0%} overall score: **{failed_task_count}**",
        f"- Weakest average dimension: **{weakest_dimension}** ({weakest_value:.4f})",
        f"- Distinct failure notes: **{len(common_notes)}**",
        "",
        "## 2. Lowest Scoring Tasks",
        "",
    ]

    if lowest_tasks:
        lines.extend(
            [
                "| Task ID | Overall | Source Cov. | Citation | Latency (s) | Warnings |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for task_score in lowest_tasks:
            lines.append(
                f"| {task_score.task_id} | {task_score.overall_score:.4f} | "
                f"{task_score.source_coverage:.4f} | "
                f"{task_score.citation_integrity:.4f} | "
                f"{task_score.latency_seconds:.2f} | {task_score.warnings_count} |"
            )
    else:
        lines.append("- No task scores available.")

    lines.extend(["", "## 3. Common Failure Notes", ""])
    if common_notes:
        for note, count in common_notes:
            lines.append(f"- ({count}) {note}")
    else:
        lines.append("- No failure notes recorded.")

    lines.extend(["", "## 4. Source Coverage Weaknesses", ""])
    if source_weaknesses:
        lines.extend(source_weaknesses)
    else:
        lines.append("- No significant source coverage weaknesses detected.")

    lines.extend(["", "## 5. Citation Integrity Issues", ""])
    if citation_issues:
        lines.extend(citation_issues)
    else:
        lines.append("- No citation integrity issues detected.")

    lines.extend(["", "## 6. Latency / Efficiency Issues", ""])
    if latency_issues:
        lines.extend(latency_issues)
    else:
        lines.append("- All tasks completed within the 30s efficiency target.")

    lines.extend(["", "## 7. Recommended Fixes for Next Phase", ""])
    for index, fix in enumerate(recommendations, start=1):
        lines.append(f"{index}. {fix}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path.resolve())
