import logging

from app.schemas.report import EvidenceItem, Source
from app.schemas.research import ResearchRequest
from app.services.evidence import build_evidence_from_results
from app.services.query_builder import build_all_queries
from app.services.search import dedupe_urls, search_web

logger = logging.getLogger(__name__)

_TRACK_SOURCE_TYPES: dict[str, str | None] = {
    "company_profile": "company_page",
    "product_features": "company_page",
    "pricing": "pricing_page",
    "recent_news": "news",
}


def run_research_track(
    track: str,
    queries: list[str],
    source_type: str | None = None,
    max_results_per_query: int = 3,
) -> dict:
    all_raw: list[dict] = []
    warnings: list[str] = []
    failed = 0

    for query in queries:
        try:
            results = search_web(query, max_results=max_results_per_query)
            all_raw.extend(results)
            logger.debug("Track '%s' query returned %d result(s): %s", track, len(results), query)
        except Exception as exc:
            failed += 1
            msg = f"Search failed for track '{track}' query '{query}' [{type(exc).__name__}]"
            logger.warning(msg)
            warnings.append(msg)

    if failed == len(queries):
        msg = f"Track '{track}': all {len(queries)} quer{'y' if len(queries) == 1 else 'ies'} failed — no results collected."
        logger.error(msg)
        warnings.append(msg)
        return {"sources": [], "evidence": [], "warnings": warnings}

    deduped = dedupe_urls(all_raw)
    sources, evidence = build_evidence_from_results(deduped, track, source_type)

    logger.info(
        "Track '%s': %d source(s), %d evidence item(s) from %d deduplicated result(s)",
        track,
        len(sources),
        len(evidence),
        len(deduped),
    )
    return {"sources": sources, "evidence": evidence, "warnings": warnings}


def run_all_basic_tracks(request: ResearchRequest) -> dict:
    all_queries = build_all_queries(request)

    all_sources: list[Source] = []
    all_evidence: list[EvidenceItem] = []
    all_warnings: list[str] = []

    for track, queries in all_queries.items():
        source_type = _TRACK_SOURCE_TYPES.get(track)
        result = run_research_track(
            track=track,
            queries=queries,
            source_type=source_type,
        )
        all_sources.extend(result["sources"])
        all_evidence.extend(result["evidence"])
        all_warnings.extend(result["warnings"])

    return {
        "sources": all_sources,
        "evidence": all_evidence,
        "warnings": all_warnings,
    }
