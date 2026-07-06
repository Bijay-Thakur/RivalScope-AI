from app.schemas.research import ResearchRequest


def build_company_profile_queries(
    company: str, market: str, *, rival: str | None = None  # noqa: ARG001
) -> list[str]:
    return [
        f"{company} official website about company {market}",
        f"{company} company profile overview {market}",
    ]


def build_product_queries(
    company: str, market: str, *, rival: str | None = None  # noqa: ARG001
) -> list[str]:
    return [
        f"{company} product features {market} official",
        f"{company} use cases {market} product",
    ]


def build_pricing_queries(
    company: str, market: str, *, rival: str | None = None  # noqa: ARG001
) -> list[str]:
    return [
        f"{company} pricing plans official site",
        f"{company} pricing packages {market}",
    ]


def build_news_queries(
    company: str, market: str, *, rival: str | None = None  # noqa: ARG001
) -> list[str]:
    return [
        f"{company} latest news 2025 2026",
        f"{company} product launch funding partnership 2026",
    ]


_TRACK_BUILDERS = {
    "company_profile": build_company_profile_queries,
    "product_features": build_product_queries,
    "pricing": build_pricing_queries,
    "recent_news": build_news_queries,
}


def build_all_queries(request: ResearchRequest) -> dict[str, dict[str, list[str]]]:
    """Symmetric queries for both sides. Shape: dict[track][company] = list[str]."""
    sides = {
        request.our_company: request.competitor,
        request.competitor: request.our_company,
    }
    return {
        track: {
            company: builder(company, request.market, rival=rival)
            for company, rival in sides.items()
        }
        for track, builder in _TRACK_BUILDERS.items()
    }
