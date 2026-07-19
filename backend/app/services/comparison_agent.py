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
from app.services.claim_policy import filter_report_input_claims
from app.services.content_sanitize import sanitize_retrieved_text
from app.services.context_budget import trim_evidence_to_budget
from app.services.llm import resolve_step_provider
from app.services.pipeline_validation import (
    build_source_allowlists,
    validate_comparison_matrix,
)
from app.services.prompts import COMPARISON_AGENT_SYSTEM_PROMPT
from app.services.structured_output import (
    StructuredOutputError,
    invoke_json_with_repair,
)

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
            sanitized = sanitize_retrieved_text(item.raw_text, max_chars=400)
            lines.append(f"  raw: {sanitized.text}")
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

    from app.services.compare_features import feature_labels

    dims = feature_labels(request.compare_features)
    lines = [
        f"our_company: {our}",
        f"competitor: {rival}",
        f"market: {request.market}",
        f"compare_features: {', '.join(dims) if dims else '(none selected — pick evidence-grounded dims)'}",
        "",
    ]
    if dims:
        lines.append(
            "REQUIRED DIMENSIONS (use these as matrix row dimensions when evidence allows; "
            "skip only if zero evidence on both sides): " + "; ".join(dims)
        )
        lines.append("")
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
    verified_claims: list[VerifiedClaim],
    *,
    run_id: str | None = None,
) -> ComparisonMatrix:
    # Unsupported claims must not drive advantages — use report-safe claims only.
    usable = filter_report_input_claims(verified_claims)
    log_run_event(
        run_id,
        "comparison_agent_started",
        {
            "source_count": len(sources),
            "evidence_count": len(evidence),
            "usable_claim_count": len(usable),
        },
        logger=logger,
    )

    context = _build_context(request, sources, evidence, run_id=run_id)
    if usable:
        context += "\n\n=== CHECKED CLAIMS (verified / weakly_supported only) ===\n"
        for c in usable[:20]:
            context += f"- [{c.verification_status}] {c.claim}\n"

    allowlists = build_source_allowlists(
        sources, request.our_company, request.competitor
    )

    try:
        schema_hint = (
            '{"rows":[{"dimension":"str","ourValue":"str","competitorValue":"str",'
            '"ourSourceIds":["src-id"],"competitorSourceIds":["src-id"],'
            '"advantage":"our|competitor|parity|unclear"}],'
            '"pricingComparison":"str","positioningGap":"str","summary":"str"}'
        )

        def _validate(data: dict | list):
            if not isinstance(data, dict):
                return None, ["expected object"]
            try:
                matrix = _matrix_from_data(data)
            except Exception as exc:
                return None, [str(exc)]
            # Business-rule coercions are applied here; only structural failures
            # (no usable rows) require LLM repair.
            matrix, validation = validate_comparison_matrix(matrix, allowlists)
            errs = [i.message for i in validation.issues if i.code == "no_rows"]
            return matrix, errs

        matrix = invoke_json_with_repair(
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
            schema_hint=schema_hint,
            validate=_validate,
            run_id=run_id,
            call_name="comparison_agent_llm",
            preferred_provider=resolve_step_provider(settings.comparison_provider),
            stage="comparison_agent",
            max_repairs=1,
        )
        # Final soft validation (pad/trim IDs) without failing the pipeline
        matrix, validation = validate_comparison_matrix(matrix, allowlists)
        if not validation.ok:
            logger.warning(
                "comparison_agent: post-repair coercions %s",
                [i.code for i in validation.issues],
            )
    except StructuredOutputError as exc:
        logger.warning(
            "comparison_agent: structured output failed %s — using fallback matrix.",
            exc.errors,
        )
        log_run_event(
            run_id,
            "comparison_agent_fallback_used",
            {"reason": "structured_output_error", "errors": exc.errors[:5]},
            logger=logger,
            level=logging.WARNING,
        )
        matrix = build_fallback_matrix(request, sources, evidence)
        matrix, _ = validate_comparison_matrix(matrix, allowlists)
        return matrix
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
        matrix = build_fallback_matrix(request, sources, evidence)
        matrix, _ = validate_comparison_matrix(matrix, allowlists)
        return matrix

    log_run_event(
        run_id,
        "comparison_agent_completed",
        {"row_count": len(matrix.rows), "used_fallback": False, "validation_ok": True},
        logger=logger,
    )
    return matrix
