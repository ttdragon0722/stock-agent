"""Unit tests for etf_proxies.py (ETF → 代理標的對照)."""
import etf_proxies as ep


class TestIsEtf:
    def test_taiwan_etf_codes(self):
        assert ep.is_etf("0050.TW")
        assert ep.is_etf("00918.TW")
        assert ep.is_etf("009816.TW")
        assert ep.is_etf("00980A.TW")

    def test_ordinary_stock_is_not_etf(self):
        assert not ep.is_etf("2330.TW")
        assert not ep.is_etf("3030.TW")

    def test_non_taiwan_symbols(self):
        assert not ep.is_etf("NVDA")
        assert not ep.is_etf("BTCUSDT")
        assert ep.is_etf("SPY")
        assert ep.is_etf("QQQ")


class TestProxiesFor:
    def test_known_etf_uses_explicit_map(self):
        assert ep.proxies_for("0050.TW") == ep.PROXY_MAP["0050.TW"]
        assert "2330.TW" in ep.proxies_for("0050.TW")

    def test_case_and_whitespace_normalized(self):
        assert ep.proxies_for("  0050.tw ") == ep.proxies_for("0050.TW")

    def test_unknown_taiwan_etf_falls_back_to_market_index(self):
        assert ep.proxies_for("00999.TW") == ["^TWII"]

    def test_us_etf_falls_back_to_spy_free_list(self):
        assert ep.proxies_for("QQQ") == ["SPY"]
        assert ep.proxies_for("SPY") == []

    def test_non_etf_has_no_proxies(self):
        assert ep.proxies_for("2330.TW") == []
        assert ep.proxies_for("BTCUSDT") == []

    def test_proxy_list_never_contains_self(self):
        for symbol in ep.PROXY_MAP:
            assert symbol not in ep.proxies_for(symbol), symbol
