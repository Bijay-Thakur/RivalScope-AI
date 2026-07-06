"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ProductLabel } from "@/components/ProductLabel";
import { ReportPreview } from "@/components/ReportPreview";
import { PANEL_CLASS, PANEL_PADDING } from "@/components/ui/styles";
import { loadReport } from "@/lib/reportStore";
import type { CompetitorReport } from "@/types/report";

export default function ReportPage() {
  const [report, setReport] = useState<CompetitorReport | null>(null);
  const [checkedStorage, setCheckedStorage] = useState(false);

  useEffect(() => {
    setReport(loadReport());
    setCheckedStorage(true);
  }, []);

  if (!checkedStorage) return null;

  if (!report) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-16 sm:px-6 lg:px-8">
        <section
          className={`${PANEL_CLASS} ${PANEL_PADDING} flex flex-col items-center text-center`}
        >
          <ProductLabel>Output</ProductLabel>
          <p className="mt-3 text-base font-medium text-neutral-200">No report yet</p>
          <p className="mt-2 max-w-sm text-sm leading-relaxed text-neutral-500">
            Generate a brief from the home page first — reports aren&apos;t saved
            between sessions.
          </p>
          <Link
            href="/"
            className="mt-6 inline-flex items-center justify-center rounded-lg bg-amber-500 px-5 py-2.5 text-sm font-semibold text-neutral-950 transition-colors hover:bg-amber-400"
          >
            Start a new brief
          </Link>
        </section>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl px-4 pb-16 pt-8 sm:px-6 sm:pt-10 lg:px-8">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <ProductLabel tone="gold">Output</ProductLabel>
          <h1 className="mt-1.5 text-lg font-semibold tracking-tight text-neutral-100 sm:text-xl">
            Brief preview
          </h1>
        </div>
        <Link
          href="/"
          className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-neutral-800 bg-neutral-900 px-3.5 py-2 text-xs font-medium text-neutral-300 transition-colors hover:border-neutral-700 hover:text-neutral-100"
        >
          New Research
        </Link>
      </div>

      <ReportPreview report={report} />
    </main>
  );
}
