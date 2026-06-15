"use client";

import { useCallback, useRef, useState } from "react";
import { Dashboard } from "@/components/Dashboard";
import {
  buildResearchStreamUrl,
  parseStreamReport,
  type StreamProgressEvent,
} from "@/lib/api";
import type { CompetitorReport, ResearchInput } from "@/types/report";

export default function Home() {
  const [isRunning, setIsRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);
  const [progressMessage, setProgressMessage] = useState<string | null>(null);
  const [showReport, setShowReport] = useState(false);
  const [report, setReport] = useState<CompetitorReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const completedRef = useRef(false);

  const closeStream = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
  }, []);

  const handleSubmit = useCallback(
    (input: ResearchInput) => {
      closeStream();
      completedRef.current = false;
      setError(null);
      setShowReport(false);
      setReport(null);
      setProgressMessage(null);
      setIsRunning(true);
      setCurrentStep(0);

      const url = buildResearchStreamUrl(input);
      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.addEventListener("progress", (event) => {
        const data = JSON.parse(event.data) as StreamProgressEvent;
        setCurrentStep(data.step);
        setProgressMessage(data.message);
      });

      eventSource.addEventListener("final_report", (event) => {
        completedRef.current = true;
        const raw = JSON.parse(event.data) as Record<string, unknown>;
        setReport(parseStreamReport(raw));
        setShowReport(true);
        closeStream();
        setIsRunning(false);
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
    [closeStream],
  );

  return (
    <Dashboard
      isRunning={isRunning}
      currentStep={currentStep}
      progressMessage={progressMessage}
      showReport={showReport}
      report={report}
      error={error}
      onSubmit={handleSubmit}
    />
  );
}
