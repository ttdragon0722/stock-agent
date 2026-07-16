"""List actively-watched symbols for the Q6 daily report (日報總覽模式).

A symbol is "watched" when it has at least one prediction whose horizon has
not yet expired (analysis timestamp + horizon_days >= now). Counterfactual
Q3_screened_out records never put a symbol on the watchlist. Each active
prediction is joined with its latest verification status from outcomes.jsonl
(status "UNVERIFIED" means verify_predictions.py has not covered it yet —
the daily report must run `verify_predictions.py --fetch` first anyway).

Usage:
  python watchlist.py                       # JSON watchlist to stdout
  python watchlist.py --grace-days 3        # keep symbols expired < 3 days ago
  python watchlist.py --analyzed-within 14  # only symbols analyzed recently

Output: JSON {generated_at, count, symbols: [{symbol, asset_type,
  active_predictions, last_analysis, last_question_type, last_direction,
  last_recommendation_score, last_confidence_score, horizon_end,
  predictions: [{id, date, question_type, direction, recommendation_score,
                 horizon_end, status}]}]}
"""
from __future__ import annotations

import argparse
import sys

import common

DAY_SECONDS = 86400
# Counterfactuals are funnel bookkeeping, not positions the user follows.
EXCLUDED_QUESTION_TYPES = {"Q3_screened_out"}


def horizon_end_epoch(rec: dict) -> int:
    return common.iso_to_epoch(rec["timestamp"]) + int(
        rec["horizon_days"] * DAY_SECONDS)


def is_active(rec: dict, now: int, grace_days: int) -> bool:
    if rec.get("question_type") in EXCLUDED_QUESTION_TYPES:
        return False
    return horizon_end_epoch(rec) + grace_days * DAY_SECONDS >= now


def _entry(rec: dict, status_by_id: dict[str, str]) -> dict:
    return {
        "id": rec.get("id"),
        "date": rec["timestamp"][:10],
        "question_type": rec.get("question_type"),
        "direction": rec.get("direction"),
        "recommendation_score": rec.get("recommendation_score"),
        "horizon_end": common.iso_utc(horizon_end_epoch(rec))[:10],
        "status": status_by_id.get(rec.get("id"), "UNVERIFIED"),
    }


def _symbol_summary(symbol: str, records: list[dict],
                    status_by_id: dict[str, str]) -> dict:
    ordered = sorted(records, key=lambda r: r["timestamp"])
    latest = ordered[-1]
    return {
        "symbol": symbol,
        "asset_type": latest.get("asset_type"),
        "active_predictions": len(ordered),
        "last_analysis": latest["timestamp"][:10],
        "last_question_type": latest.get("question_type"),
        "last_direction": latest.get("direction"),
        "last_recommendation_score": latest.get("recommendation_score"),
        "last_confidence_score": latest.get("confidence_score"),
        "horizon_end": max(e["horizon_end"] for e in
                           (_entry(r, status_by_id) for r in ordered)),
        "predictions": [_entry(r, status_by_id) for r in ordered],
    }


def build_watchlist(predictions: list[dict], outcomes: list[dict],
                    now: int, grace_days: int = 0,
                    analyzed_within: int | None = None) -> dict:
    """Pure function: predictions + outcomes -> watchlist document.

    analyzed_within: keep only symbols whose LAST analysis is within N days
    (scope guard for the daily overview — a Q2/Q3 horizon keeps a symbol
    active for months, but a full-pipeline daily run over all of them is
    impractical).
    """
    status_by_id = {o["id"]: o.get("status", "UNVERIFIED")
                    for o in outcomes if o.get("id")}
    by_symbol: dict[str, list[dict]] = {}
    for rec in predictions:
        if not all(k in rec for k in ("asset", "timestamp", "horizon_days")):
            continue
        if is_active(rec, now, grace_days):
            by_symbol.setdefault(rec["asset"].upper(), []).append(rec)

    symbols = sorted(
        (_symbol_summary(sym, recs, status_by_id)
         for sym, recs in by_symbol.items()),
        key=lambda s: (s["last_analysis"], s["symbol"]), reverse=True)
    if analyzed_within is not None:
        cutoff = common.iso_utc(now - analyzed_within * DAY_SECONDS)[:10]
        symbols = [s for s in symbols if s["last_analysis"] >= cutoff]
    return {"generated_at": common.iso_utc(now),
            "count": len(symbols), "symbols": symbols}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--predictions", default=None,
                        help="override predictions.jsonl path")
    parser.add_argument("--outcomes", default=None,
                        help="override outcomes.jsonl path")
    parser.add_argument("--grace-days", type=int, default=0,
                        help="also keep symbols whose horizon expired "
                             "within the last N days")
    parser.add_argument("--analyzed-within", type=int, default=None,
                        help="only symbols whose last analysis is within "
                             "N days (daily-overview scope guard)")
    args = parser.parse_args()
    if args.grace_days < 0 or (args.analyzed_within is not None
                               and args.analyzed_within <= 0):
        common.eprint("ERROR: --grace-days must be >= 0 and "
                      "--analyzed-within must be > 0")
        return 1

    predictions = common.read_jsonl(args.predictions or common.PREDICTIONS_FILE)
    outcomes = common.read_jsonl(args.outcomes or common.OUTCOMES_FILE)
    doc = build_watchlist(predictions, outcomes, common.utc_now(),
                          args.grace_days, args.analyzed_within)
    if doc["count"] == 0:
        common.eprint("NOTE: watchlist is empty — no predictions within "
                      "horizon. Daily overview has nothing to track.")
    common.print_json(doc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
