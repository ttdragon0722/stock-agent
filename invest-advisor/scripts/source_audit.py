"""新聞來源多樣性稽核:把「幾則新聞」換算成「幾個獨立來源」。

同一則通稿被 udn / ETtoday / 中時同時轉載,對判斷的資訊增量趨近於零,
但在 news_cache 裡是三列。本模組以 registrable domain(並合併同集團網域)
去重,產出可直接寫進報告的獨立來源數、來源分層與信心扣分建議。

純函式模組,無 I/O;由 cache_news.py --stats 與 dashboard 共用。
規則對應 references/scoring-rubric.md §IV 與 references/data-sources.md §4.1。
"""
from __future__ import annotations

from urllib.parse import urlparse

# 獨立來源數低於此值 → 視為資料稀缺(rubric §IV −10)
MIN_INDEPENDENT_SOURCES = 3
# 單一網域佔比超過此值 → 視為單邊敘事主導(rubric §IV −5)
DOMINANCE_RATIO = 0.6
# 觸發 dominance 判定所需的最少則數(樣本太小談不上「主導」)
DOMINANCE_MIN_ITEMS = 4
DEFAULT_SINCE_HOURS = 24
MAX_PENALTY = -15

# no_primary_source / no_foreign_source 只提示不扣分:一手數據由
# fetch_chips / fetch_mops 供應(rubric §IV 已另有 −5),外媒缺口只對
# 權值股成立,交由報告判斷,避免同一件事扣兩次。
PENALTIES = {
    "weak_source_count": -10,
    "single_domain_dominant": -5,
}

# 多段 TLD:註冊網域要多取一段(ctee.com.tw 而非 com.tw)
MULTI_PART_TLDS = frozenset({
    "com.tw", "org.tw", "net.tw", "gov.tw", "edu.tw", "idv.tw",
    "com.hk", "com.cn", "com.au", "co.jp", "co.uk", "co.kr",
})

# 同集團/同編輯台:轉載彼此的稿,計為同一個獨立來源
DOMAIN_ALIASES = {
    "wantrich.chinatimes.com": "chinatimes.com",
    "ctee.com.tw": "chinatimes.com",
    "money.udn.com": "udn.com",
    "stock.yahoo.com": "yahoo.com",
    "tw.stock.yahoo.com": "yahoo.com",
    "tw.news.yahoo.com": "yahoo.com",
    "finance.yahoo.com": "yahoo.com",
    "news.cnyes.com": "cnyes.com",
    "invest.cnyes.com": "cnyes.com",
}

# A 級一手來源:交易所、主管機關、公司 IR、ETF 發行商官網
PRIMARY_DOMAINS = frozenset({
    "twse.com.tw", "tpex.org.tw", "taifex.com.tw", "gov.tw", "fsc.gov.tw",
    "mopsfin.twse.com.tw", "isin.twse.com.tw",
    "yuantaetfs.com", "kgifund.com.tw", "fhtrust.com.tw", "capitalfund.com.tw",
    "cathaysite.com.tw", "fsitc.com.tw", "sinopac.com", "nomurafunds.com.tw",
})
PRIMARY_PREFIXES = ("investor.", "ir.")

# 外媒/英文對照層(rubric 要求權值股至少一個)。
# 英文發行的台灣媒體(Taipei Times、Focus Taiwan)計入:其編輯視角與
# 讀者是國際投資人,正是「外媒溫差」要對照的對象。
FOREIGN_DOMAINS = frozenset({
    "reuters.com", "bloomberg.com", "wsj.com", "cnbc.com", "ft.com",
    "nikkei.com", "asia.nikkei.com", "scmp.com", "cnn.com", "fortune.com",
    "apnews.com", "bbc.com", "nytimes.com", "economist.com", "barrons.com",
    "taipeitimes.com", "focustaiwan.tw", "taiwannews.com.tw",
    "marketwatch.com", "seekingalpha.com", "investing.com", "tipranks.com",
    "coindesk.com", "cointelegraph.com", "theblock.co", "crypto.news",
    "beincrypto.com", "cryptobriefing.com", "coinpedia.org", "hdfcsky.com",
})


def registrable_domain(url: str) -> str:
    """https://finance.ettoday.net/a → ettoday.net;無法解析回傳空字串。"""
    if not isinstance(url, str) or not url.strip():
        return ""
    host = (urlparse(url.strip()).netloc or "").lower().split(":")[0]
    if not host or "." not in host:
        return ""
    if host in DOMAIN_ALIASES:
        return DOMAIN_ALIASES[host]
    parts = host.split(".")
    take = 3 if ".".join(parts[-2:]) in MULTI_PART_TLDS else 2
    base = ".".join(parts[-take:]) if len(parts) >= take else host
    if base in DOMAIN_ALIASES:
        return DOMAIN_ALIASES[base]
    if host.startswith(PRIMARY_PREFIXES):
        return host
    return base


def tier_of(domain: str) -> str:
    """primary(一手)/ foreign(外媒)/ media(本地財經媒體與其他)。"""
    if not domain:
        return "media"
    if domain in PRIMARY_DOMAINS or domain.startswith(PRIMARY_PREFIXES):
        return "primary"
    if domain.endswith(".gov.tw"):
        return "primary"
    if domain in FOREIGN_DOMAINS:
        return "foreign"
    return "media"


def _domain_counts(items: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for it in items:
        domain = registrable_domain(it.get("source_url", ""))
        if domain:
            counts[domain] = counts.get(domain, 0) + 1
    return counts


def _flags(counts: dict[str, int], item_count: int) -> tuple[list[str], str | None]:
    flags: list[str] = []
    independent = len(counts)
    if independent < MIN_INDEPENDENT_SOURCES:
        flags.append("weak_source_count")

    dominant = None
    if counts and item_count >= DOMINANCE_MIN_ITEMS:
        top, top_n = max(counts.items(), key=lambda kv: (kv[1], kv[0]))
        if top_n / item_count > DOMINANCE_RATIO:
            flags.append("single_domain_dominant")
            dominant = top

    tiers = {tier_of(d) for d in counts}
    if "primary" not in tiers:
        flags.append("no_primary_source")
    if "foreign" not in tiers:
        flags.append("no_foreign_source")
    return flags, dominant


def _summarize(items: list[dict]) -> dict:
    counts = _domain_counts(items)
    flags, dominant = _flags(counts, len(items))
    tier_counts = {"primary": 0, "foreign": 0, "media": 0}
    for domain, n in counts.items():
        tier_counts[tier_of(domain)] += n
    penalty = max(MAX_PENALTY, sum(PENALTIES.get(f, 0) for f in flags))
    return {
        "item_count": len(items),
        "independent_sources": len(counts),
        "domain_counts": dict(sorted(counts.items(),
                                     key=lambda kv: (-kv[1], kv[0]))),
        "tier_counts": tier_counts,
        "dominant_domain": dominant,
        "flags": flags,
        "confidence_penalty": penalty,
    }


def audit(items: list[dict], now: int,
          since_hours: int = DEFAULT_SINCE_HOURS) -> dict:
    """稽核一組新聞項目的來源多樣性。

    items 需含 source_url;symbol 與 fetched_at 為選填(有才產出對應細項)。
    回傳整體統計 + by_symbol 細項;`confidence_penalty` 為建議扣分(≤ 0)。
    """
    cutoff = now - since_hours * 3600
    result = _summarize(items)
    result["since_hours"] = since_hours
    result["recent_item_count"] = sum(
        1 for it in items
        if isinstance(it.get("fetched_at"), (int, float))
        and it["fetched_at"] >= cutoff)

    by_symbol: dict[str, list[dict]] = {}
    for it in items:
        by_symbol.setdefault(it.get("symbol") or "?", []).append(it)
    result["by_symbol"] = {
        sym: _summarize(rows) for sym, rows in sorted(by_symbol.items())
    }
    return result
