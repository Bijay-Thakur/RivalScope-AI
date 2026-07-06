/** Display metadata for the 9 backend graph nodes (PROGRESS_STEP_LABELS order). */
export interface StepMeta {
  step: number;
  node: string;
  label: string;
  hint: string;
}

export const WORKFLOW_STEPS: StepMeta[] = [
  { step: 1, node: "normalize_input", label: "Normalize input", hint: "Parse competitive set" },
  { step: 2, node: "create_research_plan", label: "Create research plan", hint: "Fan out tracks" },
  { step: 3, node: "company_profile_track", label: "Company profile track", hint: "Homepage, about" },
  { step: 4, node: "product_track", label: "Product feature track", hint: "Features, docs" },
  { step: 5, node: "pricing_track", label: "Pricing track", hint: "Plans, tiers" },
  { step: 6, node: "news_track", label: "News track", hint: "Launches, funding" },
  { step: 7, node: "fact_checker_stub", label: "Verify claims", hint: "Ground each claim" },
  { step: 8, node: "comparison_agent", label: "Compare head-to-head", hint: "Build matrix" },
  { step: 9, node: "report_generator", label: "Generate report", hint: "Synthesize brief" },
];

export const TOTAL_STEPS = WORKFLOW_STEPS.length;
