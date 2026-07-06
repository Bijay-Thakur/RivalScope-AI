"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Card, Dot, PageHeader, PrimaryButton } from "@/components/ui/primitives";
import { fetchConfig, type AppConfig } from "@/lib/api";
import { useRun } from "@/lib/runContext";
import type { ReportType, ResearchInput } from "@/types/report";

const REPORT_TYPES: { value: ReportType; label: string }[] = [
  { value: "quick_brief", label: "Quick Brief" },
  { value: "deep_research", label: "Deep Research" },
  { value: "sales_battlecard", label: "Sales Battlecard" },
];

const RESEARCH_TRACKS = [
  { dot: "blue", title: "Company Profile", detail: "Homepage, about, funding, ICP" },
  { dot: "green", title: "Product Track", detail: "Features, docs, integrations" },
  { dot: "yellow", title: "Pricing Track", detail: "Plans, add-ons, enterprise notes" },
  { dot: "purple", title: "News Track", detail: "Launches, partnerships, releases" },
  { dot: "pink", title: "Market Track", detail: "Analyst mentions, category shifts (planned)" },
];

const DEFAULTS: ResearchInput = {
  ourCompany: "ClickUp",
  competitor: "Notion",
  market: "Project management / docs",
  reportType: "sales_battlecard",
};

export default function NewResearchPage() {
  const router = useRouter();
  const { startRun } = useRun();
  const [form, setForm] = useState<ResearchInput>(DEFAULTS);
  const [config, setConfig] = useState<AppConfig | null>(null);

  useEffect(() => {
    fetchConfig().then(setConfig).catch(() => setConfig(null));
  }, []);

  const valid =
    form.ourCompany.trim() && form.competitor.trim() && form.market.trim();

  const update = <K extends keyof ResearchInput>(k: K, v: ResearchInput[K]) =>
    setForm((prev) => ({ ...prev, [k]: v }));

  const handleGenerate = () => {
    if (!valid) return;
    startRun(form);
    router.push("/workflow");
  };

  const llmLabel = config ? `${cap(config.llmProvider)} primary` : "Groq primary";
  const fallbackLabel = config
    ? config.providers.gemini
      ? `${cap(config.llmFallback)} ready`
      : "None configured"
    : "Gemini ready";

  return (
    <div className="rs-fade-in">
      <PageHeader
        badge="Page 1"
        title="New Research Run"
        subtitle="A serious GTM research console: clear input, advanced controls, and a plan preview before execution."
      />

      <div className="grid gap-6 lg:grid-cols-[1.15fr_1fr]">
        {/* Configuration */}
        <Card className="p-6 sm:p-7">
          <h2 className="text-lg font-bold tracking-tight">Research Configuration</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Define the competitive set and control source depth before launching the agent.
          </p>

          <div className="mt-6 grid gap-5 sm:grid-cols-2">
            <Field label="Our Company">
              <TextInput
                value={form.ourCompany}
                onChange={(v) => update("ourCompany", v)}
                placeholder="e.g. ClickUp"
              />
            </Field>
            <Field label="Competitor">
              <TextInput
                value={form.competitor}
                onChange={(v) => update("competitor", v)}
                placeholder="e.g. Notion"
              />
            </Field>
          </div>

          <div className="mt-5">
            <Field label="Market / Category">
              <TextInput
                value={form.market}
                onChange={(v) => update("market", v)}
                placeholder="e.g. Project management / docs"
              />
            </Field>
          </div>

          <div className="mt-5">
            <Field label="Report Type">
              <div className="relative">
                <select
                  value={form.reportType}
                  onChange={(e) => update("reportType", e.target.value as ReportType)}
                  className="w-full appearance-none rounded-xl border border-[var(--border-strong)] bg-white px-4 py-2.5 text-sm text-[var(--foreground)] outline-none focus:border-[var(--accent-strong)]"
                >
                  {REPORT_TYPES.map((rt) => (
                    <option key={rt.value} value={rt.value}>
                      {rt.label}
                    </option>
                  ))}
                </select>
                <span className="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-[var(--muted-2)]">
                  ▾
                </span>
              </div>
            </Field>
          </div>

          <div className="mt-6">
            <p className="text-sm font-semibold text-[var(--foreground)]">Advanced controls</p>
            <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <ControlChip label="Source depth" value="Balanced" />
              <ControlChip label="Research window" value="Last 90 days" />
              <ControlChip label="LLM" value={llmLabel} />
              <ControlChip label="Fallback" value={fallbackLabel} />
            </div>
          </div>
        </Card>

        {/* Plan preview */}
        <Card className="p-6 sm:p-7">
          <h2 className="text-lg font-bold tracking-tight">Research Plan Preview</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            The planned agent behavior, made visible before you commit a run.
          </p>

          <div className="mt-5 space-y-3">
            {RESEARCH_TRACKS.map((track) => (
              <div
                key={track.title}
                className="flex items-start gap-3 rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] px-4 py-3.5"
              >
                <span className="mt-0.5">
                  <Dot color={track.dot} />
                </span>
                <div>
                  <p className="text-sm font-semibold text-[var(--foreground)]">{track.title}</p>
                  <p className="text-xs text-[var(--muted)]">{track.detail}</p>
                </div>
              </div>
            ))}
          </div>

          <div
            className={`mt-4 rounded-lg px-3 py-2 text-center text-xs font-semibold ${
              valid
                ? "bg-[var(--ok-bg)] text-[var(--ok)]"
                : "bg-[var(--bad-bg)] text-[var(--bad)]"
            }`}
          >
            {valid ? "Ready: all required fields are valid" : "Fill in all fields to continue"}
          </div>

          <div className="mt-5 flex justify-end">
            <PrimaryButton onClick={handleGenerate} disabled={!valid}>
              Generate Brief
            </PrimaryButton>
          </div>

          {config && (
            <p className="mt-3 text-center text-[11px] text-[var(--muted-2)]">
              Mode: <span className="font-semibold">{config.researchMode}</span>
              {" · "}search via {config.searchProvider}
              {config.isRealResearchEnabled ? " · live tool calls" : " · mock data"}
            </p>
          )}
        </Card>
      </div>
    </div>
  );
}

function cap(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-medium text-[var(--muted)]">{label}</span>
      {children}
    </label>
  );
}

function TextInput({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full rounded-xl border border-[var(--border-strong)] bg-white px-4 py-2.5 text-sm text-[var(--foreground)] outline-none placeholder:text-[var(--muted-2)] focus:border-[var(--accent-strong)]"
    />
  );
}

function ControlChip({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] px-3 py-2.5">
      <p className="text-[11px] text-[var(--muted-2)]">{label}</p>
      <p className="mt-0.5 text-sm font-semibold text-[var(--foreground)]">{value}</p>
    </div>
  );
}
