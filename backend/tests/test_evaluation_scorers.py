import pytest

from app.evaluation.loader import load_benchmark_tasks
from app.evaluation.scorers import (
    score_citation_integrity,
    score_report,
    score_source_coverage,
)
from app.schemas.report import CompetitorReport, EvidenceItem, SalesBattlecard, Source
from app.schemas.research import ReportType, ResearchRequest
from app.services.mock_data import build_mock_report


@pytest.fixture
def benchmark_task():
    return load_benchmark_tasks()[0]


@pytest.fixture
def mock_report():
    return build_mock_report(
        ResearchRequest(
            our_company="ClickUp",
            competitor="Notion",
            market="Project management / docs",
            report_type=ReportType.SALES_BATTLECARD,
        )
    )


def test_scoring_works_on_mock_report(benchmark_task, mock_report):
    result = score_report(
        benchmark_task,
        mock_report,
        latency_seconds=12.0,
        warnings_count=0,
    )

    assert result.task_id == benchmark_task.id
    assert result.task_completion == 1.0
    assert result.section_coverage == 1.0
    assert result.citation_integrity == 1.0
    assert result.evidence_count == len(mock_report.evidence)
    assert result.source_count == len(mock_report.sources)
    assert 0.0 < result.overall_score <= 1.0


def test_citation_integrity_catches_missing_source_ids():
    report = CompetitorReport(
        company_snapshot="Snapshot",
        product_positioning="Positioning",
        feature_comparison=["Feature A"],
        pricing_intelligence="Tiered pricing",
        recent_moves=["Recent move"],
        strengths=["Strength"],
        weaknesses=["Weakness"],
        sales_battlecard=SalesBattlecard(
            talk_tracks=["Talk track"],
            objection_handling=["Objection"],
            landmines=["Landmine"],
        ),
        evidence=[
            EvidenceItem(
                id="ev-1",
                claim="Valid claim",
                source_id="src-valid",
                confidence="high",
            ),
            EvidenceItem(
                id="ev-2",
                claim="Broken claim",
                source_id="src-missing",
                confidence="medium",
            ),
        ],
        sources=[
            Source(
                id="src-valid",
                title="Valid source",
                url="https://example.com/valid",
                source_type="company_page",
                credibility_score=0.9,
            )
        ],
        confidence_score=0.7,
    )

    score, notes = score_citation_integrity(report)

    assert score < 1.0
    assert any("src-missing" in note for note in notes)


def test_source_coverage_gives_partial_credit():
    report = CompetitorReport(
        company_snapshot="Snapshot",
        product_positioning="Positioning",
        feature_comparison=["Feature A"],
        pricing_intelligence="Tiered pricing",
        recent_moves=["Recent move"],
        strengths=["Strength"],
        weaknesses=["Weakness"],
        sales_battlecard=SalesBattlecard(
            talk_tracks=["Talk track"],
            objection_handling=["Objection"],
            landmines=["Landmine"],
        ),
        evidence=[],
        sources=[
            Source(
                id="src-1",
                title="Company page",
                url="https://example.com/about",
                source_type="company_page",
                credibility_score=0.9,
            ),
            Source(
                id="src-2",
                title="Pricing page",
                url="https://example.com/pricing",
                source_type="pricing_page",
                credibility_score=0.9,
            ),
        ],
        confidence_score=0.7,
    )
    expected_source_types = [
        "company_page",
        "pricing_page",
        "news",
        "docs",
    ]

    score, notes = score_source_coverage(report, expected_source_types)

    assert score == 0.5
    assert len(notes) == 2
    assert all("Expected source type" in note for note in notes)
