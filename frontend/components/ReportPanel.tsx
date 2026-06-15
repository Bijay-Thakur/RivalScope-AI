interface ReportPanelProps {
  hasReport?: boolean;
}

export function ReportPanel({ hasReport = false }: ReportPanelProps) {
  return (
    <section className="rounded-2xl border border-slate-800/80 bg-slate-900/40 p-6 shadow-xl shadow-black/20 backdrop-blur-sm">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-white">Final Report</h2>
          <p className="mt-1 text-sm text-slate-400">
            Your source-grounded competitive intelligence brief will render here.
          </p>
        </div>
        {hasReport && (
          <button
            type="button"
            disabled
            className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800/60 px-3 py-1.5 text-xs font-medium text-slate-400 opacity-50 cursor-not-allowed"
          >
            <DownloadIcon />
            Export
          </button>
        )}
      </div>

      {!hasReport ? (
        <EmptyState />
      ) : (
        <article className="prose prose-invert max-w-none rounded-xl border border-slate-800/60 bg-slate-950/40 p-6">
          <p className="text-slate-300">Report content will appear here.</p>
        </article>
      )}
    </section>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-700/60 bg-slate-950/30 px-6 py-16 text-center">
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
            d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
          />
        </svg>
      </div>
      <p className="text-sm font-medium text-slate-400">No report yet</p>
      <p className="mt-1 max-w-sm text-xs text-slate-600">
        Once the agent finishes researching, your brief will be displayed with
        citations and structured sections.
      </p>
    </div>
  );
}

function DownloadIcon() {
  return (
    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
    </svg>
  );
}
