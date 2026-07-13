// API contract types — mirror dashboard/backend/main.py responses.

export interface Envelope<T> {
  success: boolean;
  data: T;
  error: string | null;
  meta?: Record<string, unknown>;
}

export interface PredictionRow {
  id: string;
  asset: string;
  question_type: string;
  direction: "long" | "short" | "neutral";
  recommendation_score: number | null;
  confidence_score: number | null;
  price_at_analysis: number | null;
  entry_zone: number[] | null;
  stop_loss: number | null;
  take_profit: number[] | null;
  risk_reward: number | null;
  falsification_condition: string | null;
  logged: string;
  horizon_end: string;
  days_left: number;
  status: string;
  return_pct: number | null;
  excess_return_pct: number | null;
  resolved: boolean;
  verifiable_now: boolean;
}

export interface Stats {
  total: number;
  by_status: Record<string, number>;
  win_rate: number | null;
  expectancy_r: number | null;
  direction_accuracy: number | null;
  avg_excess_return_pct: number | null;
  sample_warning: string | null;
}

export interface ReportInfo {
  name: string;
  size: number;
  modified: string;
}

export interface ReportContent {
  name: string;
  markdown: string;
}

export interface VerifyResult {
  summary: Stats;
  log: string;
}

// events.json 兩區塊文件 — mirror invest-advisor/scripts/log_events.py。
// 兩種 record 都可能帶腳本保留的擴充欄位,故加 index signature。

export interface ImportantEvent {
  id: string;
  symbol: string;
  date: string; // YYYY-MM-DD
  title: string;
  category: string;
  impact: "bullish" | "bearish" | "neutral";
  description?: string;
  source_url?: string;
  logged_at?: string;
  reports?: string[];
  [extra: string]: unknown;
}

export interface KeyDate {
  id: string;
  symbol: string;
  date: string; // YYYY-MM-DD
  time?: string; // HH:MM
  label: string;
  date_type: string;
  status: "confirmed" | "estimated";
  note?: string;
  logged_at?: string;
  reports?: string[];
  [extra: string]: unknown;
}

export interface EventsDoc {
  schema_version: string;
  updated_at: string | null;
  important_events: ImportantEvent[];
  key_dates: KeyDate[];
}
