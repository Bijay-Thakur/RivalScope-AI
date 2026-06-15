import type { ReportType } from "@/types";

export interface ReportTypeOption {
  value: ReportType;
  label: string;
  description: string;
}

export const REPORT_TYPE_OPTIONS: ReportTypeOption[] = [
  {
    value: "quick_brief",
    label: "Quick Brief",
    description: "High-level snapshot with key differentiators and positioning.",
  },
  {
    value: "deep_research",
    label: "Deep Research",
    description: "Comprehensive analysis with sources, trends, and strategic implications.",
  },
  {
    value: "sales_battlecard",
    label: "Sales Battlecard",
    description: "Talk tracks, objection handling, and win themes for sales teams.",
  },
];

export const PLACEHOLDER_PROGRESS_STEPS = [
  { id: "1", label: "Gathering public sources", status: "pending" as const },
  { id: "2", label: "Analyzing competitor positioning", status: "pending" as const },
  { id: "3", label: "Synthesizing GTM insights", status: "pending" as const },
  { id: "4", label: "Drafting final brief", status: "pending" as const },
];

export const EMPTY_FORM: {
  yourCompany: string;
  competitor: string;
  marketCategory: string;
  reportType: ReportType;
} = {
  yourCompany: "",
  competitor: "",
  marketCategory: "",
  reportType: "quick_brief",
};
