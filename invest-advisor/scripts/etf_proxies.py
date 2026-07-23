"""ETF → 代理標的對照:ETF 沒有「個股新聞」,但它的成分股有。

0050/009816 這類標的搜尋不到個股層級的消息面,報告只能引用大盤通稿,
造成來源看似有 3 條、實際資訊量為零。分析 ETF 時一併 recall 代理標的
(權重最大的成分股 + 對應指數)的新聞,消息面才有可歸因的證據。

純資料模組,無 I/O。對照表要隨成分股權重變化維護,
新增 ETF 時同步更新 references/data-sources.md §3.1。
"""
from __future__ import annotations

import re

TW_SUFFIXES = (".TW", ".TWO")
TW_INDEX = "^TWII"
US_INDEX = "SPY"

# 已知 ETF 的代理標的:權重最大的 1–3 檔成分股 + 市場指數
PROXY_MAP: dict[str, list[str]] = {
    # 市值型(台灣 50 / TOP50):台積電權重逾三成,新聞幾乎等同 ETF 的消息面
    "0050.TW": ["2330.TW", "2317.TW", TW_INDEX],
    "009816.TW": ["2330.TW", "2317.TW", TW_INDEX],
    "006208.TW": ["2330.TW", TW_INDEX],
    # 高股息型:成分分散,以金融/電子高息代表 + 大盤為錨
    "0056.TW": ["2308.TW", "2454.TW", TW_INDEX],
    "00918.TW": ["2308.TW", "2382.TW", TW_INDEX],
    "00919.TW": ["2330.TW", "2308.TW", TW_INDEX],
    "00878.TW": ["2412.TW", "2882.TW", TW_INDEX],
    # 海外科技型:持股為美股巨頭,對照美股指數與權值
    "009824.TW": ["NVDA", "MSFT", US_INDEX],
    "00980A.TW": ["NVDA", "MSFT", US_INDEX],
    "00981A.TW": ["2330.TW", TW_INDEX],
}

# 台股 ETF 代碼:00 開頭的 4–6 位數字,可帶一位英文級別碼(如 00980A)
_TW_ETF_CODE = re.compile(r"^00\d{2,4}[A-Z]?$")
_US_ETF_TICKERS = frozenset({"SPY", "QQQ", "VOO", "VTI", "IVV", "DIA", "ARKK"})


def normalize(symbol: str) -> str:
    return (symbol or "").strip().upper()


def is_etf(symbol: str) -> bool:
    """判斷是否為 ETF(台股以代碼規則,美股以白名單)。"""
    sym = normalize(symbol)
    if not sym:
        return False
    for suffix in TW_SUFFIXES:
        if sym.endswith(suffix):
            return bool(_TW_ETF_CODE.match(sym[: -len(suffix)]))
    return sym in _US_ETF_TICKERS


def proxies_for(symbol: str) -> list[str]:
    """ETF 的代理標的清單;非 ETF 或已是指數本身回傳空清單。"""
    sym = normalize(symbol)
    if sym in PROXY_MAP:
        return [p for p in PROXY_MAP[sym] if p != sym]
    if not is_etf(sym):
        return []
    if sym.endswith(TW_SUFFIXES):
        return [TW_INDEX]
    return [US_INDEX] if sym != US_INDEX else []
