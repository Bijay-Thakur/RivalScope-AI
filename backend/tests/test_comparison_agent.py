"""Comparison agent — all externals (LLM) mocked, zero real API calls."""

import json

import app.services.comparison_agent as ca
import app.services.structured_output as so
from app.schemas.report import EvidenceItem, Source
from app.schemas.research import ReportType, ResearchRequest
from app.services.mock_data import build_mock_comparison_matrix

_REQUEST = ResearchRequest(
    our_company="ClickUp",
    competitor="Notion",
    market="project management",
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


_SOURCES = [_source("s1", "ClickUp"), _source("s2", "Notion")]
_EVIDENCE = [_evidence("e1", "s1", "ClickUp"), _evidence("e2", "s2", "Notion")]


def _valid_json() -> str:
    return json.dumps(
        {
            "rows": [
                {
                    "dimension": "Pricing model",
                    "ourValue": "ClickUp $7/user/mo",
                    "competitorValue": "Notion free + per-seat",
                    "ourSourceIds": ["s1"],
                    "competitorSourceIds": ["s2"],
                    "advantage": "our",
                },
                {
                    "dimension": "Docs",
                    "ourValue": "Not found in available sources",
                    "competitorValue": "Notion docs-first",
                    "ourSourceIds": [],
                    "competitorSourceIds": ["s2"],
                    "advantage": "bogus_value",  # -> coerced to unclear
                },
            ],
            "pricingComparison": "ClickUp flat vs Notion tiered",
            "positioningGap": "execution vs docs",
            "summary": "mixed",
        }
    )


def test_valid_llm_output_parsed_two_sided(monkeypatch):
    monkeypatch.setattr(so, "invoke_with_fallback", lambda messages, **kwargs: _valid_json())

    matrix = ca.build_comparison_matrix(_REQUEST, _SOURCES, _EVIDENCE, [])

    assert len(matrix.rows) == 2
    r0 = matrix.rows[0]
    assert r0.our_value and r0.competitor_value
    assert r0.our_source_ids == ["s1"]
    assert r0.competitor_source_ids == ["s2"]
    assert all(row.advantage in {"our", "competitor", "parity", "unclear"} for row in matrix.rows)
    assert matrix.rows[1].advantage == "unclear"  # bad value coerced


def test_fallback_matrix_on_bad_json(monkeypatch):
    monkeypatch.setattr(
        so, "invoke_with_fallback", lambda messages, **kwargs: "not json at all {{{"
    )

    matrix = ca.build_comparison_matrix(_REQUEST, _SOURCES, _EVIDENCE, [])

    assert len(matrix.rows) >= 1  # deterministic fallback, pipeline never dies
    assert matrix.rows[0].advantage == "unclear"


def test_fallback_matrix_on_empty_rows(monkeypatch):
    monkeypatch.setattr(
        so,
        "invoke_with_fallback",
        lambda messages, **kwargs: json.dumps(
            {"rows": [], "pricingComparison": "", "positioningGap": "", "summary": ""}
        ),
    )

    matrix = ca.build_comparison_matrix(_REQUEST, _SOURCES, _EVIDENCE, [])
    assert len(matrix.rows) >= 1  # fell back because no valid rows


def test_fallback_matrix_pulls_from_both_sides():
    matrix = ca.build_fallback_matrix(_REQUEST, _SOURCES, _EVIDENCE)
    row = matrix.rows[0]
    assert row.our_value == "claim-e1"
    assert row.competitor_value == "claim-e2"


def test_mock_matrix_offline_two_sided():
    matrix = build_mock_comparison_matrix(_REQUEST)
    assert 5 <= len(matrix.rows) <= 8
    for row in matrix.rows:
        assert "ClickUp" in row.our_value
        assert "Notion" in row.competitor_value
        assert row.advantage in {"our", "competitor", "parity", "unclear"}
