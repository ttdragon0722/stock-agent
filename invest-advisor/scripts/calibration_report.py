"""Calibration & performance report (Layer 2): is the scoring system honest?

Joins predictions.jsonl with outcomes.jsonl and produces a Markdown report:
  - confidence calibration table + Brier score vs always-50 baseline
  - recommendation-score monotonicity (higher score -> higher return?)
  - market-regime split (bull / bear / sideways by benchmark window return)

Calibration uses only resolved WIN/LOSS trades; return stats also include FLAT.

Usage:
  python calibration_report.py
  python calibration_report.py --out data/reports/custom.md
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

import common

CONF_BUCKETS = [(0, 50), (50, 60), (60, 70), (70, 80), (80, 90), (90, 101)]
REC_BUCKETS = [(80, 101), (60, 80), (40, 60), (1, 40)]
REGIME_THRESHOLD_PCT = 3.0


# ------------------------------------------------------------ stats (pure)

def brier_score(pairs: list[tuple[float, int]]) -> float | None:
    """pairs: (confidence in [0,1], outcome 0/1). Lower is better."""
    if not pairs:
        return None
    return round(sum((c - o) ** 2 for c, o in pairs) / len(pairs), 4)


def bucket_label(value: float, buckets: list[tuple[int, int]]) -> str | None:
    for lo, hi in buckets:
        if lo <= value < hi:
            return f"[{lo}-{hi - 1}]"
    return None


def confidence_calibration(rows: list[dict]) -> list[dict]:
    """rows: joined records with confidence_score + status WIN/LOSS."""
    table = []
    for lo, hi in CONF_BUCKETS:
        in_bucket = [r for r in rows if lo <= r["confidence_score"] < hi]
        wins = sum(1 for r in in_bucket if r["status"] == "WIN")
        table.append({
            "bucket": f"[{lo}-{hi - 1}]",
            "n": len(in_bucket),
            "avg_confidence": round(sum(r["confidence_score"] for r in in_bucket)
                                    / len(in_bucket), 1) if in_bucket else None,
            "actual_win_rate": round(wins / len(in_bucket) * 100, 1)
            if in_bucket else None,
        })
    return table


def recommendation_monotonicity(rows: list[dict]) -> list[dict]:
    """rows: records with recommendation_score + return_pct."""
    table = []
    for lo, hi in REC_BUCKETS:
        in_bucket = [r for r in rows
                     if lo <= r["recommendation_score"] < hi
                     and r.get("return_pct") is not None]
        rets = [r["return_pct"] for r in in_bucket]
        table.append({
            "bucket": f"[{lo}-{hi - 1}]",
            "n": len(in_bucket),
            "avg_return_pct": round(sum(rets) / len(rets), 2) if rets else None,
        })
    return table


def classify_regime(benchmark_return_pct: float | None) -> str:
    if benchmark_return_pct is None:
        return "unknown"
    if benchmark_return_pct >= REGIME_THRESHOLD_PCT:
        return "bull"
    if benchmark_return_pct <= -REGIME_THRESHOLD_PCT:
        return "bear"
    return "sideways"


def regime_split(rows: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(classify_regime(r.get("benchmark_return_pct")), []).append(r)
    table = []
    for regime in ("bull", "bear", "sideways", "unknown"):
        rs = groups.get(regime, [])
        wl = [r for r in rs if r["status"] in ("WIN", "LOSS")]
        wins = sum(1 for r in wl if r["status"] == "WIN")
        table.append({
            "regime": regime, "n": len(rs),
            "win_rate": round(wins / len(wl) * 100, 1) if wl else None,
        })
    return table


# --------------------------------------------------------------- rendering

def md_table(rows: list[dict]) -> str:
    if not rows:
        return "_no data_"
    headers = list(rows[0].keys())
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows:
        lines.append("| " + " | ".join(
            "—" if r[h] is None else str(r[h]) for h in headers) + " |")
    return "\n".join(lines)


def build_report(joined: list[dict], now_iso: str) -> str:
    resolved_wl = [r for r in joined if r["status"] in ("WIN", "LOSS")]
    with_returns = [r for r in joined
                    if r["status"] in ("WIN", "LOSS", "FLAT",
                                       "RESOLVED_DIRECTIONAL")]
    pairs = [(r["confidence_score"] / 100, 1 if r["status"] == "WIN" else 0)
             for r in resolved_wl]
    baseline_pairs = [(0.5, o) for _, o in pairs]
    brier = brier_score(pairs)
    baseline = brier_score(baseline_pairs)

    versions = sorted({r.get("rubric_version") or "?" for r in joined})
    sections = [
        f"# Calibration Report — {now_iso}",
        f"- 樣本:總預測 {len(joined)} 筆,已判定 WIN/LOSS {len(resolved_wl)} 筆",
        f"- rubric 版本:{', '.join(versions)}",
        "",
        "## 1. 信心校準(Confidence Calibration)",
        "> 各信心分桶的實際勝率應接近平均信心;實際勝率明顯低於信心 = 過度自信。",
        "",
        md_table(confidence_calibration(resolved_wl)),
        "",
        f"- **Brier Score:{brier if brier is not None else '—'}**"
        f"(baseline 永遠輸出 50 分:{baseline if baseline is not None else '—'};"
        f"必須顯著低於 baseline 分數才有資訊量)",
        "",
        "## 2. 推薦指數單調性(Monotonicity)",
        "> 高推薦分桶的平均報酬應高於低分桶;無單調關係 = rubric 需重新設計。",
        "",
        md_table(recommendation_monotonicity(with_returns)),
        "",
        "## 3. 市場 Regime 分層",
        f"> 以 benchmark 同窗報酬 ±{REGIME_THRESHOLD_PCT}% 劃分。"
        "只在牛市贏 = 沒有超額能力。",
        "",
        md_table(regime_split(joined)),
        "",
        "## 4. 統計注意事項",
        "- WIN/LOSS 樣本 < 50 時所有結論僅供參考(95% CI 極寬)。",
        "- 多維度同時檢視時,個別維度「碰巧顯著」的機率上升,解讀保守。",
        "- 發現系統性偏差 → 調整 references/scoring-rubric.md 並遞增版本號。",
    ]
    if len(resolved_wl) < 50:
        sections.insert(3, f"\n> ⚠️ **樣本不足**:已判定僅 {len(resolved_wl)} 筆"
                           f"(建議 ≥ 50),以下統計僅供趨勢參考。")
    return "\n".join(sections) + "\n"


def join_records(predictions: list[dict], outcomes: list[dict]) -> list[dict]:
    """Merge prediction fields into outcome records (new dicts)."""
    pred_by_id = {p.get("id"): p for p in predictions}
    joined = []
    for o in outcomes:
        p = pred_by_id.get(o["id"], {})
        merged = {**p, **o}
        if "confidence_score" in merged and "recommendation_score" in merged:
            joined.append(merged)
    return joined


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", default=None)
    parser.add_argument("--outcomes", default=None)
    parser.add_argument("--out", default=None, help="output .md path")
    args = parser.parse_args()

    predictions = common.read_jsonl(args.predictions or common.PREDICTIONS_FILE)
    outcomes = common.read_jsonl(args.outcomes or common.OUTCOMES_FILE)
    if not outcomes:
        common.eprint("No outcomes yet — run verify_predictions.py first.")
        return 1

    now = datetime.now(timezone.utc)
    report = build_report(join_records(predictions, outcomes),
                          now.strftime("%Y-%m-%d"))
    out_path = args.out or (common.REPORTS_DIR /
                            f"{now.strftime('%Y-%m-%d')}_calibration.md")
    out_path = str(out_path)
    common.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    common.eprint(f"Report written to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
