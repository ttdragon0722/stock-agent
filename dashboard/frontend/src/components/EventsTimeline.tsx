"use client";

import { useMemo, useState } from "react";

import type { EventsDoc, ImportantEvent, KeyDate } from "@/lib/types";

const MS_PER_DAY = 86_400_000;

const impactStyle: Record<ImportantEvent["impact"], string> = {
  bullish: "border-emerald-300/30 bg-emerald-300/10 text-emerald-200",
  bearish: "border-rose-300/30 bg-rose-300/10 text-rose-200",
  neutral: "border-slate-300/20 bg-slate-300/10 text-slate-300",
};

const impactLabel: Record<ImportantEvent["impact"], string> = {
  bullish: "利多",
  bearish: "利空",
  neutral: "中性",
};

function startOfToday(): Date {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate());
}

function daysUntil(date: string): number | null {
  const target = new Date(`${date}T00:00:00`);
  if (Number.isNaN(target.getTime())) return null;
  return Math.round((target.getTime() - startOfToday().getTime()) / MS_PER_DAY);
}

function countdownBadge(days: number | null) {
  if (days === null) return { text: "—", cls: "text-slate-500" };
  if (days < 0) return { text: `${-days} 天前`, cls: "text-slate-500" };
  if (days === 0) return { text: "今天", cls: "text-rose-200" };
  if (days <= 7) return { text: `${days} 天後`, cls: "text-amber-200" };
  return { text: `${days} 天後`, cls: "text-cyan-100" };
}

function SymbolFilter({
  symbols, active, onChange,
}: {
  symbols: string[];
  active: string | null;
  onChange: (symbol: string | null) => void;
}) {
  if (symbols.length < 2) return null;
  const baseCls =
    "min-h-8 whitespace-nowrap rounded-[6px] border px-2.5 text-xs transition focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:ring-offset-2 focus:ring-offset-slate-950";
  return (
    <div className="flex gap-2 overflow-x-auto pb-1">
      <button
        type="button"
        onClick={() => onChange(null)}
        className={`${baseCls} ${
          active === null
            ? "border-cyan-300/40 bg-cyan-300/15 text-cyan-100"
            : "border-white/10 text-slate-400 hover:border-cyan-300/30"
        }`}
      >
        全部
      </button>
      {symbols.map((symbol) => (
        <button
          key={symbol}
          type="button"
          onClick={() => onChange(symbol)}
          className={`${baseCls} font-mono ${
            active === symbol
              ? "border-cyan-300/40 bg-cyan-300/15 text-cyan-100"
              : "border-white/10 text-slate-400 hover:border-cyan-300/30"
          }`}
        >
          {symbol}
        </button>
      ))}
    </div>
  );
}

function KeyDateRow({ item }: { item: KeyDate }) {
  const badge = countdownBadge(daysUntil(item.date));
  return (
    <li className="relative pl-6">
      <span className="absolute left-0 top-2 h-2.5 w-2.5 rounded-full border border-cyan-300/50 bg-cyan-300/20" />
      <span className="absolute bottom-[-14px] left-[4.5px] top-5 w-px bg-white/10" />
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-mono text-sm text-white">
          {item.date}
          {item.time ? ` ${item.time}` : ""}
        </span>
        <span className={`font-mono text-xs ${badge.cls}`}>{badge.text}</span>
        {item.status === "estimated" && (
          <span className="rounded-[5px] border border-amber-300/25 bg-amber-300/10 px-1.5 py-0.5 text-[10px] text-amber-200">
            預估
          </span>
        )}
      </div>
      <p className="mt-1 text-sm text-slate-200">
        <span className="mr-2 font-mono text-xs text-cyan-200/80">
          {item.symbol}
        </span>
        {item.label}
      </p>
      {item.note && <p className="mt-0.5 text-xs text-slate-500">{item.note}</p>}
    </li>
  );
}

function EventCard({ event }: { event: ImportantEvent }) {
  return (
    <li className="rounded-[8px] border border-white/10 bg-white/[0.03] p-3">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded-[5px] border px-1.5 py-0.5 text-[10px] font-medium ${impactStyle[event.impact] ?? impactStyle.neutral}`}
        >
          {impactLabel[event.impact] ?? event.impact}
        </span>
        <span className="font-mono text-xs text-cyan-200/80">{event.symbol}</span>
        <span className="font-mono text-xs text-slate-500">{event.date}</span>
        <span className="rounded-[5px] bg-white/[0.06] px-1.5 py-0.5 text-[10px] text-slate-400">
          {event.category}
        </span>
      </div>
      <p className="mt-2 text-sm font-medium text-slate-100">{event.title}</p>
      {event.description && (
        <p className="mt-1 text-xs leading-5 text-slate-400">{event.description}</p>
      )}
      {event.source_url && (
        <a
          href={event.source_url}
          target="_blank"
          rel="noreferrer"
          className="mt-1 inline-block max-w-full truncate text-xs text-cyan-200/70 underline-offset-2 hover:underline"
        >
          資料來源
        </a>
      )}
    </li>
  );
}

export default function EventsTimeline({ events }: { events: EventsDoc | null }) {
  const [symbol, setSymbol] = useState<string | null>(null);
  const [showPast, setShowPast] = useState(false);

  const symbols = useMemo(() => {
    if (!events) return [];
    const all = [...events.important_events, ...events.key_dates].map(
      (record) => record.symbol,
    );
    return [...new Set(all)].sort();
  }, [events]);

  const importantEvents = useMemo(
    () =>
      (events?.important_events ?? []).filter(
        (event) => symbol === null || event.symbol === symbol,
      ),
    [events, symbol],
  );

  const keyDates = useMemo(() => {
    const filtered = (events?.key_dates ?? []).filter(
      (item) => symbol === null || item.symbol === symbol,
    );
    if (showPast) return filtered;
    return filtered.filter((item) => (daysUntil(item.date) ?? 0) >= 0);
  }, [events, symbol, showPast]);

  if (!events || (!events.important_events.length && !events.key_dates.length)) {
    return (
      <div className="rounded-[8px] border border-white/10 bg-white/[0.035] px-4 py-8 text-sm text-slate-500">
        尚無事件紀錄。產出決策報告後,skill 會自動把重要事件與關鍵日期寫入
        events.json。
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <SymbolFilter symbols={symbols} active={symbol} onChange={setSymbol} />

      <div className="grid min-w-0 gap-4 lg:grid-cols-2">
        <section
          aria-labelledby="key-dates-heading"
          className="min-w-0 rounded-[8px] border border-white/10 bg-white/[0.035] p-4"
        >
          <div className="flex items-center justify-between gap-3">
            <h3 id="key-dates-heading" className="text-sm font-semibold text-white">
              關鍵日期和時間
              <span className="ml-2 font-mono text-xs text-slate-500">
                {keyDates.length}
              </span>
            </h3>
            <button
              type="button"
              onClick={() => setShowPast((current) => !current)}
              className="min-h-8 rounded-[6px] border border-white/10 px-2.5 text-xs text-slate-400 transition hover:border-cyan-300/30 hover:text-cyan-100 focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:ring-offset-2 focus:ring-offset-slate-950"
            >
              {showPast ? "只看未來" : "含已過期"}
            </button>
          </div>
          {keyDates.length ? (
            <ul className="mt-4 space-y-5">
              {keyDates.map((item) => (
                <KeyDateRow key={item.id} item={item} />
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm text-slate-500">目前沒有即將到來的關鍵日期。</p>
          )}
        </section>

        <section
          aria-labelledby="important-events-heading"
          className="min-w-0 rounded-[8px] border border-white/10 bg-white/[0.035] p-4"
        >
          <h3
            id="important-events-heading"
            className="text-sm font-semibold text-white"
          >
            重要事件
            <span className="ml-2 font-mono text-xs text-slate-500">
              {importantEvents.length}
            </span>
          </h3>
          {importantEvents.length ? (
            <ul className="mt-4 max-h-[480px] space-y-3 overflow-y-auto pr-1">
              {importantEvents.map((event) => (
                <EventCard key={event.id} event={event} />
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm text-slate-500">此篩選條件下沒有事件。</p>
          )}
        </section>
      </div>

      {events.updated_at && (
        <p className="text-right font-mono text-[11px] text-slate-600">
          events.json 更新於 {events.updated_at}
        </p>
      )}
    </div>
  );
}
