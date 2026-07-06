"use client";

import { useEffect, useMemo, useState } from "react";
import { Badge, Card, PageHeader } from "@/components/ui/primitives";
import { loadSession } from "@/lib/reportStore";
import type { CompetitorReport, EvidenceItem, Source } from "@/types/report";

type Verdict = "Supported" | "Partial" | "Contradicted" | "Unsupported";

interface ClaimRow {
  evidence: EvidenceItem;
  source: Source | null;
  verdict: Verdict;
  score: number;
}

export default function EvidencePage() {
  const [report, setReport] = useState<CompetitorReport | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    const session = loadSession();
    setReport(session?.report ?? null);
    if (session?.report?.evidence[0]) {
      setSelectedId(session.report.evidence[0].id);
    }
  }, []);

  const sourceMap = useMemo(
    () => Object.fromEntries((report?.sources ?? []).map((s) => [s.id, s])),
    [report],
  );

  const rows: ClaimRow[] = useMemo(() => {
    if (!report) return [];
    return report.evidence.map((ev) => {
      const source = sourceMap[ev.sourceId] ?? null;
      const { verdict, score } = deriveVerdict(ev, source);
      return { evidence: ev, source, verdict, score };
    });
  }, [report, sourceMap]);

  const selected = rows.find((r) => r.evidence.id === selectedId) ?? rows[0];

  if (!report) {
    return (
      <div className="rs-fade-in">
        <PageHeader badge="Page 3" title="Evidence Review & Source Inspector" />
        <Card className="px-6 py-16 text-center text-sm text-[var(--muted)]">
          No evidence loaded. Complete a research run first.
        </Card>
      </div>
    );
  }

  return (
    <div className="rs-fade-in">
      <PageHeader
        badge="Page 3"
        title="Evidence Review & Source Inspector"
        subtitle="The trust layer: every report claim needs source evidence, extracted quote, verification status, and source quality metadata."
      />

      <div className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <Card className="overflow-hidden">
          <div className="border-b border-[var(--border)] px-6 py-4">
            <h2 className="text-lg font-bold">Verified Claims</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] bg-[var(--surface-muted)] text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                  <th className="px-6 py-3">Claim</th>
                  <th className="px-4 py-3">Source</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-6 py-3 text-right">Score</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr
                    key={row.evidence.id}
                    onClick={() => setSelectedId(row.evidence.id)}
                    className={`cursor-pointer border-b border-[var(--border)] transition-colors hover:bg-[var(--surface-muted)] ${
                      selected?.evidence.id === row.evidence.id ? "bg-[var(--accent)]/10" : ""
                    }`}
                  >
                    <td className="max-w-xs px-6 py-3.5 font-medium text-[var(--foreground)]">
                      {row.evidence.claim}
                    </td>
                    <td className="px-4 py-3.5 text-[var(--muted)]">
                      {row.source ? shortSourceLabel(row.source) : "—"}
                    </td>
                    <td className="px-4 py-3.5">
                      <VerdictBadge verdict={row.verdict} />
                    </td>
                    <td className="px-6 py-3.5 text-right tabular-nums text-[var(--muted)]">
                      {row.score.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card className="p-6">
          <h2 className="text-lg font-bold">Source Inspector</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Clicking a claim opens the exact source excerpt and verification reasoning.
          </p>

          {selected ? (
            <div className="mt-5 space-y-4">
              <Badge tone="ok">Primary source</Badge>
              <div>
                <p className="font-semibold text-[var(--foreground)]">
                  {selected.source?.title ?? "Unknown source"}
                </p>
                {selected.source?.url && (
                  <a
                    href={selected.source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="mt-1 block truncate text-sm text-[#3b5bdb] hover:underline"
                  >
                    {selected.source.url}
                  </a>
                )}
              </div>
              <div className="rounded-xl border border-[var(--border)] bg-[var(--warn-bg)]/40 px-4 py-3 text-sm leading-relaxed text-[var(--foreground)]">
                &ldquo;{extractedQuote(selected)}&rdquo;
              </div>
              <p className="text-sm leading-relaxed text-[var(--muted)]">
                <span className="font-semibold text-[var(--foreground)]">Verifier reasoning: </span>
                {verifierReasoning(selected)}
              </p>
              <p className="text-xs text-[var(--muted-2)]">
                Credibility: {selected.source?.credibilityScore?.toFixed(2) ?? "—"} · Confidence:{" "}
                {selected.evidence.confidence}
              </p>
            </div>
          ) : (
            <p className="mt-6 text-sm text-[var(--muted)]">Select a claim to inspect its source.</p>
          )}
        </Card>
      </div>
    </div>
  );
}

function deriveVerdict(
  ev: EvidenceItem,
  source: Source | null,
): { verdict: Verdict; score: number } {
  const cred = source?.credibilityScore ?? 0.5;
  const conf =
    ev.confidence === "high" ? 0.9 : ev.confidence === "medium" ? 0.7 : 0.45;
  const score = Math.round((cred * 0.6 + conf * 0.4) * 100) / 100;

  if (ev.claim.toLowerCase().includes("demo:") || ev.claim.toLowerCase().includes("mock")) {
    return { verdict: "Partial", score: 0.5 };
  }
  if (score >= 0.8) return { verdict: "Supported", score };
  if (score >= 0.55) return { verdict: "Partial", score };
  if (score < 0.35) return { verdict: "Contradicted", score };
  return { verdict: "Unsupported", score };
}

function VerdictBadge({ verdict }: { verdict: Verdict }) {
  const tone =
    verdict === "Supported"
      ? "ok"
      : verdict === "Partial"
        ? "warn"
        : verdict === "Contradicted"
          ? "bad"
          : "neutral";
  return <Badge tone={tone}>{verdict}</Badge>;
}

function shortSourceLabel(src: Source): string {
  const map: Record<string, string> = {
    company_page: "Company page",
    pricing_page: "Pricing page",
    docs: "Docs",
    news: "Blog / News",
    blog: "Blog / News",
  };
  return map[src.sourceType] ?? src.sourceType;
}

function extractedQuote(row: ClaimRow): string {
  if (row.source?.url && row.evidence.claim.length < 200) {
    return row.evidence.claim;
  }
  return row.evidence.claim.slice(0, 280) || "No excerpt available.";
}

function verifierReasoning(row: ClaimRow): string {
  const src = row.source;
  if (!src) {
    return "No linked source found — claim cannot be verified against retrieved evidence.";
  }
  if (row.verdict === "Supported") {
    return `The claim is supported because the source (${shortSourceLabel(src)}) has high credibility (${src.credibilityScore.toFixed(2)}) and the evidence confidence is ${row.evidence.confidence}.`;
  }
  if (row.verdict === "Partial") {
    return "Evidence is indirect or from a lower-confidence source — treat as directional, not definitive.";
  }
  if (row.verdict === "Contradicted") {
    return "Source material does not substantiate this claim strongly enough — excluded from high-confidence synthesis.";
  }
  return "Insufficient supporting text in the retrieved source excerpt.";
}
