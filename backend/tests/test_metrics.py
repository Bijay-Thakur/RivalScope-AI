from evals.metrics import aggregate, report_metrics
from evals.schemas import ClaimVerdict, ReportEvalResult, Verdict


def _cv(verdict: Verdict, confidence: str = "high") -> ClaimVerdict:
    return ClaimVerdict(
        claim="claim",
        source_id="src-1",
        self_confidence=confidence,
        verdict=verdict,
        rationale="r",
        judge_confidence=0.9,
    )


def test_report_metrics_empty_list_no_div_by_zero():
    m = report_metrics([])
    assert m["total_claims"] == 0
    assert m["grounding_rate_strict"] == 0.0
    assert m["hallucination_rate"] == 0.0
    assert m["calibration"] == {"high": 0.0, "medium": 0.0, "low": 0.0}


def test_report_metrics_grounding_rates():
    verdicts = [
        _cv(Verdict.SUPPORTED),
        _cv(Verdict.SUPPORTED),
        _cv(Verdict.PARTIAL),
        _cv(Verdict.UNSUPPORTED),
        _cv(Verdict.CONTRADICTED),
    ]
    m = report_metrics(verdicts)
    assert m["total_claims"] == 5
    assert m["grounding_rate_strict"] == 2 / 5
    assert m["grounding_rate_lenient"] == (2 + 0.5 * 1) / 5
    assert m["unsupported_rate"] == 1 / 5
    assert m["hallucination_rate"] == 1 / 5


def test_report_metrics_citation_invalid_excluded_from_validity():
    verdicts = [_cv(Verdict.SUPPORTED), _cv(Verdict.CITATION_INVALID)]
    m = report_metrics(verdicts)
    assert m["citation_validity"] == 1 / 2


def test_report_metrics_calibration_buckets_by_self_confidence():
    verdicts = [
        _cv(Verdict.SUPPORTED, confidence="high"),
        _cv(Verdict.UNSUPPORTED, confidence="high"),
        _cv(Verdict.SUPPORTED, confidence="low"),
    ]
    m = report_metrics(verdicts)
    assert m["calibration"]["high"] == 0.5
    assert m["calibration"]["low"] == 1.0
    assert m["calibration"]["medium"] == 0.0


def test_aggregate_is_claim_weighted_across_reports():
    r1 = ReportEvalResult(
        our_company="A", competitor="B", market="m", report_type="quick_brief",
        run_id="1", verdicts=[_cv(Verdict.SUPPORTED)], metrics={},
    )
    r2 = ReportEvalResult(
        our_company="C", competitor="D", market="m", report_type="quick_brief",
        run_id="2", verdicts=[_cv(Verdict.UNSUPPORTED), _cv(Verdict.UNSUPPORTED)], metrics={},
    )
    result = aggregate([r1, r2])
    assert result["aggregate"]["total_claims"] == 3
    assert result["aggregate"]["grounding_rate_strict"] == 1 / 3
    assert result["per_report_type"]["quick_brief"]["total_claims"] == 3


def test_aggregate_empty_results_no_div_by_zero():
    result = aggregate([])
    assert result["aggregate"]["total_claims"] == 0
    assert result["per_report_type"] == {}
