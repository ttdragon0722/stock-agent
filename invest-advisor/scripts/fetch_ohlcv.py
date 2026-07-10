"""Incremental OHLCV fetcher -> market.db.

Sources (all free, no API key, stdlib-only):
  crypto : Binance public REST      (1d / 4h / 1w)
  stock  : Yahoo Finance v8 chart API (1d / 1w)

Stocks have NO reliable free 4h history — see references/data-sources.md.

Usage:
  python fetch_ohlcv.py --symbol TSLA,SPY --asset-type stock --timeframe 1d
  python fetch_ohlcv.py --symbol BTC --asset-type crypto --timeframe 4h --days 120
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

import common

BINANCE_INTERVALS = {"1d": "1d", "4h": "4h", "1w": "1w"}
YAHOO_INTERVALS = {"1d": "1d", "1w": "1wk"}
DEFAULT_DAYS = 500
HTTP_TIMEOUT = 30
# 重抓緩衝:Yahoo 盤中即時 bar 的 ts 會漂移(如 05:30:01 而非開盤 01:00:00),
# 需回頭重抓一小段並整段取代,否則同日殘留兩根 ts 不同的 K 線
REFETCH_WINDOW_SEC = {"1d": 3 * 86400, "4h": 86400, "1w": 8 * 86400}


def http_get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as resp:
        return resp.read()


# ------------------------------------------------------------------- crypto

def normalize_crypto_symbol(symbol: str) -> str:
    s = symbol.upper().replace("/", "").replace("-", "")
    return s if "USDT" in s else s + "USDT"


def fetch_binance(symbol: str, timeframe: str, start_ms: int,
                  now_ms: int) -> list[tuple]:
    interval = BINANCE_INTERVALS[timeframe]
    rows: list[tuple] = []
    cursor = start_ms
    fetched_at = common.utc_now()
    while cursor < now_ms:
        params = urllib.parse.urlencode({
            "symbol": symbol, "interval": interval,
            "startTime": cursor, "limit": 1000,
        })
        klines = json.loads(http_get(
            f"https://api.binance.com/api/v3/klines?{params}"))
        if not klines:
            break
        for k in klines:
            rows.append((symbol, timeframe, k[0] // 1000,
                         float(k[1]), float(k[2]), float(k[3]), float(k[4]),
                         float(k[5]), "binance", fetched_at))
        cursor = klines[-1][0] + 1
        if len(klines) < 1000:
            break
    return rows


# ------------------------------------------------------------------- stocks

def parse_yahoo_chart(symbol: str, timeframe: str, payload: dict,
                      min_ts: int) -> list[tuple]:
    """Extract bars from a Yahoo v8 chart response. Pure function."""
    chart = payload.get("chart", {})
    if chart.get("error"):
        raise ValueError(f"yahoo error: {chart['error']}")
    results = chart.get("result") or []
    if not results:
        raise ValueError("yahoo returned no result")
    result = results[0]
    timestamps = result.get("timestamp") or []
    quote = (result.get("indicators", {}).get("quote") or [{}])[0]
    fetched_at = common.utc_now()
    rows: list[tuple] = []
    for i, ts in enumerate(timestamps):
        o, h, l, c = (quote.get(k, [None])[i] if i < len(quote.get(k, []))
                      else None for k in ("open", "high", "low", "close"))
        if None in (o, h, l, c) or ts < min_ts:
            continue  # nulls appear on halted/partial bars
        vols = quote.get("volume", [])
        volume = vols[i] if i < len(vols) and vols[i] is not None else 0
        rows.append((symbol.upper(), timeframe, int(ts),
                     float(o), float(h), float(l), float(c), float(volume),
                     "yahoo", fetched_at))
    return rows


def fetch_yahoo(symbol: str, timeframe: str, min_ts: int,
                now_ts: int) -> list[tuple]:
    params = urllib.parse.urlencode({
        "period1": min_ts, "period2": now_ts,
        "interval": YAHOO_INTERVALS[timeframe],
        "events": "history",
    })
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{urllib.parse.quote(symbol.upper())}?{params}")
    payload = json.loads(http_get(url))
    return parse_yahoo_chart(symbol, timeframe, payload, min_ts)


# -------------------------------------------------------------------- main

def upsert(con, rows: list[tuple]) -> None:
    con.executemany(
        "INSERT OR REPLACE INTO ohlcv "
        "(symbol, timeframe, ts, open, high, low, close, volume, source, fetched_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit()


def last_ts(con, symbol: str, timeframe: str) -> int | None:
    row = con.execute(
        "SELECT MAX(ts) FROM ohlcv WHERE symbol = ? AND timeframe = ?",
        (symbol.upper(), timeframe)).fetchone()
    return row[0] if row and row[0] is not None else None


def fetch_one(con, symbol: str, asset_type: str, timeframe: str,
              days: int) -> dict:
    now = common.utc_now()
    canonical = (normalize_crypto_symbol(symbol) if asset_type == "crypto"
                 else symbol.upper())
    existing = last_ts(con, canonical, timeframe)
    # incremental: re-fetch a small trailing window so canonical bars replace
    # any stored partial bar whose ts drifted (see REFETCH_WINDOW_SEC)
    if existing is not None:
        min_ts = existing - REFETCH_WINDOW_SEC.get(timeframe, 86400)
    else:
        min_ts = now - days * 86400

    if asset_type == "crypto":
        rows = fetch_binance(canonical, timeframe, min_ts * 1000, now * 1000)
    else:
        if timeframe not in YAHOO_INTERVALS:
            raise ValueError(
                f"timeframe '{timeframe}' unsupported for stocks "
                f"(free sources only provide 1d/1w)")
        rows = fetch_yahoo(canonical, timeframe, min_ts, now)

    if not rows:
        if existing is None:
            raise ValueError(f"no data returned for {canonical}")
        return {  # 本地已有資料,無新 K 線(假日/尚未收盤)不是錯誤
            "symbol": canonical, "timeframe": timeframe,
            "fetched_rows": 0, "note": "up_to_date",
            "last_bar": common.iso_utc(existing), "source": "local",
        }
    # 先清掉重抓窗內的舊列再寫入:漂移 ts 的部分 K 線 REPLACE 蓋不掉
    con.execute("DELETE FROM ohlcv WHERE symbol = ? AND timeframe = ? "
                "AND ts >= ?", (canonical, timeframe, min_ts))
    upsert(con, rows)
    total = con.execute(
        "SELECT COUNT(*), MAX(ts) FROM ohlcv WHERE symbol = ? AND timeframe = ?",
        (canonical, timeframe)).fetchone()
    return {
        "symbol": canonical, "timeframe": timeframe,
        "fetched_rows": len(rows), "total_rows": total[0],
        "last_bar": common.iso_utc(total[1]) if total[1] else None,
        "source": rows[0][8],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True,
                        help="comma-separated, e.g. TSLA,SPY or BTC,ETH")
    parser.add_argument("--asset-type", required=True,
                        choices=["stock", "crypto"])
    parser.add_argument("--timeframe", default="1d", choices=["1d", "4h", "1w"])
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
    parser.add_argument("--db", default=None, help="override market.db path")
    args = parser.parse_args()

    con = common.get_market_db(args.db)
    results, failures = [], []
    try:
        for sym in [s.strip() for s in args.symbol.split(",") if s.strip()]:
            try:
                results.append(fetch_one(con, sym, args.asset_type,
                                         args.timeframe, args.days))
            except (urllib.error.URLError, ValueError, json.JSONDecodeError,
                    OSError) as e:
                failures.append({"symbol": sym, "error": str(e)})
                common.eprint(f"ERROR fetching {sym}: {e}")
    finally:
        con.close()

    common.print_json({"ok": results, "failed": failures})
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
