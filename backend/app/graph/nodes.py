from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.graph.constants import TOTAL_STEPS
from app.graph.state import RivalScopeState
from app.schemas.events import ProgressEvent
from app.schemas.report import EvidenceItem, Source, VerifiedClaim
from app.schemas.research import ResearchTask
from app.services.fact_checker import verify_evidence_claims
from app.services.mock_data import build_mock_report
from app.services.query_builder import build_all_queries
from app.services.report_generator import generate_competitor_report
from app.services.research_tracks import run_research_track

logger = get_logger(__name__)

PartialState = dict[str, Any]


def is_real_mode() -> bool:
    return settings.is_real_research_enabled


# ---------------------------------------------------------------------------
# Progress helpers
# ---------------------------------------------------------------------------

def _step_index(name: str) -> int:
    from app.graph.constants import PROGRESS_STEP_LABELS

    return PROGRESS_STEP_LABELS.index(name) + 1


def _progress_event(
    state: RivalScopeState,
    step: int,
    name: str,
    message: str,
    status: str = "completed",
) -> ProgressEvent:
    return ProgressEvent(
        run_id=state["run_id"],
        step=step,
        name=name,
        message=message,
        status=status,  # type: ignore[arg-type]
    )


def _with_progress(
    state: RivalScopeState,
    step_name: str,
    message: str,
    status: str = "completed",
) -> tuple[str, list[ProgressEvent]]:
    event = _progress_event(
        state,
        step=_step_index(step_name),
        name=step_name,
        message=message,
        status=status,
    )
    return step_name, [*state["progress_events"], event]


# ---------------------------------------------------------------------------
# Normalize
# ---------------------------------------------------------------------------

def normalize_input(state: RivalScopeState) -> PartialState:
    logger.info(
        "Normalizing input for %s vs %s",
        state["request"].our_company,
        state["request"].competitor,
    )
    if is_real_mode():
        msg = (
            f"Normalizing research input — {state['request'].our_company} vs "
            f"{state['request'].competitor} in {state['request'].market}."
        )
    else:
        msg = (
            f"Demo: normalized research input for {state['request'].our_company} "
            f"vs {state['request'].competitor} in {state['request'].market} "
            f"({state['request'].report_type.value})."
        )
    step, events = _with_progress(state, "normalize_input", msg)
    return {"current_step": step, "progress_events": events}


# ---------------------------------------------------------------------------
# Research plan
# ---------------------------------------------------------------------------

def create_research_plan(state: RivalScopeState) -> PartialState:
    req = state["request"]
    real = is_real_mode()

    plan = [
        ResearchTask(
            id="task-company-profile",
            track="company_profile",
            objective=f"{'Build' if real else 'Build demo'} company profile for {req.competitor}",
            priority=1,
        ),
        ResearchTask(
            id="task-product-features",
            track="product_features",
            objective=f"Map product and feature positioning in {req.market}",
            priority=2,
        ),
        ResearchTask(
            id="task-pricing",
            track="pricing",
            objective=f"Collect {'live' if real else 'illustrative'} pricing signals for {req.competitor}",
            priority=3,
        ),
        ResearchTask(
            id="task-recent-news",
            track="recent_news",
            objective=f"Scan {'recent' if real else 'mock recent'} news and GTM moves in {req.market}",
            priority=4,
        ),
    ]
    msg = (
        f"Creating research plan — {len(plan)} research tracks."
        if real
        else f"Demo: created {len(plan)} research tasks for parallel tracks."
    )
    step, events = _with_progress(state, "create_research_plan", msg)
    return {"current_step": step, "progress_events": events, "research_plan": plan}


# ---------------------------------------------------------------------------
# Mock helpers (preserved from Phase 2)
# ---------------------------------------------------------------------------

def _mock_source(source_id: str, title: str, source_type: str) -> Source:
    return Source(
        id=source_id,
        title=title,
        url=f"https://example.com/demo/{source_id}",
        source_type=source_type,
        credibility_score=0.75,
    )


# ---------------------------------------------------------------------------
# Real-mode track helper
# ---------------------------------------------------------------------------

def _run_track(
    state: RivalScopeState,
    track: str,
    step_name: str,
    rival: str,
    source_type: str | None = None,
) -> PartialState:
    queries = build_all_queries(state["request"])[track]
    try:
        result = run_research_track(track=track, queries=queries, source_type=source_type)
        new_sources = result["sources"]
        new_evidence = result["evidence"]
        new_warnings = result["warnings"]
    except Exception as exc:
        msg = f"Track '{track}' failed unexpectedly [{type(exc).__name__}]."
        logger.error(msg)
        new_sources, new_evidence, new_warnings = [], [], [msg]

    step, events = _with_progress(
        state,
        step_name,
        f"Searched {track.replace('_', ' ')} for {rival} — {len(new_sources)} source(s) found.",
    )
    return {
        "current_step": step,
        "progress_events": events,
        "sources": [*state["sources"], *new_sources],
        "evidence": [*state["evidence"], *new_evidence],
        "errors": [*state["errors"], *new_warnings],
    }


# ---------------------------------------------------------------------------
# Track nodes
# ---------------------------------------------------------------------------

def company_profile_track(state: RivalScopeState) -> PartialState:
    rival = state["request"].competitor

    if is_real_mode():
        return _run_track(state, "company_profile", "company_profile_track", rival)

    source = _mock_source(
        "src-company-profile",
        f"{rival} — Company profile (demo snapshot)",
        "company_page",
    )
    evidence = EvidenceItem(
        id="ev-company-profile",
        claim=(
            f"Demo: {rival} public profile emphasizes leadership in "
            f"{state['request'].market} with an enterprise-ready narrative (mock)."
        ),
        source_id=source.id,
        confidence="high",
    )
    step, events = _with_progress(
        state, "company_profile_track", f"Demo: added company profile evidence for {rival}."
    )
    return {
        "current_step": step,
        "progress_events": events,
        "sources": [*state["sources"], source],
        "evidence": [*state["evidence"], evidence],
    }


def product_track(state: RivalScopeState) -> PartialState:
    rival = state["request"].competitor

    if is_real_mode():
        return _run_track(state, "product_features", "product_track", rival)

    source = _mock_source(
        "src-product",
        f"{rival} — Product & features overview (demo snapshot)",
        "docs",
    )
    evidence = EvidenceItem(
        id="ev-product",
        claim=(
            f"Demo: {rival} product messaging highlights modular capabilities and "
            f"integrations common in {state['request'].market} evaluations (mock)."
        ),
        source_id=source.id,
        confidence="medium",
    )
    step, events = _with_progress(
        state, "product_track", f"Demo: added product and features evidence for {rival}."
    )
    return {
        "current_step": step,
        "progress_events": events,
        "sources": [*state["sources"], source],
        "evidence": [*state["evidence"], evidence],
    }


def pricing_track(state: RivalScopeState) -> PartialState:
    rival = state["request"].competitor

    if is_real_mode():
        return _run_track(state, "pricing", "pricing_track", rival, source_type="pricing_page")

    source = _mock_source(
        "src-pricing",
        f"{rival} — Pricing page (demo snapshot)",
        "pricing_page",
    )
    evidence = EvidenceItem(
        id="ev-pricing",
        claim=(
            f"Demo: illustrative pricing tiers for {rival} show per-seat plans with "
            f"a starter tier and mid-market bundles (mock — not live pricing)."
        ),
        source_id=source.id,
        confidence="medium",
    )
    step, events = _with_progress(
        state, "pricing_track", f"Demo: added pricing evidence for {rival}."
    )
    return {
        "current_step": step,
        "progress_events": events,
        "sources": [*state["sources"], source],
        "evidence": [*state["evidence"], evidence],
    }


def news_track(state: RivalScopeState) -> PartialState:
    rival = state["request"].competitor

    if is_real_mode():
        return _run_track(state, "recent_news", "news_track", rival, source_type="news")

    source = _mock_source(
        "src-news",
        f"{rival} — Recent news summary (demo snapshot)",
        "news",
    )
    evidence = EvidenceItem(
        id="ev-news",
        claim=(
            f"Demo: mock press recap notes {rival} announced roadmap updates and "
            f"partnership activity relevant to {state['request'].market}."
        ),
        source_id=source.id,
        confidence="low",
    )
    step, events = _with_progress(
        state, "news_track", f"Demo: added recent news evidence for {rival}."
    )
    return {
        "current_step": step,
        "progress_events": events,
        "sources": [*state["sources"], source],
        "evidence": [*state["evidence"], evidence],
    }


# ---------------------------------------------------------------------------
# Fact checker
# ---------------------------------------------------------------------------

def fact_checker_stub(state: RivalScopeState) -> PartialState:
    if is_real_mode():
        try:
            verified = verify_evidence_claims(
                evidence=state["evidence"],
                sources=state["sources"],
            )
        except Exception as exc:
            msg = f"Fact checker failed [{type(exc).__name__}] — skipping verification."
            logger.error(msg)
            verified = []
            step, events = _with_progress(
                state, "fact_checker_stub", "Fact checking failed — evidence not verified."
            )
            return {
                "current_step": step,
                "progress_events": events,
                "verified_claims": verified,
                "errors": [*state["errors"], msg],
            }

        step, events = _with_progress(
            state,
            "fact_checker_stub",
            f"Verifying evidence claims — {len(verified)} claim(s) assessed.",
        )
        return {
            "current_step": step,
            "progress_events": events,
            "verified_claims": verified,
        }

    verified = [
        VerifiedClaim(
            id=f"vc-{item.id}",
            claim=item.claim,
            source_ids=[item.source_id],
            verification_status="mock_verified",
            confidence_score=(
                0.9 if item.confidence == "high"
                else 0.75 if item.confidence == "medium"
                else 0.6
            ),
        )
        for item in state["evidence"]
    ]
    step, events = _with_progress(
        state,
        "fact_checker_stub",
        f"Demo: mock-verified {len(verified)} evidence items (no external APIs).",
    )
    return {
        "current_step": step,
        "progress_events": events,
        "verified_claims": verified,
    }


# ---------------------------------------------------------------------------
# Report generator
# ---------------------------------------------------------------------------

def report_generator(state: RivalScopeState) -> PartialState:
    logger.info(
        "Generating %s report for %s vs %s (step %s/%s)",
        "real" if is_real_mode() else "mock",
        state["request"].our_company,
        state["request"].competitor,
        _step_index("report_generator"),
        TOTAL_STEPS,
    )

    if is_real_mode():
        try:
            report = generate_competitor_report(
                request=state["request"],
                sources=state["sources"],
                evidence=state["evidence"],
                verified_claims=state["verified_claims"],
                warnings=list(state["errors"]),
            )
        except Exception as exc:
            msg = f"Report generator failed [{type(exc).__name__}] — returning mock report."
            logger.error(msg)
            report = build_mock_report(state["request"])
            report.research_mode = "real"
            report.warnings = [msg]

        step, events = _with_progress(
            state,
            "report_generator",
            f"Generating source-grounded report — "
            f"{state['request'].our_company} vs {state['request'].competitor}.",
        )
        return {"current_step": step, "progress_events": events, "final_report": report}

    report = build_mock_report(state["request"])
    step, events = _with_progress(
        state,
        "report_generator",
        f"Demo: generated {state['request'].report_type.value} report for "
        f"{state['request'].our_company} vs {state['request'].competitor}.",
    )
    return {"current_step": step, "progress_events": events, "final_report": report}
