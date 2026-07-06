"use client";

import { useEffect, useState } from "react";
import { Badge, Card, PageHeader } from "@/components/ui/primitives";
import { fetchConfig, type AppConfig } from "@/lib/api";

export default function SettingsPage() {
  const [config, setConfig] = useState<AppConfig | null>(null);

  useEffect(() => {
    fetchConfig().then(setConfig).catch(() => setConfig(null));
  }, []);

  return (
    <div className="rs-fade-in">
      <PageHeader
        badge="Settings"
        title="Provider & Tracing Settings"
        subtitle="Non-secret runtime configuration — API keys live in backend/.env only."
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-6">
          <h2 className="text-lg font-bold">LLM Providers</h2>
          <dl className="mt-4 space-y-3 text-sm">
            <Row label="Primary" value={config?.llmProvider ?? "—"} ok={config?.providers.groq} />
            <Row label="Fallback" value={config?.llmFallback ?? "—"} ok={config?.providers.gemini} />
            <Row label="Groq model" value={config?.groqModel ?? "—"} />
            <Row label="Gemini model" value={config?.geminiModel ?? "—"} />
            <Row label="Judge model" value={config?.judgeModel ?? "—"} />
            <Row label="Research mode" value={config?.researchMode ?? "mock"} />
          </dl>
        </Card>

        <Card className="p-6">
          <h2 className="text-lg font-bold">Search & Data</h2>
          <dl className="mt-4 space-y-3 text-sm">
            <Row label="Search provider" value="Tavily" ok={config?.providers.tavily} />
            <Row label="Extract top-N URLs" value={String(config?.extractTopN ?? 3)} />
            <Row label="Max context chars" value={String(config?.maxContextChars ?? 50000)} />
            <Row label="Database" value={config?.database ?? "sqlite"} />
          </dl>
        </Card>

        <Card className="p-6 lg:col-span-2">
          <div className="flex flex-wrap items-center gap-3">
            <h2 className="text-lg font-bold">Tracing: tool use vs LangSmith</h2>
            <Badge tone={config?.tracing.toolTraceBuffer ? "ok" : "neutral"}>
              In-app tool traces: {config?.tracing.toolTraceBuffer ? "ON" : "off"}
            </Badge>
            <Badge tone={config?.tracing.langsmithEnabled ? "ok" : "warn"}>
              LangSmith: {config?.tracing.langsmithEnabled ? "ON" : "OFF (default)"}
            </Badge>
          </div>

          <div className="mt-5 grid gap-6 lg:grid-cols-2">
            <div className="space-y-3 text-sm leading-relaxed text-[var(--muted)]">
              <p className="font-semibold text-[var(--foreground)]">
                In-app trace buffer (always on)
              </p>
              <p>
                Every <strong>tool call</strong> is recorded in{" "}
                <code className="rounded bg-[var(--surface-muted)] px-1">trace_buffer.py</code> and
                streamed to the Live Workflow page via SSE <code className="rounded bg-[var(--surface-muted)] px-1">trace</code> events:
              </p>
              <ul className="list-inside list-disc space-y-1">
                <li>
                  <code>tavily_search</code> — each web search query + result count
                </li>
                <li>
                  <code>tavily_extract</code> — full-page extraction + chars cleaned
                </li>
                <li>
                  <code>fact_checker_llm</code>, <code>comparison_agent_llm</code>,{" "}
                  <code>report_generator_llm</code> — LLM synthesis steps
                </li>
              </ul>
              <p>
                Traces are persisted per run in SQLite and visible under Runs → Traces.
              </p>
            </div>

            <div className="space-y-3 text-sm leading-relaxed text-[var(--muted)]">
              <p className="font-semibold text-[var(--foreground)]">
                LangSmith (optional, off by default)
              </p>
              <p>
                LangSmith is a <strong>hosted</strong> observability platform — separate from the
                in-app log. Enable with{" "}
                <code className="rounded bg-[var(--surface-muted)] px-1">LANGSMITH_TRACING=true</code>{" "}
                in <code className="rounded bg-[var(--surface-muted)] px-1">backend/.env</code>.
              </p>
              <p>Where it hooks in today:</p>
              <ul className="list-inside list-disc space-y-1">
                <li>
                  <code>@traceable</code> on <code>search_web</code> and{" "}
                  <code>extract_urls</code> (Tavily tools)
                </li>
                <li>
                  <code>@traceable</code> on eval <code>judge_claim</code>
                </li>
                <li>
                  LangChain chat models auto-trace when LangSmith env vars are set
                </li>
              </ul>
              <p>
                <strong>Why use it?</strong> Debug latency/cost in a hosted trace tree during eval
                runs. The UI does not require LangSmith — the trace buffer covers tool-use visibility.
              </p>
              {config?.tracing.langsmithEnabled && (
                <p className="text-[var(--ok)]">
                  Project: {config.tracing.langsmithProject}
                </p>
              )}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  ok,
}: {
  label: string;
  value: string;
  ok?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-[var(--border)] pb-2">
      <dt className="text-[var(--muted)]">{label}</dt>
      <dd className="flex items-center gap-2 font-semibold">
        {value}
        {ok !== undefined && (
          <span
            className={`h-2 w-2 rounded-full ${ok ? "bg-[var(--ok)]" : "bg-[var(--bad)]"}`}
          />
        )}
      </dd>
    </div>
  );
}
