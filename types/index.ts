export type {
  ReportType,
  ResearchInput,
  SourceType,
  Source,
  EvidenceConfidence,
  EvidenceItem,
  SalesBattlecard,
  CompetitorReport,
} from "./report";

export interface ResearchFormData {
  yourCompany: string;
  competitor: string;
  marketCategory: string;
  reportType: import("./report").ReportType;
}

export interface AgentProgressStep {
  id: string;
  label: string;
  status: "pending" | "active" | "complete";
}

export interface ReportSection {
  id: string;
  title: string;
  content: string;
}
