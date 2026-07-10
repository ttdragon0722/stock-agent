"""Deterministic technical-analysis computation over local OHLCV.

Reads bars from market.db, computes indicators in pure Python, and prints a
compact JSON object. The LLM reads ONLY this output — it must never compute
indicators itself (see references/ta-checklist.md).

Usage:
  python compute_ta.py --symbol TSLA --timeframe 1d
  python compute_ta.py --symbol BTCUSDT --timeframe 4h --bars 300
"""
from __future__ import annotations

import argparse
import sys

import common

MIN_BARS = 60


# ---------------------------------------------------------------- indicators

def sma(values: list[float], n: int) -> float | None:
    if len(values) < n:
        return None
    return sum(values[-n:]) / n


def ema_series(values: list[float], n: int) -> list[float]:
    if len(values) < n:
        return []
    k = 2 / (n + 1)
    out = [sum(values[:n]) / n]
    for v in values[n:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def ema(values: list[float], n: int) -> float | None:
    series = ema_series(values, n)
    return series[-1] if series else None


def rsi(closes: list[float], n: int = 14) -> float | None:
    """Wilder-smoothed RSI."""
    if len(closes) < n + 1:
        return None
    gains, losses = [], []
    for prev, cur in zip(closes, closes[1:]):
        change = cur - prev
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = sum(gains[:n]) / n
    avg_loss = sum(losses[:n]) / n
    for g, l in zip(gains[n:], losses[n:]):
        avg_gain = (avg_gain * (n - 1) + g) / n
        avg_loss = (avg_loss * (n - 1) + l) / n
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def macd(closes: list[float], fast: int = 12, slow: int = 26,
         signal_n: int = 9) -> dict | None:
    if len(closes) < slow + signal_n:
        return None
    ema_fast = ema_series(closes, fast)
    ema_slow = ema_series(closes, slow)
    offset = slow - fast
    line = [f - s for f, s in zip(ema_fast[offset:], ema_slow)]
    signal = ema_series(line, signal_n)
    if len(signal) < 2:
        return None
    hist = line[-1] - signal[-1]
    prev_hist = line[-2] - signal[-2]
    if prev_hist <= 0 < hist:
        cross = "bullish"
    elif prev_hist >= 0 > hist:
        cross = "bearish"
    else:
        cross = "none"
    return {"line": round(line[-1], 4), "signal": round(signal[-1], 4),
            "hist": round(hist, 4), "cross": cross}


def atr(highs: list[float], lows: list[float], closes: list[float],
        n: int = 14) -> float | None:
    """Wilder-smoothed Average True Range."""
    if len(closes) < n + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i - 1]),
                 abs(lows[i] - closes[i - 1]))
        trs.append(tr)
    value = sum(trs[:n]) / n
    for tr in trs[n:]:
        value = (value * (n - 1) + tr) / n
    return value


def swing_pivots(highs: list[float], lows: list[float],
                 k: int = 3) -> tuple[list[float], list[float]]:
    """Fractal pivots: a bar that is the extreme within +/- k bars."""
    pivot_highs, pivot_lows = [], []
    for i in range(k, len(highs) - k):
        window_h = highs[i - k:i + k + 1]
        window_l = lows[i - k:i + k + 1]
        if highs[i] == max(window_h):
            pivot_highs.append(highs[i])
        if lows[i] == min(window_l):
            pivot_lows.append(lows[i])
    return pivot_highs, pivot_lows


def nearest_levels(price: float, pivot_highs: list[float],
                   pivot_lows: list[float], count: int = 3
                   ) -> tuple[list[float], list[float]]:
    all_levels = {round(p, 4) for p in pivot_highs + pivot_lows}
    supports = sorted((p for p in all_levels if p < price), reverse=True)[:count]
    resistances = sorted(p for p in all_levels if p > price)[:count]
    return supports, resistances


def classify_trend(close: float, s20: float | None, s50: float | None,
                   s200: float | None) -> str:
    if s20 is None or s50 is None:
        return "insufficient_data"
    if s200 is not None:
        if close > s50 > s200 and s20 > s50:
            return "uptrend"
        if close < s50 < s200 and s20 < s50:
            return "downtrend"
        return "range"
    if close > s20 > s50:
        return "uptrend"
    if close < s20 < s50:
        return "downtrend"
    return "range"


# ------------------------------------------------------------------ assembly

def build_snapshot(symbol: str, timeframe: str, bars: list[dict],
                   now_ts: int) -> dict:
    closes = [b["close"] for b in bars]
    highs = [b["high"] for b in bars]
    lows = [b["low"] for b in bars]
    volumes = [b["volume"] or 0.0 for b in bars]
    last = bars[-1]

    s20, s50, s200 = sma(closes, 20), sma(closes, 50), sma(closes, 200)
    atr_val = atr(highs, lows, closes)
    pivot_highs, pivot_lows = swing_pivots(highs, lows)
    supports, resistances = nearest_levels(last["close"], pivot_highs, pivot_lows)

    # 52w window: 252 daily bars / 52 weekly bars, else whatever exists
    lookback = {"1d": 252, "1w": 52}.get(timeframe, len(closes))
    hi_52w = max(highs[-lookback:])
    lo_52w = min(lows[-lookback:])

    vol_sma20 = sma(volumes, 20)
    vol_ratio = round(volumes[-1] / vol_sma20, 2) if vol_sma20 else None

    bar_seconds = {"1d": 86400, "4h": 14400, "1w": 604800}.get(timeframe, 86400)
    stale_bars = max(0.0, (now_ts - last["ts"] - bar_seconds) / bar_seconds)

    return {
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "as_of": common.iso_utc(last["ts"]),
        "stale_bars": round(stale_bars, 1),
        "data_points": len(bars),
        "last_close": last["close"],
        "sma20": round(s20, 4) if s20 else None,
        "sma50": round(s50, 4) if s50 else None,
        "sma200": round(s200, 4) if s200 else None,
        "ema20": round(ema(closes, 20), 4) if len(closes) >= 20 else None,
        "rsi14": round(rsi(closes), 2) if rsi(closes) is not None else None,
        "macd": macd(closes),
        "atr14": round(atr_val, 4) if atr_val else None,
        "atr_pct": round(atr_val / last["close"] * 100, 2) if atr_val else None,
        "vol_ratio_20": vol_ratio,
        "high_52w": hi_52w,
        "low_52w": lo_52w,
        "dist_52w_high_pct": round((last["close"] - hi_52w) / hi_52w * 100, 2),
        "supports": supports,
        "resistances": resistances,
        "trend": classify_trend(last["close"], s20, s50, s200),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", default="1d", choices=["1d", "4h", "1w"])
    parser.add_argument("--bars", type=int, default=300,
                        help="max bars loaded from db (default 300)")
    parser.add_argument("--db", default=None, help="override market.db path")
    args = parser.parse_args()

    con = common.get_market_db(args.db)
    try:
        bars = common.load_bars(con, args.symbol, args.timeframe, limit=args.bars)
    finally:
        con.close()

    if len(bars) < MIN_BARS:
        common.eprint(f"ERROR: only {len(bars)} bars for {args.symbol} "
                      f"{args.timeframe} (need >= {MIN_BARS}). "
                      f"Run fetch_ohlcv.py first.")
        return 1

    snapshot = build_snapshot(args.symbol, args.timeframe, bars, common.utc_now())
    if snapshot["stale_bars"] > 3:
        common.eprint(f"WARN: data is ~{snapshot['stale_bars']} bars stale; "
                      f"re-run fetch_ohlcv.py before using for decisions.")
    common.print_json(snapshot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
