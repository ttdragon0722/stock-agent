"use client";

export { default } from "@/components/DashboardClient";

/*

import { useCallback, useEffect, useState } from "react";

import PredictionsTable from "@/components/PredictionsTable";
import ReportsPanel from "@/components/ReportsPanel";
import StatsCards from "@/components/StatsCards";
import { fetchPredictions, fetchReports, fetchStats, runVerify } from "@/lib/api";
import type { PredictionRow, ReportInfo, Stats } from "@/lib/types";

export default function DashboardPage() {
  const [rows, setRows] = useState<PredictionRow[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [reports, setReports] = useState<ReportInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [verifyLog, setVerifyLog] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setError(null);
    try {
      const [p, s, r] = await Promise.all([
        fetchPredictions(),
        fetchStats(),
        fetchReports(),
      ]);
      setRows(p.data);
      setStats(s.data);
      setReports(r.data);
    } catch (e) {
      setError(
        e instanceof Error
          ? `無法連線 API:${e.message}(後端啟動了嗎?uvicorn main:app --port 8787)`
          : "未知錯誤",
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
      const res = await runVerify();
      setVerifyLog(res.data.log);
      await reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : "驗證失敗");
    } finally {
      setVerifying(false);
    }
  };

  const actionable = rows.filter((r) => r.verifiable_now).length;

  return (
    <main className="mx-auto max-w-6xl space-y-8 p-6 sm:p-10">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">📈 invest-advisor Dashboard</h1>
          <p className="text-sm text-zinc-500">
            預測日誌、驗證結果與歷史決策報告(所有內容非投資建議)
          </p>
        </div>
        <button
          onClick={onVerify}
          disabled={verifying}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {verifying ? "驗證中(更新 K 線)…" : "🔄 執行驗證"}
        </button>
      </header>

      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
          {error}
        </div>
      )}

      {actionable > 0 && (
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-200">
          ⏰ 有 <b>{actionable}</b> 筆預測已到期或缺資料,點右上「執行驗證」。
        </div>
      )}

      <StatsCards stats={stats} />

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">預測日誌({rows.length} 筆)</h2>
        <PredictionsTable rows={rows} />
      </section>

      {verifyLog && (
        <details className="rounded-lg border border-zinc-200 p-3 text-xs dark:border-zinc-700">
          <summary className="cursor-pointer font-semibold">
            最近一次驗證紀錄
          </summary>
          <pre className="mt-2 overflow-x-auto whitespace-pre-wrap">
            {verifyLog}
          </pre>
        </details>
      )}

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">決策報告({reports.length} 份)</h2>
        <ReportsPanel reports={reports} />
      </section>
    </main>
  );
}
*/
