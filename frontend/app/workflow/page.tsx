"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { Card, PageHeader, PrimaryButton, StatCard } from "@/components/ui/primitives";
import { WorkflowGraph } from "@/components/WorkflowGraph";
import { fetchRunTraces, type TraceEvent } from "@/lib/api";
import { estimateCost, useRun } from "@/lib/runContext";
import { WORKFLOW_STEPS } from "@/lib/steps";

function WorkflowContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const historyRunId = searchParams.get("run");

  const {
    status,
    input,
    completedSteps,
    workingSteps,
    traces,
    progressMessage,
    error,
    elapsedMs,
    sourcesFound,
  } = useRun();
  const [historyTraces, setHistoryTraces] = useState<TraceEvent[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    if (!historyRunId) return;
    setHistoryLoading(true);
    fetchRunTraces(historyRunId)
      .then(setHistoryTraces)
      .catch(() => setHistoryTraces([]))
      .finally(() => setHistoryLoading(false));
  }, [historyRunId]);

  const displayTraces = historyRunId ? historyTraces : traces;
  const isHistory = Boolean(historyRunId);

  if (!isHistory && status === "idle") {
    return (
      <div className="rs-fade-in">
        <PageHeader badge="Page 2" title="Live Agent Workflow" />
        <Card className="flex flex-col items-center gap-4 px-6 py-16 text-center">
          <p className="text-base font-semibold">No active run</p>
          <p className="max-w-sm text-sm text-[var(--muted)]">
            Start a research run to watch the multi-step LangGraph pipeline, live tool
            calls, and streaming telemetry.
          </p>
          <PrimaryButton onClick={() => router.push("/")}>Start a research run</PrimaryButton>
        </Card>
      </div>
    );
  }

  const primaryCount = displayTraces.filter(
    (t) => t.name === "tavily_extract" && t.status === "completed",
  ).length;
  const toolCount = displayTraces.filter((t) => t.kind === "tool").length;
  const cost = estimateCost(displayTraces);

  return (
    <div className="rs-fade-in">
      <PageHeader
        badge="Page 2"
        title="Live Agent Workflow"
        subtitle={
          input
            ? `${input.ourCompany} vs ${input.competitor} — multi-step LangGraph workflow, streaming logs, and operational telemetry.`
            : "Multi-step LangGraph workflow, streaming logs, and operational telemetry."
        }
      />

      {isHistory && (
        <div className="mb-6 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] px-4 py-3 text-sm">
          Viewing persisted tool traces for run <code className="font-mono text-xs">{historyRunId}</code>
          {historyLoading && " — loading…"}
          <button
            type="button"
            onClick={() => router.push("/workflow")}
            className="ml-3 text-xs font-semibold text-[#3b5bdb] hover:underline"
          >
            Back to live
          </button>
        </div>
      )}

      {error && (
        <div className="mb-6 rounded-xl border border-[var(--bad)]/30 bg-[var(--bad-bg)] px-4 py-3 text-sm text-[var(--bad)]">
          {error}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr]">
        {/* Agent progress */}
        <Card className="p-6">
          <h2 className="text-lg font-bold tracking-tight">Agent Progress</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            True SSE events from node execution, not replayed progress.
          </p>
          <ol className="mt-5 space-y-1">
            {WORKFLOW_STEPS.map((s) => {
              const done = completedSteps.includes(s.step);
              const working = workingSteps.includes(s.step);
              return (
                <li key={s.step} className="flex items-start gap-3 py-2">
                  <StepIcon step={s.step} done={done} working={working} />
                  <div className="min-w-0">
                    <p
                      className={`text-sm font-semibold ${
                        done || working ? "text-[var(--foreground)]" : "text-[var(--muted-2)]"
                      }`}
                    >
                      {s.label}
                    </p>
                    <p className="text-xs text-[var(--muted)]">
                      {working
                        ? `${s.hint}…`
                        : done
                          ? "Completed"
                          : s.hint}
                    </p>
                  </div>
                </li>
              );
            })}
          </ol>
        </Card>

        <div className="space-y-6">
          {/* Telemetry */}
          <div className="grid grid-cols-3 gap-4">
            <StatCard
              label="Elapsed"
              value={`${(elapsedMs / 1000).toFixed(0)}s`}
              hint={status === "running" ? "current run" : "final"}
              accent="gold"
            />
            <StatCard
              label="Sources found"
              value={isHistory ? "—" : sourcesFound}
              hint={`${toolCount} tool calls · ${primaryCount} extracts`}
              accent="green"
            />
            <StatCard
              label="Cost estimate"
              value={`$${cost.toFixed(2)}`}
              hint="LLM + tools"
              accent="purple"
            />
          </div>

          {/* Workflow graph */}
          <Card className="overflow-hidden p-6">
            <h2 className="text-lg font-bold tracking-tight">Workflow Graph</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              Live LangGraph topology — active nodes glow as SSE events arrive.
            </p>
            <WorkflowGraph completedSteps={completedSteps} workingSteps={workingSteps} />
          </Card>

          {/* Streaming log */}
          <StreamingLog
            traces={displayTraces}
            progressMessage={isHistory ? null : progressMessage}
            status={isHistory ? "done" : status}
            loading={historyLoading}
          />
        </div>
      </div>

      {!isHistory && status === "done" && (
        <div className="mt-6 flex justify-center gap-3">
          <Link
            href="/report"
            className="inline-flex items-center gap-2 rounded-xl bg-[var(--ink)] px-5 py-2.5 text-sm font-semibold text-white hover:bg-black"
          >
            View competitive report →
          </Link>
          <Link
            href="/evidence"
            className="inline-flex items-center gap-2 rounded-xl border border-[var(--border-strong)] bg-white px-5 py-2.5 text-sm font-semibold text-[var(--foreground)] hover:bg-[var(--surface-muted)]"
          >
            Inspect evidence
          </Link>
        </div>
      )}
    </div>
  );
}

function StepIcon({ step, done, working }: { step: number; done: boolean; working: boolean }) {
  if (done) {
    return (
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--ok-bg)] text-[var(--ok)]">
        <svg viewBox="0 0 20 20" className="h-3.5 w-3.5" fill="currentColor">
          <path
            fillRule="evenodd"
            d="M16.7 5.3a1 1 0 010 1.4l-7.5 7.5a1 1 0 01-1.4 0L3.3 9.7a1 1 0 111.4-1.4l3.8 3.8 6.8-6.8a1 1 0 011.4 0z"
            clipRule="evenodd"
          />
        </svg>
      </span>
    );
  }
  if (working) {
    return (
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[var(--warn-bg)]">
        <span
          className="h-3.5 w-3.5 rounded-full border-2 border-[var(--warn)] border-t-transparent"
          style={{ animation: "rs-spin 0.8s linear infinite" }}
        />
      </span>
    );
  }
  return (
    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-[var(--border-strong)] text-[11px] font-semibold text-[var(--muted-2)]">
      {step}
    </span>
  );
}

function StreamingLog({
  traces,
  progressMessage,
  status,
  loading = false,
}: {
  traces: TraceEvent[];
  progressMessage: string | null;
  status: string;
  loading?: boolean;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const toolTraces = traces.filter((t) => t.kind === "tool");

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [traces.length]);

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold tracking-tight">Streaming Log</h2>
        <span className="text-xs font-medium text-[var(--muted-2)]">
          {toolTraces.length} tool · {traces.length} total
        </span>
      </div>
      <div
        ref={scrollRef}
        className="rs-scroll mt-4 max-h-64 space-y-1.5 overflow-y-auto font-mono text-xs"
      >
        {loading && <p className="text-[var(--muted-2)]">Loading traces…</p>}
        {!loading && traces.length === 0 && status === "running" && (
          <p className="text-[var(--muted-2)]">Waiting for tool calls…</p>
        )}
        {traces.map((t, i) => (
          <div key={`${t.seq}-${i}`} className="flex items-start gap-2 rs-fade-in">
            <TraceKindTag kind={t.kind} status={t.status} />
            <span className="min-w-0 flex-1 text-[var(--foreground)]">
              {formatTraceLine(t)}
              {typeof t.durationMs === "number" && t.durationMs > 0 && (
                <span className="text-[var(--muted-2)]"> · {t.durationMs.toFixed(0)}ms</span>
              )}
            </span>
          </div>
        ))}
        {progressMessage && (
          <p className="pt-1 text-[var(--muted)]">{progressMessage}</p>
        )}
      </div>
    </Card>
  );
}

function formatTraceLine(t: TraceEvent): string {
  const track = t.track ? `[${t.track}] ` : "";
  if (t.kind === "tool") {
    return `${track}${t.summary}`;
  }
  return t.summary;
}

function TraceKindTag({ kind, status }: { kind: string; status: string }) {
  const failed = status === "failed";
  const color = failed
    ? "bg-[var(--bad-bg)] text-[var(--bad)]"
    : kind === "tool"
      ? "bg-[#e3ebfd] text-[#3b5bdb]"
      : kind === "llm"
        ? "bg-[#ede4fb] text-[#7c3aed]"
        : "bg-[var(--surface-muted)] text-[var(--muted)]";
  return (
    <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${color}`}>
      {kind}
    </span>
  );
}

export default function WorkflowPage() {
  return (
    <Suspense fallback={<div className="p-8 text-sm text-[var(--muted)]">Loading workflow…</div>}>
      <WorkflowContent />
    </Suspense>
  );
}
