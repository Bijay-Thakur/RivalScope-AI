"""Deterministic confidence score (0–100). Application-owned; LLM proposal may be ignored."""

from __future__ import annotations

from app.schemas.report import ComparisonMatrix, EvidenceItem, Source, VerifiedClaim
from app.services.claim_policy import status_counts

# Weights sum to 1.0
_W_SECTION = 0.20
_W_VERIFIED = 0.25
_W_SOURCE_QUALITY = 0.15
_W_PRIMARY = 0.15
_W_COMPARISON = 0.15
_W_PENALTIES = 0.10


def _avg_source_quality(sources: list[Source]) -> float:
    if not sources:
        return 0.0
    return sum(max(0.0, min(1.0, s.credibility_score)) for s in sources) / len(sources)


def _primary_coverage(sources: list[Source]) -> float:
    if not sources:
        return 0.0
    primary = {"company_page", "pricing_page", "docs"}
    return sum(1 for s in sources if s.source_type in primary) / len(sources)


def _comparison_fill(matrix: ComparisonMatrix | None) -> float:
    if matrix is None or not matrix.rows:
        return 0.0
    filled = 0
    total = 0
    for row in matrix.rows:
        for val in (row.our_value, row.competitor_value):
            total += 1
            if val and "not found in available sources" not in val.lower():
                filled += 1
    return filled / total if total else 0.0


def compute_confidence_score(
    *,
    sources: list[Source],
    evidence: list[EvidenceItem],
    verified_claims: list[VerifiedClaim],
    comparison_matrix: ComparisonMatrix | None,
    section_fill_ratio: float = 0.7,
) -> float:
    """Deterministic confidence.

    Inputs:
    - section_fill_ratio: share of major narrative sections non-empty (caller)
    - verified / weakly / unsupported claim mix
    - mean source credibility
    - primary-source share
    - comparison cell fill
    Penalties: unsupported share, missing pricing sources, untagged company sources.
    """
    counts = status_counts(verified_claims)
    total_c = max(1, sum(counts.values()) - counts["other"])
    verified_ratio = counts["verified"] / total_c
    unsupported_ratio = counts["unsupported"] / total_c
    weak_ratio = counts["weakly_supported"] / total_c

    quality = _avg_source_quality(sources)
    primary = _primary_coverage(sources)
    cmp_fill = _comparison_fill(comparison_matrix)

    has_pricing = any(s.source_type == "pricing_page" for s in sources)
    untagged = sum(1 for s in sources if not s.company) / max(1, len(sources))

    base = (
        _W_SECTION * max(0.0, min(1.0, section_fill_ratio))
        + _W_VERIFIED * verified_ratio
        + _W_SOURCE_QUALITY * quality
        + _W_PRIMARY * primary
        + _W_COMPARISON * cmp_fill
    )
    # Penalties folded into remaining weight budget
    penalty = (
        0.45 * unsupported_ratio
        + 0.20 * weak_ratio * 0.5
        + (0.20 if not has_pricing else 0.0)
        + 0.15 * untagged
    )
    score = 100.0 * (base + _W_PENALTIES * (1.0 - min(1.0, penalty)))
    # Evidence volume floor/ceiling nudge
    if len(evidence) < 3:
        score *= 0.85
    return round(max(0.0, min(100.0, score)), 1)
