import { ProductLabel } from "./ProductLabel";
import { EMPTY_STATE_CLASS, PANEL_CLASS, PANEL_PADDING } from "./ui/styles";

const PROGRESS_STEPS = [
  "Normalizing research input",
  "Creating research plan",
  "Researching company profile",
  "Analyzing product and features",
  "Collecting pricing signals",
  "Scanning recent news",
  "Verifying claims against sources",
  "Generating final report",
] as const;

interface ResearchProgressProps {
  isRunning: boolean;
  currentStep: number;
  progressMessage?: string | null;
}

type StepStatus = "complete" | "current" | "future";

function getStepStatus(
  stepNumber: number,
  isRunning: boolean,
  currentStep: number,
): StepStatus {
  if (stepNumber < currentStep) return "complete";
  if (isRunning && stepNumber === currentStep) return "current";
  return "future";
}

export function ResearchProgress({
  isRunning,
  currentStep,
  progressMessage = null,
}: ResearchProgressProps) {
  const completedCount =
    currentStep > PROGRESS_STEPS.length
      ? PROGRESS_STEPS.length
      : Math.max(0, currentStep - 1);

  return (
    <section className={`${PANEL_CLASS} ${PANEL_PADDING}`}>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4 sm:mb-7">
        <div>
          <ProductLabel tone="gold">Agent Workflow</ProductLabel>
          <h2 className="mt-2 text-lg font-semibold tracking-tight text-stone-900 sm:text-xl">
            Research Progress
          </h2>
          <p className="mt-1.5 text-sm leading-relaxed text-stone-600">
            Eight-step pipeline from input normalization through report generation.
          </p>
        </div>
        <StatusBadge isRunning={isRunning} />
      </div>

      {!isRunning && currentStep === 0 ? (
        <EmptyState />
      ) : (
        <>
          <div className="mb-5 flex items-center justify-between rounded-lg border border-stone-200 bg-stone-50 px-4 py-2.5">
            <span className="text-xs text-stone-500">Steps completed</span>
            <span className="text-xs font-medium tabular-nums text-stone-800">
              {completedCount} / {PROGRESS_STEPS.length}
            </span>
          </div>

          <ol className="relative space-y-0">
            {PROGRESS_STEPS.map((label, index) => {
              const stepNumber = index + 1;
              const status = getStepStatus(stepNumber, isRunning, currentStep);
              const isLast = index === PROGRESS_STEPS.length - 1;

              return (
                <li key={label} className="relative flex gap-4 pb-8 last:pb-0">
                  {!isLast && (
                    <span
                      className={`absolute left-[15px] top-8 h-[calc(100%-16px)] w-px ${
                        status === "complete" ? "bg-amber-700/30" : "bg-stone-200"
                      }`}
                      aria-hidden="true"
                    />
                  )}

                  <StepIndicator status={status} stepNumber={stepNumber} />
                  <div className="min-w-0 flex-1 pt-0.5">
                    <p
                      className={`text-sm leading-snug ${
                        status === "complete"
                          ? "text-stone-500"
                          : status === "current"
                            ? "font-medium text-stone-900"
                            : "text-stone-400"
                      }`}
                    >
                      {label}
                    </p>
                    {status === "current" && (
                      <p className="mt-1.5 text-xs text-amber-800">
                        {progressMessage ?? "In progress…"}
                      </p>
                    )}
                    {status === "complete" && (
                      <p className="mt-1 text-xs text-stone-400">Complete</p>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        </>
      )}
    </section>
  );
}

function StatusBadge({ isRunning }: { isRunning: boolean }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium ${
        isRunning
          ? "border border-amber-200 bg-amber-50 text-amber-900"
          : "border border-stone-200 bg-stone-50 text-stone-500"
      }`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          isRunning ? "animate-pulse bg-amber-700" : "bg-stone-400"
        }`}
      />
      {isRunning ? "Running" : "Idle"}
    </span>
  );
}

function EmptyState() {
  return (
    <div className={EMPTY_STATE_CLASS}>
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full border border-stone-200 bg-white">
        <svg
          className="h-5 w-5 text-stone-400"
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
      <p className="text-sm font-medium text-stone-700">Agent workflow idle</p>
      <p className="mt-2 max-w-xs text-xs leading-relaxed text-stone-500">
        Generate a brief to start the eight-step research pipeline. Progress
        updates stream from the backend in real time.
      </p>
    </div>
  );
}

function StepIndicator({
  status,
  stepNumber,
}: {
  status: StepStatus;
  stepNumber: number;
}) {
  if (status === "complete") {
    return (
      <span className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-amber-200 bg-amber-50 text-amber-800">
        <svg
          className="h-4 w-4"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={2.5}
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="m4.5 12.75 6 6 9-13.5"
          />
        </svg>
      </span>
    );
  }

  if (status === "current") {
    return (
      <span className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-stone-300 bg-white">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-stone-200 border-t-amber-700" />
      </span>
    );
  }

  return (
    <span className="relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-stone-200 bg-stone-50 text-xs font-medium text-stone-400">
      {stepNumber}
    </span>
  );
}
