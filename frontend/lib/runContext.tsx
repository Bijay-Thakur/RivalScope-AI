"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  buildResearchStreamUrl,
  parseStreamReport,
  type AgentStatusEvent,
  type TokenEvent,
  type TraceEvent,
} from "@/lib/api";
import { saveSession } from "@/lib/reportStore";
import type { CompetitorReport, ResearchInput } from "@/types/report";

export type RunStatus = "idle" | "running" | "done" | "error";

interface RunState {
  status: RunStatus;
  runId: string | null;
  input: ResearchInput | null;
  completedSteps: number[];
  workingSteps: number[];
  streamedText: Record<number, string>;
  traces: TraceEvent[];
  progressMessage: string | null;
  error: string | null;
  report: CompetitorReport | null;
  elapsedMs: number;
  sourcesFound: number;
}

interface RunContextValue extends RunState {
  startRun: (input: ResearchInput) => void;
  reset: () => void;
}

const RunContext = createContext<RunContextValue | null>(null);

const INITIAL: RunState = {
  status: "idle",
  runId: null,
  input: null,
  completedSteps: [],
  workingSteps: [],
  streamedText: {},
  traces: [],
  progressMessage: null,
  error: null,
  report: null,
  elapsedMs: 0,
  sourcesFound: 0,
};

export function RunProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<RunState>(INITIAL);
  const esRef = useRef<EventSource | null>(null);
  const startedAtRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const doneRef = useRef(false);

  const closeStream = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => () => closeStream(), [closeStream]);

  const reset = useCallback(() => {
    closeStream();
    doneRef.current = false;
    setState(INITIAL);
  }, [closeStream]);

  const startRun = useCallback(
    (input: ResearchInput) => {
      closeStream();
      doneRef.current = false;
      startedAtRef.current = Date.now();
      setState({
        ...INITIAL,
        status: "running",
        input,
      });

      timerRef.current = setInterval(() => {
        setState((prev) =>
          prev.status === "running"
            ? { ...prev, elapsedMs: Date.now() - startedAtRef.current }
            : prev,
        );
      }, 250);

      const es = new EventSource(buildResearchStreamUrl(input));
      esRef.current = es;

      es.addEventListener("agent_status", (event) => {
        const data = JSON.parse((event as MessageEvent).data) as AgentStatusEvent;
        setState((prev) => {
          const withRunId = data.runId ? { ...prev, runId: data.runId } : prev;
          if (data.status === "working") {
            return {
              ...withRunId,
              workingSteps: withRunId.workingSteps.includes(data.step)
                ? withRunId.workingSteps
                : [...withRunId.workingSteps, data.step],
            };
          }
          return {
            ...withRunId,
            completedSteps: withRunId.completedSteps.includes(data.step)
              ? withRunId.completedSteps
              : [...withRunId.completedSteps, data.step],
            workingSteps: withRunId.workingSteps.filter((s) => s !== data.step),
            progressMessage: data.message || withRunId.progressMessage,
          };
        });
      });

      es.addEventListener("token", (event) => {
        const data = JSON.parse((event as MessageEvent).data) as TokenEvent;
        if (!data.delta) return;
        setState((prev) => ({
          ...prev,
          streamedText: {
            ...prev.streamedText,
            [data.step]: (prev.streamedText[data.step] ?? "") + data.delta,
          },
        }));
      });

      es.addEventListener("trace", (event) => {
        const trace = JSON.parse((event as MessageEvent).data) as TraceEvent;
        setState((prev) => {
          const resultCount =
            trace.name === "tavily_search" && trace.detail
              ? Number(trace.detail.resultCount ?? 0)
              : 0;
          return {
            ...prev,
            traces: [...prev.traces, trace],
            sourcesFound: prev.sourcesFound + resultCount,
          };
        });
      });

      es.addEventListener("final_report", (event) => {
        doneRef.current = true;
        const raw = JSON.parse((event as MessageEvent).data) as Record<string, unknown>;
        const report = parseStreamReport(raw);
        closeStream();
        setState((prev) => {
          saveSession({
            report,
            input: prev.input ?? undefined,
            runId: prev.runId ?? undefined,
            traces: prev.traces,
          });
          return {
            ...prev,
            status: "done",
            report,
            sourcesFound: report.sources.length || prev.sourcesFound,
            completedSteps: Array.from({ length: 9 }, (_, i) => i + 1),
            workingSteps: [],
            elapsedMs: Date.now() - startedAtRef.current,
          };
        });
      });

      es.addEventListener("error", (event) => {
        const msgEvent = event as MessageEvent;
        if (!msgEvent.data) return;
        doneRef.current = true;
        let detail = "Research workflow failed.";
        try {
          detail = (JSON.parse(msgEvent.data) as { detail?: string }).detail ?? detail;
        } catch {
          /* keep default */
        }
        closeStream();
        setState((prev) => ({ ...prev, status: "error", error: detail }));
      });

      es.onerror = () => {
        if (doneRef.current) return;
        closeStream();
        setState((prev) =>
          prev.status === "running"
            ? {
                ...prev,
                status: "error",
                error:
                  "Lost connection to the research stream. Ensure the backend is running at http://localhost:8000.",
              }
            : prev,
        );
      };
    },
    [closeStream],
  );

  return (
    <RunContext.Provider value={{ ...state, startRun, reset }}>
      {children}
    </RunContext.Provider>
  );
}

export function useRun(): RunContextValue {
  const ctx = useContext(RunContext);
  if (!ctx) throw new Error("useRun must be used within RunProvider");
  return ctx;
}

/** Rough $ estimate for a run based on LLM trace prompt sizes (portfolio-grade heuristic). */
export function estimateCost(traces: TraceEvent[]): number {
  const llmChars = traces
    .filter((t) => t.kind === "llm")
    .reduce((sum, t) => sum + Number(t.detail?.promptChars ?? 0), 0);
  // ~4 chars/token, blended ~$0.5 / 1M tokens (Groq-ish). Cheap by design.
  const tokens = llmChars / 4;
  return (tokens / 1_000_000) * 0.5;
}
