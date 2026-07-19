from app.evaluation.schemas import BenchmarkTask, ClaimVerdict, TaskScore, Verdict
from app.schemas.report import ComparisonMatrix, CompetitorReport, SalesBattlecard

_NOT_FOUND_MARKER = "not found in available sources"

MAJOR_REPORT_FIELDS = (
    "company_snapshot",
    "product_positioning",
    "feature_comparison",
    "pricing_intelligence",
    "strengths",
    "weaknesses",
    "sales_battlecard",
    "sources",
)

SECTION_FIELD_MAP = {
    "company_snapshot": "company_snapshot",
    "product_positioning": "product_positioning",
    "feature_comparison": "feature_comparison",
    "pricing_intelligence": "pricing_intelligence",
    "recent_moves": "recent_moves",
    "strengths": "strengths",
    "weaknesses": "weaknesses",
    "sales_battlecard": "sales_battlecard",
    "sources": "sources",
}


def _is_non_empty_string(value: str | None) -> bool:
    return bool(value and value.strip())


def _is_non_empty_string_list(values: list[str]) -> bool:
    return bool(values) and any(_is_non_empty_string(item) for item in values)


def _is_battlecard_non_empty(battlecard: SalesBattlecard) -> bool:
    return any(
        _is_non_empty_string_list(items)
        for items in (
            battlecard.talk_tracks,
            battlecard.objection_handling,
            battlecard.landmines,
        )
    )


def _is_field_non_empty(report: CompetitorReport, field_name: str) -> bool:
    value = getattr(report, field_name)

    if field_name in {
        "company_snapshot",
        "product_positioning",
        "pricing_intelligence",
    }:
        return _is_non_empty_string(value)

    if field_name in {
        "feature_comparison",
        "recent_moves",
        "strengths",
        "weaknesses",
        "sources",
    }:
        if field_name == "sources":
            return bool(value)
        return _is_non_empty_string_list(value)

    if field_name == "sales_battlecard":
        return _is_battlecard_non_empty(value)

    return bool(value)


def _get_section_value(report: CompetitorReport, section_name: str):
    field_name = SECTION_FIELD_MAP.get(section_name)
    if field_name is None:
        return None
    return getattr(report, field_name)


def _efficiency_score(latency_seconds: float) -> float:
    if latency_seconds <= 30:
        return 1.0
    if latency_seconds <= 60:
        return 0.7
    if latency_seconds <= 120:
        return 0.4
    return 0.1


def score_task_completion(
    report: CompetitorReport | None,
) -> tuple[float, list[str]]:
    if report is None:
        return 0.0, ["Report is missing"]

    failure_notes: list[str] = []
    filled_fields = 0

    for field_name in MAJOR_REPORT_FIELDS:
        if _is_field_non_empty(report, field_name):
            filled_fields += 1
        else:
            failure_notes.append(f"Major field '{field_name}' is missing or empty")

    total_fields = len(MAJOR_REPORT_FIELDS)
    score = 1.0 if filled_fields == total_fields else filled_fields / total_fields
    return score, failure_notes


def score_section_coverage(
    report: CompetitorReport,
    expected_sections: list[str],
) -> tuple[float, list[str]]:
    if not expected_sections:
        return 1.0, []

    failure_notes: list[str] = []
    covered_sections = 0

    for section_name in expected_sections:
        if section_name not in SECTION_FIELD_MAP:
            failure_notes.append(f"Unknown expected section '{section_name}'")
            continue

        if _is_field_non_empty(report, SECTION_FIELD_MAP[section_name]):
            covered_sections += 1
        else:
            failure_notes.append(f"Expected section '{section_name}' is missing or empty")

    score = covered_sections / len(expected_sections)
    return score, failure_notes


def score_source_coverage(
    report: CompetitorReport,
    expected_source_types: list[str],
) -> tuple[float, list[str]]:
    if not expected_source_types:
        return 1.0, []

    failure_notes: list[str] = []
    present_types = {source.source_type for source in report.sources}
    matched_types = 0

    for source_type in expected_source_types:
        if source_type in present_types:
            matched_types += 1
        else:
            failure_notes.append(
                f"Expected source type '{source_type}' not found in report sources"
            )

    score = matched_types / len(expected_source_types)
    return score, failure_notes


def score_citation_integrity(report: CompetitorReport) -> tuple[float, list[str]]:
    failure_notes: list[str] = []
    source_ids = {source.id for source in report.sources}

    if report.evidence:
        valid_refs = sum(
            1 for evidence in report.evidence if evidence.source_id in source_ids
        )
        reference_score = valid_refs / len(report.evidence)
        for evidence in report.evidence:
            if evidence.source_id not in source_ids:
                failure_notes.append(
                    "Evidence "
                    f"'{evidence.id}' references missing source_id '{evidence.source_id}'"
                )
    else:
        reference_score = 1.0

    if report.sources:
        sources_with_url = sum(
            1 for source in report.sources if _is_non_empty_string(source.url)
        )
        url_score = sources_with_url / len(report.sources)
        for source in report.sources:
            if not _is_non_empty_string(source.url):
                failure_notes.append(f"Source '{source.id}' has missing or empty URL")
    else:
        url_score = 0.0 if report.evidence else 1.0
        if report.evidence:
            failure_notes.append("Report has evidence but no sources")

    score = (reference_score + url_score) / 2
    return score, failure_notes


# ---------------------------------------------------------------------------
# Comparison-quality scorers (deterministic, no API) — Step 4 headline metrics
# ---------------------------------------------------------------------------

def _cell_filled(value: str | None) -> bool:
    if not value or not value.strip():
        return False
    return _NOT_FOUND_MARKER not in value.strip().lower()


def score_comparison_two_sidedness(
    matrix: ComparisonMatrix | None,
) -> tuple[float | None, list[str]]:
    """% matrix rows where BOTH sides are non-empty and not 'Not found'. Measures
    the original one-sided bug directly."""
    if matrix is None or not matrix.rows:
        return None, ["No comparison matrix to score two-sidedness"]

    two_sided = 0
    notes: list[str] = []
    for row in matrix.rows:
        if _cell_filled(row.our_value) and _cell_filled(row.competitor_value):
            two_sided += 1
        else:
            notes.append(f"One-sided comparison row: '{row.dimension}'")

    return two_sided / len(matrix.rows), notes


def score_comparison_citation_validity(
    matrix: ComparisonMatrix | None,
    report: CompetitorReport,
) -> tuple[float | None, list[str]]:
    """% matrix rows where ALL cited source ids resolve to real report.sources."""
    if matrix is None or not matrix.rows:
        return None, ["No comparison matrix to score citation validity"]

    source_ids = {s.id for s in report.sources}
    valid = 0
    notes: list[str] = []
    for row in matrix.rows:
        cited = list(row.our_source_ids) + list(row.competitor_source_ids)
        unknown = [c for c in cited if c not in source_ids]
        if not unknown:
            valid += 1
        else:
            notes.append(
                f"Invalid matrix citation in row '{row.dimension}': {unknown}"
            )

    return valid / len(matrix.rows), notes


def advantage_distribution(matrix: ComparisonMatrix | None) -> dict[str, int]:
    dist: dict[str, int] = {}
    if matrix is None:
        return dist
    for row in matrix.rows:
        dist[row.advantage] = dist.get(row.advantage, 0) + 1
    return dist


def advantage_honesty_notes(matrix: ComparisonMatrix | None) -> list[str]:
    """Informational sanity flag: 100% one-sided advantage is suspicious."""
    dist = advantage_distribution(matrix)
    total = sum(dist.values())
    if total < 2:
        return []
    for side in ("our", "competitor"):
        if dist.get(side, 0) == total:
            return [f"Suspicious: 100% of advantage flags favor '{side}'"]
    return []


# ---------------------------------------------------------------------------
# Grounding metrics (pure aggregation over judge verdicts — no API)
# ---------------------------------------------------------------------------

# Verdicts that count as a successful judge call (real content judgment).
_JUDGED_OK = {
    Verdict.SUPPORTED,
    Verdict.PARTIAL,
    Verdict.UNSUPPORTED,
    Verdict.CONTRADICTED,
}


def grounding_metrics(verdicts: list[ClaimVerdict]) -> dict[str, float | int | None]:
    """Aggregate judge verdicts.

    grounding_rate / hallucination_rate are None when no claim was successfully
    judged (n_judged_ok==0) — never silently report 0.0 for a failed judge layer.
    Rates are over n_judged_ok only (ERROR / CITATION_INVALID excluded from denom).
    """
    n_claims_total = len(verdicts)
    n_judge_errors = sum(1 for v in verdicts if v.verdict == Verdict.ERROR)
    n_citation_invalid = sum(1 for v in verdicts if v.verdict == Verdict.CITATION_INVALID)
    judged = [v for v in verdicts if v.verdict in _JUDGED_OK]
    n_judged_ok = len(judged)

    if n_judged_ok == 0:
        return {
            "grounding_rate": None,
            "hallucination_rate": None,
            "citation_validity": (
                (n_claims_total - n_citation_invalid) / n_claims_total
                if n_claims_total
                else None
            ),
            "n_claims_total": n_claims_total,
            "n_judged_ok": 0,
            "n_judge_errors": n_judge_errors,
            "n_citation_invalid": n_citation_invalid,
        }

    # Grounded = supported OR partial (partial = source partly entails claim).
    # Aligns with comparison_grounding; unsupported/contradicted are not grounded.
    grounded = sum(
        1 for v in judged if v.verdict in {Verdict.SUPPORTED, Verdict.PARTIAL}
    )
    contradicted = sum(1 for v in judged if v.verdict == Verdict.CONTRADICTED)
    return {
        "grounding_rate": grounded / n_judged_ok,
        "hallucination_rate": contradicted / n_judged_ok,
        "citation_validity": (n_claims_total - n_citation_invalid) / n_claims_total,
        "n_claims_total": n_claims_total,
        "n_judged_ok": n_judged_ok,
        "n_judge_errors": n_judge_errors,
        "n_citation_invalid": n_citation_invalid,
    }


def score_report(
    task: BenchmarkTask,
    report: CompetitorReport,
    latency_seconds: float,
    warnings_count: int,
) -> TaskScore:
    task_completion, task_notes = score_task_completion(report)
    section_coverage, section_notes = score_section_coverage(
        report, task.expected_sections
    )
    source_coverage, source_notes = score_source_coverage(
        report, task.expected_source_types
    )
    citation_integrity, citation_notes = score_citation_integrity(report)
    efficiency = _efficiency_score(latency_seconds)

    matrix = report.comparison_matrix
    two_sidedness, two_sided_notes = score_comparison_two_sidedness(matrix)
    cmp_citation_validity, cmp_citation_notes = score_comparison_citation_validity(
        matrix, report
    )
    honesty_notes = advantage_honesty_notes(matrix)

    overall_score = (
        0.30 * task_completion
        + 0.25 * section_coverage
        + 0.20 * source_coverage
        + 0.15 * citation_integrity
        + 0.10 * efficiency
    )

    failure_notes = (
        task_notes
        + section_notes
        + source_notes
        + citation_notes
        + two_sided_notes
        + cmp_citation_notes
        + honesty_notes
    )

    return TaskScore(
        task_id=task.id,
        task_completion=task_completion,
        section_coverage=section_coverage,
        source_coverage=source_coverage,
        citation_integrity=citation_integrity,
        evidence_count=len(report.evidence),
        source_count=len(report.sources),
        latency_seconds=latency_seconds,
        warnings_count=warnings_count,
        overall_score=overall_score,
        failure_notes=failure_notes,
        comparison_two_sidedness=two_sidedness,
        comparison_citation_validity=cmp_citation_validity,
        advantage_distribution=advantage_distribution(matrix),
    )
