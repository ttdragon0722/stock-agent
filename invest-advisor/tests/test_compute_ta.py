"""Unit tests for deterministic TA computations."""
import pytest

import compute_ta as ta


class TestSma:
    def test_basic(self):
        assert ta.sma([1, 2, 3, 4, 5], 5) == 3.0

    def test_uses_last_n(self):
        assert ta.sma([100, 1, 2, 3], 3) == 2.0

    def test_insufficient_data(self):
        assert ta.sma([1, 2], 5) is None


class TestEma:
    def test_constant_series(self):
        assert ta.ema([5.0] * 30, 10) == pytest.approx(5.0)

    def test_moves_toward_recent(self):
        rising = list(range(1, 31))
        assert ta.ema(rising, 10) > ta.sma(rising, 30)

    def test_insufficient_data(self):
        assert ta.ema([1, 2, 3], 10) is None


class TestRsi:
    def test_all_gains_is_100(self):
        closes = [float(i) for i in range(1, 20)]
        assert ta.rsi(closes) == 100.0

    def test_all_losses_near_0(self):
        closes = [float(i) for i in range(20, 1, -1)]
        assert ta.rsi(closes) == pytest.approx(0.0, abs=1e-6)

    def test_balanced_is_mid(self):
        closes = [10.0, 11.0] * 15  # alternate +1/-1
        value = ta.rsi(closes)
        assert 40 < value < 60

    def test_bounds(self):
        closes = [10, 12, 11, 13, 12, 14, 13, 15, 14, 16,
                  15, 17, 16, 18, 17, 19, 18, 20]
        assert 0 <= ta.rsi([float(c) for c in closes]) <= 100

    def test_insufficient_data(self):
        assert ta.rsi([1.0] * 10) is None


class TestMacd:
    def test_uptrend_positive_line(self):
        closes = [100 * 1.01 ** i for i in range(60)]
        result = ta.macd(closes)
        assert result["line"] > 0
        assert result["hist"] == pytest.approx(
            result["line"] - result["signal"], abs=1e-3)

    def test_downtrend_negative_line(self):
        closes = [100 * 0.99 ** i for i in range(60)]
        assert ta.macd(closes)["line"] < 0

    def test_insufficient_data(self):
        assert ta.macd([1.0] * 20) is None


class TestAtr:
    def test_constant_range(self):
        n = 20
        highs = [12.0] * n
        lows = [10.0] * n
        closes = [11.0] * n
        assert ta.atr(highs, lows, closes) == pytest.approx(2.0)

    def test_insufficient_data(self):
        assert ta.atr([1] * 5, [1] * 5, [1] * 5) is None


class TestSwingLevels:
    def test_detects_pivot_high_and_low(self):
        highs = [10, 11, 12, 15, 12, 11, 10, 11, 12, 11, 10]
        lows = [9, 8, 7, 6, 7, 8, 5, 7, 8, 9, 9]
        pivot_highs, pivot_lows = ta.swing_pivots(
            [float(x) for x in highs], [float(x) for x in lows], k=3)
        assert 15.0 in pivot_highs
        assert 5.0 in pivot_lows or 6.0 in pivot_lows

    def test_nearest_levels_sorted(self):
        supports, resistances = ta.nearest_levels(
            100.0, [95, 105, 110, 120], [90, 85, 98])
        assert supports == [98, 95, 90]  # nearest-below first
        assert resistances == [105, 110, 120]  # nearest-above first


class TestTrend:
    def test_uptrend(self):
        assert ta.classify_trend(110, 105, 100, 90) == "uptrend"

    def test_downtrend(self):
        assert ta.classify_trend(80, 85, 90, 100) == "downtrend"

    def test_range(self):
        assert ta.classify_trend(100, 101, 99, 100) == "range"

    def test_insufficient(self):
        assert ta.classify_trend(100, None, None, None) == "insufficient_data"


class TestBuildSnapshot:
    def test_snapshot_fields(self):
        bars = [{"ts": 1700000000 + i * 86400,
                 "open": 100 + i * 0.5, "high": 101 + i * 0.5,
                 "low": 99 + i * 0.5, "close": 100.5 + i * 0.5,
                 "volume": 1000.0}
                for i in range(250)]
        snap = ta.build_snapshot("TSLA", "1d", bars,
                                 now_ts=bars[-1]["ts"] + 86400)
        assert snap["symbol"] == "TSLA"
        assert snap["trend"] == "uptrend"
        assert snap["sma200"] is not None
        assert snap["rsi14"] == 100.0
        assert snap["stale_bars"] == 0
        assert snap["last_close"] == bars[-1]["close"]
        suggestion = snap["suggested_score"]
        assert 5 <= suggestion["base"] <= 95
        assert suggestion["range"][0] <= suggestion["base"] <= suggestion["range"][1]


def make_snap(**overrides) -> dict:
    """Minimal snapshot for suggest_tech_score (pure-function input)."""
    base = {
        "last_close": 100.0, "sma20": 98.0, "sma50": 95.0, "sma200": 90.0,
        "rsi14": 60.0,
        "macd": {"line": 1.0, "signal": 0.5, "hist": 0.5, "cross": "none"},
        "vol_ratio_20": 1.0, "dist_52w_high_pct": -10.0, "trend": "uptrend",
    }
    return {**base, **overrides}


class TestSuggestScore:
    def test_bullish_setup_scores_high(self):
        snap = make_snap(macd={"line": 1, "signal": 0.5, "hist": 0.5,
                               "cross": "bullish"},
                         vol_ratio_20=1.6, dist_52w_high_pct=-2.0)
        result = ta.suggest_tech_score(snap)
        # 15 + 8 + 8 + 8 + 4 + 4 = +47 -> clamped at 95
        assert result["base"] == 95
        assert result["range"] == [90, 100]

    def test_bearish_setup_scores_low(self):
        snap = make_snap(trend="downtrend", last_close=80.0,
                         sma20=85.0, sma50=90.0, sma200=95.0, rsi14=25.0,
                         macd={"line": -1, "signal": -0.5, "hist": -0.5,
                               "cross": "bearish"},
                         vol_ratio_20=1.8, dist_52w_high_pct=-50.0)
        result = ta.suggest_tech_score(snap)
        # -15 - 8 - 10 - 8 - 4 - 6 = -51 -> clamped at 5
        assert result["base"] == 5
        assert result["range"] == [1, 10]

    def test_mixed_signals_stay_mid(self):
        snap = make_snap(trend="range", sma20=101.0, sma50=99.0, sma200=100.0,
                         rsi14=45.0,
                         macd={"line": 0.1, "signal": 0.1, "hist": 0.0,
                               "cross": "none"})
        result = ta.suggest_tech_score(snap)
        assert 40 <= result["base"] <= 60

    def test_deterministic(self):
        snap = make_snap()
        assert ta.suggest_tech_score(snap) == ta.suggest_tech_score(snap)

    def test_components_sum_to_base(self):
        result = ta.suggest_tech_score(make_snap())
        assert result["base"] == 50 + sum(result["components"].values())

    def test_missing_optional_fields_tolerated(self):
        snap = make_snap(rsi14=None, macd=None, vol_ratio_20=None,
                         dist_52w_high_pct=None, sma200=None)
        result = ta.suggest_tech_score(snap)
        assert result["components"]["rsi"] == 0
        assert result["components"]["macd"] == 0
        # trend + ma_alignment still contribute
        assert result["base"] == 50 + 15 + 8

    def test_high_volume_in_downtrend_penalized(self):
        snap = make_snap(trend="downtrend", vol_ratio_20=2.0)
        assert ta.suggest_tech_score(snap)["components"]["volume"] == -4
