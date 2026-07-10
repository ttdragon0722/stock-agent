"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import PredictionsTable from "@/components/MarketPredictions";
import ReportsPanel from "@/components/ReportsCalendar";
import StatsCards from "@/components/PerformanceCards";
import { fetchPredictions, fetchReports, fetchStats, runVerify } from "@/lib/api";
import type { PredictionRow, ReportInfo, Stats } from "@/lib/types";

export default function DashboardClient() {
  const [rows, setRows] = useState<PredictionRow[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [reports, setReports] = useState<ReportInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [verifyLog, setVerifyLog] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setError(null);
    try {
      const [predictions, summary, reportList] = await Promise.all([
        fetchPredictions(),
        fetchStats(),
        fetchReports(),
      ]);
      setRows(predictions.data);
      setStats(summary.data);
      setReports(reportList.data);
    } catch (err) {
      setError(
        err instanceof Error
          ? `無法連線到 API：${err.message}。請確認 backend 已在 8787 port 啟動。`
          : "讀取資料時發生未知錯誤。",
      );
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const onVerify = async () => {
    setVerifying(true);
    setVerifyLog(null);
    setError(null);
    try {
      const result = await runVerify();
      setVerifyLog(result.data.log);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "驗證流程執行失敗。");
    } finally {
      setVerifying(false);
    }
  };

  const actionable = useMemo(
    () => rows.filter((row) => row.verifiable_now).length,
    [rows],
  );
  const openPositions = useMemo(
    () => rows.filter((row) => row.status === "OPEN").length,
    [rows],
  );

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_20%_0%,rgba(31,185,210,0.12),transparent_28%),linear-gradient(180deg,#071015_0%,#090b10_46%,#06070a_100%)] text-slate-100">
      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-6 px-4 py-5 sm:px-6 lg:px-8">
        <header className="grid gap-5 border-b border-white/10 pb-5 lg:grid-cols-[1fr_auto] lg:items-end">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 rounded-[8px] border border-cyan-300/20 bg-cyan-300/10 px-3 py-1 text-xs font-medium text-cyan-100">
              INVEST ADVISOR
              <span className="h-1 w-1 rounded-full bg-cyan-300" />
              dark desk
            </div>
            <div className="max-w-3xl">
              <h1 className="text-balance text-3xl font-semibold tracking-normal text-white sm:text-5xl">
                決策儀表板
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400 sm:text-base">
                將預測、績效與決策報告整理成交易員可快速掃描的工作台，分開檢視台股與加密貨幣訊號。
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 lg:justify-end">
            <div className="rounded-[8px] border border-white/10 bg-white/[0.04] px-3 py-2">
              <p className="text-xs text-slate-500">待驗證</p>
              <p className="font-mono text-xl font-semibold text-amber-200">
                {actionable}
              </p>
            </div>
            <div className="rounded-[8px] border border-white/10 bg-white/[0.04] px-3 py-2">
              <p className="text-xs text-slate-500">開倉中</p>
              <p className="font-mono text-xl font-semibold text-cyan-100">
                {openPositions}
              </p>
            </div>
            <button
              onClick={onVerify}
              disabled={verifying}
              className="min-h-11 rounded-[8px] border border-cyan-300/40 bg-cyan-300 px-4 py-2 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200 focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:ring-offset-2 focus:ring-offset-slate-950 disabled:cursor-not-allowed disabled:opacity-55"
            >
              {verifying ? "驗證中..." : "更新驗證"}
            </button>
          </div>
        </header>

        {error && (
          <div className="rounded-[8px] border border-rose-300/25 bg-rose-400/10 px-4 py-3 text-sm text-rose-100">
            {error}
          </div>
        )}

        {actionable > 0 && (
          <div className="rounded-[8px] border border-amber-300/25 bg-amber-300/10 px-4 py-3 text-sm text-amber-100">
            目前有 <b>{actionable}</b> 筆預測已到可驗證時間，建議先更新驗證再檢視績效。
          </div>
        )}

        <StatsCards stats={stats} />

        <section className="space-y-4" aria-labelledby="prediction-heading">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs font-medium uppercase text-cyan-200/70">
                SIGNAL BOOK
              </p>
              <h2
                id="prediction-heading"
                className="mt-1 text-xl font-semibold text-white"
              >
                市場預測資料
              </h2>
            </div>
            <p className="text-sm text-slate-500">{rows.length} 筆紀錄</p>
          </div>
          <PredictionsTable rows={rows} />
        </section>

        {verifyLog && (
          <details className="rounded-[8px] border border-white/10 bg-white/[0.035] p-4 text-xs text-slate-300">
            <summary className="cursor-pointer font-semibold text-slate-100">
              查看最近一次驗證日誌
            </summary>
            <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap rounded-[8px] bg-black/30 p-3 font-mono text-[11px] leading-5 text-slate-400">
              {verifyLog}
            </pre>
          </details>
        )}

        <section className="space-y-4 pb-8" aria-labelledby="reports-heading">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs font-medium uppercase text-cyan-200/70">
                DECISION LOG
              </p>
              <h2
                id="reports-heading"
                className="mt-1 text-xl font-semibold text-white"
              >
                決策報告日曆
              </h2>
            </div>
            <p className="text-sm text-slate-500">{reports.length} 份報告</p>
          </div>
          <ReportsPanel reports={reports} />
        </section>
      </div>
    </main>
  );
}
