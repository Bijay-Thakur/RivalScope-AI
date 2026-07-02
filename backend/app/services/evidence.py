from datetime import datetime, timezone
from uuid import uuid4

from app.core.logging import get_logger, log_run_event
from app.schemas.report import EvidenceItem, Source

logger = get_logger(__name__)


def detect_source_type(url: str, title: str, track: str) -> str:
    combined = (url + " " + title).lower()

    if "pricing" in combined or "/plans" in combined:
        return "pricing_page"

    if track == "recent_news":
        return "news"

    if any(kw in combined for kw in ("/docs", "/help", "/support", "documentation", "knowledge base")):
        return "docs"

    if any(kw in combined for kw in ("/about", "/product", "/features", "/solutions", "/platform")):
        return "company_page"

    return "other"


def estimate_credibility(url: str, source_type: str) -> float:  # noqa: ARG001
    return {
        "pricing_page": 0.9,
        "company_page": 0.9,
        "docs": 0.85,
        "news": 0.75,
        "blog": 0.65,
    }.get(source_type, 0.5)


def infer_confidence(source_type: str) -> str:
    if source_type in {"company_page", "pricing_page", "docs"}:
        return "high"
    if source_type in {"news", "blog"}:
        return "medium"
    return "low"


def _make_claim(result: dict) -> str:
    title = (result.get("title") or "").strip()
    if title:
        return title

    content = (result.get("content") or result.get("snippet") or "").strip()
    if content:
        sentence_end = content.find(". ")
        if 0 < sentence_end < 120:
            return content[: sentence_end + 1]
        return content[:120]

    return "No claim extracted"


def source_from_search_result(
    result: dict,
    source_type: str | None = None,
    track: str = "general",
) -> Source:
    url = result.get("url") or ""
    title = result.get("title") or url or "Untitled source"
    resolved_type = source_type or detect_source_type(url, title, track)
    content = result.get("content") or result.get("snippet") or ""

    return Source(
        id=str(uuid4()),
        title=title,
        url=url,
        source_type=resolved_type,
        published_date=None,
        credibility_score=estimate_credibility(url, resolved_type),
        snippet=content[:300] if content else None,
        retrieved_at=datetime.now(timezone.utc).isoformat(),
    )


def evidence_from_search_result(
    result: dict,
    source: Source,
    track: str,
) -> EvidenceItem:
    content = result.get("content") or result.get("snippet") or ""

    return EvidenceItem(
        id=str(uuid4()),
        claim=_make_claim(result),
        source_id=source.id,
        confidence=infer_confidence(source.source_type),
        evidence_type=track,
        url=source.url,
        raw_text=content[:500] if content else None,
    )


def build_evidence_from_results(
    results: list[dict],
    track: str,
    source_type: str | None = None,
    *,
    run_id: str | None = None,
) -> tuple[list[Source], list[EvidenceItem]]:
    sources: list[Source] = []
    evidence_items: list[EvidenceItem] = []

    for result in results:
        if not (result.get("url") or "").strip():
            continue

        source = source_from_search_result(result, source_type, track)
        item = evidence_from_search_result(result, source, track)
        sources.append(source)
        evidence_items.append(item)

    log_run_event(
        run_id,
        "evidence_built",
        {
            "track": track,
            "input_result_count": len(results),
            "source_count": len(sources),
            "evidence_count": len(evidence_items),
            "source_types": sorted({source.source_type for source in sources}),
        },
        logger=logger,
    )

    return sources, evidence_items
