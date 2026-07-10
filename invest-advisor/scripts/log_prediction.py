"""Append one prediction record to data/predictions.jsonl (append-only log).

Performs Layer-3 format assertions BEFORE writing: schema validation, price
ordering, R:R computation. Rejects malformed records — fail fast.

Usage:
  python log_prediction.py --file pred.json
  echo '{...}' | python log_prediction.py
"""
from __future__ import annotations

import argparse
import json
import sys

import common

ASSET_TYPES = {"stock", "crypto"}
QUESTION_TYPES = {"Q1_short_entry", "Q2_long_hold", "Q3_screener",
                  "Q4_levels", "Q5_allocation"}
DIRECTIONS = {"long", "short", "neutral"}
MIN_RR = 1.5

REQUIRED_FIELDS = {
    "asset": str,
    "asset_type": str,
    "question_type": str,
    "direction": str,
    "recommendation_score": (int, float),
    "confidence_score": (int, float),
    "price_at_analysis": (int, float),
    "horizon_days": (int, float),
    "falsification_condition": str,
    "thesis_summary": str,
}
# Q1 (and any record carrying a trade plan) additionally requires these:
TRADE_PLAN_FIELDS = ("entry_zone", "stop_loss", "take_profit")


def compute_rr(direction: str, entry_zone: list, stop_loss: float,
               take_profit: list) -> float:
    """R:R against TP1, measured from entry-zone midpoint."""
    entry_mid = (entry_zone[0] + entry_zone[1]) / 2
    tp1 = take_profit[0]
    if direction == "long":
        risk, reward = entry_mid - stop_loss, tp1 - entry_mid
    else:
        risk, reward = stop_loss - entry_mid, entry_mid - tp1
    if risk <= 0:
        raise ValueError("risk <= 0: stop_loss on the wrong side of entry")
    return round(reward / risk, 2)


def validate_prediction(rec: dict) -> list[str]:
    """Return a list of validation errors (empty = valid). Pure function."""
    errors: list[str] = []
    for field, typ in REQUIRED_FIELDS.items():
        if field not in rec:
            errors.append(f"missing field: {field}")
        elif not isinstance(rec[field], typ) or (
                typ is str and not str(rec[field]).strip()):
            errors.append(f"invalid {field}: {rec[field]!r}")
    if errors:
        return errors

    if rec["asset_type"] not in ASSET_TYPES:
        errors.append(f"asset_type must be one of {sorted(ASSET_TYPES)}")
    if rec["question_type"] not in QUESTION_TYPES:
        errors.append(f"question_type must be one of {sorted(QUESTION_TYPES)}")
    if rec["direction"] not in DIRECTIONS:
        errors.append(f"direction must be one of {sorted(DIRECTIONS)}")
    for score_field in ("recommendation_score", "confidence_score"):
        if not 1 <= rec[score_field] <= 100:
            errors.append(f"{score_field} must be 1-100")
    if rec["price_at_analysis"] <= 0:
        errors.append("price_at_analysis must be > 0")
    if rec["horizon_days"] <= 0:
        errors.append("horizon_days must be > 0")

    has_plan = any(f in rec for f in TRADE_PLAN_FIELDS)
    needs_plan = (rec["question_type"] == "Q1_short_entry"
                  and rec["direction"] in ("long", "short"))
    if needs_plan and not all(f in rec for f in TRADE_PLAN_FIELDS):
        errors.append("Q1 long/short requires entry_zone, stop_loss, take_profit")
    elif has_plan:
        errors.extend(_validate_trade_plan(rec))
    return errors


def _validate_trade_plan(rec: dict) -> list[str]:
    errors: list[str] = []
    ez, sl, tp = (rec.get("entry_zone"), rec.get("stop_loss"),
                  rec.get("take_profit"))
    if (not isinstance(ez, list) or len(ez) != 2
            or not all(isinstance(x, (int, float)) and x > 0 for x in ez)
            or ez[0] > ez[1]):
        errors.append("entry_zone must be [low, high] with low <= high")
    if not isinstance(sl, (int, float)) or sl <= 0:
        errors.append("stop_loss must be a positive number")
    if (not isinstance(tp, list) or not tp
            or not all(isinstance(x, (int, float)) and x > 0 for x in tp)):
        errors.append("take_profit must be a non-empty list of prices")
    if errors:
        return errors

    direction = rec["direction"]
    if direction == "long" and not (sl < ez[0] and tp[0] > ez[1]):
        errors.append(f"long ordering violated: need SL {sl} < entry_low "
                      f"{ez[0]} and TP1 {tp[0]} > entry_high {ez[1]}")
    if direction == "short" and not (sl > ez[1] and tp[0] < ez[0]):
        errors.append(f"short ordering violated: need SL {sl} > entry_high "
                      f"{ez[1]} and TP1 {tp[0]} < entry_low {ez[0]}")
    if direction == "long" and sorted(tp) != tp:
        errors.append("long take_profit list must be ascending")
    if direction == "short" and sorted(tp, reverse=True) != tp:
        errors.append("short take_profit list must be descending")
    return errors


def normalize_prediction(rec: dict, now_ts: int,
                         existing_ids: set[str]) -> dict:
    """Return a NEW record with auto-fields added (input not mutated)."""
    out = dict(rec)
    out.setdefault("timestamp", common.iso_utc(now_ts))
    out["logged_at"] = common.iso_utc(now_ts)
    out["rubric_version"] = rec.get("rubric_version", common.RUBRIC_VERSION)

    if all(f in out for f in TRADE_PLAN_FIELDS):
        out["risk_reward"] = compute_rr(out["direction"], out["entry_zone"],
                                        out["stop_loss"], out["take_profit"])
        out["rr_below_min"] = out["risk_reward"] < MIN_RR

    if "id" not in out:
        date_part = out["timestamp"][:10]
        q_part = out["question_type"].split("_")[0].lower()
        base = f"{date_part}-{out['asset'].upper()}-{q_part}"
        candidate, suffix = base, 1
        while candidate in existing_ids:
            suffix += 1
            candidate = f"{base}-{suffix}"
        out["id"] = candidate
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", help="path to a JSON file (else reads stdin)")
    parser.add_argument("--log", default=None,
                        help="override predictions.jsonl path")
    args = parser.parse_args()

    try:
        raw = (open(args.file, encoding="utf-8-sig").read() if args.file
               else sys.stdin.read())
        rec = json.loads(raw.lstrip("﻿"))
    except (OSError, json.JSONDecodeError) as e:
        common.eprint(f"ERROR: cannot parse input JSON: {e}")
        return 1

    errors = validate_prediction(rec)
    if errors:
        common.eprint("VALIDATION FAILED:")
        for e in errors:
            common.eprint(f"  - {e}")
        return 1

    log_path = args.log or common.PREDICTIONS_FILE
    existing_ids = {r.get("id") for r in common.read_jsonl(log_path)}
    normalized = normalize_prediction(rec, common.utc_now(), existing_ids)

    if normalized.get("rr_below_min"):
        common.eprint(f"WARN: R:R {normalized['risk_reward']} < {MIN_RR} — "
                      f"the report should have advised skipping this trade.")

    common.append_jsonl(log_path, normalized)
    common.print_json({"logged": normalized["id"],
                       "risk_reward": normalized.get("risk_reward"),
                       "file": str(log_path)})
    return 0


if __name__ == "__main__":
    sys.exit(main())
