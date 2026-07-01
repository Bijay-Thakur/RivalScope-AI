import logging

from langchain_tavily import TavilyExtract, TavilySearch

from app.core.config import settings

logger = logging.getLogger(__name__)


def require_tavily_key() -> None:
    if not settings.has_tavily_key:
        raise ValueError(
            "TAVILY_API_KEY is not set. "
            "Set it in your .env file to enable web search."
        )


def _normalize_search_item(item: dict) -> dict:
    return {
        "title": item.get("title") or "",
        "url": item.get("url") or "",
        "content": item.get("content") or "",
        "score": item.get("score"),
        "raw": item,
    }


def search_web(query: str, max_results: int = 5) -> list[dict]:
    require_tavily_key()

    tool = TavilySearch(
        max_results=max_results,
        tavily_api_key=settings.tavily_api_key,
    )

    try:
        raw = tool.invoke({"query": query})
    except Exception as exc:
        raise RuntimeError(
            f"Tavily search failed for query '{query}': {type(exc).__name__}"
        ) from exc

    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        items = raw.get("results") or []
    else:
        items = []

    normalized = [_normalize_search_item(item) for item in items if isinstance(item, dict)]
    logger.info("search_web: %d result(s) for query '%s'", len(normalized), query)
    return normalized


def extract_urls(urls: list[str]) -> list[dict]:
    if not urls:
        return []

    require_tavily_key()

    tool = TavilyExtract(tavily_api_key=settings.tavily_api_key)

    try:
        raw = tool.invoke({"urls": urls})
    except Exception as exc:
        raise RuntimeError(
            f"Tavily extract failed for {len(urls)} URL(s): {type(exc).__name__}"
        ) from exc

    if isinstance(raw, list):
        pages = raw
    elif isinstance(raw, dict):
        pages = raw.get("results") or []
    else:
        pages = []

    normalized = [
        {
            "url": page.get("url") or "",
            "title": page.get("title") or None,
            "content": page.get("raw_content") or page.get("content") or "",
            "raw": page,
        }
        for page in pages
        if isinstance(page, dict)
    ]

    logger.info(
        "extract_urls: extracted %d page(s) from %d URL(s)",
        len(normalized),
        len(urls),
    )
    return normalized


def dedupe_urls(results: list[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for item in results:
        url = (item.get("url") or "").strip()
        if not url:
            continue
        if url not in seen:
            seen.add(url)
            deduped.append(item)
    return deduped
