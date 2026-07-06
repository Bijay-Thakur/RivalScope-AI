"use client";

import { useEffect, useLayoutEffect, useMemo, useRef } from "react";

type StageStatus = "complete" | "active" | "future";

interface StageDef {
  step: number;
  label: string;
  detail: string;
}

const STAGE_1: StageDef = { step: 1, label: "Input Agent", detail: "Normalizing research parameters" };
const STAGE_2: StageDef = { step: 2, label: "Planning Agent", detail: "Building the research plan" };
const PARALLEL_STAGES: StageDef[] = [
  { step: 3, label: "Company Profile Agent", detail: "Researching company background" },
  { step: 4, label: "Product Agent", detail: "Analyzing product & features" },
  { step: 5, label: "Pricing Agent", detail: "Collecting pricing signals" },
  { step: 6, label: "News Agent", detail: "Scanning recent news" },
];
const STAGE_7: StageDef = { step: 7, label: "Fact-Checking Agent", detail: "Verifying claims against sources" };
const STAGE_8: StageDef = { step: 8, label: "Comparison Agent", detail: "Building structured head-to-head" };
const STAGE_9: StageDef = { step: 9, label: "Report Writer Agent", detail: "Synthesizing the final report" };

const TOTAL_STEPS = 9;

interface AgentTrackerModalProps {
  isOpen: boolean;
  isRunning: boolean;
  completedSteps: number[];
  workingSteps: number[];
  streamedText: Record<number, string>;
  progressMessage: string | null;
  error: string | null;
  runLabel: { ourCompany: string; competitor: string } | null;
  onClose: () => void;
}

export function AgentTrackerModal({
  isOpen,
  isRunning,
  completedSteps,
  workingSteps,
  streamedText,
  progressMessage,
  error,
  runLabel,
  onClose,
}: AgentTrackerModalProps) {
  const doneSet = useMemo(() => new Set(completedSteps), [completedSteps]);
  const workingSet = useMemo(() => new Set(workingSteps), [workingSteps]);
  const allDone = !isRunning && !error && doneSet.size >= TOTAL_STEPS;
  const canDismiss = !isRunning;

  // Explicit, real-time status from the backend's agent_status events. Works for both
  // sequential nodes and the parallel track cluster (each node reports its own state).
  const statusOf = (step: number): StageStatus => {
    if (allDone || doneSet.has(step)) return "complete";
    if (workingSet.has(step)) return "active";
    return "future";
  };
  const sequentialStatus = statusOf;
  const laneStatus = statusOf;

  const clusterStatus: StageStatus = allDone ||
    PARALLEL_STAGES.every((s) => doneSet.has(s.step))
    ? "complete"
    : PARALLEL_STAGES.some((s) => workingSet.has(s.step))
      ? "active"
      : "future";

  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && canDismiss) onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [isOpen, canDismiss, onClose]);

  if (!isOpen) return null;

  const completedCount = allDone ? TOTAL_STEPS : doneSet.size;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Research agent progress"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      onClick={() => canDismiss && onClose()}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[90vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-neutral-800 bg-neutral-900 shadow-2xl shadow-black/50"
      >
        <div className="flex shrink-0 items-start justify-between gap-4 border-b border-neutral-800 px-6 py-5 sm:px-7">
          <div>
            <span className="inline-block text-[11px] font-semibold uppercase tracking-[0.14em] text-amber-400">
              Agent Pipeline
            </span>
            <h2 className="mt-1.5 text-lg font-semibold tracking-tight text-neutral-100 sm:text-xl">
              {error
                ? "Research run failed"
                : allDone
                  ? "Research complete"
                  : "Running research agents"}
            </h2>
            {runLabel && (
              <p className="mt-1 text-sm text-neutral-500">
                {runLabel.ourCompany} vs {runLabel.competitor}
              </p>
            )}
          </div>
          {canDismiss && (
            <button
              type="button"
              onClick={onClose}
              className="shrink-0 rounded-lg p-1.5 text-neutral-500 transition-colors hover:bg-neutral-800 hover:text-neutral-200"
              aria-label="Close"
            >
              <CloseIcon />
            </button>
          )}
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-6 sm:px-7">
          {error ? (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3.5 text-sm text-red-300">
              {error}
            </div>
          ) : (
            <div className="flex flex-col">
              <StageRow stage={STAGE_1} status={sequentialStatus(STAGE_1.step)} streamedText={streamedText[STAGE_1.step]} />
              <Connector
                flowing={sequentialStatus(STAGE_1.step) === "complete" && sequentialStatus(STAGE_2.step) !== "complete"}
                complete={sequentialStatus(STAGE_2.step) === "complete"}
              />
              <StageRow stage={STAGE_2} status={sequentialStatus(STAGE_2.step)} streamedText={streamedText[STAGE_2.step]} />
              <Connector
                flowing={sequentialStatus(STAGE_2.step) === "complete" && clusterStatus !== "complete"}
                complete={clusterStatus === "complete"}
              />

              <ParallelCluster
                stages={PARALLEL_STAGES}
                laneStatus={laneStatus}
                clusterStatus={clusterStatus}
                streamedText={streamedText}
              />

              <Connector
                flowing={clusterStatus === "complete" && sequentialStatus(STAGE_7.step) !== "complete"}
                complete={sequentialStatus(STAGE_7.step) === "complete"}
              />
              <StageRow stage={STAGE_7} status={sequentialStatus(STAGE_7.step)} streamedText={streamedText[STAGE_7.step]} />
              <Connector
                flowing={sequentialStatus(STAGE_7.step) === "complete" && sequentialStatus(STAGE_8.step) !== "complete"}
                complete={sequentialStatus(STAGE_8.step) === "complete"}
              />
              <StageRow stage={STAGE_8} status={sequentialStatus(STAGE_8.step)} streamedText={streamedText[STAGE_8.step]} />
              <Connector
                flowing={sequentialStatus(STAGE_8.step) === "complete" && sequentialStatus(STAGE_9.step) !== "complete"}
                complete={sequentialStatus(STAGE_9.step) === "complete"}
              />
              <StageRow stage={STAGE_9} status={sequentialStatus(STAGE_9.step)} streamedText={streamedText[STAGE_9.step]} isLast />
            </div>
          )}
        </div>

        <div className="shrink-0 border-t border-neutral-800 px-6 py-4 sm:px-7">
          <div className="mb-2.5 flex items-center justify-between text-xs">
            <span className="text-neutral-500">
              {error ? "Stopped" : allDone ? "All agents complete" : "Steps completed"}
            </span>
            <span className="font-medium tabular-nums text-neutral-300">
              {completedCount} / {TOTAL_STEPS}
            </span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-neutral-800">
            <div
              className={`h-full rounded-full transition-all duration-500 ease-out ${
                error ? "bg-red-500/70" : "bg-amber-500"
              }`}
              style={{ width: `${(completedCount / TOTAL_STEPS) * 100}%` }}
            />
          </div>
          {!error && !allDone && progressMessage && (
            <p className="mt-3 text-xs leading-relaxed text-neutral-500">{progressMessage}</p>
          )}
          {(error || canDismiss) && (
            <div className="mt-4 flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="inline-flex items-center rounded-lg border border-neutral-700 bg-neutral-800/60 px-4 py-2 text-xs font-semibold text-neutral-200 transition-colors hover:border-neutral-600"
              >
                {error ? "Close" : "Dismiss"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ParallelCluster({
  stages,
  laneStatus,
  clusterStatus,
  streamedText,
}: {
  stages: StageDef[];
  laneStatus: (step: number) => StageStatus;
  clusterStatus: StageStatus;
  streamedText: Record<number, string>;
}) {
  return (
    <div
      className={`rounded-xl border p-4 sm:p-5 ${
        clusterStatus === "complete"
          ? "border-amber-500/30 bg-amber-500/5"
          : clusterStatus === "active"
            ? "border-neutral-700 bg-neutral-800/40"
            : "border-neutral-800 bg-neutral-900"
      }`}
    >
      <p className="mb-3.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-neutral-500">
        Parallel research — 4 agents running together
      </p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {stages.map((stage) => (
          <LaneCard
            key={stage.step}
            stage={stage}
            status={laneStatus(stage.step)}
            streamedText={streamedText[stage.step]}
          />
        ))}
      </div>
    </div>
  );
}

function LaneCard({
  stage,
  status,
  streamedText,
}: {
  stage: StageDef;
  status: StageStatus;
  streamedText?: string;
}) {
  return (
    <div
      className={`rounded-lg border px-3.5 py-3 transition-shadow ${
        status === "complete"
          ? "border-amber-500/20 bg-amber-500/5"
          : status === "active"
            ? "border-amber-500/40 bg-neutral-900 shadow-[0_0_0_1px_rgba(245,158,11,0.25),0_0_18px_-4px_rgba(245,158,11,0.5)] motion-safe:animate-[agent-glow_2s_ease-in-out_infinite]"
            : "border-neutral-800 bg-neutral-900/60"
      }`}
    >
      <div className="flex items-center gap-3">
        <StatusIcon status={status} stepNumber={stage.step} size="sm" />
        <div className="min-w-0">
          <p
            className={`truncate text-sm font-medium ${
              status === "future" ? "text-neutral-600" : "text-neutral-200"
            }`}
          >
            {stage.label}
          </p>
          <p className="truncate text-xs text-neutral-500">
            {status === "future" ? "Queued" : stage.detail}
          </p>
        </div>
      </div>
      {status === "active" && streamedText ? <StreamPanel text={streamedText} /> : null}
    </div>
  );
}

function StageRow({
  stage,
  status,
  streamedText,
  isLast = false,
}: {
  stage: StageDef;
  status: StageStatus;
  streamedText?: string;
  isLast?: boolean;
}) {
  return (
    <div className="flex flex-col">
      <div className="flex items-center gap-4">
        <StatusIcon status={status} stepNumber={stage.step} size="md" />
        <div className="min-w-0 flex-1 py-2.5">
          <p
            className={`text-sm ${
              status === "future"
                ? "text-neutral-600"
                : status === "active"
                  ? "font-medium text-neutral-100"
                  : "text-neutral-300"
            }`}
          >
            {stage.label}
          </p>
          <p className="mt-0.5 text-xs text-neutral-500">
            {status === "future" ? "Queued" : stage.detail}
          </p>
        </div>
        {isLast && status === "complete" && (
          <span className="shrink-0 text-xs font-medium text-amber-400">Done</span>
        )}
      </div>
      {status === "active" && streamedText ? (
        <div className="ml-12 mb-1">
          <StreamPanel text={streamedText} />
        </div>
      ) : null}
    </div>
  );
}

// Live LLM token/thought text streaming into the active agent's card. Auto-scrolls to the
// newest tokens; top edge fades so older text recedes. Absent tokens -> panel simply
// never renders (status glow still communicates progress).
function StreamPanel({ text }: { text: string }) {
  const ref = useRef<HTMLDivElement | null>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [text]);

  return (
    <div
      ref={ref}
      aria-live="polite"
      className="mt-2 max-h-24 overflow-y-auto rounded-md border border-neutral-800 bg-neutral-950/70 px-3 py-2 font-mono text-[11px] leading-relaxed text-neutral-400 [mask-image:linear-gradient(to_bottom,transparent,black_1.5rem)]"
    >
      <span className="whitespace-pre-wrap break-words">{text}</span>
      <span className="ml-0.5 inline-block h-3 w-1.5 translate-y-0.5 bg-amber-400/80 motion-safe:animate-pulse" />
    </div>
  );
}

function Connector({ flowing, complete }: { flowing: boolean; complete: boolean }) {
  return (
    <div className="relative ml-[15px] h-6 w-px overflow-hidden">
      <div
        className={`absolute inset-0 w-px ${complete ? "bg-amber-500/40" : "bg-neutral-800"}`}
      />
      {flowing && !complete && (
        <span
          className="absolute left-1/2 top-0 h-2.5 w-2.5 -translate-x-1/2 animate-[flow-down_1.4s_ease-in-out_infinite] rounded-full bg-amber-400"
          aria-hidden="true"
        />
      )}
    </div>
  );
}

function StatusIcon({
  status,
  stepNumber,
  size,
}: {
  status: StageStatus;
  stepNumber: number;
  size: "sm" | "md";
}) {
  const dims = size === "sm" ? "h-7 w-7" : "h-8 w-8";

  if (status === "complete") {
    return (
      <span
        className={`relative z-10 flex ${dims} shrink-0 items-center justify-center rounded-full border border-amber-500/30 bg-amber-500/10 text-amber-400`}
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
        </svg>
      </span>
    );
  }

  if (status === "active") {
    return (
      <span
        className={`relative z-10 flex ${dims} shrink-0 items-center justify-center rounded-full border border-amber-500/50 bg-neutral-900`}
      >
        <span
          className="absolute inset-0 rounded-full bg-amber-400/20 motion-safe:animate-[agent-ring_2s_ease-in-out_infinite]"
          aria-hidden="true"
        />
        <span className="relative h-3.5 w-3.5 animate-spin rounded-full border-2 border-neutral-700 border-t-amber-400 motion-reduce:animate-none" />
      </span>
    );
  }

  return (
    <span
      className={`relative z-10 flex ${dims} shrink-0 items-center justify-center rounded-full border border-neutral-800 bg-neutral-900 text-xs font-medium text-neutral-600`}
    >
      {stepNumber}
    </span>
  );
}

function CloseIcon() {
  return (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
    </svg>
  );
}
