from datetime import datetime, timezone
from uuid import uuid4

from app.core.config import settings
from app.core.logging import get_logger, log_run_event
from app.schemas.report import EvidenceItem, Source
from app.services.content_sanitize import sanitize_retrieved_text

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
    """Prefer an extractive sentence from body text (groundable), not SEO title.

    Title-as-claim was a major driver of ~55% grounding: judge checks whether
    SOURCE TEXT entails CLAIM; titles often aren't entailed by the excerpt.
    """
    content = (result.get("content") or result.get("snippet") or "").strip()
    if content:
        for part in content.replace("\n", " ").split(". "):
            sentence = part.strip().rstrip(".")
            if 40 <= len(sentence) <= 220 and " " in sentence:
                return sentence + "."
        # Long body without clear sentences — still prefer body over title.
        if len(content) >= 40:
            return content[:180].rstrip() + ("…" if len(content) > 180 else "")

    title = (result.get("title") or "").strip()
    if title:
        return title

    return "No claim extracted"


def source_from_search_result(
    result: dict,
    source_type: str | None = None,
    track: str = "general",
    company: str | None = None,
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
        company=company,
    )


def evidence_from_search_result(
    result: dict,
    source: Source,
    track: str,
    company: str | None = None,
) -> EvidenceItem:
    content = result.get("content") or result.get("snippet") or ""

    sanitized = sanitize_retrieved_text(
        content[: settings.extract_max_chars] if content else None,
        max_chars=settings.extract_max_chars,
    )
    return EvidenceItem(
        id=str(uuid4()),
        claim=_make_claim({**result, "content": sanitized.text or content}),
        source_id=source.id,
        confidence=infer_confidence(source.source_type),
        evidence_type=track,
        url=source.url,
        raw_text=sanitized.text or None,
        company=company,
    )


def build_evidence_from_results(
    results: list[dict],
    track: str,
    source_type: str | None = None,
    *,
    company: str | None = None,
    run_id: str | None = None,
) -> tuple[list[Source], list[EvidenceItem]]:
    sources: list[Source] = []
    evidence_items: list[EvidenceItem] = []

    for result in results:
        if not (result.get("url") or "").strip():
            continue

        source = source_from_search_result(result, source_type, track, company)
        item = evidence_from_search_result(result, source, track, company)
        sources.append(source)
        evidence_items.append(item)

    log_run_event(
        run_id,
        "evidence_built",
        {
            "track": track,
            "company": company,
            "input_result_count": len(results),
            "source_count": len(sources),
            "evidence_count": len(evidence_items),
            "source_types": sorted({source.source_type for source in sources}),
        },
        logger=logger,
    )

    return sources, evidence_items
