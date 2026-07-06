"""Symmetric tracks + full-page extraction. All externals (search_web/extract_urls) mocked."""

import app.services.research_tracks as rt
from app.core.config import settings


def _r(url, score, content="short snippet"):
    return {"title": f"title-{url}", "url": url, "content": content, "score": score}


def test_extract_called_with_top_n_urls_and_content_merged(monkeypatch):
    monkeypatch.setattr(settings, "extract_top_n", 2)

    def fake_search_web(query, max_results=3, run_id=None, track=None):
        return [
            _r("https://a1.com", 0.9),
            _r("https://a2.com", 0.5),
            _r("https://a3.com", 0.1),
        ]

    extract_calls = []

    def fake_extract_urls(urls, **kwargs):
        extract_calls.append(urls)
        return [
            {"url": "https://a1.com", "title": "A1 full", "content": "FULL PAGE TEXT A1"},
            {"url": "https://a2.com", "title": "A2 full", "content": "FULL PAGE TEXT A2"},
        ]

    monkeypatch.setattr(rt, "search_web", fake_search_web)
    monkeypatch.setattr(rt, "extract_urls", fake_extract_urls)

    result = rt.run_research_track(
        track="company_profile",
        queries_by_company={"CompanyA": ["queryA"]},
    )

    assert extract_calls == [["https://a1.com", "https://a2.com"]]  # top-N only, ranked by score

    by_url = {e.url: e for e in result["evidence"]}
    assert by_url["https://a1.com"].raw_text == "FULL PAGE TEXT A1"
    assert by_url["https://a2.com"].raw_text == "FULL PAGE TEXT A2"
    assert by_url["https://a3.com"].raw_text == "short snippet"  # not extracted -> snippet kept
    assert all(e.company == "CompanyA" for e in result["evidence"])


def test_snippet_fallback_when_extract_returns_empty(monkeypatch):
    monkeypatch.setattr(rt, "search_web", lambda *a, **kw: [_r("https://b1.com", 0.9, "b1 snippet")])
    monkeypatch.setattr(rt, "extract_urls", lambda urls, **kw: [])

    result = rt.run_research_track(
        track="pricing",
        queries_by_company={"CompanyB": ["q"]},
    )
    assert result["evidence"][0].raw_text == "b1 snippet"


def test_extract_failure_never_crashes_falls_back_to_snippet(monkeypatch):
    def boom(urls, **kwargs):
        raise RuntimeError("tavily extract down")

    monkeypatch.setattr(rt, "search_web", lambda *a, **kw: [_r("https://c1.com", 0.9, "c1 snippet")])
    monkeypatch.setattr(rt, "extract_urls", boom)

    result = rt.run_research_track(
        track="recent_news",
        queries_by_company={"CompanyC": ["q"]},
    )
    assert result["evidence"][0].raw_text == "c1 snippet"


def test_symmetric_tracks_tag_both_companies_correctly(monkeypatch):
    def fake_search_web(query, max_results=3, run_id=None, track=None):
        if query == "qA":
            return [_r("https://a.com", 0.9, "a snippet")]
        return [_r("https://b.com", 0.9, "b snippet")]

    monkeypatch.setattr(rt, "search_web", fake_search_web)
    monkeypatch.setattr(rt, "extract_urls", lambda urls: [])

    result = rt.run_research_track(
        track="company_profile",
        queries_by_company={"CompanyA": ["qA"], "CompanyB": ["qB"]},
    )
    by_url = {e.url: e for e in result["evidence"]}
    assert by_url["https://a.com"].company == "CompanyA"
    assert by_url["https://b.com"].company == "CompanyB"


def test_extract_max_chars_caps_merged_content(monkeypatch):
    monkeypatch.setattr(settings, "extract_top_n", 1)
    monkeypatch.setattr(settings, "extract_max_chars", 10)

    monkeypatch.setattr(rt, "search_web", lambda *a, **kw: [_r("https://d1.com", 0.9, "short")])
    monkeypatch.setattr(
        rt, "extract_urls", lambda urls, **kw: [{"url": "https://d1.com", "content": "x" * 100}]
    )

    result = rt.run_research_track(
        track="company_profile",
        queries_by_company={"CompanyD": ["q"]},
    )
    assert len(result["evidence"][0].raw_text) == 10
