export type ReportType = "quick_brief" | "deep_research" | "sales_battlecard";

export interface ResearchInput {
  ourCompany: string;
  competitor: string;
  market: string;
  reportType: ReportType;
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
}

export type EvidenceConfidence = "low" | "medium" | "high";

export interface EvidenceItem {
  id: string;
  claim: string;
  sourceId: string;
  confidence: EvidenceConfidence;
}

export interface SalesBattlecard {
  talkTracks: string[];
  objectionHandling: string[];
  landmines: string[];
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
  evidence: EvidenceItem[];
  sources: Source[];
  confidenceScore: number;
}
