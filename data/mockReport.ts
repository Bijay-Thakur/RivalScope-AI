import type { CompetitorReport, ResearchInput } from "@/types/report";

/** Demo research input — illustrative only, not live research. */
export const MOCK_RESEARCH_INPUT: ResearchInput = {
  ourCompany: "ClickUp",
  competitor: "Notion",
  market: "Project management / docs",
  reportType: "deep_research",
};

/**
 * Demo competitive intelligence report for RivalScope AI UI development.
 * Content is fictionalized for product demos — not verified live intelligence.
 */
export const MOCK_COMPETITOR_REPORT: CompetitorReport = {
  companySnapshot:
    "Notion (demo profile) positions itself as an all-in-one workspace blending docs, wikis, databases, and lightweight project tracking. " +
    "In this mock brief, Notion is portrayed as strong with knowledge-centric teams (10–500 employees) that prioritize flexible documentation over rigid PM workflows. " +
    "Funding narrative in demo materials cites ~$343M raised; GTM motion skews product-led with enterprise upsell via Notion AI and admin controls.",

  productPositioning:
    "Notion's demo positioning emphasizes 'one workspace for notes, tasks, and knowledge' rather than deep operational PM. " +
    "Against ClickUp, the mock narrative frames Notion as the better fit when teams want a polished doc hub with embedded databases, " +
    "while ClickUp is framed as the execution layer for cross-functional delivery, dependencies, and workload visibility. " +
    "Notion AI is highlighted as a differentiator for drafting, summarization, and Q&A over workspace content.",

  featureComparison: [
    "Task hierarchy & dependencies: In this demo, ClickUp is shown with native Gantt, critical path, and multi-level subtasks; Notion relies on database views and linked records with lighter dependency modeling.",
    "Docs & wikis: Mock assessment gives Notion the edge on block-based editing, templates, and bi-directional links; ClickUp Docs are positioned as adequate for specs tied directly to tasks.",
    "Views & reporting: ClickUp demo data cites 15+ work views (List, Board, Calendar, Workload); Notion offers table/board/timeline views but fewer purpose-built resourcing reports.",
    "Automations & integrations: Illustrative comparison notes ClickUp's rule builder for status-driven automations; Notion automations in the demo are simpler, with stronger API/embed story for custom stacks.",
  ],

  pricingIntelligence:
    "Demo pricing snapshot (not live — verify on vendor sites before use): Notion Free tier in mock data includes limited blocks and guests; " +
    "Plus ~$10/user/mo, Business ~$18/user/mo, Enterprise custom. ClickUp Free Forever in the demo includes unlimited tasks; Unlimited ~$7/user/mo, Business ~$12/user/mo. " +
    "Mock takeaway: Notion's per-seat cost rises faster for doc-heavy teams adding AI add-ons; ClickUp bundles more PM capability at mid-tier in this illustrative scenario. " +
    "Enterprise discounts and annual billing are assumed to narrow the gap ~10–15% in demo models.",

  recentMoves: [
    "Demo: Notion AI expanded with Q&A-over-workspace and meeting notes templates (mock date: Q1 2026).",
    "Demo: Launch of 'Notion Mail' beta referenced in mock press — signals calendar/comms adjacency.",
    "Demo: Enterprise admin API updates for SCIM and audit logs cited in illustrative release notes.",
  ],

  strengths: [
    "Best-in-class flexible docs and wiki experience for async, writing-first teams (demo assessment).",
    "Low friction PLG adoption — mock data shows teams spinning up workspaces without IT (illustrative).",
    "Strong template gallery and community ecosystem for quick team onboarding in demo scenarios.",
    "Notion AI integrated across pages reduces context-switching for content creation in mock workflows.",
  ],

  weaknesses: [
    "Demo finding: Advanced PM (dependencies, workload, time tracking) requires workarounds vs purpose-built tools.",
    "Performance concerns noted in mock user feedback for large databases (10k+ rows) — illustrative only.",
    "Mock enterprise buyers flag granular permission models as less mature than dedicated PM suites.",
    "Offline/mobile experiences described as lagging desktop in demo user interviews (fictional).",
  ],

  salesBattlecard: {
    talkTracks: [
      "When docs are important but delivery is the bottleneck: 'Notion excels as a knowledge hub — ClickUp connects those docs to timelines, owners, and dependencies so work actually ships.'",
      "For ops-led evaluations: 'In demo benchmarks, teams switching from Notion databases to ClickUp reduce status-meeting time by centralizing work, docs, and goals in one execution layer.'",
      "On AI: 'Notion AI helps you write pages; ClickUp Brain (demo positioning) ties AI to tasks, priorities, and standups — action over authorship.'",
    ],
    objectionHandling: [
      "'We already run our wiki in Notion.' — Acknowledge strength; propose ClickUp for delivery while linking out or embedding Notion pages (mock integration path).",
      "'Notion is cheaper.' — Walk through demo TCO: PM add-ons, automation limits, and AI seats; compare bundled ClickUp tiers for cross-functional teams.",
      "'Notion is simpler.' — Agree for pure docs; ask about missed due dates, unclear ownership, and reporting gaps — pains the demo maps to ClickUp views.",
    ],
    landmines: [
      "Do not dismiss Notion's doc UX — mock win/loss data shows trash-talking docs erodes credibility with content teams.",
      "Avoid claiming ClickUp replaces a full company wiki on day one — demo rollout assumes phased migration.",
      "Do not cite this brief's pricing or feature claims as live facts — always verify on clickup.com and notion.so before customer calls.",
    ],
  },

  evidence: [
    {
      id: "ev-1",
      claim:
        "Demo: Notion markets an all-in-one workspace spanning docs, projects, and wikis on its homepage hero.",
      sourceId: "src-1",
      confidence: "high",
    },
    {
      id: "ev-2",
      claim:
        "Demo: Illustrative Plus tier listed at ~$10/user/month on mock Notion pricing page snapshot.",
      sourceId: "src-2",
      confidence: "medium",
    },
    {
      id: "ev-3",
      claim:
        "Demo: Mock blog post announces Notion AI Q&A feature rolling out to Business plans.",
      sourceId: "src-3",
      confidence: "medium",
    },
    {
      id: "ev-4",
      claim:
        "Demo: ClickUp product page highlights 15+ views including Gantt, Workload, and Mind Maps (illustrative screenshot).",
      sourceId: "src-4",
      confidence: "high",
    },
    {
      id: "ev-5",
      claim:
        "Demo: Fictional analyst roundup cites Notion's gap on native critical-path scheduling vs PM specialists.",
      sourceId: "src-5",
      confidence: "low",
    },
  ],

  sources: [
    {
      id: "src-1",
      title: "Notion — Product homepage (demo snapshot)",
      url: "https://www.notion.so/product",
      sourceType: "company_page",
      credibilityScore: 0.92,
    },
    {
      id: "src-2",
      title: "Notion — Pricing page (demo snapshot)",
      url: "https://www.notion.so/pricing",
      sourceType: "pricing_page",
      credibilityScore: 0.9,
    },
    {
      id: "src-3",
      title: "Notion Blog — AI Q&A announcement (mock)",
      url: "https://www.notion.so/blog/example-ai-qa-demo",
      sourceType: "blog",
      publishedDate: "2026-01-15",
      credibilityScore: 0.78,
    },
    {
      id: "src-4",
      title: "ClickUp — Features overview (demo snapshot)",
      url: "https://clickup.com/features",
      sourceType: "company_page",
      credibilityScore: 0.91,
    },
    {
      id: "src-5",
      title: "Demo analyst note — PM suite comparison (fictional)",
      url: "https://example.com/demo/notion-vs-pm-tools",
      sourceType: "other",
      publishedDate: "2025-11-01",
      credibilityScore: 0.55,
    },
  ],

  confidenceScore: 84,
};
