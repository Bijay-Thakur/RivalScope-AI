"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge, Card, PageHeader, PrimaryButton } from "@/components/ui/primitives";
import { fetchConfig, fetchRuns, type AppConfig, type RunSummary } from "@/lib/api";

export default function RunsPage() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [config, setConfig] = useState<AppConfig | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchRuns(50), fetchConfig()])
      .then(([r, c]) => {
        setRuns(r);
        setConfig(c);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="rs-fade-in">
      <PageHeader
        badge="Page 7"
        title="Run History, Export, and Settings"
        subtitle="Store past runs, source counts, verification metrics, and exported artifacts — a real internal GTM tool, not a one-off demo."
      />

      <div className="grid gap-6 lg:grid-cols-[1.5fr_1fr]">
        <Card className="overflow-hidden">
          <div className="border-b border-[var(--border)] px-6 py-4">
            <h2 className="text-lg font-bold">Research Run History</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              Past runs with source counts, confidence, and tool-use traces.
            </p>
          </div>

          {loading ? (
            <p className="px-6 py-12 text-sm text-[var(--muted)]">Loading runs…</p>
          ) : runs.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <p className="text-sm text-[var(--muted)]">No runs saved yet.</p>
              <Link href="/" className="mt-4 inline-block">
                <PrimaryButton>Start first run</PrimaryButton>
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] bg-[var(--surface-muted)] text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
                    <th className="px-6 py-3">Run</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Sources</th>
                    <th className="px-4 py-3">Confidence</th>
                    <th className="px-6 py-3">Export</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.map((run) => (
                    <tr key={run.runId} className="border-b border-[var(--border)]">
                      <td className="px-6 py-3.5 font-medium">
                        {run.ourCompany} vs {run.competitor}
                        <p className="text-xs font-normal text-[var(--muted)]">{run.market}</p>
                      </td>
                      <td className="px-4 py-3.5">
                        <StatusBadge status={run.status} />
                      </td>
                      <td className="px-4 py-3.5 tabular-nums">{run.sourceCount}</td>
                      <td className="px-4 py-3.5 tabular-nums">
                        {run.confidenceScore != null ? Math.round(run.confidenceScore) : "—"}
                      </td>
                      <td className="px-6 py-3.5">
                        <Link
                          href={`/workflow?run=${run.runId}`}
                          className="text-xs font-semibold text-[#3b5bdb] hover:underline"
                        >
                          Traces
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <div className="space-y-6">
          <Card className="p-6">
            <h2 className="text-lg font-bold">Export Center</h2>
            <ul className="mt-4 space-y-3 text-sm">
              <ExportRow title="PDF report" detail="Executive-ready artifact" />
              <ExportRow title="Markdown" detail="Paste into GitHub/Notion" />
              <ExportRow title="Battlecard copy" detail="Sales-call quick reference" />
            </ul>
          </Card>

          <Card className="p-6">
            <h2 className="text-lg font-bold">Provider Settings</h2>
            <p className="mt-1 text-sm text-[var(--muted)]">
              API providers explicit and configurable.
            </p>
            <dl className="mt-4 space-y-2.5 text-sm">
              <SettingRow
                label="LLM primary"
                value={config ? cap(config.llmProvider) : "—"}
              />
              <SettingRow
                label="LLM fallback"
                value={config ? cap(config.llmFallback) : "—"}
              />
              <SettingRow label="Search provider" value="Tavily" configured={config?.providers.tavily} />
              <SettingRow label="Database" value="SQLite → Postgres" />
              <SettingRow
                label="Tool traces"
                value={config?.tracing.toolTraceBuffer ? "Always on (in-app)" : "Off"}
              />
              <SettingRow
                label="LangSmith"
                value={
                  config?.tracing.langsmithEnabled
                    ? `On · ${config.tracing.langsmithProject}`
                    : "Off (optional)"
                }
              />
            </dl>
          </Card>

          <span className="inline-flex w-full justify-center rounded-full bg-[var(--ok-bg)] px-4 py-2 text-center text-xs font-semibold text-[var(--ok)]">
            Production polish: env vars, CI, Docker, deployment links
          </span>
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const s = status.toLowerCase();
  const tone =
    s === "completed" ? "ok" : s === "failed" ? "bad" : "warn";
  const label =
    s === "completed" ? "Completed" : s === "failed" ? "Failed" : "Review needed";
  return <Badge tone={tone}>{label}</Badge>;
}

function ExportRow({ title, detail }: { title: string; detail: string }) {
  return (
    <li className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] px-4 py-3">
      <p className="font-semibold">{title}</p>
      <p className="text-xs text-[var(--muted)]">{detail}</p>
    </li>
  );
}

function SettingRow({
  label,
  value,
  configured,
}: {
  label: string;
  value: string;
  configured?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-[var(--border)] pb-2 last:border-0">
      <dt className="text-[var(--muted)]">{label}</dt>
      <dd className="flex items-center gap-2 font-semibold">
        {value}
        {configured !== undefined && (
          <span
            className={`h-2 w-2 rounded-full ${configured ? "bg-[var(--ok)]" : "bg-[var(--bad)]"}`}
            title={configured ? "Configured" : "Not configured"}
          />
        )}
      </dd>
    </div>
  );
}

function cap(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
