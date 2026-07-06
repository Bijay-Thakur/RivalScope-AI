"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge, Card, DarkCallout, PageHeader, PrimaryButton, StatCard } from "@/components/ui/primitives";
import { loadSession } from "@/lib/reportStore";
import type { CompetitorReport, ResearchInput, Source } from "@/types/report";

const REPORT_TYPE_LABELS: Record<string, string> = {
  quick_brief: "Quick Brief",
  deep_research: "Deep Research",
  sales_battlecard: "Sales Battlecard",
};

export default function ReportPage() {
  const [session, setSession] = useState<{
    report: CompetitorReport;
    input?: ResearchInput;
  } | null>(null);

  useEffect(() => {
    setSession(loadSession());
  }, []);

  if (!session?.report) {
    return (
      <div className="rs-fade-in">
        <PageHeader badge="Page 4" title="Competitive Report Summary" />
        <Card className="flex flex-col items-center gap-4 px-6 py-16 text-center">
          <p className="text-base font-semibold">No report yet</p>
          <p className="max-w-sm text-sm text-[var(--muted)]">
            Run a research brief first — the executive summary appears here with cited sources.
          </p>
          <PrimaryButton onClick={() => (window.location.href = "/")}>
            Start a research run
          </PrimaryButton>
        </Card>
      </div>
    );
  }

  const { report, input } = session;
  const title = input
    ? `${input.ourCompany} vs ${input.competitor}`
    : "Competitive Report";
  const subtitle = input
    ? `${input.market} · ${REPORT_TYPE_LABELS[input.reportType] ?? input.reportType} · Generated from ${report.sources.length} sources`
    : `Generated from ${report.sources.length} sources`;

  const sourceMap = Object.fromEntries(report.sources.map((s) => [s.id, s]));

  return (
    <div className="rs-fade-in">
      <PageHeader
        badge="Page 4"
        title="Competitive Report Summary"
        subtitle="Polished executive output: concise, cited, confidence-scored, and structured for product marketing or sales leadership."
      />

      <Card className="mb-6 p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div>
            <h2 className="text-2xl font-bold tracking-tight">{title}</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">{subtitle}</p>
            {report.researchMode && (
              <Badge tone={report.researchMode === "real" ? "ok" : "warn"}>
                {report.researchMode} mode
              </Badge>
            )}
          </div>
          <div className="grid grid-cols-3 gap-3">
            <StatCard
              label="Confidence"
              value={Math.round(report.confidenceScore)}
              hint="overall"
              accent="gold"
            />
            <StatCard
              label="Sources"
              value={report.sources.length}
              hint="public"
              accent="green"
            />
            <StatCard
              label="Claims"
              value={report.evidence.length}
              hint="evidence"
              accent="blue"
            />
          </div>
        </div>
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <SummaryCard
          title="Company Snapshot"
          body={report.companySnapshot}
          chips={chipsForSection(report.evidence, sourceMap, ["company"])}
        />
        <SummaryCard
          title="Product Positioning"
          body={report.productPositioning}
          chips={chipsForSection(report.evidence, sourceMap, ["product", "docs"])}
        />
        <SummaryCard
          title="Pricing Intelligence"
          body={report.pricingIntelligence}
          chips={chipsForSection(report.evidence, sourceMap, ["pricing"])}
        />
      </div>

      <DarkCallout>
        Design rule: every key sentence should either cite a source chip or be clearly framed as
        analysis/inference.
      </DarkCallout>

      <div className="mt-6 flex flex-wrap justify-center gap-3">
        <Link href="/battlecard">
          <PrimaryButton>View sales battlecard →</PrimaryButton>
        </Link>
        <Link
          href="/evidence"
          className="inline-flex items-center rounded-xl border border-[var(--border-strong)] bg-white px-5 py-2.5 text-sm font-semibold hover:bg-[var(--surface-muted)]"
        >
          Inspect evidence
        </Link>
      </div>
    </div>
  );
}

function SummaryCard({
  title,
  body,
  chips,
}: {
  title: string;
  body: string;
  chips: { label: string; tone: "blue" | "orange" | "green" }[];
}) {
  const CHIP_TONE: Record<string, string> = {
    blue: "bg-[#e3ebfd] text-[#3b5bdb]",
    orange: "bg-[var(--warn-bg)] text-[var(--warn)]",
    green: "bg-[var(--ok-bg)] text-[var(--ok)]",
  };

  return (
    <Card className="flex flex-col p-6">
      <h3 className="text-base font-bold tracking-tight">{title}</h3>
      <p className="mt-3 flex-1 text-sm leading-relaxed text-[var(--muted)]">{body}</p>
      {chips.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {chips.map((chip, i) => (
            <span
              key={`${chip.label}-${i}`}
              className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${CHIP_TONE[chip.tone]}`}
            >
              {chip.label}
            </span>
          ))}
        </div>
      )}
    </Card>
  );
}

function chipsForSection(
  evidence: CompetitorReport["evidence"],
  sourceMap: Record<string, Source>,
  keywords: string[],
): { label: string; tone: "blue" | "orange" | "green" }[] {
  const tones: ("blue" | "orange" | "green")[] = ["blue", "orange", "green"];
  const chips: { label: string; tone: "blue" | "orange" | "green" }[] = [];
  let idx = 0;

  for (const ev of evidence) {
    const src = sourceMap[ev.sourceId];
    if (!src) continue;
    const type = src.sourceType.toLowerCase();
    if (!keywords.some((k) => type.includes(k) || ev.claim.toLowerCase().includes(k))) continue;
    chips.push({
      label: `[${idx + 1}] ${shortSourceLabel(src)}`,
      tone: tones[idx % tones.length],
    });
    idx++;
    if (idx >= 3) break;
  }
  return chips;
}

function shortSourceLabel(src: Source): string {
  const labels: Record<string, string> = {
    company_page: "Company page",
    pricing_page: "Pricing page",
    docs: "Docs",
    news: "News",
    blog: "Blog",
  };
  return labels[src.sourceType] ?? src.title.slice(0, 24);
}
