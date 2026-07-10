import type { Stats } from "@/lib/types";

const fmt = (v: number | null, suffix = "") =>
  v === null || v === undefined ? "—" : `${v}${suffix}`;

export default function StatsCards({ stats }: { stats: Stats | null }) {
  const cards = [
    { label: "預測總數", value: fmt(stats?.total ?? null) },
    {
      label: "勝率",
      value:
        stats?.win_rate != null ? `${(stats.win_rate * 100).toFixed(1)}%` : "—",
    },
    { label: "期望值 (R)", value: fmt(stats?.expectancy_r ?? null) },
    {
      label: "方向準確率",
      value:
        stats?.direction_accuracy != null
          ? `${(stats.direction_accuracy * 100).toFixed(1)}%`
          : "—",
    },
    { label: "平均超額報酬", value: fmt(stats?.avg_excess_return_pct ?? null, "%") },
  ];
  return (
    <section>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {cards.map((c) => (
          <div
            key={c.label}
            className="rounded-xl border border-zinc-200 bg-white p-4 dark:border-zinc-700 dark:bg-zinc-900"
          >
            <div className="text-xs text-zinc-500 dark:text-zinc-400">
              {c.label}
            </div>
            <div className="mt-1 text-xl font-semibold">{c.value}</div>
          </div>
        ))}
      </div>
      {stats?.sample_warning && (
        <p className="mt-2 text-xs text-amber-600 dark:text-amber-400">
          ⚠️ {stats.sample_warning}
        </p>
      )}
    </section>
  );
}
