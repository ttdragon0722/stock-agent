"""台股籌碼面:三大法人買賣超 + 融資融券(官方 API,免 key)。

來源:
  上市(.TW)  TWSE rwd API,支援逐日回補(T86 / MI_MARGN)
  上櫃(.TWO) TPEx OpenAPI,僅有最新交易日三大法人(無融資融券、無歷史);
             歷史靠每次執行累積入庫
單位:法人買賣超為「股數」;融資融券餘額為「張」。
資料落地 market.db `chips` 表(歷史不變,增量更新),輸出含 5/20 日累計。
解析一律以「欄位名」對照,官方調整欄位結構時 raise 而非靜默錯位;
確認的非交易日記入 non_trading_days 表,避免重複打 API。

Usage:
  python fetch_chips.py --symbol 2330.TW [--days 10]
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import date, timedelta

import common
from common import parse_int

T86_URL = ("https://www.twse.com.tw/rwd/zh/fund/T86"
           "?date={d}&selectType=ALLBUT0999&response=json")
MARGIN_URL = ("https://www.twse.com.tw/rwd/zh/marginTrading/MI_MARGN"
              "?date={d}&selectType=ALL&response=json")
TPEX_3INSTI_URL = "https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading"

POLITE_DELAY_SEC = 2  # TWSE rwd API throttles bursts
DEFAULT_DAYS = 10
SUMMARY_WINDOWS = (5, 20)

# T86 欄位名(以名稱定位,順序無關);外資 = 外陸資(不含自營商)+ 外資自營商
T86_COLUMNS = {
    "code": "證券代號",
    "foreign_ex_dealer": "外陸資買賣超股數(不含外資自營商)",
    "foreign_dealer": "外資自營商買賣超股數",
    "trust": "投信買賣超股數",
    "dealer": "自營商買賣超股數",
    "total": "三大法人買賣超股數",
}
MARGIN_TABLE_TITLE = "融資融券彙總"


def market_for(symbol: str) -> str:
    s = symbol.strip().upper()
    if s.endswith(".TWO"):
        return "tpex"
    if s.endswith(".TW"):
        return "twse"
    raise ValueError(f"chips data only covers .TW/.TWO symbols, got: {symbol}")


def _code(symbol: str) -> str:
    return symbol.strip().upper().split(".")[0]


def _index_map(fields: list[str], wanted: dict[str, str],
               dataset: str) -> dict[str, int]:
    """欄位名 → index;缺任何預期欄位即 raise,防止靜默錯位。"""
    stripped = [str(f).strip() for f in fields]
    missing = [name for name in wanted.values() if name not in stripped]
    if missing:
        raise ValueError(f"{dataset} 欄位結構改變,缺少 {missing},請更新腳本")
    return {key: stripped.index(name) for key, name in wanted.items()}


def parse_t86(payload: dict, code: str) -> dict | None:
    """三大法人個股買賣超(股數),以欄位名定位。"""
    if payload.get("stat") != "OK":
        return None
    idx = _index_map(payload.get("fields") or [], T86_COLUMNS, "T86")
    min_len = max(idx.values()) + 1
    for row in payload.get("data") or []:
        if len(row) < min_len or str(row[idx["code"]]).strip() != code:
            continue
        return {
            "foreign_net": (parse_int(row[idx["foreign_ex_dealer"]])
                            + parse_int(row[idx["foreign_dealer"]])),
            "trust_net": parse_int(row[idx["trust"]]),
            "dealer_net": parse_int(row[idx["dealer"]]),
            "total_net": parse_int(row[idx["total"]]),
        }
    return None


def _margin_table(payload: dict) -> dict | None:
    for table in payload.get("tables") or []:
        if MARGIN_TABLE_TITLE in (table.get("title") or ""):
            return table
    return None


def parse_margin(payload: dict, code: str) -> dict | None:
    """融資融券個股餘額(張)。

    欄位名重複(融資/融券各有「前日餘額」「今日餘額」),依官方格式
    以第一組=融資、第二組=融券;組數不符即 raise。
    """
    if payload.get("stat") != "OK":
        return None
    table = _margin_table(payload)
    if table is None:
        return None
    fields = [str(f).strip() for f in table.get("fields") or []]
    prev_idx = [i for i, f in enumerate(fields) if f == "前日餘額"]
    today_idx = [i for i, f in enumerate(fields) if f == "今日餘額"]
    if len(prev_idx) != 2 or len(today_idx) != 2 or "代號" not in fields:
        raise ValueError("MI_MARGN 欄位結構改變,請更新 parse_margin")
    code_i = fields.index("代號")
    min_len = max(prev_idx[1], today_idx[1]) + 1
    for row in table.get("data") or []:
        if len(row) < min_len or str(row[code_i]).strip() != code:
            continue
        margin_prev, margin_today = parse_int(row[prev_idx[0]]), parse_int(row[today_idx[0]])
        short_prev, short_today = parse_int(row[prev_idx[1]]), parse_int(row[today_idx[1]])
        return {
            "margin_balance": margin_today,
            "margin_change": margin_today - margin_prev,
            "short_balance": short_today,
            "short_change": short_today - short_prev,
        }
    return None


def _normalize_key(k: str) -> str:
    return k.replace(" ", "").lower()


def parse_tpex_3insti(rows: list[dict], code: str) -> tuple[str, dict] | None:
    """TPEx OpenAPI 最新日三大法人;鍵名空白不一致,先正規化再取值。"""
    for row in rows:
        norm = {_normalize_key(k): v for k, v in row.items()}
        if str(norm.get("securitiescompanycode", "")).strip() != code:
            continue
        date_iso = common.roc_to_iso(str(norm["date"]))
        return date_iso, {
            "foreign_net": parse_int(
                norm["foreigninvestorsincludemainlandareainvestors-difference"]),
            "trust_net": parse_int(
                norm["securitiesinvestmenttrustcompanies-difference"]),
            "dealer_net": parse_int(norm["dealers-difference"]),
            "total_net": parse_int(norm["totaldifference"]),
        }
    return None


def should_mark_non_trading(date_iso: str, today_iso: str | None = None) -> bool:
    """僅過去日期可標記為休市;當日「查無資料」可能只是尚未發布。"""
    today = today_iso or date.today().strftime("%Y-%m-%d")
    return date_iso < today


def mark_non_trading(con, market: str, date_iso: str) -> None:
    con.execute("INSERT OR IGNORE INTO non_trading_days (market, date) "
                "VALUES (?, ?)", (market, date_iso))
    con.commit()


def load_non_trading(con, market: str) -> set[str]:
    rows = con.execute("SELECT date FROM non_trading_days WHERE market = ?",
                       (market,)).fetchall()
    return {r[0] for r in rows}


def upsert_chips(con, symbol: str, date_iso: str, values: dict,
                 source: str, fetched_at: int) -> None:
    con.execute(
        "INSERT OR REPLACE INTO chips "
        "(symbol, date, foreign_net, trust_net, dealer_net, total_net, "
        " margin_balance, margin_change, short_balance, short_change, "
        " source, fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (symbol.upper(), date_iso,
         values.get("foreign_net"), values.get("trust_net"),
         values.get("dealer_net"), values.get("total_net"),
         values.get("margin_balance"), values.get("margin_change"),
         values.get("short_balance"), values.get("short_change"),
         source, fetched_at))
    con.commit()


def load_chips(con, symbol: str, limit: int = 40) -> list[dict]:
    cols = ("date", "foreign_net", "trust_net", "dealer_net", "total_net",
            "margin_balance", "margin_change", "short_balance", "short_change")
    rows = con.execute(
        f"SELECT {', '.join(cols)} FROM chips WHERE symbol = ? "
        "ORDER BY date DESC LIMIT ?", (symbol.upper(), limit)).fetchall()
    return [dict(zip(cols, r)) for r in reversed(rows)]


def summarize(rows: list[dict]) -> dict:
    summary = {"days_available": len(rows)}
    for n in SUMMARY_WINDOWS:
        window = rows[-n:]
        for field in ("foreign_net", "trust_net", "total_net"):
            summary[f"{field}_{n}d"] = sum(r[field] or 0 for r in window)
    if rows and rows[-1].get("margin_balance") is not None:
        summary["margin_balance_latest"] = rows[-1]["margin_balance"]
        summary["margin_change_latest"] = rows[-1]["margin_change"]
    return summary


def _recent_weekdays(days: int) -> list[str]:
    out, d = [], date.today()
    while len(out) < days:
        if d.weekday() < 5:
            out.append(d.strftime("%Y-%m-%d"))
        d -= timedelta(days=1)
    return out


def _get_and_sleep(url: str):
    payload = common.http_get_json(url)
    time.sleep(POLITE_DELAY_SEC)
    return payload


def fetch_twse(con, symbol: str, days: int, now: int) -> int:
    """回補最近 days 個平日中缺少或不完整的日期。

    - API 回非 OK → 記入 non_trading_days,之後不再重查
    - 已入庫但 margin 為 NULL 的日期 → 只補抓 MI_MARGN
    """
    code = _code(symbol)
    existing = {r["date"]: r for r in load_chips(con, symbol)}
    skip = load_non_trading(con, "twse")
    fetched = 0
    for date_iso in _recent_weekdays(days):
        if date_iso in skip:
            continue
        row = existing.get(date_iso)
        need_full = row is None
        need_margin = row is not None and row.get("margin_balance") is None
        if not need_full and not need_margin:
            continue
        compact = date_iso.replace("-", "")
        if need_full:
            payload = _get_and_sleep(T86_URL.format(d=compact))
            if payload.get("stat") != "OK":
                # 全市場無資料:過去日期 = 非交易日;當日可能只是尚未發布,
                # 不得永久標記(否則該日資料永遠不會被回補)
                if should_mark_non_trading(date_iso):
                    mark_non_trading(con, "twse", date_iso)
                continue
            t86 = parse_t86(payload, code)
            if t86 is None:  # 交易日但該股無法人資料(停牌等),留待下次
                continue
        else:
            t86 = {k: row[k] for k in
                   ("foreign_net", "trust_net", "dealer_net", "total_net")}
        margin = parse_margin(
            _get_and_sleep(MARGIN_URL.format(d=compact)), code) or {}
        if need_full or margin:
            upsert_chips(con, symbol, date_iso, {**t86, **margin}, "twse", now)
        if need_full:
            fetched += 1
    return fetched


def fetch_tpex(con, symbol: str, now: int) -> int:
    rows = common.http_get_json(TPEX_3INSTI_URL, relax_ssl_strict=True)
    parsed = parse_tpex_3insti(rows, _code(symbol))
    if parsed is None:
        return 0
    date_iso, values = parsed
    upsert_chips(con, symbol, date_iso, values, "tpex", now)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True, help="如 2330.TW / 6488.TWO")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS,
                        help=f"上市回補天數(預設 {DEFAULT_DAYS};上櫃僅最新日)")
    parser.add_argument("--market-db", default=None)
    args = parser.parse_args()

    now = common.utc_now()
    con = common.get_market_db(args.market_db)
    try:
        market = market_for(args.symbol)
        if market == "twse":
            new_days = fetch_twse(con, args.symbol, args.days, now)
        else:
            new_days = fetch_tpex(con, args.symbol, now)
        rows = load_chips(con, args.symbol)
        common.print_json({
            "symbol": args.symbol.upper(), "market": market,
            "new_days_fetched": new_days,
            "as_of": rows[-1]["date"] if rows else None,
            "summary": summarize(rows),
            "daily": rows[-10:],
            "units": {"institutional_net": "股", "margin": "張"},
            "note": ("上櫃無融資融券與歷史回補,累計值以已入庫日數為準"
                     if market == "tpex" else None),
        })
    except ValueError as e:
        common.eprint(f"ERROR: {e}")
        return 1
    except OSError as e:
        common.eprint(f"ERROR: 官方 API 連線失敗,降級處理見 data-sources.md: {e}")
        return 1
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
