"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Card, Dot, PageHeader, PrimaryButton } from "@/components/ui/primitives";
import { fetchConfig, type AppConfig } from "@/lib/api";
import { useRun } from "@/lib/runContext";
import type { CompareFeatureId, ReportType, ResearchInput } from "@/types/report";

const REPORT_TYPES: { value: ReportType; label: string }[] = [
  { value: "quick_brief", label: "Quick Brief" },
  { value: "deep_research", label: "Deep Research" },
  { value: "sales_battlecard", label: "Sales Battlecard" },
];

/** Keep ids/labels in sync with backend/app/services/compare_features.py */
const COMPARE_FEATURES: {
  id: CompareFeatureId;
  label: string;
  detail: string;
}[] = [
  {
    id: "pricing",
    label: "Pricing & packaging",
    detail: "Plans, seats, free tier, enterprise quotes",
  },
  {
    id: "core_features",
    label: "Core product features",
    detail: "Flagship workflows and capability depth",
  },
  {
    id: "integrations",
    label: "Integrations & ecosystem",
    detail: "Connectors, API, marketplace apps",
  },
  {
    id: "security",
    label: "Security & admin",
    detail: "SSO, SOC2, roles, compliance controls",
  },
  {
    id: "ai_capabilities",
    label: "AI capabilities",
    detail: "Built-in AI, copilots, automation",
  },
  {
    id: "collaboration",
    label: "Collaboration & UX",
    detail: "Sharing, real-time/async collab, usability",
  },
];

const RESEARCH_TRACKS = [
  { dot: "blue", title: "Company Profile", detail: "Homepage, about, security/admin signals" },
  { dot: "green", title: "Product Track", detail: "Features, integrations, AI, collaboration" },
  { dot: "yellow", title: "Pricing Track", detail: "Plans, packaging, enterprise notes" },
  { dot: "purple", title: "News Track", detail: "Launches, partnerships, releases" },
];

const DEFAULT_FEATURES: CompareFeatureId[] = [
  "pricing",
  "core_features",
  "integrations",
  "ai_capabilities",
];

function marketFromFeatures(ids: CompareFeatureId[]): string {
  const labels = COMPARE_FEATURES.filter((f) => ids.includes(f.id)).map((f) => f.label);
  return labels.join(" · ") || "B2B software";
}

const DEFAULTS: ResearchInput = {
  ourCompany: "ClickUp",
  competitor: "Notion",
  market: marketFromFeatures(DEFAULT_FEATURES),
  reportType: "sales_battlecard",
  compareFeatures: DEFAULT_FEATURES,
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
    Boolean(form.ourCompany.trim()) &&
    Boolean(form.competitor.trim()) &&
    form.compareFeatures.length > 0;

  const update = <K extends keyof ResearchInput>(k: K, v: ResearchInput[K]) =>
    setForm((prev) => ({ ...prev, [k]: v }));

  const toggleFeature = (id: CompareFeatureId) => {
    setForm((prev) => {
      const has = prev.compareFeatures.includes(id);
      const next = has
        ? prev.compareFeatures.filter((f) => f !== id)
        : [...prev.compareFeatures, id];
      return {
        ...prev,
        compareFeatures: next,
        market: marketFromFeatures(next),
      };
    });
  };

  const handleGenerate = () => {
    if (!valid) return;
    startRun({
      ...form,
      market: marketFromFeatures(form.compareFeatures),
    });
    router.push("/workflow");
  };

  const routingLabel = useMemo(() => {
    if (!config) return "Groq light · Gemini real";
    if (!config.isRealResearchEnabled) return "Mock → Groq";
    const fc = config.factCheckerProvider ?? "groq";
    const cmp = config.comparisonProvider ?? "gemini";
    const rep = config.reportProvider ?? "gemini";
    return `${cap(fc)} FC · ${cap(cmp)} compare · ${cap(rep)} report`;
  }, [config]);

  return (
    <div className="rs-fade-in">
      <PageHeader
        badge="Page 1"
        title="New Research Run"
        subtitle="Pick the companies and the comparison dimensions that drive search and the matrix."
      />

      <div className="grid gap-6 lg:grid-cols-[1.15fr_1fr]">
        <Card className="p-6 sm:p-7">
          <h2 className="text-lg font-bold tracking-tight">Research Configuration</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Selected dimensions steer Tavily queries and required comparison-matrix rows.
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
            <span className="mb-1.5 block text-xs font-medium text-[var(--muted)]">
              Compare on (select at least one)
            </span>
            <p className="mb-3 text-xs text-[var(--muted-2)]">
              These are the dimensions a buyer actually weighs — and that search can ground
              in official pages, pricing, docs, and news.
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              {COMPARE_FEATURES.map((feat) => {
                const checked = form.compareFeatures.includes(feat.id);
                return (
                  <label
                    key={feat.id}
                    className={`flex cursor-pointer items-start gap-3 rounded-xl border px-3 py-3 transition-colors ${
                      checked
                        ? "border-[var(--accent-strong)] bg-[var(--surface-muted)]"
                        : "border-[var(--border)] bg-white"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleFeature(feat.id)}
                      className="mt-1 h-4 w-4 accent-[var(--accent-strong)]"
                    />
                    <span>
                      <span className="block text-sm font-semibold text-[var(--foreground)]">
                        {feat.label}
                      </span>
                      <span className="mt-0.5 block text-xs text-[var(--muted)]">
                        {feat.detail}
                      </span>
                    </span>
                  </label>
                );
              })}
            </div>
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
              <ControlChip label="LLM routing" value={routingLabel} />
              <ControlChip label="Search" value="Tavily" />
            </div>
          </div>
        </Card>

        <Card className="p-6 sm:p-7">
          <h2 className="text-lg font-bold tracking-tight">Research Plan Preview</h2>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Tracks run in parallel; selected dimensions bias queries inside each track.
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
            {valid
              ? `Ready: ${form.compareFeatures.length} dimension(s) selected`
              : "Select companies and at least one compare dimension"}
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
      <p className="mt-0.5 text-sm font-semibold leading-snug text-[var(--foreground)]">
        {value}
      </p>
    </div>
  );
}
