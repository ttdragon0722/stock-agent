"""Unit tests for source_audit.py (新聞來源多樣性稽核)."""
import source_audit as sa

NOW = 1_780_000_000


def item(url: str, symbol: str = "0050.TW", fetched_at: int = NOW,
         headline: str = "h") -> dict:
    return {"symbol": symbol, "headline": headline, "source_url": url,
            "sentiment": "neutral", "fetched_at": fetched_at}


class TestRegistrableDomain:
    def test_strips_www_and_subdomains(self):
        assert sa.registrable_domain("https://www.chinatimes.com/x") == "chinatimes.com"
        assert sa.registrable_domain("https://finance.ettoday.net/a") == "ettoday.net"

    def test_multi_part_tld_kept(self):
        assert sa.registrable_domain("https://money.udn.com/a") == "udn.com"
        assert sa.registrable_domain("https://www.cnyes.com.tw/n/1") == "cnyes.com.tw"
        assert sa.registrable_domain("https://mops.twse.com.tw/x") == "twse.com.tw"

    def test_ctee_folded_into_chinatimes_group(self):
        assert sa.registrable_domain("https://www.ctee.com.tw/news/1") == "chinatimes.com"

    def test_group_aliases_collapse_to_one_source(self):
        """同集團轉載不得計為兩個獨立來源。"""
        a = sa.registrable_domain("https://www.chinatimes.com/x")
        b = sa.registrable_domain("https://wantrich.chinatimes.com/y")
        assert a == b

    def test_malformed_url_returns_empty(self):
        assert sa.registrable_domain("not a url") == ""
        assert sa.registrable_domain("") == ""


class TestTier:
    def test_primary_sources(self):
        assert sa.tier_of("twse.com.tw") == "primary"
        assert sa.tier_of("tpex.org.tw") == "primary"
        assert sa.tier_of("investor.tsmc.com") == "primary"

    def test_foreign_sources(self):
        assert sa.tier_of("reuters.com") == "foreign"
        assert sa.tier_of("bloomberg.com") == "foreign"
        assert sa.tier_of("coindesk.com") == "foreign"

    def test_english_language_taiwan_media_count_as_foreign(self):
        """英文發行的台媒面向國際投資人,正是外媒溫差要對照的對象。"""
        assert sa.tier_of("taipeitimes.com") == "foreign"
        assert sa.tier_of("focustaiwan.tw") == "foreign"

    def test_everything_else_is_media(self):
        assert sa.tier_of("udn.com") == "media"
        assert sa.tier_of("unknown-blog.xyz") == "media"


class TestAudit:
    def test_counts_independent_domains_not_rows(self):
        items = [item("https://udn.com/1", headline="a"),
                 item("https://money.udn.com/2", headline="b"),
                 item("https://udn.com/3", headline="c")]
        result = sa.audit(items, now=NOW)
        assert result["item_count"] == 3
        assert result["independent_sources"] == 1

    def test_weak_flag_when_below_minimum(self):
        result = sa.audit([item("https://udn.com/1")], now=NOW)
        assert result["independent_sources"] == 1
        assert "weak_source_count" in result["flags"]
        assert result["confidence_penalty"] <= -10

    def test_no_flag_when_diverse_enough(self):
        items = [item("https://udn.com/1", headline="a"),
                 item("https://reuters.com/2", headline="b"),
                 item("https://twse.com.tw/3", headline="c"),
                 item("https://cnyes.com/4", headline="d")]
        result = sa.audit(items, now=NOW)
        assert result["independent_sources"] == 4
        assert "weak_source_count" not in result["flags"]
        assert "no_foreign_source" not in result["flags"]
        assert "no_primary_source" not in result["flags"]

    def test_dominance_flag_when_one_domain_over_threshold(self):
        items = [item(f"https://udn.com/{i}", headline=f"u{i}") for i in range(7)]
        items += [item("https://reuters.com/1", headline="r"),
                  item("https://twse.com.tw/1", headline="t")]
        result = sa.audit(items, now=NOW)
        assert "single_domain_dominant" in result["flags"]
        assert result["dominant_domain"] == "udn.com"

    def test_missing_foreign_and_primary_flags(self):
        items = [item("https://udn.com/1", headline="a"),
                 item("https://cnyes.com/2", headline="b"),
                 item("https://ettoday.net/3", headline="c")]
        result = sa.audit(items, now=NOW)
        assert "no_foreign_source" in result["flags"]
        assert "no_primary_source" in result["flags"]

    def test_recent_window_counts_only_fresh_fetches(self):
        items = [item("https://udn.com/1", fetched_at=NOW, headline="new"),
                 item("https://cnyes.com/2", fetched_at=NOW - 80 * 3600,
                      headline="old")]
        result = sa.audit(items, now=NOW, since_hours=24)
        assert result["item_count"] == 2
        assert result["recent_item_count"] == 1

    def test_empty_input_is_maximally_weak(self):
        result = sa.audit([], now=NOW)
        assert result["independent_sources"] == 0
        assert "weak_source_count" in result["flags"]

    def test_tier_counts_reported(self):
        items = [item("https://reuters.com/1", headline="a"),
                 item("https://twse.com.tw/2", headline="b"),
                 item("https://udn.com/3", headline="c")]
        result = sa.audit(items, now=NOW)
        assert result["tier_counts"] == {"primary": 1, "foreign": 1, "media": 1}

    def test_penalty_is_capped(self):
        result = sa.audit([item("https://udn.com/1")], now=NOW)
        assert result["confidence_penalty"] >= sa.MAX_PENALTY

    def test_per_symbol_breakdown(self):
        items = [item("https://udn.com/1", symbol="0050.TW", headline="a"),
                 item("https://cnyes.com/2", symbol="3030.TW", headline="b"),
                 item("https://reuters.com/3", symbol="3030.TW", headline="c")]
        result = sa.audit(items, now=NOW)
        assert result["by_symbol"]["3030.TW"]["independent_sources"] == 2
        assert result["by_symbol"]["0050.TW"]["independent_sources"] == 1
