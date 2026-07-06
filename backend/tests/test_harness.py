import json

from evals import harness
from evals.schemas import Verdict
from app.schemas.report import CompetitorReport, EvidenceItem, SalesBattlecard, Source
from app.schemas.research import ReportType, ResearchRequest

_DATASET = [
    {"ourCompany": "ClickUp", "competitor": "Notion", "market": "PM software", "reportType": "quick_brief"},
]


def _fake_report() -> CompetitorReport:
    source = Source(
        id="src-1", title="Notion site", url="https://notion.so", source_type="company_page",
        credibility_score=0.9, snippet="Notion is a workspace tool.",
    )
    evidence_valid = EvidenceItem(
        id="ev-1", claim="Notion is a workspace tool", source_id="src-1",
        confidence="high", raw_text="Notion is a workspace tool.",
    )
    evidence_invalid = EvidenceItem(
        id="ev-2", claim="Notion has 100M users", source_id="src-missing",
        confidence="low", raw_text=None,
    )
    return CompetitorReport(
        company_snapshot="snap", product_positioning="pos", feature_comparison=[],
        pricing_intelligence="n/a", recent_moves=[], strengths=[], weaknesses=[],
        sales_battlecard=SalesBattlecard(talk_tracks=[], objection_handling=[], landmines=[]),
        evidence=[evidence_valid, evidence_invalid], sources=[source],
        confidence_score=0.8, research_mode="real",
    )


async def _fake_run_research_graph(request: ResearchRequest) -> dict:
    return {"run_id": "run-abc", "final_report": _fake_report()}


async def _fake_judge_claims(items, model, max_concurrency=3):
    return [(Verdict.SUPPORTED, "matches", 0.9) for _ in items]


def test_dataset_loads_and_maps_to_research_requests(tmp_path):
    dataset_path = tmp_path / "cases.json"
    dataset_path.write_text(json.dumps(_DATASET), encoding="utf-8")

    cases = harness._load_dataset(dataset_path, limit=None)

    assert len(cases) == 1
    assert cases[0].our_company == "ClickUp"
    assert cases[0].report_type == ReportType.QUICK_BRIEF


async def test_eval_single_report_marks_missing_source_as_citation_invalid(monkeypatch):
    monkeypatch.setattr(harness, "run_research_graph", _fake_run_research_graph)
    monkeypatch.setattr(harness, "judge_claims", _fake_judge_claims)

    request = ResearchRequest(
        our_company="ClickUp", competitor="Notion", market="PM software",
        report_type=ReportType.QUICK_BRIEF,
    )
    result = await harness._eval_single_report(request, judge_model="gemini-2.5-pro", max_concurrency=3)

    assert len(result.verdicts) == 2
    by_id = {v.source_id: v for v in result.verdicts}
    assert by_id["src-1"].verdict == Verdict.SUPPORTED
    assert by_id["src-missing"].verdict == Verdict.CITATION_INVALID
    assert result.metrics["total_claims"] == 2


async def test_run_eval_writes_result_files_and_summary_shape(tmp_path, monkeypatch):
    monkeypatch.setattr(harness, "run_research_graph", _fake_run_research_graph)
    monkeypatch.setattr(harness, "judge_claims", _fake_judge_claims)

    dataset_path = tmp_path / "cases.json"
    dataset_path.write_text(json.dumps(_DATASET), encoding="utf-8")
    out_dir = tmp_path / "results"

    summary = await harness.run_eval(dataset_path, limit=None, out_dir=out_dir)

    assert summary.n_reports == 1
    assert summary.n_claims == 2
    assert "grounding_rate_strict" in summary.aggregate
    assert "quick_brief" in summary.per_report_type

    written = list(out_dir.glob("eval_*.json"))
    assert len(written) == 1
    assert (out_dir / "latest_summary.json").exists()
