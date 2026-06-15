import type {
  CompetitorReport,
  EvidenceItem,
  ReportType,
  ResearchInput,
  SalesBattlecard,
  Source,
} from "@/types/report";

const API_BASE_URL = "http://localhost:8000";

const BACKEND_REPORT_TYPE: Record<ReportType, string> = {
  quick_brief: "quick_brief",
  deep_research: "deep_research",
  sales_battlecard: "sales_battlecard",
};

export interface StreamProgressEvent {
  runId: string;
  step: number;
  name: string;
  message: string;
  status: string;
}

export function buildResearchStreamUrl(input: ResearchInput): string {
  const query = [
    `our_company=${encodeURIComponent(input.ourCompany)}`,
    `competitor=${encodeURIComponent(input.competitor)}`,
    `market=${encodeURIComponent(input.market)}`,
    `report_type=${encodeURIComponent(BACKEND_REPORT_TYPE[input.reportType])}`,
  ].join("&");

  return `${API_BASE_URL}/api/research/stream?${query}`;
}

function readString(
  raw: Record<string, unknown>,
  camel: string,
  snake: string,
): string {
  const value = raw[camel] ?? raw[snake];
  return typeof value === "string" ? value : "";
}

function readNumber(
  raw: Record<string, unknown>,
  camel: string,
  snake: string,
): number {
  const value = raw[camel] ?? raw[snake];
  return typeof value === "number" ? value : 0;
}

function readStringArray(
  raw: Record<string, unknown>,
  camel: string,
  snake: string,
): string[] {
  const value = raw[camel] ?? raw[snake];
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function parseSources(raw: Record<string, unknown>): Source[] {
  const items = raw.sources;
  if (!Array.isArray(items)) return [];

  return items.map((item, index) => {
    const source = item as Record<string, unknown>;
    return {
      id: readString(source, "id", "id") || `source-${index}`,
      title: readString(source, "title", "title"),
      url: readString(source, "url", "url"),
      sourceType: (readString(source, "sourceType", "source_type") ||
        "other") as Source["sourceType"],
      publishedDate:
        readString(source, "publishedDate", "published_date") || undefined,
      credibilityScore: readNumber(
        source,
        "credibilityScore",
        "credibility_score",
      ),
    };
  });
}

function parseEvidence(raw: Record<string, unknown>): EvidenceItem[] {
  const items = raw.evidence;
  if (!Array.isArray(items)) return [];

  return items.map((item, index) => {
    const evidence = item as Record<string, unknown>;
    return {
      id: readString(evidence, "id", "id") || `evidence-${index}`,
      claim: readString(evidence, "claim", "claim"),
      sourceId: readString(evidence, "sourceId", "source_id"),
      confidence: (readString(evidence, "confidence", "confidence") ||
        "medium") as EvidenceItem["confidence"],
    };
  });
}

function parseBattlecard(raw: Record<string, unknown>): SalesBattlecard {
  const battlecard =
    (raw.salesBattlecard as Record<string, unknown> | undefined) ??
    (raw.sales_battlecard as Record<string, unknown> | undefined) ??
    {};

  return {
    talkTracks: readStringArray(battlecard, "talkTracks", "talk_tracks"),
    objectionHandling: readStringArray(
      battlecard,
      "objectionHandling",
      "objection_handling",
    ),
    landmines: readStringArray(battlecard, "landmines", "landmines"),
  };
}

export function parseStreamReport(raw: Record<string, unknown>): CompetitorReport {
  return {
    companySnapshot: readString(raw, "companySnapshot", "company_snapshot"),
    productPositioning: readString(
      raw,
      "productPositioning",
      "product_positioning",
    ),
    featureComparison: readStringArray(
      raw,
      "featureComparison",
      "feature_comparison",
    ),
    pricingIntelligence: readString(
      raw,
      "pricingIntelligence",
      "pricing_intelligence",
    ),
    recentMoves: readStringArray(raw, "recentMoves", "recent_moves"),
    strengths: readStringArray(raw, "strengths", "strengths"),
    weaknesses: readStringArray(raw, "weaknesses", "weaknesses"),
    salesBattlecard: parseBattlecard(raw),
    evidence: parseEvidence(raw),
    sources: parseSources(raw),
    confidenceScore: readNumber(raw, "confidenceScore", "confidence_score"),
  };
}
