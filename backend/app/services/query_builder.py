from app.schemas.research import ResearchRequest


def build_company_profile_queries(
    our_company: str, competitor: str, market: str
) -> list[str]:
    return [
        f"{competitor} official website about company {market}",
        f"{competitor} company profile overview {market}",
        f"{our_company} vs {competitor} {market}",
    ]


def build_product_queries(
    our_company: str, competitor: str, market: str
) -> list[str]:
    return [
        f"{competitor} product features {market} official",
        f"{competitor} use cases {market} product",
        f"{competitor} vs {our_company} features comparison {market}",
    ]


def build_pricing_queries(
    our_company: str, competitor: str, market: str
) -> list[str]:
    return [
        f"{competitor} pricing plans official site",
        f"{competitor} pricing packages {market}",
        f"{competitor} plans cost per seat {market}",
    ]


def build_news_queries(
    our_company: str, competitor: str, market: str
) -> list[str]:
    return [
        f"{competitor} latest news 2025 2026",
        f"{competitor} product launch funding partnership 2026",
        f"{competitor} strategic moves {market} recent",
    ]


def build_all_queries(request: ResearchRequest) -> dict[str, list[str]]:
    args = (request.our_company, request.competitor, request.market)
    return {
        "company_profile": build_company_profile_queries(*args),
        "product_features": build_product_queries(*args),
        "pricing": build_pricing_queries(*args),
        "recent_news": build_news_queries(*args),
    }
