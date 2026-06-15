"use client";

import { useState } from "react";
import type { ResearchInput } from "@/types/report";
import { ProductLabel } from "./ProductLabel";
import { FormField } from "./FormField";
import { ReportTypeSelect } from "./ReportTypeSelect";
import { PANEL_CLASS, PANEL_PADDING } from "./ui/styles";

const DEFAULT_VALUES: ResearchInput = {
  ourCompany: "ClickUp",
  competitor: "Notion",
  market: "Project management / docs",
  reportType: "sales_battlecard",
};

interface ResearchFormProps {
  onSubmit: (data: ResearchInput) => void;
  isRunning?: boolean;
}

export function ResearchForm({ onSubmit, isRunning = false }: ResearchFormProps) {
  const [form, setForm] = useState<ResearchInput>(DEFAULT_VALUES);

  const updateField = <K extends keyof ResearchInput>(
    key: K,
    value: ResearchInput[K],
  ) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (isRunning) return;
    onSubmit(form);
  };

  return (
    <section className={`${PANEL_CLASS} ${PANEL_PADDING}`}>
      <div className="mb-6 sm:mb-7">
        <ProductLabel tone="gold">Research Configuration</ProductLabel>
        <h2 className="mt-2 text-lg font-semibold tracking-tight text-stone-900 sm:text-xl">
          New Research
        </h2>
        <p className="mt-1.5 text-sm leading-relaxed text-stone-600">
          Define the competitive set and report type. Progress streams from the
          local backend via Server-Sent Events.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5 sm:space-y-6">
        <div className="grid gap-5 sm:grid-cols-2 sm:gap-6">
          <FormField
            id="ourCompany"
            label="Our Company"
            placeholder="e.g. ClickUp"
            value={form.ourCompany}
            onChange={(v) => updateField("ourCompany", v)}
            required
            disabled={isRunning}
          />
          <FormField
            id="competitor"
            label="Competitor"
            placeholder="e.g. Notion"
            value={form.competitor}
            onChange={(v) => updateField("competitor", v)}
            required
            disabled={isRunning}
          />
        </div>

        <FormField
          id="market"
          label="Market / Category"
          placeholder="e.g. Project management / docs"
          value={form.market}
          onChange={(v) => updateField("market", v)}
          required
          disabled={isRunning}
        />

        <ReportTypeSelect
          value={form.reportType}
          onChange={(v) => updateField("reportType", v)}
          disabled={isRunning}
        />

        <div className="flex flex-col gap-4 border-t border-stone-200 pt-5 sm:flex-row sm:items-center sm:justify-between sm:pt-6">
          <p className="text-xs leading-relaxed text-stone-500">
            All fields required. Demo uses mock data streamed from the backend.
          </p>
          <button
            type="submit"
            disabled={isRunning}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-stone-800 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-stone-700 focus:outline-none focus:ring-2 focus:ring-stone-400 focus:ring-offset-2 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100 sm:w-auto"
          >
            {isRunning ? (
              <>
                <LoadingSpinner />
                Running…
              </>
            ) : (
              <>
                <SparkIcon />
                Generate Brief
              </>
            )}
          </button>
        </div>
      </form>
    </section>
  );
}

function LoadingSpinner() {
  return (
    <span
      className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
      aria-hidden="true"
    />
  );
}

function SparkIcon() {
  return (
    <svg
      className="h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={2}
      stroke="currentColor"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456ZM16.894 20.567 16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423Z"
      />
    </svg>
  );
}
