import { PLACEHOLDER_PROGRESS_STEPS } from "@/data/constants";
import type { AgentProgressStep } from "@/types";

interface AgentProgressPanelProps {
  steps?: AgentProgressStep[];
  isActive?: boolean;
}

export function AgentProgressPanel({
  steps = PLACEHOLDER_PROGRESS_STEPS,
  isActive = false,
}: AgentProgressPanelProps) {
  return (
    <section className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 shadow-xl shadow-black/20 backdrop-blur-sm">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-white">Agent Progress</h2>
          <p className="mt-1 text-sm text-slate-400">
            Live status updates from the research agent will appear here.
          </p>
        </div>
        <StatusBadge isActive={isActive} />
      </div>

      {!isActive ? (
        <EmptyState />
      ) : (
        <ol className="space-y-3">
          {steps.map((step, index) => (
            <li
              key={step.id}
              className="flex items-center gap-4 rounded-lg border border-slate-800/60 bg-slate-950/40 px-4 py-3"
            >
              <StepIndicator status={step.status} index={index} />
              <span
                className={`text-sm ${
                  step.status === "complete"
                    ? "text-slate-400 line-through"
                    : step.status === "active"
                      ? "font-medium text-indigo-300"
                      : "text-slate-500"
                }`}
              >
                {step.label}
              </span>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function StatusBadge({ isActive }: { isActive: boolean }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
        isActive
          ? "bg-indigo-500/15 text-indigo-300 ring-1 ring-indigo-500/30"
          : "bg-slate-800 text-slate-500 ring-1 ring-slate-700"
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          isActive ? "animate-pulse bg-indigo-400" : "bg-slate-600"
        }`}
      />
      {isActive ? "Running" : "Idle"}
    </span>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-700/60 bg-slate-950/30 px-6 py-12 text-center">
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-slate-800/80">
        <svg
          className="h-6 w-6 text-slate-500"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z"
          />
        </svg>
      </div>
      <p className="text-sm font-medium text-slate-400">Waiting to start</p>
      <p className="mt-1 max-w-xs text-xs text-slate-600">
        Submit the research form above to kick off the agent pipeline.
      </p>
    </div>
  );
}

function StepIndicator({
  status,
  index,
}: {
  status: AgentProgressStep["status"];
  index: number;
}) {
  if (status === "complete") {
    return (
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400">
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
        </svg>
      </span>
    );
  }

  if (status === "active") {
    return (
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-500/20 ring-2 ring-indigo-500/40">
        <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-400" />
      </span>
    );
  }

  return (
    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-800 text-xs font-medium text-slate-500">
      {index + 1}
    </span>
  );
}
