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
      <header className={`${PANEL_CLASS} ${PANEL_PADDING} border-amber-200/60 bg-gradient-to-br from-white to-amber-50/40`}>
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="min-w-0 flex-1">
            <ProductLabel tone="gold">Source-Grounded Brief</ProductLabel>
            <h2 className="mt-2 text-xl font-semibold tracking-tight text-stone-900 sm:text-2xl">
              Competitive Intelligence Report
            </h2>
            <p className="mt-2 max-w-lg text-sm leading-relaxed text-stone-600">
              Evidence-linked analysis for GTM review. Share with sales, product
              marketing, or leadership ahead of your next competitive deal.
            </p>
          </div>
          <ConfidenceBadge score={report.confidenceScore} />
        </div>
      </header>

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
  const tier =
    score >= 90 ? "high" : score >= 80 ? "strong" : score >= 70 ? "moderate" : "low";

  const styles = {
    high: {
      border: "border-amber-200",
      bg: "bg-amber-50",
      text: "text-amber-900",
      label: "High confidence",
    },
    strong: {
      border: "border-stone-300",
      bg: "bg-stone-50",
      text: "text-stone-800",
      label: "Strong confidence",
    },
    moderate: {
      border: "border-stone-200",
      bg: "bg-white",
      text: "text-stone-600",
      label: "Moderate confidence",
    },
    low: {
      border: "border-stone-200",
      bg: "bg-stone-50",
      text: "text-stone-500",
      label: "Low confidence",
    },
  }[tier];

  return (
    <div
      className={`flex shrink-0 flex-col items-center rounded-xl border px-5 py-3.5 ${styles.border} ${styles.bg}`}
    >
      <span className={`text-3xl font-bold tabular-nums tracking-tight ${styles.text}`}>
        {score}
      </span>
      <span className="mt-0.5 text-[11px] font-medium uppercase tracking-wider text-stone-500">
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
      <p className="text-[0.9375rem] leading-[1.75] text-stone-700">{content}</p>
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
            className="flex gap-3 rounded-lg border border-stone-200 bg-stone-50/50 px-4 py-3.5"
          >
            <span
              className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-700"
              aria-hidden="true"
            />
            <p className="text-[0.9375rem] leading-[1.65] text-stone-700">{item}</p>
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
      <h3 className="text-base font-semibold tracking-tight text-stone-900">{title}</h3>
      {description && (
        <p className="mt-1 text-xs leading-relaxed text-stone-500">{description}</p>
      )}
    </div>
  );
}
