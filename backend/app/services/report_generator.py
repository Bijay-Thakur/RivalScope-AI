import logging
from datetime import datetime, timezone

from app.core.logging import log_run_event
from app.schemas.report import (
    CompetitorReport,
    EvidenceItem,
    SalesBattlecard,
    Source,
    VerifiedClaim,
)
from app.schemas.research import ResearchRequest
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


def _build_context(
    request: ResearchRequest,
    sources: list[Source],
    evidence: list[EvidenceItem],
    verified_claims: list[VerifiedClaim],
) -> str:
    lines: list[str] = [
        f"our_company: {request.our_company}",
        f"competitor: {request.competitor}",
        f"market: {request.market}",
        f"report_type: {request.report_type}",
        "",
        "=== SOURCES ===",
    ]
    for src in sources[:_MAX_SOURCES]:
        lines.append(f"[{src.id}] {src.title} | {src.url} | credibility={src.credibility_score}")
        if src.snippet:
            lines.append(f"  snippet: {src.snippet[:200]}")

    lines += ["", "=== EVIDENCE ==="]
    for item in evidence[:_MAX_EVIDENCE]:
        lines.append(f"- [{item.source_id}] {item.claim}")
        if item.raw_text:
            lines.append(f"  raw: {item.raw_text[:200]}")

    lines += ["", "=== VERIFIED CLAIMS ==="]
    for claim in verified_claims[:_MAX_CLAIMS]:
        lines.append(
            f"- [{claim.verification_status} | score={claim.confidence_score}] {claim.claim}"
        )

    return "\n".join(lines)


def _extract_strengths_from_evidence(evidence: list[EvidenceItem]) -> list[str]:
    positive_kws = ("leader", "top", "best", "fast", "reliable", "trusted", "award", "growth")
    out: list[str] = []
    for item in evidence[:_MAX_EVIDENCE]:
        low = item.claim.lower()
        if any(kw in low for kw in positive_kws):
            out.append(item.claim)
        if len(out) >= 3:
            break
    return out


def _extract_weaknesses_from_evidence(evidence: list[EvidenceItem]) -> list[str]:
    negative_kws = ("limited", "lack", "issue", "complaint", "expensive", "slow", "difficult", "missing")
    out: list[str] = []
    for item in evidence[:_MAX_EVIDENCE]:
        low = item.claim.lower()
        if any(kw in low for kw in negative_kws):
            out.append(item.claim)
        if len(out) >= 3:
            break
    return out


def _build_fallback_report(
    request: ResearchRequest,
    sources: list[Source],
    evidence: list[EvidenceItem],
    warnings: list[str],
    generated_at: str,
) -> CompetitorReport:
    rival = request.competitor
    our = request.our_company
    top_claims = [e.claim for e in evidence[:5]] or ["No evidence available."]

    return CompetitorReport(
        company_snapshot=(
            f"Research data was collected for {rival} (vs {our}) but structured "
            "synthesis failed. Review the raw evidence items below."
        ),
        product_positioning="Not found in available sources.",
        feature_comparison=top_claims,
        pricing_intelligence=_NOT_FOUND,
        recent_moves=[],
        strengths=_extract_strengths_from_evidence(evidence),
        weaknesses=_extract_weaknesses_from_evidence(evidence),
        sales_battlecard=SalesBattlecard(
            talk_tracks=[],
            objection_handling=[],
            landmines=[],
        ),
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

    context = _build_context(request, sources, evidence, verified_claims)

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
            ]
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
        report = _build_fallback_report(request, sources, evidence, warnings, generated_at)
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
        report = _build_fallback_report(request, sources, evidence, warnings, generated_at)
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
            feature_comparison=_safe_list(
                data.get("featureComparison") or data.get("feature_comparison"), []
            ),
            pricing_intelligence=_safe_str(pricing, _NOT_FOUND),
            recent_moves=_safe_list(
                data.get("recentMoves") or data.get("recent_moves"), []
            ),
            strengths=_safe_list(data.get("strengths"), []),
            weaknesses=_safe_list(data.get("weaknesses"), []),
            sales_battlecard=battlecard,
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
        report = _build_fallback_report(request, sources, evidence, warnings, generated_at)
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
