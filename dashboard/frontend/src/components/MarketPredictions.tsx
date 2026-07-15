"use client";

import { useMemo, useState } from "react";

import type { PredictionRow } from "@/lib/types";

type MarketId = "tw" | "crypto";

type MarketGroup = {
  id: MarketId;
  title: string;
  subtitle: string;
  rows: PredictionRow[];
};

type FilterMode = "all" | "unfilled" | "unverified" | "verified";

// 未驗證 = 尚未結案(等待中/開倉中);已驗證 = 已有判定結果(勝/負/未成交結案…)
const FILTER_OPTIONS: {
  id: FilterMode;
  label: string;
  match: (row: PredictionRow) => boolean;
}[] = [
  { id: "all", label: "全部", match: () => true },
  { id: "unfilled", label: "未成交掛單", match: (row) => row.unfilled },
  { id: "unverified", label: "未驗證", match: (row) => !row.resolved },
  { id: "verified", label: "已驗證", match: (row) => row.resolved },
];

const CRYPTO_HINTS = [
  "USDT",
  "USDC",
  "BTC",
  "ETH",
  "SOL",
  "BNB",
  "XRP",
  "DOGE",
  "ADA",
  "AVAX",
  "DOT",
  "LINK",
  "LTC",
  "BCH",
  "TRX",
  "TON",
  "NEAR",
  "ARB",
  "OP",
  "SUI",
];

const STATUS_LABELS: Record<string, string> = {
  WIN: "勝",
  LOSS: "負",
  FLAT: "持平",
  NOT_FILLED: "未成交",
  OPEN: "開倉",
  PENDING: "等待",
  NO_DATA: "缺資料",
  RESOLVED_DIRECTIONAL: "方向結案",
  RESOLVED_NEUTRAL: "中性結案",
};

const STATUS_STYLES: Record<string, string> = {
  WIN: "border-emerald-300/30 bg-emerald-300/12 text-emerald-100",
  LOSS: "border-rose-300/30 bg-rose-300/12 text-rose-100",
  FLAT: "border-amber-300/30 bg-amber-300/12 text-amber-100",
  NOT_FILLED: "border-slate-300/20 bg-slate-300/10 text-slate-300",
  OPEN: "border-cyan-300/35 bg-cyan-300/12 text-cyan-100",
  PENDING: "border-slate-300/20 bg-slate-300/10 text-slate-300",
  NO_DATA: "border-rose-300/30 bg-rose-300/12 text-rose-100",
  RESOLVED_DIRECTIONAL: "border-emerald-300/30 bg-emerald-300/12 text-emerald-100",
  RESOLVED_NEUTRAL: "border-amber-300/30 bg-amber-300/12 text-amber-100",
};

const DIRECTION_LABELS: Record<PredictionRow["direction"], string> = {
  long: "做多",
  short: "做空",
  neutral: "觀望",
};

const DIRECTION_STYLES: Record<PredictionRow["direction"], string> = {
  long: "text-emerald-100 bg-emerald-300/12 border-emerald-300/30",
  short: "text-rose-100 bg-rose-300/12 border-rose-300/30",
  neutral: "text-slate-200 bg-slate-300/10 border-slate-300/20",
};

const numberFormatter = new Intl.NumberFormat("zh-TW", {
  maximumFractionDigits: 2,
});

const compactFormatter = new Intl.NumberFormat("zh-TW", {
  maximumFractionDigits: 2,
  notation: "compact",
});

function isCryptoAsset(asset: string) {
  const value = asset.toUpperCase();
  return (
    CRYPTO_HINTS.some((hint) => value.includes(hint)) ||
    value.endsWith("-USD") ||
    value.endsWith("USD")
  );
}

// 市場分類以預測日誌的 asset_type 為準(單一事實來源);
// 舊資料缺 asset_type 時 fallback 用代號啟發式判斷。
function isCryptoRow(row: PredictionRow) {
  if (row.asset_type) return row.asset_type === "crypto";
  return isCryptoAsset(row.asset);
}

function formatValue(value: number | null | undefined, compact = false) {
  if (value == null) return "--";
  return compact ? compactFormatter.format(value) : numberFormatter.format(value);
}

function formatRange(value: number[] | null | undefined) {
  if (!value?.length) return "--";
  const compact = value.some((item) => item >= 10000);
  return value.map((item) => formatValue(item, compact)).join(" - ");
}

function formatDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value || "--";
  return new Intl.DateTimeFormat("zh-TW", {
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

function formatReturn(value: number | null) {
  if (value == null) return "--";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

function getScore(row: PredictionRow) {
  const confidence = row.confidence_score ?? 0;
  const recommendation = row.recommendation_score ?? 0;
  return Math.max(0, Math.min(100, Math.round((confidence + recommendation) / 2)));
}

function DueLabel({ row }: { row: PredictionRow }) {
  if (row.verifiable_now) {
    return <span className="font-medium text-amber-100">可驗證</span>;
  }
  if (row.resolved) {
    return <span className="text-slate-500">已結案</span>;
  }
  return <span className="text-slate-300">剩 {row.days_left} 天</span>;
}

function ScoreBar({ row }: { row: PredictionRow }) {
  const score = getScore(row);
  return (
    <div className="min-w-[120px]">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-sm text-slate-100">{score}</span>
        <span className="text-xs text-slate-500">信心</span>
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-[4px] bg-white/10">
        <div
          className="h-full rounded-[4px] bg-cyan-300"
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}

function RowStatus({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex min-h-7 items-center rounded-[6px] border px-2 text-xs font-medium ${
        STATUS_STYLES[status] ?? "border-slate-300/20 bg-slate-300/10 text-slate-300"
      }`}
    >
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

function DirectionBadge({ direction }: { direction: PredictionRow["direction"] }) {
  return (
    <span
      className={`inline-flex min-h-7 items-center rounded-[6px] border px-2 text-xs font-medium ${DIRECTION_STYLES[direction]}`}
    >
      {DIRECTION_LABELS[direction]}
    </span>
  );
}

function MarketTable({ group }: { group: MarketGroup }) {
  const winning = group.rows.filter((row) =>
    ["WIN", "RESOLVED_DIRECTIONAL"].includes(row.status),
  ).length;
  const open = group.rows.filter((row) => row.status === "OPEN").length;
  const due = group.rows.filter((row) => row.verifiable_now).length;
  const unfilled = group.rows.filter((row) => row.unfilled).length;

  return (
    <section className="min-w-0 rounded-[8px] border border-white/10 bg-white/[0.035]">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-white/10 px-4 py-4">
        <div className="min-w-0">
          <h3 className="text-base font-semibold text-white">{group.title}</h3>
          <p className="mt-1 text-sm text-slate-500">{group.subtitle}</p>
        </div>
        <div className="grid grid-cols-4 gap-2 text-center">
          <div className="rounded-[6px] bg-black/20 px-3 py-2">
            <p className="font-mono text-sm text-slate-100">{group.rows.length}</p>
            <p className="text-[11px] text-slate-500">總筆數</p>
          </div>
          <div className="rounded-[6px] bg-black/20 px-3 py-2">
            <p className="font-mono text-sm text-cyan-100">{open}</p>
            <p className="text-[11px] text-slate-500">開倉</p>
          </div>
          <div className="rounded-[6px] bg-black/20 px-3 py-2">
            <p className="font-mono text-sm text-orange-200">{unfilled}</p>
            <p className="text-[11px] text-slate-500">未成交</p>
          </div>
          <div className="rounded-[6px] bg-black/20 px-3 py-2">
            <p className="font-mono text-sm text-amber-100">{due || winning}</p>
            <p className="text-[11px] text-slate-500">{due ? "待驗證" : "已命中"}</p>
          </div>
        </div>
      </div>

      {!group.rows.length ? (
        <p className="px-4 py-8 text-sm text-slate-500">此區目前沒有資料。</p>
      ) : (
        <>
          <div className="hidden min-w-0 overflow-x-auto md:block">
            <table className="w-full min-w-[980px] text-left text-sm">
              <thead className="border-b border-white/10 bg-black/20 text-xs text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">標的</th>
                  <th className="px-4 py-3 font-medium">方向</th>
                  <th className="px-4 py-3 font-medium">信心</th>
                  <th className="px-4 py-3 font-medium">進場 / 停損 / 停利</th>
                  <th className="px-4 py-3 font-medium">風報比</th>
                  <th className="px-4 py-3 font-medium">時程</th>
                  <th className="px-4 py-3 font-medium">狀態</th>
                  <th className="px-4 py-3 font-medium">報酬</th>
                  <th className="px-4 py-3 font-medium">驗證</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {group.rows.map((row) => (
                  <tr key={row.id} className="transition hover:bg-white/[0.045]">
                    <td className="px-4 py-4">
                      <div className="font-semibold text-slate-100">{row.asset}</div>
                      <div className="mt-1 text-xs text-slate-500">
                        {row.question_type.replaceAll("_", " ")}
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <DirectionBadge direction={row.direction} />
                    </td>
                    <td className="px-4 py-4">
                      <ScoreBar row={row} />
                    </td>
                    <td className="px-4 py-4">
                      <dl className="grid grid-cols-[44px_1fr] gap-x-2 gap-y-1 text-xs">
                        <dt className="text-slate-500">進場</dt>
                        <dd className="font-mono text-slate-200">
                          {formatRange(row.entry_zone)}
                        </dd>
                        <dt className="text-slate-500">停損</dt>
                        <dd className="font-mono text-rose-100">
                          {formatValue(row.stop_loss)}
                        </dd>
                        <dt className="text-slate-500">停利</dt>
                        <dd className="font-mono text-emerald-100">
                          {formatRange(row.take_profit)}
                        </dd>
                        <dt className="text-slate-500">失效</dt>
                        <dd
                          className="max-w-56 truncate text-slate-300"
                          title={row.falsification_condition ?? undefined}
                        >
                          {row.falsification_condition ?? "--"}
                        </dd>
                      </dl>
                    </td>
                    <td className="px-4 py-4 font-mono text-slate-100">
                      {formatValue(row.risk_reward)}
                    </td>
                    <td className="px-4 py-4 text-xs text-slate-400">
                      <div>{formatDate(row.logged)}</div>
                      <div className="mt-1 text-slate-600">到 {formatDate(row.horizon_end)}</div>
                    </td>
                    <td className="px-4 py-4">
                      <RowStatus status={row.status} />
                    </td>
                    <td
                      className={`px-4 py-4 font-mono ${
                        (row.return_pct ?? 0) > 0
                          ? "text-emerald-100"
                          : (row.return_pct ?? 0) < 0
                            ? "text-rose-100"
                            : "text-slate-300"
                      }`}
                    >
                      {formatReturn(row.return_pct)}
                    </td>
                    <td className="px-4 py-4 text-xs">
                      <DueLabel row={row} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="grid gap-3 p-3 md:hidden">
            {group.rows.map((row) => (
              <article
                key={row.id}
                className="rounded-[8px] border border-white/10 bg-black/20 p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <h4 className="truncate font-semibold text-white">{row.asset}</h4>
                    <p className="mt-1 text-xs text-slate-500">
                      {row.question_type.replaceAll("_", " ")}
                    </p>
                  </div>
                  <DirectionBadge direction={row.direction} />
                </div>
                <div className="mt-4">
                  <ScoreBar row={row} />
                </div>
                <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <dt className="text-slate-500">進場</dt>
                    <dd className="mt-1 font-mono text-slate-200">
                      {formatRange(row.entry_zone)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">風報比</dt>
                    <dd className="mt-1 font-mono text-slate-100">
                      {formatValue(row.risk_reward)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">報酬</dt>
                    <dd className="mt-1 font-mono text-slate-100">
                      {formatReturn(row.return_pct)}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-slate-500">驗證</dt>
                    <dd className="mt-1">
                      <DueLabel row={row} />
                    </dd>
                  </div>
                  <div className="col-span-2">
                    <dt className="text-slate-500">失效條件</dt>
                    <dd className="mt-1 text-slate-300">
                      {row.falsification_condition ?? "--"}
                    </dd>
                  </div>
                </dl>
                <div className="mt-4 flex items-center justify-between gap-3 border-t border-white/10 pt-3">
                  <RowStatus status={row.status} />
                  <span className="text-xs text-slate-500">
                    {formatDate(row.logged)} - {formatDate(row.horizon_end)}
                  </span>
                </div>
              </article>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

export default function MarketPredictions({ rows }: { rows: PredictionRow[] }) {
  const groups = useMemo<MarketGroup[]>(
    () => [
      {
        id: "tw",
        title: "台股",
        subtitle: "以交易日節奏檢視進出場價位與驗證期限",
        rows: rows.filter((row) => !isCryptoRow(row)),
      },
      {
        id: "crypto",
        title: "加密貨幣",
        subtitle: "適合 24/7 市場的快速風險掃描",
        rows: rows.filter((row) => isCryptoRow(row)),
      },
    ],
    [rows],
  );
  const [activeMarket, setActiveMarket] = useState<MarketId>("tw");
  const [filterMode, setFilterMode] = useState<FilterMode>("all");
  const activeGroup = groups.find((group) => group.id === activeMarket) ?? groups[0];
  // 篩選計數各市場分開計算(切換市場 tab 時顯示該市場自己的數字)
  const activeFilter =
    FILTER_OPTIONS.find((option) => option.id === filterMode) ?? FILTER_OPTIONS[0];
  const visibleGroup = useMemo<MarketGroup>(
    () => ({ ...activeGroup, rows: activeGroup.rows.filter(activeFilter.match) }),
    [activeGroup, activeFilter],
  );

  if (!rows.length) {
    return (
      <div className="rounded-[8px] border border-white/10 bg-white/[0.035] px-4 py-10 text-center text-sm text-slate-500">
        尚未取得預測資料。
      </div>
    );
  }

  return (
    <div className="min-w-0 space-y-3">
      <div className="flex flex-wrap gap-2 rounded-[8px] border border-white/10 bg-black/20 p-2" role="tablist" aria-label="市場分類">
        {groups.map((group) => (
          <button
            key={group.id}
            type="button"
            role="tab"
            aria-selected={activeMarket === group.id}
            onClick={() => setActiveMarket(group.id)}
            className={`min-h-10 rounded-[6px] border px-4 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-cyan-200 focus:ring-offset-2 focus:ring-offset-slate-950 ${
              activeMarket === group.id
                ? "border-cyan-300/40 bg-cyan-300/15 text-cyan-100"
                : "border-transparent text-slate-400 hover:border-white/10 hover:bg-white/[0.045] hover:text-slate-100"
            }`}
          >
            {group.title}
            <span className="ml-2 font-mono text-xs text-slate-500">{group.rows.length}</span>
          </button>
        ))}
        <div
          className="ml-auto flex flex-wrap gap-1"
          role="radiogroup"
          aria-label="驗證狀態篩選"
        >
          {FILTER_OPTIONS.map((option) => {
            const count = activeGroup.rows.filter(option.match).length;
            return (
              <button
                key={option.id}
                type="button"
                role="radio"
                aria-checked={filterMode === option.id}
                onClick={() => setFilterMode(option.id)}
                className={`min-h-10 rounded-[6px] border px-3 text-sm font-medium transition focus:outline-none focus:ring-2 focus:ring-orange-200 focus:ring-offset-2 focus:ring-offset-slate-950 ${
                  filterMode === option.id
                    ? "border-orange-300/40 bg-orange-300/15 text-orange-100"
                    : "border-transparent text-slate-400 hover:border-white/10 hover:bg-white/[0.045] hover:text-slate-100"
                }`}
              >
                {option.label}
                <span className="ml-1.5 font-mono text-xs text-slate-500">
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>
      {!visibleGroup.rows.length && activeGroup.rows.length ? (
        <div className="rounded-[8px] border border-white/10 bg-white/[0.035] px-4 py-10 text-center text-sm text-slate-500">
          {activeGroup.title}目前沒有「{activeFilter.label}」的紀錄。
        </div>
      ) : (
        <MarketTable group={visibleGroup} />
      )}
    </div>
  );
}
