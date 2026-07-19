"""Independent post-generation grounding checks (deterministic first).

Does not ask the report generator to certify itself. Strips or rewrites
ungrounded / contradicted narrative fragments before return.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.schemas.report import (
    ComparisonMatrix,
    CompetitorReport,
    EvidenceItem,
    VerifiedClaim,
)
from app.services.claim_policy import filter_report_input_claims

_NOT_FOUND = "not found in available sources"
_PRICE_RE = re.compile(
    r"\$\s?\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s*(?:usd|eur|gbp|/mo|/month|/yr|/year)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class GroundingFinding:
    field_path: str
    statement: str
    status: str  # grounded | partially_grounded | ungrounded | contradicted
    source_ids: tuple[str, ...]
    reason: str


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]{4,}", (text or "").lower()) if t}


def _support_corpus(
    evidence: list[EvidenceItem],
    claims: list[VerifiedClaim],
    matrix: ComparisonMatrix | None,
) -> str:
    parts: list[str] = []
    for e in evidence:
        parts.append(e.claim or "")
        parts.append(e.raw_text or "")
    for c in filter_report_input_claims(claims):
        parts.append(c.claim or "")
    if matrix:
        for row in matrix.rows:
            parts.append(row.our_value or "")
            parts.append(row.competitor_value or "")
        parts.append(matrix.pricing_comparison or "")
        parts.append(matrix.summary or "")
    return "\n".join(parts).lower()


def _score_statement(statement: str, corpus: str) -> tuple[str, str]:
    s = (statement or "").strip()
    if not s or _NOT_FOUND in s.lower():
        return "grounded", "empty_or_not_found"

    # Price figures must appear in corpus when claimed
    for m in _PRICE_RE.findall(s):
        needle = re.sub(r"\s+", "", m.lower())
        corpus_compact = re.sub(r"\s+", "", corpus)
        if needle not in corpus_compact and re.sub(r"[^\d.]", "", needle) not in re.sub(
            r"[^\d.]", "", corpus_compact
        ):
            return "ungrounded", f"price_or_figure_not_in_evidence:{m}"

    toks = _tokens(s)
    if not toks:
        return "partially_grounded", "too_short_to_verify"
    hits = sum(1 for t in toks if t in corpus)
    ratio = hits / len(toks)
    if ratio >= 0.45:
        return "grounded", f"token_overlap={ratio:.2f}"
    if ratio >= 0.25:
        return "partially_grounded", f"token_overlap={ratio:.2f}"
    return "ungrounded", f"token_overlap={ratio:.2f}"


def verify_report_grounding(
    report: CompetitorReport,
    *,
    evidence: list[EvidenceItem],
    verified_claims: list[VerifiedClaim],
) -> list[GroundingFinding]:
    corpus = _support_corpus(evidence, verified_claims, report.comparison_matrix)
    findings: list[GroundingFinding] = []

    def check(path: str, text: str) -> None:
        status, reason = _score_statement(text, corpus)
        findings.append(
            GroundingFinding(
                field_path=path,
                statement=text[:240],
                status=status,
                source_ids=(),
                reason=reason,
            )
        )

    check("company_snapshot", report.company_snapshot)
    check("product_positioning", report.product_positioning)
    check("pricing_intelligence", report.pricing_intelligence)
    for i, line in enumerate(report.strengths):
        check(f"strengths[{i}]", line)
    for i, line in enumerate(report.weaknesses):
        check(f"weaknesses[{i}]", line)
    for i, line in enumerate(report.recent_moves):
        check(f"recent_moves[{i}]", line)
    for i, line in enumerate(report.sales_battlecard.talk_tracks):
        check(f"sales_battlecard.talk_tracks[{i}]", line)
    for i, line in enumerate(report.sales_battlecard.objection_handling):
        check(f"sales_battlecard.objection_handling[{i}]", line)
    for i, line in enumerate(report.sales_battlecard.landmines):
        check(f"sales_battlecard.landmines[{i}]", line)

    # Absence-as-weakness heuristic
    for i, line in enumerate(report.weaknesses):
        low = line.lower()
        if "no evidence" in low or "not found" in low or "couldn't find" in low:
            findings.append(
                GroundingFinding(
                    field_path=f"weaknesses[{i}]",
                    statement=line[:240],
                    status="contradicted",
                    source_ids=(),
                    reason="absence_of_evidence_as_weakness",
                )
            )
    return findings


def apply_grounding_repairs(
    report: CompetitorReport,
    findings: list[GroundingFinding],
) -> tuple[CompetitorReport, list[str]]:
    """Remove ungrounded/contradicted list items; soften bad string fields."""
    bad_paths = {
        f.field_path
        for f in findings
        if f.status in {"ungrounded", "contradicted"}
    }
    warnings: list[str] = []

    def keep_list(items: list[str], prefix: str) -> list[str]:
        kept: list[str] = []
        for i, item in enumerate(items):
            path = f"{prefix}[{i}]"
            if path in bad_paths:
                warnings.append(f"Removed ungrounded {path}")
                continue
            kept.append(item)
        return kept

    def soften(field: str, value: str) -> str:
        if field in bad_paths:
            warnings.append(f"Softened ungrounded {field}")
            return "Not found in available sources."
        return value

    report.company_snapshot = soften("company_snapshot", report.company_snapshot)
    report.product_positioning = soften(
        "product_positioning", report.product_positioning
    )
    report.pricing_intelligence = soften(
        "pricing_intelligence", report.pricing_intelligence
    )
    report.strengths = keep_list(report.strengths, "strengths")
    report.weaknesses = keep_list(report.weaknesses, "weaknesses")
    report.recent_moves = keep_list(report.recent_moves, "recent_moves")
    report.sales_battlecard.talk_tracks = keep_list(
        report.sales_battlecard.talk_tracks, "sales_battlecard.talk_tracks"
    )
    report.sales_battlecard.objection_handling = keep_list(
        report.sales_battlecard.objection_handling,
        "sales_battlecard.objection_handling",
    )
    report.sales_battlecard.landmines = keep_list(
        report.sales_battlecard.landmines, "sales_battlecard.landmines"
    )
    report.warnings = list(report.warnings) + warnings
    return report, warnings
