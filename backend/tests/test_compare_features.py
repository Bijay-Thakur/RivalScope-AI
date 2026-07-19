from app.schemas.research import ReportType, ResearchRequest
from app.services.compare_features import (
    market_from_features,
    normalize_compare_features,
    parse_compare_features_param,
)
from app.services.query_builder import build_all_queries


def test_normalize_keeps_catalog_order():
    assert normalize_compare_features(["ai_capabilities", "pricing", "nope"]) == [
        "pricing",
        "ai_capabilities",
    ]


def test_request_derives_market_from_features():
    req = ResearchRequest(
        our_company="A",
        competitor="B",
        report_type=ReportType.QUICK_BRIEF,
        compare_features=["pricing", "security"],
    )
    assert "Pricing" in req.market
    assert "Security" in req.market


def test_feature_queries_bias_product_track():
    req = ResearchRequest(
        our_company="ClickUp",
        competitor="Notion",
        report_type=ReportType.QUICK_BRIEF,
        compare_features=["integrations", "ai_capabilities"],
    )
    qs = build_all_queries(req)["product_features"]["ClickUp"]
    blob = " ".join(qs).lower()
    assert "integration" in blob or "ai" in blob


def test_parse_query_param():
    assert parse_compare_features_param("pricing,core_features") == [
        "pricing",
        "core_features",
    ]
    assert market_from_features(["pricing"]).startswith("Pricing")
