"""Pure aggregation over judge verdicts. No LLM calls, no IO."""

from evals.schemas import ClaimVerdict, ReportEvalResult, Verdict

_CONFIDENCE_BUCKETS = ("high", "medium", "low")


def _grounding_rate_strict(verdicts: list[ClaimVerdict]) -> float:
    if not verdicts:
        return 0.0
    supported = sum(1 for v in verdicts if v.verdict == Verdict.SUPPORTED)
    return supported / len(verdicts)


def report_metrics(verdicts: list[ClaimVerdict]) -> dict:
    total = len(verdicts)
    if total == 0:
        return {
            "total_claims": 0,
            "grounding_rate_strict": 0.0,
            "grounding_rate_lenient": 0.0,
            "unsupported_rate": 0.0,
            "hallucination_rate": 0.0,
            "citation_validity": 0.0,
            "calibration": {bucket: 0.0 for bucket in _CONFIDENCE_BUCKETS},
        }

    counts = {v: 0 for v in Verdict}
    for cv in verdicts:
        counts[cv.verdict] += 1

    supported = counts[Verdict.SUPPORTED]
    partial = counts[Verdict.PARTIAL]
    unsupported = counts[Verdict.UNSUPPORTED]
    contradicted = counts[Verdict.CONTRADICTED]
    invalid = counts[Verdict.CITATION_INVALID]

    calibration = {
        bucket: _grounding_rate_strict([v for v in verdicts if v.self_confidence == bucket])
        for bucket in _CONFIDENCE_BUCKETS
    }

    return {
        "total_claims": total,
        "grounding_rate_strict": supported / total,
        "grounding_rate_lenient": (supported + 0.5 * partial) / total,
        "unsupported_rate": unsupported / total,
        "hallucination_rate": contradicted / total,
        "citation_validity": (total - invalid) / total,
        "calibration": calibration,
    }


def aggregate(results: list[ReportEvalResult]) -> dict:
    """Claim-weighted aggregate + per-report-type breakdown."""
    all_verdicts = [v for r in results for v in r.verdicts]

    by_type: dict[str, list[ClaimVerdict]] = {}
    for r in results:
        by_type.setdefault(r.report_type, []).extend(r.verdicts)

    return {
        "aggregate": report_metrics(all_verdicts),
        "per_report_type": {rt: report_metrics(vs) for rt, vs in by_type.items()},
    }
