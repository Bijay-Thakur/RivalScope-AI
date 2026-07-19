"""Downstream claim policy — unsupported claims must not drive decisive narrative."""

from __future__ import annotations

from app.schemas.report import VerifiedClaim

DECISIVE_STATUSES = frozenset({"verified", "mock_verified"})
ALLOWED_WITH_QUALIFIER = frozenset({"verified", "weakly_supported", "mock_verified"})


def filter_decisive_claims(claims: list[VerifiedClaim]) -> list[VerifiedClaim]:
    """Claims allowed to drive strengths/weaknesses/advantages (verified only)."""
    return [c for c in claims if c.verification_status in DECISIVE_STATUSES]


def filter_report_input_claims(claims: list[VerifiedClaim]) -> list[VerifiedClaim]:
    """Claims passed into report context: verified + weakly_supported (marked)."""
    return [c for c in claims if c.verification_status in ALLOWED_WITH_QUALIFIER]


def format_claims_for_report_context(claims: list[VerifiedClaim]) -> str:
    lines: list[str] = ["Checked claims (unsupported already removed):"]
    for c in claims:
        tag = c.verification_status
        lines.append(
            f"- [{tag}] {c.claim} (sources={','.join(c.source_ids) or 'none'})"
        )
    if len(lines) == 1:
        lines.append("(none)")
    return "\n".join(lines)


def status_counts(claims: list[VerifiedClaim]) -> dict[str, int]:
    out: dict[str, int] = {
        "verified": 0,
        "weakly_supported": 0,
        "unsupported": 0,
        "mock_verified": 0,
        "other": 0,
    }
    for c in claims:
        if c.verification_status in out:
            out[c.verification_status] += 1
        else:
            out["other"] += 1
    return out
