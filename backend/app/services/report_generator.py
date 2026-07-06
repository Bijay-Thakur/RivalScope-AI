import logging
from datetime import datetime, timezone

from app.core.config import settings
from app.core.logging import log_run_event
from app.schemas.report import (
    ComparisonMatrix,
    CompetitorReport,
    EvidenceItem,
    SalesBattlecard,
    Source,
    VerifiedClaim,
)
from app.schemas.research import ResearchRequest
from app.services.context_budget import trim_evidence_to_budget
from app.services.json_utils import extract_json_from_text, safe_get_message_text
from app.services.llm import invoke_with_fallback
from app.services.mock_data import build_mock_report
from app.services.prompts import REPORT_GENERATOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_MAX_SOURCES = 10
_MAX_EVIDENCE = 15
_MAX_CLAIMS = 10
_NOT_FOUND = "Pricing information was not found in available sources."


def _safe_str(value, fallback: str) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return fallback


def _safe_list(value, fallback: list) -> list:
    return value if isinstance(value, list) else fallback


def _partition_by_company(
    items: list, our: str, rival: str
) -> tuple[list, list, list]:
    """Split sources/evidence by tagged company. Untagged items -> 'other' (never dropped)."""
    ours, theirs, other = [], [], []
    for item in items:
        if item.company == our:
            ours.append(item)
        elif item.company == rival:
            theirs.append(item)
        else:
            other.append(item)
    return ours, theirs, other


def _append_side_section(
    lines: list[str],
    label: str,
    sources: list[Source],
    evidence: list[EvidenceItem],
) -> None:
    lines.append(f"=== {label} ===")
    lines.append("--- Sources ---")
    for src in sources[:_MAX_SOURCES]:
        lines.append(f"[{src.id}] {src.title} | {src.url} | credibility={src.credibility_score}")
        if src.snippet:
            lines.append(f"  snippet: {src.snippet[:200]}")

    lines.append("--- Evidence ---")
    for item in evidence[:_MAX_EVIDENCE]:
        lines.append(f"- [{item.source_id}] {item.claim}")
        if item.raw_text:
            lines.append(f"  raw: {item.raw_text[:200]}")
    lines.append("")


def _append_comparison_section(
    lines: list[str], request: ResearchRequest, matrix: ComparisonMatrix
) -> None:
    our, rival = request.our_company, request.competitor
    lines.append("=== HEAD-TO-HEAD COMPARISON ===")
    lines.append(f"summary: {matrix.summary}")
    lines.append(f"pricing: {matrix.pricing_comparison}")
    lines.append(f"positioning_gap: {matrix.positioning_gap}")
    for row in matrix.rows:
        lines.append(
            f"- {row.dimension} [advantage={row.advantage}]: "
            f"{our} -> {row.our_value} (src {row.our_source_ids}) | "
            f"{rival} -> {row.competitor_value} (src {row.competitor_source_ids})"
        )
    lines.append("")


def _feature_comparison_from_matrix(
    request: ResearchRequest, matrix: ComparisonMatrix
) -> list[str]:
    our, rival = request.our_company, request.competitor
    return [
        f"{row.dimension}: {our} -> {row.our_value} | {rival} -> {row.competitor_value}"
        for row in matrix.rows
    ]


def _build_context(
    request: ResearchRequest,
    sources: list[Source],
    evidence: list[EvidenceItem],
    verified_claims: list[VerifiedClaim],
    comparison_matrix: ComparisonMatrix | None = None,
    *,
    run_id: str | None = None,
) -> str:
    our, rival = request.our_company, request.competitor

    evidence = trim_evidence_to_budget(
        evidence, sources, our, rival, settings.max_context_chars, run_id=run_id
    )
    our_sources, rival_sources, other_sources = _partition_by_company(sources, our, rival)
    our_evidence, rival_evidence, other_evidence = _partition_by_company(evidence, our, rival)

    lines: list[str] = [
        f"our_company: {our}",
        f"competitor: {rival}",
        f"market: {request.market}",
        f"report_type: {request.report_type}",
        "",
    ]

    _append_side_section(lines, f"OUR COMPANY: {our}", our_sources, our_evidence)
    _append_side_section(lines, f"COMPETITOR: {rival}", rival_sources, rival_evidence)
    if other_sources or other_evidence:
        _append_side_section(lines, "OTHER / UNTAGGED", other_sources, other_evidence)

    if comparison_matrix is not None:
        _append_comparison_section(lines, request, comparison_matrix)

    lines += ["=== VERIFIED CLAIMS ==="]
    for claim in verified_claims[:_MAX_CLAIMS]:
        lines.append(
            f"- [{claim.verification_status} | score={claim.confidence_score}] {claim.claim}"
        )

    return "\n".join(lines)


def _match_claims(evidence: list[EvidenceItem], kws: tuple[str, ...], limit: int) -> list[str]:
    out: list[str] = []
    for item in evidence[:_MAX_EVIDENCE]:
        if any(kw in item.claim.lower() for kw in kws):
            out.append(item.claim)
        if len(out) >= limit:
            break
    return out


def _balanced_extract(
    evidence: list[EvidenceItem],
    our: str,
    rival: str,
    kws: tuple[str, ...],
) -> list[str]:
    """Pull matching claims from BOTH sides so one company can't dominate the fallback."""
    our_ev, rival_ev, _ = _partition_by_company(evidence, our, rival)
    return _match_claims(our_ev, kws, 3) + _match_claims(rival_ev, kws, 3)


_POSITIVE_KWS = ("leader", "top", "best", "fast", "reliable", "trusted", "award", "growth")
_NEGATIVE_KWS = ("limited", "lack", "issue", "complaint", "expensive", "slow", "difficult", "missing")


def _extract_strengths_from_evidence(
    evidence: list[EvidenceItem], our: str, rival: str
) -> list[str]:
    return _balanced_extract(evidence, our, rival, _POSITIVE_KWS)


def _extract_weaknesses_from_evidence(
    evidence: list[EvidenceItem], our: str, rival: str
) -> list[str]:
    return _balanced_extract(evidence, our, rival, _NEGATIVE_KWS)


def _build_fallback_report(
    request: ResearchRequest,
    sources: list[Source],
    evidence: list[EvidenceItem],
    warnings: list[str],
    generated_at: str,
    comparison_matrix: ComparisonMatrix | None = None,
) -> CompetitorReport:
    rival = request.competitor
    our = request.our_company
    if comparison_matrix is not None:
        feature_comparison = _feature_comparison_from_matrix(request, comparison_matrix)
    else:
        feature_comparison = [e.claim for e in evidence[:5]] or ["No evidence available."]

    return CompetitorReport(
        company_snapshot=(
            f"Research data was collected for {rival} (vs {our}) but structured "
            "synthesis failed. Review the raw evidence items below."
        ),
        product_positioning="Not found in available sources.",
        feature_comparison=feature_comparison,
        pricing_intelligence=_NOT_FOUND,
        recent_moves=[],
        strengths=_extract_strengths_from_evidence(evidence, our, rival),
        weaknesses=_extract_weaknesses_from_evidence(evidence, our, rival),
        sales_battlecard=SalesBattlecard(
            talk_tracks=[],
            objection_handling=[],
            landmines=[],
        ),
        comparison_matrix=comparison_matrix,
        evidence=evidence,
        sources=sources,
        confidence_score=45.0,
        generated_at=generated_at,
        research_mode="real",
        warnings=warnings + ["Report synthesis failed — showing collected evidence only."],
    )


def _log_report_fallback(
    run_id: str | None,
    reason: str,
    fallback_type: str,
) -> None:
    log_run_event(
        run_id,
        "report_generator_fallback_used",
        {
            "reason": reason,
            "fallback_type": fallback_type,
        },
        logger=logger,
        level=logging.WARNING,
    )


def generate_competitor_report(
    request: ResearchRequest,
    sources: list[Source],
    evidence: list[EvidenceItem],
    verified_claims: list[VerifiedClaim],
    comparison_matrix: ComparisonMatrix | None = None,
    warnings: list[str] | None = None,
    *,
    run_id: str | None = None,
) -> CompetitorReport:
    warnings = list(warnings or [])
    generated_at = datetime.now(timezone.utc).isoformat()

    log_run_event(
        run_id,
        "report_generator_started",
        {
            "report_type": request.report_type.value,
            "source_count": len(sources),
            "evidence_count": len(evidence),
            "verified_claim_count": len(verified_claims),
            "warning_count": len(warnings),
        },
        logger=logger,
    )

    if not evidence:
        logger.warning("report_generator: no evidence — falling back to mock report.")
        _log_report_fallback(run_id, "no_evidence", "mock_report")
        mock = build_mock_report(request)
        mock.warnings = ["Real research returned no evidence."] + warnings
        mock.generated_at = generated_at
        mock.research_mode = "real"
        mock.comparison_matrix = comparison_matrix
        mock.confidence_score = 15.0  # no evidence at all — should not inherit mock's demo score
        log_run_event(
            run_id,
            "report_generator_completed",
            {
                "confidence_score": mock.confidence_score,
                "used_fallback": True,
                "fallback_type": "mock_report",
            },
            logger=logger,
            level=logging.WARNING,
        )
        return mock

    context = _build_context(
        request, sources, evidence, verified_claims, comparison_matrix, run_id=run_id
    )

    try:
        response = invoke_with_fallback(
            messages=[
                {"role": "system", "content": REPORT_GENERATOR_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Generate a competitor intelligence report from the context below. "
                        "Return JSON only.\n\n" + context
                    ),
                },
            ],
            run_id=run_id,
            call_name="report_generator_llm",
        )
        raw = safe_get_message_text(response)
        data = extract_json_from_text(raw)
    except Exception as exc:
        logger.warning(
            "report_generator: LLM call or parse failed [%s] — using fallback report.",
            type(exc).__name__,
        )
        warnings.append("Report generation failed — showing collected evidence only.")
        _log_report_fallback(run_id, type(exc).__name__, "evidence_only")
        report = _build_fallback_report(
            request, sources, evidence, warnings, generated_at, comparison_matrix
        )
        log_run_event(
            run_id,
            "report_generator_completed",
            {
                "confidence_score": report.confidence_score,
                "used_fallback": True,
                "fallback_type": "evidence_only",
            },
            logger=logger,
            level=logging.WARNING,
        )
        return report

    if not isinstance(data, dict):
        logger.warning("report_generator: unexpected JSON type — using fallback report.")
        warnings.append("Report generation returned unexpected JSON — showing collected evidence only.")
        _log_report_fallback(run_id, "invalid_json_shape", "evidence_only")
        report = _build_fallback_report(
            request, sources, evidence, warnings, generated_at, comparison_matrix
        )
        log_run_event(
            run_id,
            "report_generator_completed",
            {
                "confidence_score": report.confidence_score,
                "used_fallback": True,
                "fallback_type": "evidence_only",
            },
            logger=logger,
            level=logging.WARNING,
        )
        return report

    try:
        bc_raw = data.get("salesBattlecard") or data.get("sales_battlecard") or {}
        battlecard = SalesBattlecard(
            talk_tracks=_safe_list(bc_raw.get("talkTracks") or bc_raw.get("talk_tracks"), []),
            objection_handling=_safe_list(
                bc_raw.get("objectionHandling") or bc_raw.get("objection_handling"), []
            ),
            landmines=_safe_list(bc_raw.get("landmines"), []),
        )

        raw_score = data.get("confidenceScore") or data.get("confidence_score") or 50
        try:
            score = float(raw_score)
            if 0 < score <= 1.0:
                score = score * 100.0  # tolerate a model returning a 0-1 fraction despite the prompt
            score = max(0.0, min(100.0, score))
        except (TypeError, ValueError):
            score = 50.0

        pricing = (
            data.get("pricingIntelligence")
            or data.get("pricing_intelligence")
            or _NOT_FOUND
        )

        report = CompetitorReport(
            company_snapshot=_safe_str(
                data.get("companySnapshot") or data.get("company_snapshot"),
                "Not found in available sources.",
            ),
            product_positioning=_safe_str(
                data.get("productPositioning") or data.get("product_positioning"),
                "Not found in available sources.",
            ),
            feature_comparison=(
                _feature_comparison_from_matrix(request, comparison_matrix)
                if comparison_matrix is not None
                else _safe_list(
                    data.get("featureComparison") or data.get("feature_comparison"), []
                )
            ),
            pricing_intelligence=_safe_str(pricing, _NOT_FOUND),
            recent_moves=_safe_list(
                data.get("recentMoves") or data.get("recent_moves"), []
            ),
            strengths=_safe_list(data.get("strengths"), []),
            weaknesses=_safe_list(data.get("weaknesses"), []),
            sales_battlecard=battlecard,
            comparison_matrix=comparison_matrix,
            evidence=evidence,
            sources=sources,
            confidence_score=score,
            generated_at=generated_at,
            research_mode="real",
            warnings=warnings,
        )
    except Exception as exc:
        logger.warning(
            "report_generator: schema construction failed [%s] — using fallback report.",
            type(exc).__name__,
        )
        warnings.append("Report schema construction failed — showing collected evidence only.")
        _log_report_fallback(run_id, type(exc).__name__, "evidence_only")
        report = _build_fallback_report(
            request, sources, evidence, warnings, generated_at, comparison_matrix
        )
        log_run_event(
            run_id,
            "report_generator_completed",
            {
                "confidence_score": report.confidence_score,
                "used_fallback": True,
                "fallback_type": "evidence_only",
            },
            logger=logger,
            level=logging.WARNING,
        )
        return report

    log_run_event(
        run_id,
        "report_generator_completed",
        {
            "confidence_score": report.confidence_score,
            "used_fallback": False,
            "source_count": len(sources),
            "evidence_count": len(evidence),
            "warning_count": len(warnings),
        },
        logger=logger,
    )
    return report
