"""Demo mock data — illustrative only, not live intelligence."""

from app.schemas.report import (
    CompetitorReport,
    EvidenceItem,
    SalesBattlecard,
    Source,
)
from app.schemas.research import ReportType, ResearchRequest

REPORT_TYPE_LABELS: dict[ReportType, str] = {
    ReportType.QUICK_BRIEF: "Quick Brief",
    ReportType.DEEP_RESEARCH: "Deep Research",
    ReportType.SALES_BATTLECARD: "Sales Battlecard",
}

CONFIDENCE_BY_REPORT_TYPE: dict[ReportType, float] = {
    ReportType.QUICK_BRIEF: 78.0,
    ReportType.DEEP_RESEARCH: 84.0,
    ReportType.SALES_BATTLECARD: 86.0,
}


def _slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace("/", "-")


def build_mock_report(request: ResearchRequest) -> CompetitorReport:
    """Build a demo competitor report tailored to the research request."""
    our = request.our_company.strip()
    rival = request.competitor.strip()
    market = request.market.strip()
    report_label = REPORT_TYPE_LABELS[request.report_type]
    confidence = CONFIDENCE_BY_REPORT_TYPE[request.report_type]
    rival_slug = _slug(rival)
    our_slug = _slug(our)

    sources = [
        Source(
            id="src-1",
            title=f"{rival} — Product homepage (demo snapshot)",
            url=f"https://www.example.com/demo/{rival_slug}/product",
            source_type="company_page",
            credibility_score=0.91,
        ),
        Source(
            id="src-2",
            title=f"{rival} — Pricing page (demo snapshot)",
            url=f"https://www.example.com/demo/{rival_slug}/pricing",
            source_type="pricing_page",
            credibility_score=0.89,
        ),
        Source(
            id="src-3",
            title=f"{rival} Blog — {market} positioning note (mock)",
            url=f"https://www.example.com/demo/{rival_slug}/blog/market-update",
            source_type="blog",
            published_date="2026-01-20",
            credibility_score=0.76,
        ),
        Source(
            id="src-4",
            title=f"{our} — Features overview (demo snapshot)",
            url=f"https://www.example.com/demo/{our_slug}/features",
            source_type="company_page",
            credibility_score=0.90,
        ),
        Source(
            id="src-5",
            title=f"Demo analyst note — {rival} in {market} (fictional)",
            url=f"https://www.example.com/demo/analyst/{rival_slug}-vs-{our_slug}",
            source_type="other",
            published_date="2025-12-01",
            credibility_score=0.58,
        ),
    ]

    evidence = [
        EvidenceItem(
            id="ev-1",
            claim=(
                f"Demo: {rival} homepage copy positions the product as a leading option "
                f"in {market} (illustrative snapshot — not verified live)."
            ),
            source_id="src-1",
            confidence="high",
        ),
        EvidenceItem(
            id="ev-2",
            claim=(
                f"Demo: Mock pricing page for {rival} shows tiered per-seat plans "
                f"with a free/starter entry point in the {market} category."
            ),
            source_id="src-2",
            confidence="medium",
        ),
        EvidenceItem(
            id="ev-3",
            claim=(
                f"Demo: Fictional blog post cites {rival} expanding AI-assisted workflows "
                f"for teams evaluating {market} tools."
            ),
            source_id="src-3",
            confidence="medium",
        ),
        EvidenceItem(
            id="ev-4",
            claim=(
                f"Demo: {our} product page highlights differentiated execution and reporting "
                f"capabilities for {market} buyers (mock marketing snapshot)."
            ),
            source_id="src-4",
            confidence="high",
        ),
        EvidenceItem(
            id="ev-5",
            claim=(
                f"Demo: Illustrative analyst roundup notes {rival} may trade depth in "
                f"operational workflows for breadth in {market} — fictional summary."
            ),
            source_id="src-5",
            confidence="low",
        ),
    ]

    return CompetitorReport(
        company_snapshot=(
            f"[Demo brief · {report_label}] {rival} is portrayed in this mock profile as an "
            f"established player in {market}, with GTM motion skewing toward product-led adoption "
            f"and upsell into team or enterprise tiers. Illustrative positioning emphasizes "
            f"flexibility and fast time-to-value for cross-functional buyers. "
            f"This snapshot is generated for a {our} vs {rival} evaluation — not live research."
        ),
        product_positioning=(
            f"In this demo narrative, {rival} leads with a unified workspace story in {market}, "
            f"while {our} is framed as the stronger fit when buyers prioritize execution, "
            f"ownership, and delivery visibility over pure content creation. "
            f"Report type requested: {report_label}. Messaging themes below are mock placeholders "
            f"for sales and PMM review — verify all claims before customer use."
        ),
        feature_comparison=[
            f"Core workflow depth: Demo comparison suggests {our} emphasizes structured delivery "
            f"and accountability in {market}; {rival} leans toward configurable hubs and lighter PM.",
            f"Collaboration & docs: Mock assessment gives {rival} an edge on async writing-first "
            f"workflows; {our} is positioned for teams that tie specs directly to execution.",
            f"Reporting & visibility: Illustrative data cites {our} as stronger on operational "
            f"dashboards; {rival} offers flexible views that may require customization in {market}.",
            f"Integrations & extensibility: Demo notes both vendors integrate with common stacks; "
            f"differentiation in this mock is framed around native {market} workflows vs add-ons.",
        ],
        pricing_intelligence=(
            f"Demo pricing snapshot for {rival} vs {our} in {market} (not live — verify on vendor sites): "
            f"Mock tiers show {rival} with a freemium/starter entry and per-seat mid-market plans; "
            f"{our} is illustrated with bundled capability at mid-tier for cross-functional teams. "
            f"Mock TCO takeaway: seat growth, AI add-ons, and services can shift the gap 10–20% "
            f"depending on rollout scope. Enterprise discounts assumed but not quoted here."
        ),
        recent_moves=[
            f"Demo: {rival} referenced a Q1 2026 mock release expanding AI-assisted summaries for {market} teams.",
            f"Demo: Illustrative press note positions {rival} adjacent to calendar/comms — fictional GTM signal.",
            f"Demo: Mock enterprise release notes cite admin API and SSO improvements for regulated buyers.",
        ],
        strengths=[
            f"Strong brand recall and template-led onboarding in {market} (demo assessment).",
            f"Flexible configuration appeals to content-centric and ops-light teams (illustrative).",
            f"Active community and partner ecosystem cited in mock win/loss notes.",
            f"AI-assisted authoring positioned as a differentiator in demo marketing snapshots.",
        ],
        weaknesses=[
            f"Demo finding: Advanced delivery workflows in {market} may require workarounds vs specialists.",
            f"Mock buyer feedback flags performance at scale for large, multi-team deployments.",
            f"Illustrative enterprise reviews note permission granularity as a gap vs mature suites.",
            f"Demo interviews suggest mobile/offline experiences lag desktop for field teams.",
        ],
        sales_battlecard=SalesBattlecard(
            talk_tracks=[
                f"When {rival} wins on familiarity: '{rival} is strong in {market} for teams that start with docs — "
                f"{our} connects strategy to owners, timelines, and delivery so initiatives actually ship.'",
                f"For ops-led evaluations: 'In this demo storyline, teams choosing {our} over {rival} "
                f"reduce status-meeting load by centralizing work and reporting in one execution layer.'",
                f"On AI (mock): '{rival} helps you draft content; {our} ties insights to priorities, "
                f"tasks, and next steps — optimized for action, not authorship alone.'",
            ],
            objection_handling=[
                f"'We already use {rival}.' — Acknowledge strength; propose phased coexistence or "
                f"integration while {our} owns delivery in {market}.",
                f"'{rival} is cheaper.' — Walk through demo TCO: seats, add-ons, services, and "
                f"hidden PM workarounds vs bundled {our} tiers in this mock model.",
                f"'{rival} is simpler.' — Agree for small teams; probe missed deadlines, unclear "
                f"ownership, and reporting gaps mapped to {our} views in the demo.",
            ],
            landmines=[
                f"Do not dismiss {rival}'s core UX — mock win/loss data shows credibility loss when reps trash-talk the incumbent.",
                f"Avoid claiming {our} replaces every {rival} workflow on day one — demo assumes phased rollout.",
                f"Do not cite this brief's pricing or feature claims as live facts — verify on vendor sites before calls.",
            ],
        ),
        evidence=evidence,
        sources=sources,
        confidence_score=confidence,
    )


def get_mock_report(request: ResearchRequest | None = None) -> CompetitorReport:
    """Return a mock report; uses a default request when none is provided."""
    if request is None:
        request = ResearchRequest(
            our_company="ClickUp",
            competitor="Notion",
            market="Project management / docs",
            report_type=ReportType.DEEP_RESEARCH,
        )
    return build_mock_report(request)
