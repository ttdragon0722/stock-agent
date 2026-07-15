"""Outcome verification (Layer 1): resolve predictions against actual price paths.

Reads data/predictions.jsonl (append-only source of truth) and local OHLCV,
writes data/outcomes.jsonl (DERIVED file, fully rebuilt each run).

Judgment rules (conservative by design — see references/scoring-rubric.md §V):
  - Evaluation starts from the first bar OPENING at/after analysis time.
  - Long fills when a bar's low trades into the entry zone (fill = entry_high,
    or the open if it gapped inside/below the zone).
  - If a bar touches BOTH stop-loss and TP1, it counts as LOSS.
  - If a bar OPENS beyond the stop, the exit books at the open (gap slippage),
    not at the stop price — losses are never understated.
  - Never filled by horizon end -> NOT_FILLED (excluded from win rate).
  - Filled but no touch by horizon end -> FLAT, booked at final close
    (open positions are never dropped — survivorship-bias rule).
  - Directional calls (no trade plan) must clear a horizon-scaled noise band
    to count as correct/incorrect; drifts inside the band are excluded from
    direction accuracy (judging noise as skill inflates the stats).
  - Q5_allocation and Q3_screened_out records are excluded from headline
    direction accuracy: the former because a single price path cannot
    represent a portfolio, the latter because they are counterfactuals.

Usage:
  python verify_predictions.py            # verify all, print summary
  python verify_predictions.py --fetch    # auto-update needed OHLCV first
"""
from __future__ import annotations

import argparse
import math
import sys

import common

NEUTRAL_BASE_PCT = 5.0   # neutral band at the 30-day reference horizon
NOISE_BASE_PCT = 1.0     # directional noise band at the 14-day reference horizon


def neutral_band_pct(horizon_days: float) -> float:
    """|return| within this band counts as 'correct' for neutral calls.

    Scales with sqrt(horizon) — a 5% band is meaningful at 30 days but far
    too narrow at 180 days. Capped at 15%.
    """
    return round(min(15.0, NEUTRAL_BASE_PCT * math.sqrt(horizon_days / 30)), 2)


def noise_band_pct(horizon_days: float) -> float:
    """Directional calls must drift beyond this band to be judged at all.

    Scales with sqrt(horizon), capped at 3%: at 14 days a +0.4% drift is
    market noise, not a confirmed long call.
    """
    return round(min(3.0, NOISE_BASE_PCT * math.sqrt(horizon_days / 14)), 2)


# ------------------------------------------------------------ core (pure)

def evaluate_prediction(pred: dict, bars: list[dict],
                        bench_bars: list[dict], now_ts: int) -> dict:
    """Resolve one prediction against a daily price path. Pure function."""
    analysis_ts = common.iso_to_epoch(pred["timestamp"])
    horizon_end = analysis_ts + int(pred["horizon_days"]) * 86400
    window = [b for b in bars if analysis_ts <= b["ts"] <= min(now_ts, horizon_end)]
    expired = now_ts >= horizon_end

    out = {
        "id": pred["id"], "asset": pred["asset"],
        "asset_type": pred.get("asset_type"),
        "question_type": pred.get("question_type"),
        "direction": pred["direction"],
        "recommendation_score": pred.get("recommendation_score"),
        "confidence_score": pred.get("confidence_score"),
        "rubric_version": pred.get("rubric_version"),
        "status": "PENDING", "filled": False, "fill_price": None,
        "exit_price": None, "return_pct": None, "r_multiple": None,
        "direction_correct": None, "benchmark_return_pct": None,
        "excess_return_pct": None, "bars_evaluated": len(window),
        "verified_at": common.iso_utc(now_ts),
    }

    if not window:
        out["status"] = "NO_DATA" if expired else "PENDING"
        return out

    end_close = window[-1]["close"]
    ref_price = pred["price_at_analysis"]
    drift_pct = (end_close - ref_price) / ref_price * 100

    if bench_bars:
        bwindow = [b for b in bench_bars
                   if analysis_ts <= b["ts"] <= min(now_ts, horizon_end)]
        if len(bwindow) >= 2:
            out["benchmark_return_pct"] = round(
                (bwindow[-1]["close"] - bwindow[0]["close"])
                / bwindow[0]["close"] * 100, 2)

    has_plan = all(k in pred for k in ("entry_zone", "stop_loss", "take_profit"))
    if pred["direction"] == "neutral" or not has_plan:
        _resolve_directional_only(out, pred, drift_pct, expired)
    else:
        _resolve_trade_plan(out, pred, window, end_close, expired)

    if out["return_pct"] is not None and out["benchmark_return_pct"] is not None:
        out["excess_return_pct"] = round(
            out["return_pct"] - out["benchmark_return_pct"], 2)
    return out


def _resolve_directional_only(out: dict, pred: dict, drift_pct: float,
                              expired: bool) -> None:
    """No trade plan (Q2/Q3/Q5 or neutral): judge direction at horizon end."""
    out["return_pct"] = round(drift_pct, 2)
    if not expired:
        out["status"] = "PENDING"
        return
    horizon = float(pred["horizon_days"])
    out["status"] = "RESOLVED_NEUTRAL" if pred["direction"] == "neutral" \
        else "RESOLVED_DIRECTIONAL"
    if pred["direction"] == "neutral":
        band = neutral_band_pct(horizon)
        out["neutral_band_pct"] = band
        out["direction_correct"] = abs(drift_pct) <= band
        return
    band = noise_band_pct(horizon)
    out["noise_band_pct"] = band
    if abs(drift_pct) <= band:
        # drift indistinguishable from noise — excluded from accuracy stats
        out["direction_correct"] = None
        out["within_noise_band"] = True
    elif pred["direction"] == "long":
        out["direction_correct"] = drift_pct > 0
    else:
        out["direction_correct"] = drift_pct < 0


def _resolve_trade_plan(out: dict, pred: dict, window: list[dict],
                        end_close: float, expired: bool) -> None:
    direction = pred["direction"]
    entry_lo, entry_hi = pred["entry_zone"]
    sl, tp1 = pred["stop_loss"], pred["take_profit"][0]
    is_long = direction == "long"

    filled, fill_price = False, None
    for bar in window:
        if not filled:
            if is_long and bar["low"] <= entry_hi:
                filled, fill_price = True, min(bar["open"], entry_hi)
            elif not is_long and bar["high"] >= entry_lo:
                filled, fill_price = True, max(bar["open"], entry_lo)
        if not filled:
            continue
        hit_sl = bar["low"] <= sl if is_long else bar["high"] >= sl
        hit_tp = bar["high"] >= tp1 if is_long else bar["low"] <= tp1
        if hit_sl:  # both-touched -> LOSS (conservative)
            # gap slippage: a bar opening beyond the stop exits at the open
            exit_price = min(bar["open"], sl) if is_long else max(bar["open"], sl)
            _book(out, direction, fill_price, exit_price, "LOSS", sl_price=sl)
            return
        if hit_tp:
            _book(out, direction, fill_price, tp1, "WIN", sl_price=sl)
            return

    if not filled:
        out["status"] = "NOT_FILLED" if expired else "PENDING"
        return
    _book(out, direction, fill_price, end_close,
          "FLAT" if expired else "OPEN", sl_price=sl)


def _book(out: dict, direction: str, fill: float, exit_price: float,
          status: str, sl_price: float) -> None:
    is_long = direction == "long"
    pnl = (exit_price - fill) if is_long else (fill - exit_price)
    risk = (fill - sl_price) if is_long else (sl_price - fill)
    out.update({
        "status": status, "filled": True,
        "fill_price": round(fill, 4), "exit_price": round(exit_price, 4),
        "return_pct": round(pnl / fill * 100, 2),
        "r_multiple": round(pnl / risk, 2) if risk > 0 else None,
        "direction_correct": pnl > 0,
    })


RESOLVED_STATUSES = ("WIN", "LOSS", "FLAT",
                     "RESOLVED_DIRECTIONAL", "RESOLVED_NEUTRAL")


def _is_counterfactual(o: dict) -> bool:
    return o.get("question_type") == "Q3_screened_out"


def _is_allocation(o: dict) -> bool:
    return o.get("question_type") == "Q5_allocation"


def _mean(xs: list) -> float | None:
    return round(sum(xs) / len(xs), 3) if xs else None


def _screener_funnel(outcomes: list[dict]) -> dict | None:
    """Picked (Q3_screener) vs rejected (Q3_screened_out) resolved returns —
    the only way to know whether the screening funnel adds value."""
    def resolved_returns(rows):
        return [o["return_pct"] for o in rows
                if o["status"] in RESOLVED_STATUSES
                and o.get("return_pct") is not None]

    rejected = resolved_returns([o for o in outcomes if _is_counterfactual(o)])
    if not rejected:
        return None
    picked = resolved_returns(
        [o for o in outcomes if o.get("question_type") == "Q3_screener"])
    funnel = {
        "picked_n": len(picked), "picked_avg_return_pct": _mean(picked),
        "rejected_n": len(rejected), "rejected_avg_return_pct": _mean(rejected),
    }
    if picked:
        funnel["edge_pct"] = round(funnel["picked_avg_return_pct"]
                                   - funnel["rejected_avg_return_pct"], 3)
    return funnel


def summarize(outcomes: list[dict]) -> dict:
    """Aggregate performance stats. Pure function.

    Counterfactual (Q3_screened_out) and allocation (Q5) records are excluded
    from headline accuracy/excess stats; see module docstring.
    """
    by_status: dict[str, int] = {}
    for o in outcomes:
        by_status[o["status"]] = by_status.get(o["status"], 0) + 1

    core = [o for o in outcomes
            if not _is_counterfactual(o) and not _is_allocation(o)]
    wins = sum(1 for o in core if o["status"] == "WIN")
    losses = sum(1 for o in core if o["status"] == "LOSS")
    resolved_trades = [o for o in core
                       if o["status"] in ("WIN", "LOSS", "FLAT")
                       and o["r_multiple"] is not None]
    directional = [o for o in core if o["direction_correct"] is not None]
    excess = [o["excess_return_pct"] for o in core
              if o["excess_return_pct"] is not None
              and o["status"] in RESOLVED_STATUSES]

    stats = {
        "total": len(outcomes),
        "by_status": by_status,
        "win_rate": round(wins / (wins + losses), 3) if wins + losses else None,
        "expectancy_r": _mean([o["r_multiple"] for o in resolved_trades]),
        "direction_accuracy": (
            round(sum(1 for o in directional if o["direction_correct"])
                  / len(directional), 3) if directional else None),
        "avg_excess_return_pct": _mean(excess),
        "noise_band_excluded": sum(1 for o in core
                                   if o.get("within_noise_band")),
        "sample_warning": (
            "n < 50: statistics not yet meaningful (95% CI is very wide)"
            if wins + losses < 50 else None),
    }
    funnel = _screener_funnel(outcomes)
    if funnel:
        stats["screener_funnel"] = funnel
    allocation_n = sum(1 for o in outcomes if _is_allocation(o))
    if allocation_n:
        stats["allocation_excluded_n"] = allocation_n
    return stats


def summarize_by_market(outcomes: list[dict]) -> dict:
    """全體 + 台股/加密貨幣分開的統計。Pure function.

    缺 asset_type 的舊紀錄只計入 all,不歸入任一市場。
    """
    return {
        "all": summarize(outcomes),
        "stock": summarize(
            [o for o in outcomes if o.get("asset_type") == "stock"]),
        "crypto": summarize(
            [o for o in outcomes if o.get("asset_type") == "crypto"]),
    }


# ---------------------------------------------------------------------- io

def needed_symbols(predictions: list[dict]) -> set[tuple[str, str]]:
    """(canonical symbol, asset_type) pairs required to verify, incl. benchmarks."""
    pairs = set()
    for pred in predictions:
        asset_type = pred.get("asset_type", "stock")
        symbol = pred["asset"].upper()
        if asset_type == "crypto" and "USDT" not in symbol:
            symbol += "USDT"
        pairs.add((symbol, asset_type))
        bench = common.BENCHMARK_BY_ASSET_TYPE.get(asset_type)
        if bench:
            pairs.add((bench, asset_type))
    return pairs


def auto_fetch(con, predictions: list[dict]) -> None:
    import fetch_ohlcv
    for symbol, asset_type in sorted(needed_symbols(predictions)):
        try:
            result = fetch_ohlcv.fetch_one(con, symbol, asset_type, "1d", 500)
            common.eprint(f"fetched {symbol}: +{result['fetched_rows']} rows "
                          f"(last bar {result['last_bar']})")
        except Exception as e:  # network errors must not block verification
            common.eprint(f"WARN: fetch failed for {symbol}: {e} — "
                          f"using existing local data")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=None)
    parser.add_argument("--predictions", default=None)
    parser.add_argument("--outcomes", default=None)
    parser.add_argument("--fetch", action="store_true",
                        help="auto-update OHLCV for all needed symbols first")
    args = parser.parse_args()

    predictions = common.read_jsonl(args.predictions or common.PREDICTIONS_FILE)
    if not predictions:
        common.eprint("No predictions logged yet.")
        return 0

    now = common.utc_now()
    con = common.get_market_db(args.db)
    if args.fetch:
        auto_fetch(con, predictions)
    bar_cache: dict[str, list[dict]] = {}

    def bars_for(symbol: str) -> list[dict]:
        key = symbol.upper()
        if key not in bar_cache:
            bar_cache[key] = common.load_bars(con, key, "1d")
        return bar_cache[key]

    outcomes, missing = [], set()
    try:
        for pred in predictions:
            symbol = pred["asset"].upper()
            if pred.get("asset_type") == "crypto" and "USDT" not in symbol:
                symbol += "USDT"
            bars = bars_for(symbol)
            bench_symbol = common.BENCHMARK_BY_ASSET_TYPE.get(
                pred.get("asset_type", "stock"))
            bench = bars_for(bench_symbol) if bench_symbol else []
            if not bars:
                missing.add(symbol)
            if bench_symbol and not bench:
                missing.add(bench_symbol)
            outcomes.append(evaluate_prediction(pred, bars, bench, now))
    finally:
        con.close()

    common.write_jsonl(args.outcomes or common.OUTCOMES_FILE, outcomes)
    stats = summarize(outcomes)
    if missing:
        stats["missing_ohlcv"] = sorted(missing)
        common.eprint(f"WARN: no local OHLCV for {sorted(missing)} — "
                      f"run fetch_ohlcv.py, then re-run this script.")
    common.print_json(stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
