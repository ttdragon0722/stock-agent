import type {
  Envelope, EventsDoc, PredictionRow, ReportContent, ReportInfo,
  StatsByMarket, VerifyResult,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8787";

async function request<T>(path: string, init?: RequestInit): Promise<Envelope<T>> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    throw new Error(`API ${res.status}: ${detail || res.statusText}`);
  }
  return res.json() as Promise<Envelope<T>>;
}

export const fetchPredictions = () =>
  request<PredictionRow[]>("/api/predictions");

export const fetchStats = () => request<StatsByMarket>("/api/stats");

export const fetchReports = () => request<ReportInfo[]>("/api/reports");

export const fetchReport = (name: string) =>
  request<ReportContent>(`/api/reports/${encodeURIComponent(name)}`);

export const fetchEvents = (symbol?: string) =>
  request<EventsDoc>(
    symbol ? `/api/events?symbol=${encodeURIComponent(symbol)}` : "/api/events",
  );

export const runVerify = () =>
  request<VerifyResult>("/api/verify?fetch=true", { method: "POST" });
