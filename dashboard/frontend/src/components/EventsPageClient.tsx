"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import EventsTimeline from "@/components/EventsTimeline";
import { fetchEvents } from "@/lib/api";
import type { EventsDoc } from "@/lib/types";

export default function EventsPageClient() {
  const [events, setEvents] = useState<EventsDoc | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const response = await fetchEvents();
      setEvents(response.data);
    } catch (err) {
      setError(
        err instanceof Error
          ? `無法連線到 API：${err.message}。請確認 backend 已在 8787 port 啟動。`
          : "讀取事件資料時發生未知錯誤。",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void reload();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [reload]);

  const totalEvents = events?.important_events.length ?? 0;
  const totalKeyDates = events?.key_dates.length ?? 0;

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_20%_0%,rgba(31,185,210,0.12),transparent_28%),linear-gradient(180deg,#071015_0%,#090b10_46%,#06070a_100%)] text-slate-100">
      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
        <header className="grid gap-5 border-b border-white/10 pb-5 lg:grid-cols-[1fr_auto] lg:items-end">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 rounded-[8px] border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-xs font-medium text-cyan-100">
              INVEST ADVISOR
              <span className="h-1 w-1 rounded-full bg-cyan-300" />
              event radar
            </div>
            <div className="max-w-3xl">
              <h1 className="text-balance text-3xl font-semibold text-white sm:text-5xl">
                重要事件與關鍵日期
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400 sm:text-base">
                決策報告萃取的事件檔（events.json）：左側是即將到來的關鍵日期時間軸，
                右側是影響判斷的重要事件與多空標籤。
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 lg:justify-end">
            <div className="rounded-[8px] border border-white/10 bg-white/[0.04] px-3 py-2">
              <p className="text-xs text-slate-500">關鍵日期</p>
              <p className="font-mono text-xl font-semibold text-cyan-100">
                {totalKeyDates}
              </p>
            </div>
            <div className="rounded-[8px] border border-white/10 bg-white/[0.04] px-3 py-2">
              <p className="text-xs text-slate-500">重要事件</p>
              <p className="font-mono text-xl font-semibold text-amber-200">
                {totalEvents}
              </p>
            </div>
            <button
              onClick={() => void reload()}
              disabled={loading}
              className="min-h-11 rounded-[8px] border border-cyan-300/40 bg-cyan-300 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:ring-offset-2 focus:ring-offset-slate-950 disabled:cursor-not-allowed disabled:opacity-55"
            >
              {loading ? "載入中..." : "重新整理"}
            </button>
            <Link
              href="/"
              className="min-h-11 rounded-[8px] border border-white/15 px-4 py-2 text-sm font-medium leading-7 text-slate-300 transition hover:border-cyan-300/30 hover:text-cyan-100 focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:ring-offset-2 focus:ring-offset-slate-950"
            >
              ← 回儀表板
            </Link>
          </div>
        </header>

        <div className="space-y-6 pb-8">
          {error && (
            <div className="rounded-[8px] border border-rose-300/25 bg-rose-400/10 px-4 py-3 text-sm text-rose-100">
              {error}
            </div>
          )}
          {loading && !events && (
            <p className="text-sm text-slate-500">載入事件資料中...</p>
          )}
          {!loading || events ? <EventsTimeline events={events} /> : null}
        </div>
      </div>
    </main>
  );
}
