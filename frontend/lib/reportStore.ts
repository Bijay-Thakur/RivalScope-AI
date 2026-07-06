import type { CompetitorReport } from "@/types/report";

const STORAGE_KEY = "rivalscope:lastReport";

export function saveReport(report: CompetitorReport): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(report));
  } catch {
    // sessionStorage unavailable (e.g. private mode) — report won't survive navigation
  }
}

export function loadReport(): CompetitorReport | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as CompetitorReport) : null;
  } catch {
    return null;
  }
}

export function clearReport(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}
