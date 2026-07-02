from app.evaluation.schemas import BenchmarkTask, TaskScore
from app.schemas.report import CompetitorReport, SalesBattlecard

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

    overall_score = (
        0.30 * task_completion
        + 0.25 * section_coverage
        + 0.20 * source_coverage
        + 0.15 * citation_integrity
        + 0.10 * efficiency
    )

    failure_notes = task_notes + section_notes + source_notes + citation_notes

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
    )
