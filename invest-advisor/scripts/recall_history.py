"""Recall past predictions, outcomes, and reports for a symbol (Step 1.5 歷史回顧).

Joins predictions.jsonl with outcomes.jsonl and lists matching reports in
data/reports/, so a new analysis can reference (and must reconcile with)
previous calls on the same symbol.

Also surfaces SYSTEM-WIDE confidence calibration (all symbols): each
confidence bucket's actual win rate, so Step 4 can apply the overconfidence
penalty in scoring-rubric.md §IV instead of letting calibration reports rot
unread in data/reports/.

Usage:
  python recall_history.py --symbol 2330.TW
Output: JSON {symbol, prediction_count, stats, last_direction, predictions,
              reports, calibration}
"""
from __future__ import annotations

import argparse
import sys

import common
from calibration_report import confidence_calibration, join_records

# Calibration feedback thresholds (scoring-rubric.md §IV 校準回饋條款)
MIN_RESOLVED_FOR_FEEDBACK = 20   # below this, calibration is noise
MIN_BUCKET_N = 10                # a bucket needs this many resolved trades
OVERCONFIDENCE_GAP_PP = 15.0     # avg confidence − actual win rate (pp)

# Fields carried into the recalled prediction summary (keep output compact)
PREDICTION_FIELDS = (
    "id", "timestamp", "question_type", "direction",
    "recommendation_score", "confidence_score", "price_at_analysis",
    "horizon_days", "falsification_condition", "thesis_summary",
)


def symbol_matches(a: str, b: str) -> bool:
    return a.strip().upper() == b.strip().upper()


def _filename_variants(symbol: str) -> tuple[str, ...]:
    """Report filenames use '-' instead of '.' (e.g. 00918-TW)."""
    s = symbol.strip().upper()
    return (s, s.replace(".", "-"))


def _part_contains_symbol(part: str, variants: tuple[str, ...]) -> bool:
    """Dash-bounded token match — 'GOOG' must not hit 'GOOGL',
    but 'SOL' must hit the multi-symbol theme 'SOL-ONDO'."""
    padded = f"-{part.upper()}-"
    return any(f"-{v}-" in padded for v in variants)


def match_reports(symbol: str, reports_dir) -> list[str]:
    """Report filenames matching the symbol, newest first (date-prefixed names)."""
    if not reports_dir.is_dir():
        return []
    variants = _filename_variants(symbol)
    matched = [
        p.name for p in reports_dir.glob("*.md")
        if any(_part_contains_symbol(part, variants)
               for part in p.stem.split("_"))
    ]
    return sorted(matched, reverse=True)


def build_history(symbol: str, predictions: list[dict],
                  outcomes: list[dict]) -> dict:
    """Join predictions with outcomes for one symbol; inputs are not mutated."""
    outcome_by_id = {o.get("id"): o for o in outcomes}
    mine = sorted(
        (p for p in predictions if symbol_matches(p.get("asset", ""), symbol)),
        key=lambda p: p.get("timestamp", ""), reverse=True,
    )
    merged = []
    stats: dict[str, int] = {}
    for p in mine:
        outcome = outcome_by_id.get(p.get("id"))
        status = outcome["status"] if outcome else "PENDING"
        stats[status] = stats.get(status, 0) + 1
        merged.append({
            **{k: p.get(k) for k in PREDICTION_FIELDS},
            "outcome": dict(outcome) if outcome else None,
        })
    return {
        "symbol": symbol.strip().upper(),
        "prediction_count": len(merged),
        "stats": stats,
        "last_direction": merged[0]["direction"] if merged else None,
        "last_timestamp": merged[0]["timestamp"] if merged else None,
        "predictions": merged,
    }


def calibration_feedback(predictions: list[dict],
                         outcomes: list[dict]) -> dict:
    """System-wide confidence calibration for Step 4 (pure function).

    Counterfactual (Q3_screened_out) records are excluded — they never carry
    a real confidence commitment.
    """
    joined = [r for r in join_records(predictions, outcomes)
              if r["status"] in ("WIN", "LOSS")
              and r.get("question_type") != "Q3_screened_out"]
    buckets = [b for b in confidence_calibration(joined) if b["n"] > 0]
    feedback: dict = {"resolved_n": len(joined), "buckets": buckets}
    if len(joined) < MIN_RESOLVED_FOR_FEEDBACK:
        feedback["note"] = (f"已判定 {len(joined)} 筆 < "
                            f"{MIN_RESOLVED_FOR_FEEDBACK},樣本不足,"
                            f"不觸發 rubric §IV 校準回饋調整")
        return feedback
    feedback["overconfident_buckets"] = [
        b["bucket"] for b in buckets
        if b["n"] >= MIN_BUCKET_N
        and b["avg_confidence"] is not None
        and b["actual_win_rate"] is not None
        and b["avg_confidence"] - b["actual_win_rate"] >= OVERCONFIDENCE_GAP_PP
    ]
    return feedback


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True,
                        help="asset symbol, e.g. TSLA / 2330.TW / SOLUSDT")
    args = parser.parse_args()

    try:
        predictions = common.read_jsonl(common.PREDICTIONS_FILE)
        outcomes = common.read_jsonl(common.OUTCOMES_FILE)
        history = build_history(args.symbol, predictions, outcomes)
        history["reports"] = match_reports(args.symbol, common.REPORTS_DIR)
        history["calibration"] = calibration_feedback(predictions, outcomes)
    except OSError as e:
        common.eprint(f"ERROR: cannot read history files: {e}")
        return 1
    common.print_json(history)
    return 0


if __name__ == "__main__":
    sys.exit(main())
