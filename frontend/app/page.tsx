"use client";

import { useCallback, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AgentTrackerModal } from "@/components/AgentTrackerModal";
import { ProductLabel } from "@/components/ProductLabel";
import { ResearchForm } from "@/components/ResearchForm";
import {
  buildResearchStreamUrl,
  parseStreamReport,
  type StreamProgressEvent,
} from "@/lib/api";
import { saveReport } from "@/lib/reportStore";
import type { ResearchInput } from "@/types/report";

const REDIRECT_DELAY_MS = 700;

export default function Home() {
  const router = useRouter();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [progressMessage, setProgressMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [runLabel, setRunLabel] = useState<{ ourCompany: string; competitor: string } | null>(
    null,
  );
  const eventSourceRef = useRef<EventSource | null>(null);
  const completedRef = useRef(false);

  const closeStream = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
  }, []);

  const handleClose = useCallback(() => {
    closeStream();
    setIsModalOpen(false);
    setIsRunning(false);
  }, [closeStream]);

  const handleSubmit = useCallback(
    (input: ResearchInput) => {
      closeStream();
      completedRef.current = false;
      setError(null);
      setProgressMessage(null);
      setCompletedSteps([]);
      setRunLabel({ ourCompany: input.ourCompany, competitor: input.competitor });
      setIsModalOpen(true);
      setIsRunning(true);

      const url = buildResearchStreamUrl(input);
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.addEventListener("progress", (event) => {
        const data = JSON.parse(event.data) as StreamProgressEvent;
        // Parallel research tracks (steps 3-6) can complete out of order — accumulate
        // instead of overwriting a single "current step" number.
        setCompletedSteps((prev) => (prev.includes(data.step) ? prev : [...prev, data.step]));
        setProgressMessage(data.message);
      });

      eventSource.addEventListener("final_report", (event) => {
        completedRef.current = true;
        const raw = JSON.parse(event.data) as Record<string, unknown>;
        const report = parseStreamReport(raw);
        closeStream();
        setIsRunning(false);
        saveReport(report);
        window.setTimeout(() => {
          router.push("/report");
        }, REDIRECT_DELAY_MS);
      });

      eventSource.addEventListener("error", (event) => {
        if (!(event instanceof MessageEvent) || !event.data) return;

        completedRef.current = true;
        try {
          const data = JSON.parse(event.data) as { detail?: string };
          setError(data.detail ?? "Research workflow failed.");
        } catch {
          setError("Research workflow failed.");
        }
        closeStream();
        setIsRunning(false);
      });

      eventSource.onerror = () => {
        if (completedRef.current) return;

        setError(
          "Lost connection to the research stream. Ensure the backend is running at http://localhost:8000.",
        );
        closeStream();
        setIsRunning(false);
      };
    },
    [closeStream, router],
  );

  return (
    <>
      <main className="mx-auto max-w-3xl px-4 pb-16 pt-10 sm:px-6 sm:pt-14 lg:px-8">
        <div className="mb-8 text-center sm:mb-10">
          <ProductLabel tone="gold">Input & Workflow</ProductLabel>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-neutral-100 sm:text-3xl">
            Configure your research
          </h1>
          <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-neutral-500">
            Set the competitive parameters below. A live agent pipeline gathers
            evidence, verifies claims, and writes a source-grounded brief.
          </p>
        </div>

        <ResearchForm onSubmit={handleSubmit} isRunning={isRunning} />
      </main>

      <AgentTrackerModal
        isOpen={isModalOpen}
        isRunning={isRunning}
        completedSteps={completedSteps}
        progressMessage={progressMessage}
        error={error}
        runLabel={runLabel}
        onClose={handleClose}
      />
    </>
  );
}
