import Link from "next/link";
import { Card, DarkCallout, Dot, PrimaryButton, StatCard } from "@/components/ui/primitives";

const PIPELINE = [
  { n: 1, title: "Live public source discovery", detail: "Company pages, pricing, docs, blogs, news" },
  { n: 2, title: "Evidence extraction", detail: "Webpages → cited claims with metadata" },
  { n: 3, title: "Claim verification", detail: "Unsupported statements filtered before synthesis" },
  { n: 4, title: "Battlecard generation", detail: "Talk tracks, objections, and win themes" },
];

const ARCH_NODES = [
  "Planner",
  "Parallel Tracks",
  "Evidence Store",
  "Verifier",
  "Synthesizer",
  "Cited UI",
];

export default function OverviewPage() {
  return (
    <div className="rs-fade-in">
      <div className="mb-10">
        <span className="inline-flex rounded-md bg-[var(--accent)]/35 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-[#7a5f16]">
          Portfolio Product
        </span>
        <h1 className="mt-4 max-w-3xl text-3xl font-bold tracking-tight text-[var(--foreground)] sm:text-4xl lg:text-[2.65rem] lg:leading-tight">
          Source-grounded competitive intelligence for GTM teams
        </h1>
        <p className="mt-4 max-w-2xl text-sm leading-relaxed text-[var(--muted)] sm:text-base">
          RivalScope researches public sources, verifies claims, and creates battlecards with
          citations — not a static chatbot. Every step is traced: Tavily search, page extract,
          and LLM synthesis.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_1fr]">
        <Card className="p-6 sm:p-8">
          <h2 className="text-lg font-bold tracking-tight">What RivalScope produces</h2>
          <ol className="mt-6 space-y-5">
            {PIPELINE.map((step) => (
              <li key={step.n} className="flex gap-4">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--ink)] text-sm font-bold text-white">
                  {step.n}
                </span>
                <div>
                  <p className="text-sm font-semibold text-[var(--foreground)]">{step.title}</p>
                  <p className="mt-0.5 text-sm text-[var(--muted)]">{step.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        </Card>

        <Card className="p-6 sm:p-8">
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full bg-[#e3ebfd] px-3 py-1 text-xs font-semibold text-[#3b5bdb]">
              ClickUp vs Notion
            </span>
            <span className="rounded-full bg-[var(--warn-bg)] px-3 py-1 text-xs font-semibold text-[var(--warn)]">
              Sales Battlecard
            </span>
          </div>
          <h2 className="mt-4 text-lg font-bold tracking-tight">Sample report preview</h2>
          <div className="mt-4 grid grid-cols-3 gap-3">
            <StatCard label="Confidence" value="87" hint="verified claims" accent="gold" />
            <StatCard label="Sources" value="18" hint="public pages" accent="green" />
            <StatCard label="Unsupported" value="6%" hint="filtered out" accent="red" />
          </div>
          <ul className="mt-5 space-y-2 text-sm text-[var(--foreground)]">
            {["Company Snapshot", "Product Positioning", "Pricing Intelligence", "Recent Moves"].map(
              (item) => (
                <li key={item} className="flex items-center gap-2">
                  <Dot color="yellow" />
                  {item}
                </li>
              ),
            )}
          </ul>
        </Card>
      </div>

      <div className="mt-8">
        <DarkCallout>
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-between sm:text-left">
            <div>
              <p className="text-xs font-bold uppercase tracking-wider text-[var(--accent)]">
                Agent architecture
              </p>
              <div className="mt-3 flex flex-wrap items-center justify-center gap-2 sm:justify-start">
                {ARCH_NODES.map((node, i) => (
                  <span key={node} className="flex items-center gap-2">
                    <span className="rounded-lg bg-white/10 px-3 py-1.5 text-xs font-semibold text-white">
                      {node}
                    </span>
                    {i < ARCH_NODES.length - 1 && (
                      <span className="text-white/40" aria-hidden="true">
                        →
                      </span>
                    )}
                  </span>
                ))}
              </div>
            </div>
            <Link href="/">
              <PrimaryButton className="bg-white text-[var(--ink)] hover:bg-neutral-100">
                Start a research run
              </PrimaryButton>
            </Link>
          </div>
        </DarkCallout>
      </div>
    </div>
  );
}
