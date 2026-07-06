"""Safety cap on assembled two-sided context. Trims lowest-credibility evidence
first, always keeping both companies represented. Not aggressive — a guard."""

import logging

from app.schemas.report import EvidenceItem, Source

logger = logging.getLogger(__name__)


def _evidence_chars(evidence: list[EvidenceItem]) -> int:
    return sum(len(e.raw_text or e.claim or "") for e in evidence)


def _cred_map(sources: list[Source]) -> dict[str, float]:
    return {s.id: s.credibility_score for s in sources}


def trim_evidence_to_budget(
    evidence: list[EvidenceItem],
    sources: list[Source],
    our: str,
    rival: str,
    max_chars: int,
    *,
    run_id: str | None = None,  # noqa: ARG001 — kept for symmetry / future logging
) -> list[EvidenceItem]:
    """Return evidence trimmed to <= max_chars. Drops lowest-credibility items
    first; never trims either company below one item."""
    if _evidence_chars(evidence) <= max_chars:
        return evidence

    cred = _cred_map(sources)
    kept = list(evidence)

    def _count(company: str) -> int:
        return sum(1 for e in kept if e.company == company)

    dropped = 0
    while _evidence_chars(kept) > max_chars:
        # candidates: droppable without zeroing a side (None-company always droppable)
        candidates = [
            e for e in kept
            if e.company not in (our, rival)
            or (e.company == our and _count(our) > 1)
            or (e.company == rival and _count(rival) > 1)
        ]
        if not candidates:
            break
        victim = min(candidates, key=lambda e: cred.get(e.source_id, 0.0))
        kept.remove(victim)
        dropped += 1

    if dropped:
        logger.info(
            "context_budget: trimmed %d evidence item(s) to fit %d-char cap "
            "(our=%d, rival=%d remaining).",
            dropped, max_chars, _count(our), _count(rival),
        )
    return kept
