import type {
  ComparisonAdvantage,
  ComparisonMatrix,
  CompetitorReport,
  EvidenceItem,
  FeatureComparisonRow,
  ReportType,
  ResearchInput,
  SalesBattlecard,
  Source,
} from "@/types/report";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const BACKEND_REPORT_TYPE: Record<ReportType, string> = {
  quick_brief: "quick_brief",
  deep_research: "deep_research",
  sales_battlecard: "sales_battlecard",
};

export interface AgentStatusEvent {
  runId: string;
  step: number;
  name: string;
  status: "working" | "done";
  message?: string;
}

export interface TokenEvent {
  step: number;
  node: string;
  delta: string;
}

/** A single tool-use / LLM trace span emitted by the backend (see trace_buffer). */
export interface TraceEvent {
  seq: number;
  ts?: string;
  kind: "tool" | "llm" | "node";
  name: string;
  status: "completed" | "failed";
  summary: string;
  track?: string | null;
  durationMs?: number | null;
  detail?: Record<string, unknown>;
}

export interface RunSummary {
  runId: string;
  ourCompany: string;
  competitor: string;
  market: string;
  reportType: string;
  status: string;
  researchMode?: string | null;
  confidenceScore?: number | null;
  sourceCount: number;
  evidenceCount: number;
  verifiedClaimCount: number;
  warningCount: number;
  durationMs?: number | null;
  createdAt: string;
}

export interface AppConfig {
  researchMode: string;
  isRealResearchEnabled: boolean;
  llmProvider: string;
  llmFallback: string;
  groqModel: string;
  geminiModel: string;
  judgeModel: string;
  searchProvider: string;
  database: string;
  providers: { tavily: boolean; groq: boolean; gemini: boolean };
  tracing: { langsmithEnabled: boolean; langsmithProject: string; toolTraceBuffer: boolean };
  extractTopN: number;
  maxContextChars: number;
}

export async function fetchConfig(): Promise<AppConfig> {
  const res = await fetch(`${API_BASE_URL}/api/config`);
  if (!res.ok) throw new Error(`config ${res.status}`);
  return res.json();
}

export async function fetchRuns(limit = 50): Promise<RunSummary[]> {
  const res = await fetch(`${API_BASE_URL}/api/runs?limit=${limit}`);
  if (!res.ok) throw new Error(`runs ${res.status}`);
  const data = (await res.json()) as { runs: RunSummary[] };
  return data.runs;
}

export interface RunDetail extends RunSummary {
  report: Record<string, unknown> | null;
  traces: TraceEvent[];
}

export async function fetchRun(runId: string): Promise<RunDetail> {
  const res = await fetch(`${API_BASE_URL}/api/runs/${runId}`);
  if (!res.ok) throw new Error(`run ${res.status}`);
  return res.json();
}

export async function fetchRunTraces(runId: string): Promise<TraceEvent[]> {
  const res = await fetch(`${API_BASE_URL}/api/runs/${runId}/traces`);
  if (!res.ok) throw new Error(`traces ${res.status}`);
  const data = (await res.json()) as { traces: TraceEvent[] };
  return data.traces;
}

export async function fetchEvaluations(limit = 25): Promise<EvaluationRecord[]> {
  const res = await fetch(`${API_BASE_URL}/api/evaluations?limit=${limit}`);
  if (!res.ok) throw new Error(`evaluations ${res.status}`);
  const data = (await res.json()) as { evaluations: EvaluationRecord[] };
  return data.evaluations;
}

export async function runEvaluation(payload: {
  experimentName?: string;
  maxTasks?: number;
  mode?: "structural" | "full";
}): Promise<{ id: number; result: EvaluationResult }> {
  const res = await fetch(`${API_BASE_URL}/api/evaluations/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error((detail as { detail?: string }).detail ?? `evaluation ${res.status}`);
  }
  return res.json();
}

export interface EvaluationResult {
  experiment_name: string;
  model_provider: string;
  research_mode: string;
  eval_mode: string;
  judge_model?: string | null;
  langsmith_tracing?: boolean;
  langsmith_project?: string | null;
  total_tasks: number;
  average_score: number;
  average_latency_seconds: number;
  average_source_count: number;
  avg_comparison_two_sidedness?: number | null;
  avg_comparison_citation_validity?: number | null;
  avg_grounding_rate?: number | null;
  avg_hallucination_rate?: number | null;
  avg_comparison_grounding?: number | null;
  task_scores: Array<Record<string, unknown>>;
}

export interface EvaluationRecord {
  id: number;
  experimentName: string;
  createdAt: string;
  modelProvider?: string | null;
  researchMode?: string | null;
  evalMode?: string | null;
  judgeModel?: string | null;
  totalTasks?: number | null;
  averageScore?: number | null;
  averageLatencySeconds?: number | null;
  averageSourceCount?: number | null;
  result: EvaluationResult | null;
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
      snippet: readString(source, "snippet", "snippet") || undefined,
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
      url: readString(evidence, "url", "url") || undefined,
      rawText: readString(evidence, "rawText", "raw_text") || undefined,
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

const ADVANTAGES: ComparisonAdvantage[] = ["our", "competitor", "parity", "unclear"];

function parseComparisonMatrix(
  raw: Record<string, unknown>,
): ComparisonMatrix | undefined {
  const matrix =
    (raw.comparisonMatrix as Record<string, unknown> | undefined) ??
    (raw.comparison_matrix as Record<string, unknown> | undefined);
  if (!matrix) return undefined;

  const rawRows = Array.isArray(matrix.rows) ? matrix.rows : [];
  const rows: FeatureComparisonRow[] = rawRows.map((item) => {
    const row = item as Record<string, unknown>;
    const advantage = readString(row, "advantage", "advantage");
    return {
      dimension: readString(row, "dimension", "dimension"),
      ourValue: readString(row, "ourValue", "our_value"),
      competitorValue: readString(row, "competitorValue", "competitor_value"),
      ourSourceIds: readStringArray(row, "ourSourceIds", "our_source_ids"),
      competitorSourceIds: readStringArray(
        row,
        "competitorSourceIds",
        "competitor_source_ids",
      ),
      advantage: (ADVANTAGES.includes(advantage as ComparisonAdvantage)
        ? advantage
        : "unclear") as ComparisonAdvantage,
    };
  });

  return {
    rows,
    pricingComparison: readString(matrix, "pricingComparison", "pricing_comparison"),
    positioningGap: readString(matrix, "positioningGap", "positioning_gap"),
    summary: readString(matrix, "summary", "summary"),
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
    comparisonMatrix: parseComparisonMatrix(raw),
    evidence: parseEvidence(raw),
    sources: parseSources(raw),
    confidenceScore: readNumber(raw, "confidenceScore", "confidence_score"),
    researchMode: readString(raw, "researchMode", "research_mode") || undefined,
    generatedAt: readString(raw, "generatedAt", "generated_at") || undefined,
    warnings: readStringArray(raw, "warnings", "warnings"),
  };
}
