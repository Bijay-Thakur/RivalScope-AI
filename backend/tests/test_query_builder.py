from app.schemas.research import ReportType, ResearchRequest
from app.services.query_builder import build_all_queries

_REQUEST = ResearchRequest(
    our_company="ClickUp",
    competitor="Notion",
    market="Project management / docs",
    report_type=ReportType.QUICK_BRIEF,
)

_TRACKS = {"company_profile", "product_features", "pricing", "recent_news"}


def test_build_all_queries_covers_all_tracks():
    result = build_all_queries(_REQUEST)
    assert set(result.keys()) == _TRACKS


def test_build_all_queries_is_symmetric_per_track():
    result = build_all_queries(_REQUEST)
    for track in _TRACKS:
        companies = set(result[track].keys())
        assert companies == {"ClickUp", "Notion"}


def test_each_side_gets_two_focused_queries_per_track():
    result = build_all_queries(_REQUEST)
    for track in _TRACKS:
        for company, queries in result[track].items():
            assert len(queries) == 2
            for q in queries:
                assert company in q


def test_queries_target_company_itself_not_comparison():
    result = build_all_queries(_REQUEST)
    for track in _TRACKS:
        for company, queries in result[track].items():
            other = "Notion" if company == "ClickUp" else "ClickUp"
            for q in queries:
                assert other not in q
                assert " vs " not in q.lower()
