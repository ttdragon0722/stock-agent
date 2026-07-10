"use client";

import { useMemo, useState } from "react";
import { createPortal } from "react-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { fetchReport } from "@/lib/api";
import type { ReportInfo } from "@/lib/types";

const dayNames = ["日", "一", "二", "三", "四", "五", "六"];

function toDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function dateKey(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function formatMonth(date: Date) {
  return new Intl.DateTimeFormat("zh-TW", {
    year: "numeric",
    month: "long",
  }).format(date);
}

function formatDateTime(value: string) {
  const date = toDate(value);
  if (!date) return value;
  return new Intl.DateTimeFormat("zh-TW", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function getReportDate(report: ReportInfo) {
  return toDate(report.modified) ?? new Date(0);
}

function buildCalendar(monthDate: Date) {
  const first = new Date(monthDate.getFullYear(), monthDate.getMonth(), 1);
  const last = new Date(monthDate.getFullYear(), monthDate.getMonth() + 1, 0);
  const cells: Date[] = [];

  for (let index = first.getDay(); index > 0; index -= 1) {
    cells.push(new Date(first.getFullYear(), first.getMonth(), 1 - index));
  }
  for (let day = 1; day <= last.getDate(); day += 1) {
    cells.push(new Date(first.getFullYear(), first.getMonth(), day));
  }
  while (cells.length % 7 !== 0) {
    const previous = cells[cells.length - 1];
    cells.push(
      new Date(previous.getFullYear(), previous.getMonth(), previous.getDate() + 1),
    );
  }

  return cells;
}

export default function ReportsCalendar({ reports }: { reports: ReportInfo[] }) {
  const sortedReports = useMemo(
    () =>
      [...reports].sort(
        (a, b) => getReportDate(b).getTime() - getReportDate(a).getTime(),
      ),
    [reports],
  );

  const latestDate = sortedReports[0] ? getReportDate(sortedReports[0]) : new Date();
  const latestMonth = new Date(latestDate.getFullYear(), latestDate.getMonth(), 1);
  const latestDayKey = sortedReports[0] ? dateKey(latestDate) : null;
  const [monthDate, setMonthDate] = useState<Date | null>(null);
  const [selectedDay, setSelectedDay] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [markdown, setMarkdown] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const reportsByDay = useMemo(() => {
    const map = new Map<string, ReportInfo[]>();
    for (const report of sortedReports) {
      const key = dateKey(getReportDate(report));
      const items = map.get(key) ?? [];
      items.push(report);
      map.set(key, items);
    }
    return map;
  }, [sortedReports]);

  const visibleMonth = monthDate ?? latestMonth;
  const activeDay = selectedDay ?? latestDayKey;
  const selectedReports = useMemo(
    () => (activeDay ? reportsByDay.get(activeDay) ?? [] : []),
    [activeDay, reportsByDay],
  );
  const calendarDays = buildCalendar(visibleMonth);

  const openReport = async (report: ReportInfo) => {
    setSelected(report.name);
    setMarkdown("");
    setError(null);
    setLoading(true);
    try {
      const response = await fetchReport(report.name);
      setMarkdown(response.data.markdown);
    } catch (err) {
      setError(err instanceof Error ? err.message : "讀取報告失敗。");
    } finally {
      setLoading(false);
    }
  };

  const changeMonth = (offset: number) => {
    setMonthDate((current) => {
      const base = current ?? visibleMonth;
      return new Date(base.getFullYear(), base.getMonth() + offset, 1);
    });
  };

  const sidebarTarget =
    typeof document === "undefined"
      ? null
      : document.getElementById("report-calendar-sidebar");

  const sidebar = (
    <aside className="min-w-0 overflow-hidden rounded-[8px] border border-white/10 bg-white/[0.035]">
      {!reports.length ? (
        <div className="px-4 py-8 text-sm text-slate-500">尚未產生決策報告。</div>
      ) : (
        <>
        <div className="flex items-center justify-between gap-3 border-b border-white/10 px-4 py-4">
          <button
            type="button"
            onClick={() => changeMonth(-1)}
            className="min-h-9 rounded-[6px] border border-white/10 px-3 text-sm text-slate-300 transition hover:border-cyan-300/30 hover:text-cyan-100 focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:ring-offset-2 focus:ring-offset-slate-950"
            aria-label="上一個月"
          >
            上月
          </button>
          <h3 className="text-base font-semibold text-white">{formatMonth(visibleMonth)}</h3>
          <button
            type="button"
            onClick={() => changeMonth(1)}
            className="min-h-9 rounded-[6px] border border-white/10 px-3 text-sm text-slate-300 transition hover:border-cyan-300/30 hover:text-cyan-100 focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:ring-offset-2 focus:ring-offset-slate-950"
            aria-label="下一個月"
          >
            下月
          </button>
        </div>

        <div className="grid grid-cols-7 border-b border-white/10 bg-black/20 text-center text-xs text-slate-500">
          {dayNames.map((day) => (
            <div key={day} className="py-2">
              {day}
            </div>
          ))}
        </div>

        <div className="grid grid-cols-7">
          {calendarDays.map((day) => {
            const key = dateKey(day);
            const dayReports = reportsByDay.get(key) ?? [];
            const inMonth = day.getMonth() === visibleMonth.getMonth();
            const active = activeDay === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => {
                  setSelectedDay(key);
                  if (dayReports[0]) {
                    void openReport(dayReports[0]);
                  } else {
                    setSelected(null);
                    setMarkdown("");
                    setError(null);
                    setLoading(false);
                  }
                }}
                className={`h-[82px] min-w-0 overflow-hidden border-b border-r border-white/10 p-2 text-left transition focus:outline-none focus:ring-2 focus:ring-inset focus:ring-cyan-200 ${
                  active
                    ? "bg-cyan-300/12"
                    : dayReports.length
                      ? "bg-white/[0.045] hover:bg-white/[0.07]"
                      : "hover:bg-white/[0.035]"
                } ${inMonth ? "text-slate-200" : "text-slate-700"}`}
              >
                <span className="font-mono text-xs">{day.getDate()}</span>
                {dayReports.length > 0 && (
                  <span className="mt-2 block rounded-[5px] bg-cyan-300/15 px-1.5 py-1 text-[11px] font-medium text-cyan-100">
                    {dayReports.length} 份
                  </span>
                )}
                {dayReports[0] && (
                  <span className="mt-1 block truncate text-[11px] text-slate-500">
                    {dayReports[0].name}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        <div className="grid min-w-0 gap-4 border-t border-white/10 p-4">
          <div className="min-w-0">
            <p className="text-xs text-slate-500">選取日期</p>
            <p className="mt-1 truncate font-mono text-lg text-white">{activeDay ?? "--"}</p>
          </div>
          <div className="grid max-h-48 min-w-0 gap-2 overflow-y-auto pr-1">
            {selectedReports.length ? (
              selectedReports.map((report) => (
                <button
                  key={report.name}
                  type="button"
                  onClick={() => openReport(report)}
                  className={`min-h-10 w-full truncate rounded-[6px] border px-3 text-left text-sm transition focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:ring-offset-2 focus:ring-offset-slate-950 ${
                    selected === report.name
                      ? "border-cyan-300/40 bg-cyan-300/15 text-cyan-100"
                      : "border-white/10 text-slate-300 hover:border-cyan-300/30"
                  }`}
                  title={`${report.name}，${formatDateTime(report.modified)}`}
                >
                  {report.name}
                </button>
              ))
            ) : (
              <p className="text-sm text-slate-500">這一天沒有報告。</p>
            )}
          </div>
        </div>
        </>
      )}
    </aside>
  );

  return (
    <>
      {sidebarTarget ? createPortal(sidebar, sidebarTarget) : null}
      <div className="min-w-0 overflow-hidden rounded-[8px] border border-white/10 bg-white/[0.035]">
        <div className="flex min-w-0 items-center justify-between gap-3 border-b border-white/10 p-4">
          <div className="min-w-0">
            <p className="text-xs text-slate-500">目前報告</p>
            <p className="mt-1 truncate text-sm font-medium text-slate-200">
              {selected ?? "尚未選取報告"}
            </p>
          </div>
          {selected && (
            <span className="hidden rounded-[6px] border border-cyan-300/25 bg-cyan-300/10 px-2 py-1 text-xs text-cyan-100 sm:inline-flex">
              Markdown
            </span>
          )}
        </div>

        <div className="min-h-[420px] min-w-0 overflow-hidden p-4">
          {loading && <p className="text-sm text-slate-500">載入報告中...</p>}
          {error && <p className="text-sm text-rose-100">{error}</p>}
          {!loading && !error && !selected && (
            <p className="text-sm text-slate-500">請從日曆選擇一份決策報告。</p>
          )}
          {markdown && (
            <article className="prose prose-invert prose-sm max-w-none overflow-x-auto prose-headings:text-white prose-a:text-cyan-200 prose-table:text-xs prose-th:border-white/10 prose-td:border-white/10 [&_pre]:max-w-full [&_pre]:overflow-x-auto [&_table]:block [&_table]:max-w-full [&_table]:overflow-x-auto">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
            </article>
          )}
        </div>
      </div>
    </>
  );
}
