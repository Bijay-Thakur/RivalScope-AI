"use client";

import { useEffect, useRef, useState } from "react";
import { MOCK_COMPETITOR_REPORT } from "@/data/mockReport";
import { Header } from "./Header";
import { ProductLabel } from "./ProductLabel";
import { ReportPreview } from "./ReportPreview";
import { ResearchForm } from "./ResearchForm";
import { ResearchProgress } from "./ResearchProgress";
import { PANEL_CLASS, PANEL_PADDING } from "./ui/styles";

const TOTAL_STEPS = 6;
const STEP_DURATION_MS = 1200;

export function Dashboard() {
  const [isRunning, setIsRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [showReport, setShowReport] = useState(false);
  const runIdRef = useRef(0);

  useEffect(() => {
    if (!isRunning || currentStep === 0 || currentStep > TOTAL_STEPS) return;

    const runId = runIdRef.current;
    const timer = setTimeout(() => {
      if (runId !== runIdRef.current) return;

      if (currentStep >= TOTAL_STEPS) {
        setCurrentStep(TOTAL_STEPS + 1);
        setIsRunning(false);
        setShowReport(true);
      } else {
        setCurrentStep((step) => step + 1);
      }
    }, STEP_DURATION_MS);

    return () => clearTimeout(timer);
  }, [isRunning, currentStep]);

  const handleSubmit = () => {
    runIdRef.current += 1;
    setShowReport(false);
    setIsRunning(true);
    setCurrentStep(1);
  };

  return (
    <div className="min-h-screen bg-stone-50">
      <Header />

      <main className="mx-auto max-w-7xl px-4 pb-12 pt-8 sm:px-6 sm:pt-10 lg:px-8">
        <div className="grid gap-10 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)] xl:gap-12">
          <div className="space-y-6 sm:space-y-8">
            <ColumnHeader
              label="Input & workflow"
              title="Configure & run"
              description="Set your competitive parameters and watch the agent pipeline execute."
            />
            <ResearchForm onSubmit={handleSubmit} isRunning={isRunning} />
            <ResearchProgress isRunning={isRunning} currentStep={currentStep} />
          </div>

          <div className="xl:sticky xl:top-8 xl:self-start">
            <ColumnHeader
              label="Output"
              title="Brief preview"
              description="Your source-grounded report renders here when research completes."
              className="mb-6"
            />
            {showReport ? (
              <ReportPreview report={MOCK_COMPETITOR_REPORT} />
            ) : (
              <ReportPlaceholder isRunning={isRunning} />
            )}
          </div>
        </div>
      </main>

      <footer className="border-t border-stone-200 bg-white py-8 text-center">
        <p className="text-xs text-stone-500">
          RivalScope AI — Portfolio demo · Mock data only · No backend
        </p>
      </footer>
    </div>
  );
}

function ColumnHeader({
  label,
  title,
  description,
  className = "",
}: {
  label: string;
  title: string;
  description: string;
  className?: string;
}) {
  return (
    <div className={className}>
      <ProductLabel>{label}</ProductLabel>
      <h2 className="mt-1.5 text-sm font-semibold text-stone-800">{title}</h2>
      <p className="mt-1 text-xs leading-relaxed text-stone-500">{description}</p>
    </div>
  );
}

function ReportPlaceholder({ isRunning }: { isRunning: boolean }) {
  return (
    <section
      className={`${PANEL_CLASS} ${PANEL_PADDING} flex min-h-[360px] flex-col items-center justify-center text-center sm:min-h-[420px] lg:min-h-[480px]`}
    >
      <div
        className={`mb-5 flex h-16 w-16 items-center justify-center rounded-2xl border ${
          isRunning
            ? "border-amber-200 bg-amber-50"
            : "border-stone-200 bg-stone-50"
        }`}
      >
        {isRunning ? (
          <span className="h-7 w-7 animate-spin rounded-full border-2 border-stone-200 border-t-amber-700" />
        ) : (
          <svg
            className="h-7 w-7 text-stone-400"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
            />
          </svg>
        )}
      </div>

      <ProductLabel tone={isRunning ? "gold" : "default"}>
        Source-Grounded Brief
      </ProductLabel>
      <p className="mt-3 text-base font-medium text-stone-800">
        {isRunning ? "Generating your brief…" : "Awaiting research run"}
      </p>
      <p className="mt-2 max-w-sm text-sm leading-relaxed text-stone-500">
        {isRunning
          ? "The agent workflow is gathering evidence and synthesizing insights. Your full brief will appear here shortly."
          : "Click Generate Brief to run the demo pipeline and preview a mock competitive intelligence report."}
      </p>
    </section>
  );
}
