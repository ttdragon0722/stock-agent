import type { Stats } from "@/lib/types";

const formatPercent = (value: number | null | undefined) =>
  value == null ? "--" : `${(value * 100).toFixed(1)}%`;

const formatNumber = (
  value: number | null | undefined,
  options?: Intl.NumberFormatOptions,
) => (value == null ? "--" : new Intl.NumberFormat("zh-TW", options).format(value));

export default function PerformanceCards({ stats }: { stats: Stats | null }) {
  const cards = [
    {
      label: "追蹤預測",
      value: formatNumber(stats?.total),
      detail: "目前資料庫內的決策樣本",
    },
    {
      label: "勝率",
      value: formatPercent(stats?.win_rate),
      detail: "已結案預測的命中比例",
    },
    {
      label: "期望值",
      value: formatNumber(stats?.expectancy_r, {
        maximumFractionDigits: 2,
        signDisplay: "exceptZero",
      }),
      detail: "平均每筆風險報酬 R",
    },
    {
      label: "方向準確率",
      value: formatPercent(stats?.direction_accuracy),
      detail: "多空方向判斷品質",
    },
    {
      label: "超額報酬",
      value:
        stats?.avg_excess_return_pct == null
          ? "--"
          : `${stats.avg_excess_return_pct.toFixed(2)}%`,
      detail: "相對市場的平均表現",
    },
  ];

  return (
    <section className="space-y-3" aria-label="績效摘要">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {cards.map((card, index) => (
          <div
            key={card.label}
            className="group rounded-[8px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.075),rgba(255,255,255,0.025))] p-4 shadow-[0_18px_60px_rgba(0,0,0,0.22)] transition duration-200 hover:border-cyan-300/30"
          >
            <div className="flex items-start justify-between gap-3">
              <p className="text-xs font-medium text-slate-400">{card.label}</p>
              <span className="font-mono text-[10px] text-slate-600">
                M{index + 1}
              </span>
            </div>
            <p className="mt-3 font-mono text-2xl font-semibold text-slate-50">
              {card.value}
            </p>
            <p className="mt-2 text-xs leading-5 text-slate-500">{card.detail}</p>
          </div>
        ))}
      </div>
      {stats?.sample_warning && (
        <p className="rounded-[8px] border border-amber-300/20 bg-amber-300/10 px-3 py-2 text-xs text-amber-100">
          樣本提醒：{stats.sample_warning}
        </p>
      )}
    </section>
  );
}
