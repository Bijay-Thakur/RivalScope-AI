from app.services.evidence import build_evidence_from_results, source_from_search_result


def test_source_from_search_result_tags_company():
    result = {"url": "https://a.com", "title": "A", "content": "hello"}
    source = source_from_search_result(result, "company_page", "company_profile", company="ClickUp")
    assert source.company == "ClickUp"


def test_source_from_search_result_company_defaults_none():
    result = {"url": "https://a.com", "title": "A", "content": "hello"}
    source = source_from_search_result(result, "company_page", "company_profile")
    assert source.company is None


def test_build_evidence_from_results_tags_both_source_and_evidence():
    results = [{"url": "https://a.com", "title": "A", "content": "hello world"}]
    sources, evidence = build_evidence_from_results(results, "company_profile", company="Notion")

    assert sources[0].company == "Notion"
    assert evidence[0].company == "Notion"


def test_raw_text_not_truncated_to_500_for_full_page_content():
    long_content = "x" * 4000
    results = [{"url": "https://a.com", "title": "A", "content": long_content}]
    _, evidence = build_evidence_from_results(results, "company_profile", company="ClickUp")

    assert len(evidence[0].raw_text) == 4000
