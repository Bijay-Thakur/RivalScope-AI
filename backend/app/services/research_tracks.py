import logging

from app.core.config import settings
from app.core.logging import log_run_event
from app.schemas.report import EvidenceItem, Source
from app.schemas.research import ResearchRequest
from app.services.evidence import build_evidence_from_results
from app.services.query_builder import build_all_queries
from app.services.search import dedupe_urls, extract_urls, search_web

logger = logging.getLogger(__name__)

_TRACK_SOURCE_TYPES: dict[str, str | None] = {
    "company_profile": "company_page",
    "product_features": "company_page",
    "pricing": "pricing_page",
    "recent_news": "news",
}


def _extract_top_n(
    results: list[dict],
    *,
    track: str,
    company: str,
    run_id: str | None = None,
) -> dict[str, str]:
    """Full-page extract for top-N ranked results. url -> content map. Never raises."""
    ranked = sorted(results, key=lambda r: r.get("score") or 0, reverse=True)
    top_urls = [r["url"] for r in ranked[: settings.extract_top_n] if r.get("url")]
    if not top_urls:
        return {}

    try:
        pages = extract_urls(top_urls, run_id=run_id, track=track)
    except Exception as exc:
        msg = (
            f"extract_urls failed for track '{track}' company '{company}' "
            f"[{type(exc).__name__}] — falling back to snippets."
        )
        logger.warning(msg)
        log_run_event(
            run_id,
            "extract_urls_failed",
            {"track": track, "company": company, "error_type": type(exc).__name__},
            logger=logger,
            level=logging.WARNING,
        )
        return {}

    return {p["url"]: p["content"] for p in pages if p.get("url") and p.get("content")}


def _merge_full_content(results: list[dict], extracted: dict[str, str]) -> list[dict]:
    if not extracted:
        return results

    merged: list[dict] = []
    for item in results:
        full = extracted.get(item.get("url") or "")
        if full:
            enriched = dict(item)
            enriched["content"] = full[: settings.extract_max_chars]
            merged.append(enriched)
        else:
            merged.append(item)  # extract missed this url — snippet fallback, never lose source
    return merged


def _run_company_track(
    track: str,
    company: str,
    queries: list[str],
    source_type: str | None,
    max_results_per_query: int,
    *,
    run_id: str | None = None,
) -> dict:
    all_raw: list[dict] = []
    warnings: list[str] = []
    failed = 0

    for query in queries:
        try:
            results = search_web(
                query,
                max_results=max_results_per_query,
                run_id=run_id,
                track=track,
            )
            all_raw.extend(results)
            logger.debug(
                "Track '%s' company '%s' query returned %d result(s): %s",
                track, company, len(results), query,
            )
        except Exception as exc:
            failed += 1
            msg = f"Search failed for track '{track}' company '{company}' query '{query}' [{type(exc).__name__}]"
            logger.warning(msg)
            warnings.append(msg)

    if queries and failed == len(queries):
        msg = (
            f"Track '{track}' company '{company}': all {len(queries)} "
            f"quer{'y' if len(queries) == 1 else 'ies'} failed — no results collected."
        )
        logger.error(msg)
        warnings.append(msg)
        return {"sources": [], "evidence": [], "warnings": warnings}

    deduped = dedupe_urls(all_raw)
    extracted = _extract_top_n(deduped, track=track, company=company, run_id=run_id)
    enriched = _merge_full_content(deduped, extracted)

    sources, evidence = build_evidence_from_results(
        enriched,
        track,
        source_type,
        company=company,
        run_id=run_id,
    )

    logger.info(
        "Track '%s' company '%s': %d source(s), %d evidence item(s), %d full-page extract(s)",
        track, company, len(sources), len(evidence), len(extracted),
    )
    return {"sources": sources, "evidence": evidence, "warnings": warnings}


def run_research_track(
    track: str,
    queries_by_company: dict[str, list[str]],
    source_type: str | None = None,
    max_results_per_query: int = 3,
    *,
    run_id: str | None = None,
) -> dict:
    all_sources: list[Source] = []
    all_evidence: list[EvidenceItem] = []
    all_warnings: list[str] = []

    for company, queries in queries_by_company.items():
        result = _run_company_track(
            track, company, queries, source_type, max_results_per_query, run_id=run_id
        )
        all_sources.extend(result["sources"])
        all_evidence.extend(result["evidence"])
        all_warnings.extend(result["warnings"])

    return {"sources": all_sources, "evidence": all_evidence, "warnings": all_warnings}


def run_all_basic_tracks(
    request: ResearchRequest,
    *,
    run_id: str | None = None,
) -> dict:
    all_queries = build_all_queries(request)

    all_sources: list[Source] = []
    all_evidence: list[EvidenceItem] = []
    all_warnings: list[str] = []

    for track, queries_by_company in all_queries.items():
        source_type = _TRACK_SOURCE_TYPES.get(track)
        result = run_research_track(
            track=track,
            queries_by_company=queries_by_company,
            source_type=source_type,
            run_id=run_id,
        )
        all_sources.extend(result["sources"])
        all_evidence.extend(result["evidence"])
        all_warnings.extend(result["warnings"])

    return {
        "sources": all_sources,
        "evidence": all_evidence,
        "warnings": all_warnings,
    }
