"""Comparison-quality + grounding metric scorers. Deterministic, no API."""

from app.evaluation.schemas import ClaimVerdict, Verdict
from app.evaluation.scorers import (
    advantage_distribution,
    advantage_honesty_notes,
    grounding_metrics,
    score_comparison_citation_validity,
    score_comparison_two_sidedness,
)
from app.schemas.report import (
    ComparisonMatrix,
    CompetitorReport,
    FeatureComparisonRow,
    SalesBattlecard,
    Source,
)


def _row(dim, our, comp, our_ids=None, comp_ids=None, adv="unclear"):
    return FeatureComparisonRow(
        dimension=dim, our_value=our, competitor_value=comp,
        our_source_ids=our_ids or [], competitor_source_ids=comp_ids or [], advantage=adv,
    )


def _matrix(rows):
    return ComparisonMatrix(rows=rows, pricing_comparison="p", positioning_gap="g", summary="s")


def _report(sources, matrix):
    return CompetitorReport(
        company_snapshot="x", product_positioning="x", feature_comparison=[],
        pricing_intelligence="x", recent_moves=[], strengths=[], weaknesses=[],
        sales_battlecard=SalesBattlecard(talk_tracks=[], objection_handling=[], landmines=[]),
        comparison_matrix=matrix, evidence=[], sources=sources, confidence_score=50.0,
    )


def test_two_sidedness_counts_only_both_sides_filled():
    matrix = _matrix([
        _row("A", "our val", "comp val"),                       # two-sided
        _row("B", "our val", "Not found in available sources"), # one-sided
        _row("C", "", "comp val"),                              # one-sided (empty)
    ])
    score, notes = score_comparison_two_sidedness(matrix)
    assert score == 1 / 3
    assert any("One-sided" in n for n in notes)


def test_two_sidedness_none_when_no_matrix():
    score, notes = score_comparison_two_sidedness(None)
    assert score is None


def test_citation_validity_flags_unknown_source_ids():
    sources = [Source(id="s1", title="t", url="u", source_type="other", credibility_score=0.5)]
    matrix = _matrix([
        _row("A", "o", "c", our_ids=["s1"], comp_ids=["s1"]),     # valid
        _row("B", "o", "c", our_ids=["s1"], comp_ids=["ghost"]),  # invalid
    ])
    report = _report(sources, matrix)
    score, notes = score_comparison_citation_validity(matrix, report)
    assert score == 1 / 2
    assert any("Invalid matrix citation" in n for n in notes)


def test_advantage_distribution_and_honesty_flag():
    matrix = _matrix([_row("A", "o", "c", adv="our"), _row("B", "o", "c", adv="our")])
    assert advantage_distribution(matrix) == {"our": 2}
    assert advantage_honesty_notes(matrix)  # 100% one side -> suspicious

    mixed = _matrix([_row("A", "o", "c", adv="our"), _row("B", "o", "c", adv="parity")])
    assert advantage_honesty_notes(mixed) == []


def _cv(verdict):
    return ClaimVerdict(claim="c", source_id="s", self_confidence="high",
                        verdict=verdict, rationale="r", judge_confidence=0.9)


def test_grounding_metrics_rates():
    verdicts = [
        _cv(Verdict.SUPPORTED), _cv(Verdict.SUPPORTED),
        _cv(Verdict.CONTRADICTED), _cv(Verdict.CITATION_INVALID),
    ]
    m = grounding_metrics(verdicts)
    # rates over judged_ok only (3); grounded = supported|partial
    assert m["grounding_rate"] == 2 / 3  # 2 supported, 0 partial
    assert m["hallucination_rate"] == 1 / 3
    assert m["citation_validity"] == 3 / 4
    assert m["n_judged_ok"] == 3
    assert m["n_citation_invalid"] == 1
    assert m["n_judge_errors"] == 0


def test_grounding_metrics_counts_partial_as_grounded():
    m = grounding_metrics(
        [_cv(Verdict.SUPPORTED), _cv(Verdict.PARTIAL), _cv(Verdict.UNSUPPORTED)]
    )
    assert m["grounding_rate"] == 2 / 3
    assert m["hallucination_rate"] == 1 / 3  # unsupported only
    assert m["n_judged_ok"] == 3


def test_grounding_metrics_empty_returns_null_rates():
    m = grounding_metrics([])
    assert m["grounding_rate"] is None
    assert m["hallucination_rate"] is None
    assert m["n_judged_ok"] == 0
    assert m["n_claims_total"] == 0


def test_grounding_metrics_all_errors_null_not_zero():
    m = grounding_metrics([_cv(Verdict.ERROR), _cv(Verdict.ERROR)])
    assert m["grounding_rate"] is None
    assert m["hallucination_rate"] is None
    assert m["n_judge_errors"] == 2
    assert m["n_judged_ok"] == 0


def test_grounding_metrics_mixed_error_excluded_from_denom():
    m = grounding_metrics(
        [_cv(Verdict.SUPPORTED), _cv(Verdict.ERROR), _cv(Verdict.UNSUPPORTED)]
    )
    assert m["grounding_rate"] == 0.5
    assert m["hallucination_rate"] == 0.5  # unsupported / judged_ok
    assert m["n_judged_ok"] == 2
    assert m["n_judge_errors"] == 1
