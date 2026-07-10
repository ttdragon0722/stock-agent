import type { PredictionRow } from "@/lib/types";

const STATUS_STYLES: Record<string, string> = {
  WIN: "bg-green-600",
  LOSS: "bg-red-600",
  FLAT: "bg-amber-600",
  NOT_FILLED: "bg-zinc-500",
  OPEN: "bg-blue-600",
  PENDING: "bg-zinc-500",
  NO_DATA: "bg-red-500",
  RESOLVED_DIRECTIONAL: "bg-green-700",
  RESOLVED_NEUTRAL: "bg-amber-700",
  未驗證: "bg-zinc-400",
};

const fmt = (v: unknown): string => {
  if (v === null || v === undefined) return "—";
  if (Array.isArray(v)) return v.join("~");
  return String(v);
};

function DueCell({ row }: { row: PredictionRow }) {
  if (row.verifiable_now)
    return <span className="font-semibold text-amber-600">可驗證</span>;
  if (row.resolved) return <span className="text-zinc-400">已結案</span>;
  return <span>{row.days_left} 天</span>;
}

export default function PredictionsTable({ rows }: { rows: PredictionRow[] }) {
  if (!rows.length)
    return <p className="text-sm text-zinc-500">尚無預測紀錄。</p>;
  return (
    <div className="overflow-x-auto rounded-xl border border-zinc-200 dark:border-zinc-700">
      <table className="w-full whitespace-nowrap text-left text-sm">
        <thead className="bg-zinc-100 text-xs uppercase text-zinc-500 dark:bg-zinc-800 dark:text-zinc-400">
          <tr>
            {[
              "標的", "題型", "方向", "推薦/信心", "分析價", "進場區",
              "SL", "TP", "R:R", "期間", "狀態", "到期", "報酬%",
            ].map((h) => (
              <th key={h} className="px-3 py-2 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-100 dark:divide-zinc-800">
          {rows.map((r) => (
            <tr key={r.id} title={r.id}
                className="hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
              <td className="px-3 py-2 font-semibold">{r.asset}</td>
              <td className="px-3 py-2">{r.question_type.split("_")[0]}</td>
              <td className="px-3 py-2">{r.direction}</td>
              <td className="px-3 py-2">
                {fmt(r.recommendation_score)}/{fmt(r.confidence_score)}
              </td>
              <td className="px-3 py-2">{fmt(r.price_at_analysis)}</td>
              <td className="px-3 py-2">{fmt(r.entry_zone)}</td>
              <td className="px-3 py-2">{fmt(r.stop_loss)}</td>
              <td className="px-3 py-2">{fmt(r.take_profit)}</td>
              <td className="px-3 py-2">{fmt(r.risk_reward)}</td>
              <td className="px-3 py-2 text-xs">
                {r.logged} → {r.horizon_end}
              </td>
              <td className="px-3 py-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs text-white ${
                    STATUS_STYLES[r.status] ?? "bg-zinc-500"
                  }`}
                >
                  {r.status}
                </span>
              </td>
              <td className="px-3 py-2"><DueCell row={r} /></td>
              <td className="px-3 py-2">{fmt(r.return_pct)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
