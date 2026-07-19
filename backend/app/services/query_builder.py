from app.schemas.research import ResearchRequest
from app.services.compare_features import FEATURE_BY_ID


def _terms(feature_id: str) -> list[str]:
    feat = FEATURE_BY_ID.get(feature_id)
    return list(feat["search_terms"]) if feat else []


def build_company_profile_queries(
    company: str,
    market: str,
    *,
    rival: str | None = None,  # noqa: ARG001
    features: list[str] | None = None,
) -> list[str]:
    features = features or []
    if "security" in features:
        return [
            f"{company} {_terms('security')[0]}",
            f"{company} company profile overview official",
        ]
    return [
        f"{company} official website about company {market}",
        f"{company} company profile overview {market}",
    ]


def build_product_queries(
    company: str,
    market: str,
    *,
    rival: str | None = None,  # noqa: ARG001
    features: list[str] | None = None,
) -> list[str]:
    features = features or []
    productish = [
        fid
        for fid in ("core_features", "integrations", "ai_capabilities", "collaboration")
        if fid in features
    ]
    if productish:
        queries: list[str] = []
        for fid in productish[:2]:
            term = _terms(fid)[0]
            queries.append(f"{company} {term} official")
        while len(queries) < 2:
            queries.append(f"{company} product features {market} official")
        return queries[:2]
    return [
        f"{company} product features {market} official",
        f"{company} use cases {market} product",
    ]


def build_pricing_queries(
    company: str,
    market: str,
    *,
    rival: str | None = None,  # noqa: ARG001
    features: list[str] | None = None,
) -> list[str]:
    features = features or []
    if "pricing" in features:
        return [
            f"{company} pricing plans official site",
            f"{company} {_terms('pricing')[1]} official",
        ]
    return [
        f"{company} pricing plans official site",
        f"{company} pricing packages {market}",
    ]


def build_news_queries(
    company: str,
    market: str,  # noqa: ARG001
    *,
    rival: str | None = None,  # noqa: ARG001
    features: list[str] | None = None,
) -> list[str]:
    features = features or []
    if "ai_capabilities" in features:
        return [
            f"{company} AI product launch news 2025 2026",
            f"{company} product launch funding partnership 2026",
        ]
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
    feats = list(request.compare_features)
    return {
        track: {
            company: builder(
                company, request.market, rival=rival, features=feats
            )
            for company, rival in sides.items()
        }
        for track, builder in _TRACK_BUILDERS.items()
    }
