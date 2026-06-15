import { ProductLabel } from "./ProductLabel";

export function Header() {
  return (
    <header className="border-b border-stone-200 bg-white">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-6 py-8 sm:py-10 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-stone-800 text-amber-100">
                <svg
                  className="h-5 w-5"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
                  />
                </svg>
              </div>
              <ProductLabel tone="gold">Source-Grounded Brief</ProductLabel>
            </div>

            <h1 className="mt-4 text-3xl font-semibold tracking-tight text-stone-900 sm:text-4xl">
              RivalScope AI
            </h1>
            <p className="mt-2 text-base leading-relaxed text-stone-600 sm:text-lg">
              Source-grounded competitive intelligence briefs for GTM teams
            </p>
          </div>

          <div className="flex flex-wrap gap-2 lg:max-w-md lg:justify-end">
            <StatPill label="Evidence-linked claims" />
            <StatPill label="Sales-ready outputs" />
            <StatPill label="Portfolio demo" />
          </div>
        </div>
      </div>
    </header>
  );
}

function StatPill({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center rounded-full border border-stone-200 bg-stone-50 px-3 py-1.5 text-xs text-stone-600">
      {label}
    </span>
  );
}
