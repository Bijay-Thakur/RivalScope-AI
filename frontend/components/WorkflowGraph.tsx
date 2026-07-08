"use client";

type NodeState = "idle" | "working" | "done";

interface WorkflowGraphProps {
  completedSteps: number[];
  workingSteps: number[];
}

const TONE_STYLES: Record<
  string,
  { bg: string; border: string; glow: string; dot: string }
> = {
  gold: {
    bg: "rgba(250, 237, 207, 0.95)",
    border: "#e0a92e",
    glow: "rgba(224, 169, 46, 0.55)",
    dot: "var(--accent-strong)",
  },
  blue: {
    bg: "rgba(227, 235, 253, 0.95)",
    border: "#7c9cf0",
    glow: "rgba(124, 156, 240, 0.5)",
    dot: "var(--dot-blue)",
  },
  green: {
    bg: "rgba(220, 245, 233, 0.95)",
    border: "#6fce9f",
    glow: "rgba(111, 206, 159, 0.5)",
    dot: "var(--dot-green)",
  },
  yellow: {
    bg: "rgba(250, 240, 207, 0.95)",
    border: "#f2cf6a",
    glow: "rgba(242, 207, 106, 0.5)",
    dot: "var(--dot-yellow)",
  },
  purple: {
    bg: "rgba(237, 228, 251, 0.95)",
    border: "#b79be6",
    glow: "rgba(183, 155, 230, 0.5)",
    dot: "var(--dot-purple)",
  },
};

export function WorkflowGraph({ completedSteps, workingSteps }: WorkflowGraphProps) {
  const nodeState = (step: number): NodeState =>
    completedSteps.includes(step)
      ? "done"
      : workingSteps.includes(step)
        ? "working"
        : "idle";

  const trackStates = [3, 4, 5, 6].map(nodeState);
  const tracksWorking = trackStates.includes("working");
  const tracksDone = trackStates.every((s) => s === "done");

  return (
    <div className="rs-graph-canvas mt-5 overflow-x-auto rs-scroll rounded-2xl border border-[var(--border-strong)] p-5 sm:p-6">
      <div className="rs-graph-mesh pointer-events-none absolute inset-0 opacity-80" aria-hidden />
      <div className="relative flex min-w-[720px] items-center justify-between gap-1">
        <GraphNode label="Planner" sub="fan-out" tone="gold" state={nodeState(2)} step={2} />
        <FlowArrow active={nodeState(2) === "done" || tracksWorking || tracksDone} />
        <TrackCluster
          states={trackStates}
          labels={["Company", "Product", "Pricing", "News"]}
          tones={["blue", "green", "yellow", "purple"]}
          steps={[3, 4, 5, 6]}
        />
        <FlowArrow active={tracksDone || nodeState(7) !== "idle"} />
        <GraphNode label="Verifier" sub="ground claims" tone="purple" state={nodeState(7)} step={7} />
        <FlowArrow active={nodeState(7) === "done" || nodeState(8) !== "idle"} />
        <GraphNode label="Compare" sub="matrix" tone="blue" state={nodeState(8)} step={8} />
        <FlowArrow active={nodeState(8) === "done" || nodeState(9) !== "idle"} />
        <GraphNode label="Report" sub="synthesize" tone="gold" state={nodeState(9)} step={9} />
      </div>
      <p className="relative mt-4 text-center text-[10px] font-medium uppercase tracking-widest text-[var(--muted-2)]">
        LangGraph · 4 parallel research tracks · live SSE
      </p>
    </div>
  );
}

function TrackCluster({
  labels,
  tones,
  steps,
  states,
}: {
  labels: string[];
  tones: string[];
  steps: number[];
  states: NodeState[];
}) {
  const clusterState: NodeState = states.some((s) => s === "working")
    ? "working"
    : states.every((s) => s === "done")
      ? "done"
      : "idle";

  return (
    <div
      className={`rs-track-cluster flex flex-col gap-2 rounded-xl border px-2 py-2 transition-all duration-500 ${
        clusterState === "working"
          ? "rs-track-cluster-active border-[var(--accent-strong)]"
          : clusterState === "done"
            ? "border-[var(--ok)]/40 bg-[var(--ok-bg)]/30"
            : "border-[var(--border)] bg-white/40"
      }`}
    >
      {labels.map((label, i) => (
        <GraphNode
          key={steps[i]}
          label={label}
          tone={tones[i]}
          state={states[i]}
          step={steps[i]}
          compact
        />
      ))}
    </div>
  );
}

function GraphNode({
  label,
  sub,
  tone,
  state,
  step,
  compact = false,
}: {
  label: string;
  sub?: string;
  tone: string;
  state: NodeState;
  step: number;
  compact?: boolean;
}) {
  const style = TONE_STYLES[tone] ?? TONE_STYLES.gold;

  return (
    <div
      className={`rs-graph-node group relative shrink-0 text-center transition-all duration-300 ${
        compact ? "min-w-[88px]" : "min-w-[96px]"
      } ${state === "working" ? "rs-graph-node-active z-10 scale-105" : ""} ${
        state === "done" ? "rs-graph-node-done" : ""
      } ${state === "idle" ? "opacity-55 hover:opacity-80" : "opacity-100"}`}
      data-state={state}
      title={`Step ${step}`}
    >
      {state === "working" && (
        <span
          className="rs-graph-pulse-ring pointer-events-none absolute inset-0 rounded-xl"
          style={{ boxShadow: `0 0 0 2px ${style.glow}` }}
          aria-hidden
        />
      )}
      <div
        className={`relative rounded-xl border-2 font-semibold transition-all duration-300 ${
          compact ? "px-2.5 py-1.5 text-[10px]" : "px-3 py-2.5 text-xs"
        } ${state === "working" ? "rs-graph-node-glow" : ""}`}
        style={{
          backgroundColor: style.bg,
          borderColor: state === "idle" ? "var(--border)" : style.border,
          boxShadow:
            state === "working"
              ? `0 0 20px ${style.glow}, 0 4px 14px rgba(28,27,26,0.08)`
              : state === "done"
                ? `0 0 8px ${style.glow}`
                : "none",
        }}
      >
        <span
          className="mb-0.5 inline-block h-1.5 w-1.5 rounded-full"
          style={{ backgroundColor: style.dot }}
          aria-hidden
        />
        <div className="leading-tight text-[var(--foreground)]">{label}</div>
        {sub && !compact && (
          <div className="mt-0.5 text-[9px] font-normal uppercase tracking-wide text-[var(--muted)]">
            {sub}
          </div>
        )}
        {state === "done" && (
          <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full bg-[var(--ok)] text-[8px] text-white shadow-sm">
            ✓
          </span>
        )}
        {state === "working" && (
          <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center">
            <span className="rs-graph-spinner h-3.5 w-3.5 rounded-full border-2 border-[var(--warn)] border-t-transparent" />
          </span>
        )}
      </div>
    </div>
  );
}

function FlowArrow({ active }: { active: boolean }) {
  return (
    <svg
      className={`rs-flow-arrow h-6 w-10 shrink-0 ${active ? "rs-flow-arrow-active" : ""}`}
      viewBox="0 0 40 24"
      fill="none"
      aria-hidden
    >
      <line
        x1="2"
        y1="12"
        x2="30"
        y2="12"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        className="text-[var(--border-strong)]"
      />
      <path
        d="M28 7 L34 12 L28 17"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-[var(--border-strong)]"
      />
      {active && (
        <circle r="3" className="rs-flow-dot fill-[var(--accent-strong)]">
          <animateMotion dur="1.2s" repeatCount="indefinite" path="M4,12 L30,12" />
        </circle>
      )}
    </svg>
  );
}
