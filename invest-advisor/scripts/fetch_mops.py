"""MOPS 官方一手資料:重大訊息 + 月營收(TWSE/TPEx OpenAPI,免 key)。

官方公告先於媒體且無立場,屬來源分層 A 級(scoring-rubric §來源分層)。
即時性資料,現抓不快取;報告引用時標註查詢時間。

Usage:
  python fetch_mops.py --symbol 2330.TW
"""
from __future__ import annotations

import argparse
import sys

import common

DETAIL_MAX_CHARS = 300

TWSE_BASE = "https://openapi.twse.com.tw/v1/opendata"
TPEX_BASE = "https://www.tpex.org.tw/openapi/v1"


def dataset_urls(symbol: str) -> dict:
    s = symbol.strip().upper()
    if s.endswith(".TWO"):
        return {"announcements": f"{TPEX_BASE}/mopsfin_t187ap04_O",
                "revenue": f"{TPEX_BASE}/mopsfin_t187ap05_O",
                "relax_ssl": True}
    if s.endswith(".TW"):
        return {"announcements": f"{TWSE_BASE}/t187ap04_L",
                "revenue": f"{TWSE_BASE}/t187ap05_L",
                "relax_ssl": False}
    raise ValueError(f"MOPS data only covers .TW/.TWO symbols, got: {symbol}")


def _code(symbol: str) -> str:
    return symbol.strip().upper().split(".")[0]


def _field(row: dict, name: str) -> str:
    """TWSE/TPEx 鍵名有尾端空白與中英文差異,strip 後比對。

    JSON null 一律回空字串,不得讓字面 "None" 洩入報告或炸掉數字解析。
    """
    for k, v in row.items():
        if k.strip() == name:
            return "" if v is None else str(v)
    return ""


def filter_announcements(rows: list[dict], code: str) -> list[dict]:
    """該公司的重大訊息,新→舊;說明截斷避免灌爆報告。"""
    out = []
    for row in rows:
        row_code = (_field(row, "公司代號")
                    or _field(row, "SecuritiesCompanyCode")).strip()
        if row_code != code:
            continue
        detail = _field(row, "說明")
        if len(detail) > DETAIL_MAX_CHARS:
            detail = detail[:DETAIL_MAX_CHARS] + "…"
        out.append({
            "date": common.roc_to_iso(_field(row, "發言日期")),
            "subject": _field(row, "主旨").strip(),
            "matched_clause": _field(row, "符合條款").strip(),
            "fact_date": common.roc_to_iso(_field(row, "事實發生日")),
            "detail": detail,
        })
    return sorted(out, key=lambda a: a["date"], reverse=True)


def parse_revenue(rows: list[dict], code: str) -> dict | None:
    """最新公告月營收(千元)與月增/年增率。"""
    for row in rows:
        if _field(row, "公司代號").strip() != code:
            continue
        return {
            "year_month": common.roc_ym_to_iso(_field(row, "資料年月")),
            "revenue_thousand_twd": common.parse_int(
                _field(row, "營業收入-當月營收")),
            "mom_pct": round(common.parse_float(
                _field(row, "營業收入-上月比較增減(%)")), 2),
            "yoy_pct": round(common.parse_float(
                _field(row, "營業收入-去年同月增減(%)")), 2),
            "cum_yoy_pct": round(common.parse_float(
                _field(row, "累計營業收入-前期比較增減(%)")), 2),
        }
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", required=True, help="如 2330.TW / 6488.TWO")
    args = parser.parse_args()

    try:
        urls = dataset_urls(args.symbol)
        code = _code(args.symbol)
        announcements = filter_announcements(
            common.http_get_json(urls["announcements"],
                                 relax_ssl_strict=urls["relax_ssl"]), code)
        revenue = parse_revenue(
            common.http_get_json(urls["revenue"],
                                 relax_ssl_strict=urls["relax_ssl"]), code)
        common.print_json({
            "symbol": args.symbol.upper(),
            "queried_at": common.iso_utc(common.utc_now()),
            "announcements": announcements,
            "announcement_note": "OpenAPI 僅含近期公告;無資料不代表期間內無公告",
            "monthly_revenue": revenue,
            "source": "MOPS via TWSE/TPEx OpenAPI(官方,A 級來源)",
        })
    except ValueError as e:
        common.eprint(f"ERROR: {e}")
        return 1
    except OSError as e:
        common.eprint(f"ERROR: 官方 API 連線失敗: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
