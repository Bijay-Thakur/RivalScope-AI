import app.services.report_generator as rg
from app.schemas.report import (
    ComparisonMatrix,
    EvidenceItem,
    FeatureComparisonRow,
    Source,
)
from app.schemas.research import ReportType, ResearchRequest
from app.services.report_generator import (
    _build_context,
    _extract_strengths_from_evidence,
    _extract_weaknesses_from_evidence,
    _feature_comparison_from_matrix,
    generate_competitor_report,
)

_REQUEST = ResearchRequest(
    our_company="ClickUp",
    competitor="Notion",
    market="Project management",
    report_type=ReportType.QUICK_BRIEF,
)


def _source(id_, company):
    return Source(
        id=id_, title=f"title-{id_}", url=f"https://x.com/{id_}",
        source_type="company_page", credibility_score=0.8, company=company,
    )


def _evidence(id_, source_id, company):
    return EvidenceItem(
        id=id_, claim=f"claim-{id_}", source_id=source_id,
        confidence="high", raw_text=f"raw-{id_}", company=company,
    )


def test_context_has_both_labeled_sections():
    sources = [_source("s1", "ClickUp"), _source("s2", "Notion")]
    evidence = [_evidence("e1", "s1", "ClickUp"), _evidence("e2", "s2", "Notion")]

    context = _build_context(_REQUEST, sources, evidence, [])

    assert "=== OUR COMPANY: ClickUp ===" in context
    assert "=== COMPETITOR: Notion ===" in context


def test_each_side_shows_only_its_own_evidence():
    sources = [_source("s1", "ClickUp"), _source("s2", "Notion")]
    evidence = [_evidence("e1", "s1", "ClickUp"), _evidence("e2", "s2", "Notion")]

    context = _build_context(_REQUEST, sources, evidence, [])
    our_section = context.split("=== COMPETITOR: Notion ===")[0]
    rival_section = context.split("=== COMPETITOR: Notion ===")[1]

    assert "claim-e1" in our_section
    assert "claim-e2" not in our_section
    assert "claim-e2" in rival_section


def test_untagged_items_go_to_other_section_not_dropped():
    sources = [_source("s1", None)]
    evidence = [_evidence("e1", "s1", None)]

    context = _build_context(_REQUEST, sources, evidence, [])
    assert "OTHER / UNTAGGED" in context
    assert "claim-e1" in context


# --- Step 2: comparison matrix consumption -------------------------------

def _matrix() -> ComparisonMatrix:
    return ComparisonMatrix(
        rows=[
            FeatureComparisonRow(
                dimension="Pricing",
                our_value="ClickUp $7",
                competitor_value="Notion free tier",
                our_source_ids=["s1"],
                competitor_source_ids=["s2"],
                advantage="our",
            )
        ],
        pricing_comparison="flat vs tiered",
        positioning_gap="execution vs docs",
        summary="mixed bag",
    )


def test_context_includes_head_to_head_section():
    sources = [_source("s1", "ClickUp"), _source("s2", "Notion")]
    evidence = [_evidence("e1", "s1", "ClickUp"), _evidence("e2", "s2", "Notion")]

    context = _build_context(_REQUEST, sources, evidence, [], _matrix())
    assert "=== HEAD-TO-HEAD COMPARISON ===" in context
    assert "Pricing" in context
    assert "advantage=our" in context


def test_feature_comparison_derived_from_matrix():
    flat = _feature_comparison_from_matrix(_REQUEST, _matrix())
    assert flat == ["Pricing: ClickUp -> ClickUp $7 | Notion -> Notion free tier"]


def test_generate_report_derives_feature_comparison_and_attaches_matrix(monkeypatch):
    # LLM returns valid report JSON WITHOUT featureComparison — must come from matrix.
    import json

    monkeypatch.setattr(
        rg,
        "invoke_with_fallback",
        lambda messages, **kwargs: json.dumps(
            {
                "companySnapshot": "snap",
                "productPositioning": "pos",
                "featureComparison": ["LLM SHOULD NOT WIN"],
                "pricingIntelligence": "pi",
                "recentMoves": [],
                "strengths": [],
                "weaknesses": [],
                "salesBattlecard": {"talkTracks": [], "objectionHandling": [], "landmines": []},
                "confidenceScore": 70,
            }
        ),
    )

    sources = [_source("s1", "ClickUp"), _source("s2", "Notion")]
    evidence = [_evidence("e1", "s1", "ClickUp"), _evidence("e2", "s2", "Notion")]

    report = generate_competitor_report(
        _REQUEST, sources, evidence, [], comparison_matrix=_matrix()
    )

    assert report.feature_comparison == [
        "Pricing: ClickUp -> ClickUp $7 | Notion -> Notion free tier"
    ]
    assert "LLM SHOULD NOT WIN" not in report.feature_comparison
    assert report.comparison_matrix is not None
    assert report.comparison_matrix.rows[0].dimension == "Pricing"


def test_balanced_strengths_pull_from_both_companies():
    # each side has one "leader" claim; balanced extractor must include both.
    evidence = [
        EvidenceItem(id="a", claim="ClickUp is a leader here", source_id="s1",
                     confidence="high", company="ClickUp"),
        EvidenceItem(id="b", claim="Notion is a leader too", source_id="s2",
                     confidence="high", company="Notion"),
    ]
    out = _extract_strengths_from_evidence(evidence, "ClickUp", "Notion")
    assert "ClickUp is a leader here" in out
    assert "Notion is a leader too" in out


def test_balanced_weaknesses_pull_from_both_companies():
    evidence = [
        EvidenceItem(id="a", claim="ClickUp has limited X", source_id="s1",
                     confidence="high", company="ClickUp"),
        EvidenceItem(id="b", claim="Notion is missing Y", source_id="s2",
                     confidence="high", company="Notion"),
    ]
    out = _extract_weaknesses_from_evidence(evidence, "ClickUp", "Notion")
    assert "ClickUp has limited X" in out
    assert "Notion is missing Y" in out
