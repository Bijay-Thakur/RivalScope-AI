import type { TraceEvent } from "@/lib/api";
import type { CompetitorReport, ResearchInput } from "@/types/report";

const STORAGE_KEY = "rivalscope:session";

export interface RunSession {
  report: CompetitorReport;
  input?: ResearchInput;
  runId?: string;
  traces?: TraceEvent[];
}

export function saveSession(session: RunSession): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  } catch {
    /* sessionStorage unavailable */
  }
}

export function loadSession(): RunSession | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as RunSession;
  } catch {
    return null;
  }
}

/** @deprecated use loadSession */
export function loadReport(): CompetitorReport | null {
  return loadSession()?.report ?? null;
}

/** @deprecated use saveSession */
export function saveReport(report: CompetitorReport): void {
  const prev = loadSession();
  saveSession({ ...prev, report });
}

export function clearSession(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    /* ignore */
  }
}
