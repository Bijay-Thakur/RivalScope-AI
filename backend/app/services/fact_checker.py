import logging
from uuid import uuid4

from app.core.logging import log_run_event
from app.schemas.report import EvidenceItem, Source, VerifiedClaim
from app.services.json_utils import extract_json_from_text, safe_get_message_text
from app.services.llm import invoke_with_fallback
from app.services.prompts import FACT_CHECKER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


def _conservative_claims(evidence: list[EvidenceItem]) -> list[VerifiedClaim]:
    return [
        VerifiedClaim(
            id=str(uuid4()),
            claim=item.claim,
            source_ids=[item.source_id],
            verification_status="weakly_supported",
            confidence_score=0.5,
        )
        for item in evidence
    ]


def _build_evidence_packet(
    evidence: list[EvidenceItem],
    source_map: dict[str, Source],
) -> str:
    lines = ["Evidence items to verify:"]
    for item in evidence:
        src = source_map.get(item.source_id)
        entry = {
            "id": item.id,
            "claim": item.claim,
            "source_id": item.source_id,
            "source_title": src.title if src else None,
            "source_url": (src.url if src else None) or item.url,
            "raw_text": item.raw_text or (src.snippet if src else None),
        }
        lines.append(str(entry))
    lines.append(
        "\nReturn a JSON array of objects with keys: "
        "id, claim, source_ids (array), verification_status, confidence_score."
    )
    return "\n".join(lines)


def verify_evidence_claims(
    evidence: list[EvidenceItem],
    sources: list[Source],
    max_claims: int = 10,
    *,
    run_id: str | None = None,
) -> list[VerifiedClaim]:
    if not evidence:
        return []

    batch = evidence[:max_claims]
    source_map = {s.id: s for s in sources}
    user_message = _build_evidence_packet(batch, source_map)

    log_run_event(
        run_id,
        "fact_checker_started",
        {
            "evidence_count": len(evidence),
            "claims_to_verify": len(batch),
            "source_count": len(sources),
        },
        logger=logger,
    )

    try:
        response = invoke_with_fallback(
            messages=[
                {"role": "system", "content": FACT_CHECKER_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ]
        )
        raw = safe_get_message_text(response)
        parsed = extract_json_from_text(raw)
    except Exception as exc:
        logger.warning(
            "Fact checker LLM call or parse failed [%s] — returning conservative claims.",
            type(exc).__name__,
        )
        results = _conservative_claims(batch)
        log_run_event(
            run_id,
            "fact_checker_completed",
            {
                "verified_count": len(results),
                "used_conservative_fallback": True,
                "error_type": type(exc).__name__,
            },
            logger=logger,
            level=logging.WARNING,
        )
        return results

    if isinstance(parsed, dict):
        parsed = parsed.get("checked_claims", [])

    if not isinstance(parsed, list):
        logger.warning("Fact checker returned non-list JSON — returning conservative claims.")
        results = _conservative_claims(batch)
        log_run_event(
            run_id,
            "fact_checker_completed",
            {
                "verified_count": len(results),
                "used_conservative_fallback": True,
                "error_type": "invalid_json_shape",
            },
            logger=logger,
            level=logging.WARNING,
        )
        return results

    results: list[VerifiedClaim] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        try:
            results.append(
                VerifiedClaim(
                    id=item.get("id") or str(uuid4()),
                    claim=item.get("claim", ""),
                    source_ids=item.get("source_ids") or [],
                    verification_status=item.get("verification_status", "weakly_supported"),
                    confidence_score=float(item.get("confidence_score", 0.5)),
                )
            )
        except Exception as exc:
            logger.warning("Skipping malformed claim entry [%s].", type(exc).__name__)

    if not results:
        logger.warning("Fact checker produced no valid claims — returning conservative claims.")
        results = _conservative_claims(batch)
        log_run_event(
            run_id,
            "fact_checker_completed",
            {
                "verified_count": len(results),
                "used_conservative_fallback": True,
                "error_type": "empty_results",
            },
            logger=logger,
            level=logging.WARNING,
        )
        return results

    status_counts: dict[str, int] = {}
    for claim in results:
        status_counts[claim.verification_status] = (
            status_counts.get(claim.verification_status, 0) + 1
        )

    log_run_event(
        run_id,
        "fact_checker_completed",
        {
            "verified_count": len(results),
            "used_conservative_fallback": False,
            "verification_status_counts": status_counts,
        },
        logger=logger,
    )
    return results
