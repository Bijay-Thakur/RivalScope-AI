export type ReportType = "quick_brief" | "deep_research" | "sales_battlecard";

/** Buyer-critical dims — must match backend compare_features catalog ids. */
export type CompareFeatureId =
  | "pricing"
  | "core_features"
  | "integrations"
  | "security"
  | "ai_capabilities"
  | "collaboration";

export interface ResearchInput {
  ourCompany: string;
  competitor: string;
  /** Derived label for display/DB; optional when compareFeatures set. */
  market: string;
  reportType: ReportType;
  compareFeatures: CompareFeatureId[];
}

export type SourceType =
  | "company_page"
  | "pricing_page"
  | "news"
  | "blog"
  | "docs"
  | "other";

export interface Source {
  id: string;
  title: string;
  url: string;
  sourceType: SourceType;
  publishedDate?: string;
  credibilityScore: number;
  snippet?: string;
}

export type EvidenceConfidence = "low" | "medium" | "high";

export interface EvidenceItem {
  id: string;
  claim: string;
  sourceId: string;
  confidence: EvidenceConfidence;
  url?: string;
  rawText?: string;
}

export interface SalesBattlecard {
  talkTracks: string[];
  objectionHandling: string[];
  landmines: string[];
}

export type ComparisonAdvantage = "our" | "competitor" | "parity" | "unclear";

export interface FeatureComparisonRow {
  dimension: string;
  ourValue: string;
  competitorValue: string;
  ourSourceIds: string[];
  competitorSourceIds: string[];
  advantage: ComparisonAdvantage;
}

export interface ComparisonMatrix {
  rows: FeatureComparisonRow[];
  pricingComparison: string;
  positioningGap: string;
  summary: string;
}

export interface CompetitorReport {
  companySnapshot: string;
  productPositioning: string;
  featureComparison: string[];
  pricingIntelligence: string;
  recentMoves: string[];
  strengths: string[];
  weaknesses: string[];
  salesBattlecard: SalesBattlecard;
  comparisonMatrix?: ComparisonMatrix;
  evidence: EvidenceItem[];
  sources: Source[];
  confidenceScore: number;
  researchMode?: string;
  generatedAt?: string;
  warnings?: string[];
}
