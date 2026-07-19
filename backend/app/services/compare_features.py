"""Buyer-critical compare dimensions — drive Tavily queries + comparison matrix.

Ids are stable API values. Labels are UI / prompt text. search_terms are
Tavily-friendly phrases that surface official/product pages (not vague category).
"""

from __future__ import annotations

from typing import TypedDict


class CompareFeature(TypedDict):
    id: str
    label: str
    search_terms: list[str]
    description: str


COMPARE_FEATURES: list[CompareFeature] = [
    {
        "id": "pricing",
        "label": "Pricing & packaging",
        "search_terms": ["pricing plans", "subscription tiers", "enterprise pricing"],
        "description": "Plans, seats, free tier, enterprise quotes",
    },
    {
        "id": "core_features",
        "label": "Core product features",
        "search_terms": ["product features", "platform capabilities", "key features"],
        "description": "Flagship workflows and capability depth",
    },
    {
        "id": "integrations",
        "label": "Integrations & ecosystem",
        "search_terms": ["integrations", "API marketplace", "apps integrations"],
        "description": "Native connectors, API, partner apps",
    },
    {
        "id": "security",
        "label": "Security & admin",
        "search_terms": ["security compliance SOC2", "SSO admin controls", "enterprise security"],
        "description": "SSO, SOC2, roles, audit, compliance",
    },
    {
        "id": "ai_capabilities",
        "label": "AI capabilities",
        "search_terms": ["AI features", "AI assistant automation", "generative AI product"],
        "description": "Built-in AI / copilots / automation",
    },
    {
        "id": "collaboration",
        "label": "Collaboration & UX",
        "search_terms": ["collaboration features", "team workspace UX", "real-time collaboration"],
        "description": "Sharing, async/sync collab, usability",
    },
]

FEATURE_BY_ID: dict[str, CompareFeature] = {f["id"]: f for f in COMPARE_FEATURES}
VALID_FEATURE_IDS: frozenset[str] = frozenset(FEATURE_BY_ID)


def normalize_compare_features(raw: list[str] | None) -> list[str]:
    """Dedupe, keep catalog order, drop unknown ids."""
    if not raw:
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    wanted = {x.strip() for x in raw if x and x.strip()}
    for feat in COMPARE_FEATURES:
        fid = feat["id"]
        if fid in wanted and fid not in seen:
            ordered.append(fid)
            seen.add(fid)
    return ordered


def feature_labels(feature_ids: list[str]) -> list[str]:
    return [FEATURE_BY_ID[fid]["label"] for fid in feature_ids if fid in FEATURE_BY_ID]


def market_from_features(feature_ids: list[str]) -> str:
    labels = feature_labels(feature_ids)
    return " · ".join(labels) if labels else "B2B software"


def parse_compare_features_param(raw: str | None) -> list[str]:
    """Comma-separated query param → normalized ids."""
    if not raw or not raw.strip():
        return []
    parts = [p.strip() for p in raw.split(",")]
    return normalize_compare_features(parts)
