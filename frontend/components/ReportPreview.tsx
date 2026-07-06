import type { CompetitorReport } from "@/types/report";
import { Battlecard } from "./Battlecard";
import { EvidencePanel } from "./EvidencePanel";
import { ProductLabel } from "./ProductLabel";
import { PANEL_CLASS, PANEL_PADDING } from "./ui/styles";

interface ReportPreviewProps {
  report: CompetitorReport;
}

export function ReportPreview({ report }: ReportPreviewProps) {
  return (
    <article className="space-y-5 sm:space-y-6">
      <header className={`${PANEL_CLASS} ${PANEL_PADDING} border-t-2 border-t-amber-500/50`}>
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="min-w-0 flex-1">
            <ProductLabel tone="gold">Source-Grounded Brief</ProductLabel>
            <h2 className="mt-2 text-xl font-semibold tracking-tight text-neutral-100 sm:text-2xl">
              Competitive Intelligence Report
            </h2>
            <p className="mt-2 max-w-lg text-sm leading-relaxed text-neutral-400">
              Evidence-linked analysis for GTM review. Share with sales, product
              marketing, or leadership ahead of your next competitive deal.
            </p>
            <ReportMeta researchMode={report.researchMode} generatedAt={report.generatedAt} />
          </div>
          <ConfidenceBadge score={report.confidenceScore} />
        </div>
      </header>

      {report.warnings && report.warnings.length > 0 && (
        <WarningsAlert warnings={report.warnings} />
      )}

      <div className="grid gap-5 sm:gap-6 lg:grid-cols-2">
        <TextSection title="Company Snapshot" content={report.companySnapshot} />
        <TextSection title="Product Positioning" content={report.productPositioning} />
      </div>

      <ListSection
        title="Feature Comparison"
        description="Head-to-head capability assessment across key evaluation criteria."
        items={report.featureComparison}
      />

      <TextSection title="Pricing Intelligence" content={report.pricingIntelligence} />

      <ListSection
        title="Recent Moves"
        description="Notable product, GTM, and market signals from the research window."
        items={report.recentMoves}
      />

      <div className="grid gap-5 sm:gap-6 lg:grid-cols-2">
        <ListSection
          title="Strengths"
          description="Where the competitor wins mindshare and deals."
          items={report.strengths}
        />
        <ListSection
          title="Weaknesses"
          description="Gaps and vulnerabilities to press in competitive cycles."
          items={report.weaknesses}
        />
      </div>

      <Battlecard salesBattlecard={report.salesBattlecard} />

      <EvidencePanel evidence={report.evidence} sources={report.sources} />
    </article>
  );
}

function ConfidenceBadge({ score }: { score: number }) {
  const rounded = Math.round(score);
  const tier =
    rounded >= 90 ? "high" : rounded >= 80 ? "strong" : rounded >= 70 ? "moderate" : "low";

  const styles = {
    high: {
      border: "border-amber-500/30",
      bg: "bg-amber-500/10",
      text: "text-amber-400",
      label: "High confidence",
    },
    strong: {
      border: "border-neutral-700",
      bg: "bg-neutral-800/60",
      text: "text-neutral-200",
      label: "Strong confidence",
    },
    moderate: {
      border: "border-neutral-800",
      bg: "bg-neutral-900",
      text: "text-neutral-400",
      label: "Moderate confidence",
    },
    low: {
      border: "border-neutral-800",
      bg: "bg-neutral-800/40",
      text: "text-neutral-500",
      label: "Low confidence",
    },
  }[tier];

  return (
    <div
      className={`flex shrink-0 flex-col items-center rounded-xl border px-5 py-3.5 ${styles.border} ${styles.bg}`}
    >
      <span className={`text-3xl font-bold tabular-nums tracking-tight ${styles.text}`}>
        {rounded}%
      </span>
      <span className="mt-0.5 text-[11px] font-medium uppercase tracking-wider text-neutral-500">
        Confidence
      </span>
      <span className={`mt-1 text-xs font-medium ${styles.text}`}>{styles.label}</span>
    </div>
  );
}

function TextSection({ title, content }: { title: string; content: string }) {
  return (
    <section className={`${PANEL_CLASS} ${PANEL_PADDING}`}>
      <SectionHeading title={title} />
      <p className="text-[0.9375rem] leading-[1.75] text-neutral-300">{content}</p>
    </section>
  );
}

function ListSection({
  title,
  description,
  items,
}: {
  title: string;
  description?: string;
  items: string[];
}) {
  return (
    <section className={`${PANEL_CLASS} ${PANEL_PADDING}`}>
      <SectionHeading title={title} description={description} />
      <ul className="space-y-2.5 sm:space-y-3">
        {items.map((item, index) => (
          <li
            key={`${title}-${index}`}
            className="flex gap-3 rounded-lg border border-neutral-800 bg-neutral-800/40 px-4 py-3.5"
          >
            <span
              className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500"
              aria-hidden="true"
            />
            <p className="text-[0.9375rem] leading-[1.65] text-neutral-300">{item}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function SectionHeading({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  return (
    <div className="mb-4 sm:mb-5">
      <h3 className="text-base font-semibold tracking-tight text-neutral-100">{title}</h3>
      {description && (
        <p className="mt-1 text-xs leading-relaxed text-neutral-500">{description}</p>
      )}
    </div>
  );
}

function ReportMeta({
  researchMode,
  generatedAt,
}: {
  researchMode?: string;
  generatedAt?: string;
}) {
  if (!researchMode && !generatedAt) return null;

  const modeLabel =
    researchMode === "real" ? "Research mode: real" : "Research mode: mock";
  const modeStyles =
    researchMode === "real"
      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
      : "bg-amber-500/10 text-amber-400 border-amber-500/30";

  let formattedDate: string | undefined;
  if (generatedAt) {
    try {
      formattedDate = new Date(generatedAt).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      });
    } catch {
      formattedDate = generatedAt;
    }
  }

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2">
      {researchMode && (
        <span
          className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-medium ${modeStyles}`}
        >
          {modeLabel}
        </span>
      )}
      {formattedDate && (
        <span className="text-[11px] text-neutral-600">
          Generated at: {formattedDate}
        </span>
      )}
    </div>
  );
}

function WarningsAlert({ warnings }: { warnings: string[] }) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3"
    >
      <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-amber-400">
        Research notes
      </p>
      <ul className="space-y-1">
        {warnings.map((warning, index) => (
          <li key={index} className="text-xs leading-relaxed text-amber-300">
            {warning}
          </li>
        ))}
      </ul>
    </div>
  );
}
