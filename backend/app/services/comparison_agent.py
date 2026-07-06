"""Comparison/analyst agent — structured, grounded head-to-head from two dossiers."""

import logging

from app.core.config import settings
from app.core.logging import log_run_event
from app.schemas.report import (
    ComparisonMatrix,
    EvidenceItem,
    FeatureComparisonRow,
    Source,
    VerifiedClaim,
)
from app.schemas.research import ResearchRequest
from app.services.context_budget import trim_evidence_to_budget
from app.services.json_utils import extract_json_from_text, safe_get_message_text
from app.services.llm import invoke_with_fallback
from app.services.prompts import COMPARISON_AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_MAX_SOURCES = 12
_MAX_EVIDENCE = 18
_ALLOWED_ADVANTAGE = {"our", "competitor", "parity", "unclear"}
_NOT_FOUND = "Not found in available sources."


def _partition(items: list, our: str, rival: str) -> tuple[list, list, list]:
    ours, theirs, other = [], [], []
    for item in items:
        if item.company == our:
            ours.append(item)
        elif item.company == rival:
            theirs.append(item)
        else:
            other.append(item)
    return ours, theirs, other


def _append_side(lines: list[str], label: str, sources: list[Source], evidence: list[EvidenceItem]) -> None:
    lines.append(f"=== {label} ===")
    lines.append("--- Sources ---")
    for src in sources[:_MAX_SOURCES]:
        lines.append(f"[{src.id}] {src.title} | {src.url}")
    lines.append("--- Evidence ---")
    for item in evidence[:_MAX_EVIDENCE]:
        lines.append(f"- [{item.source_id}] {item.claim}")
        if item.raw_text:
            lines.append(f"  raw: {item.raw_text[:400]}")
    lines.append("")


def _build_context(
    request: ResearchRequest,
    sources: list[Source],
    evidence: list[EvidenceItem],
    *,
    run_id: str | None = None,
) -> str:
    our, rival = request.our_company, request.competitor
    evidence = trim_evidence_to_budget(
        evidence, sources, our, rival, settings.max_context_chars, run_id=run_id
    )
    our_src, rival_src, _ = _partition(sources, our, rival)
    our_ev, rival_ev, _ = _partition(evidence, our, rival)

    lines = [
        f"our_company: {our}",
        f"competitor: {rival}",
        f"market: {request.market}",
        "",
    ]
    _append_side(lines, f"OUR COMPANY: {our}", our_src, our_ev)
    _append_side(lines, f"COMPETITOR: {rival}", rival_src, rival_ev)
    return "\n".join(lines)


def _parse_row(raw: dict) -> FeatureComparisonRow:
    advantage = str(raw.get("advantage") or "unclear").strip().lower()
    if advantage not in _ALLOWED_ADVANTAGE:
        advantage = "unclear"
    return FeatureComparisonRow(
        dimension=str(raw.get("dimension") or "").strip() or "Unspecified dimension",
        our_value=str(raw.get("ourValue") or raw.get("our_value") or _NOT_FOUND).strip(),
        competitor_value=str(
            raw.get("competitorValue") or raw.get("competitor_value") or _NOT_FOUND
        ).strip(),
        our_source_ids=[str(s) for s in (raw.get("ourSourceIds") or raw.get("our_source_ids") or [])],
        competitor_source_ids=[
            str(s) for s in (raw.get("competitorSourceIds") or raw.get("competitor_source_ids") or [])
        ],
        advantage=advantage,
    )


def _matrix_from_data(data: dict) -> ComparisonMatrix:
    rows_raw = data.get("rows") or []
    rows = [_parse_row(r) for r in rows_raw if isinstance(r, dict)]
    if not rows:
        raise ValueError("no valid rows in comparison JSON")
    return ComparisonMatrix(
        rows=rows,
        pricing_comparison=str(
            data.get("pricingComparison") or data.get("pricing_comparison") or _NOT_FOUND
        ).strip(),
        positioning_gap=str(
            data.get("positioningGap") or data.get("positioning_gap") or _NOT_FOUND
        ).strip(),
        summary=str(data.get("summary") or "").strip() or "Comparison summary unavailable.",
    )


def build_fallback_matrix(
    request: ResearchRequest,
    sources: list[Source],
    evidence: list[EvidenceItem],
) -> ComparisonMatrix:
    """Deterministic minimal matrix when LLM output unusable — pipeline never dies."""
    our, rival = request.our_company, request.competitor
    our_ev, rival_ev, _ = _partition(evidence, our, rival)

    def _cell(items: list[EvidenceItem]) -> tuple[str, list[str]]:
        if not items:
            return _NOT_FOUND, []
        return items[0].claim[:200], [items[0].source_id]

    our_val, our_ids = _cell(our_ev)
    rival_val, rival_ids = _cell(rival_ev)

    rows = [
        FeatureComparisonRow(
            dimension="Overall positioning (auto-derived)",
            our_value=our_val,
            competitor_value=rival_val,
            our_source_ids=our_ids,
            competitor_source_ids=rival_ids,
            advantage="unclear",
        )
    ]
    return ComparisonMatrix(
        rows=rows,
        pricing_comparison=_NOT_FOUND,
        positioning_gap=_NOT_FOUND,
        summary=(
            f"Structured comparison unavailable for {our} vs {rival}; "
            "auto-derived from evidence."
        ),
    )


def build_comparison_matrix(
    request: ResearchRequest,
    sources: list[Source],
    evidence: list[EvidenceItem],
    verified_claims: list[VerifiedClaim],  # noqa: ARG001 — reserved; context uses evidence
    *,
    run_id: str | None = None,
) -> ComparisonMatrix:
    log_run_event(
        run_id,
        "comparison_agent_started",
        {"source_count": len(sources), "evidence_count": len(evidence)},
        logger=logger,
    )

    context = _build_context(request, sources, evidence, run_id=run_id)

    try:
        response = invoke_with_fallback(
            messages=[
                {"role": "system", "content": COMPARISON_AGENT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Produce a structured head-to-head ComparisonMatrix from the context "
                        "below. Return JSON only.\n\n" + context
                    ),
                },
            ],
            run_id=run_id,
            call_name="comparison_agent_llm",
        )
        raw = safe_get_message_text(response)
        data = extract_json_from_text(raw)
        if not isinstance(data, dict):
            raise ValueError(f"unexpected JSON type: {type(data).__name__}")
        matrix = _matrix_from_data(data)
    except Exception as exc:
        logger.warning(
            "comparison_agent: LLM/parse failed [%s] — using fallback matrix.",
            type(exc).__name__,
        )
        log_run_event(
            run_id,
            "comparison_agent_fallback_used",
            {"reason": type(exc).__name__},
            logger=logger,
            level=logging.WARNING,
        )
        return build_fallback_matrix(request, sources, evidence)

    log_run_event(
        run_id,
        "comparison_agent_completed",
        {"row_count": len(matrix.rows), "used_fallback": False},
        logger=logger,
    )
    return matrix
