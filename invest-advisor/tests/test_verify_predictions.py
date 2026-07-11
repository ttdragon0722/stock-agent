"""Unit tests for outcome-verification first-touch logic."""
import pytest

import verify_predictions as vp

DAY = 86400
T0 = 1750000000  # analysis time


def make_pred(**overrides) -> dict:
    base = {
        "id": "test-1", "asset": "TSLA", "asset_type": "stock",
        "question_type": "Q1_short_entry", "direction": "long",
        "recommendation_score": 72, "confidence_score": 65,
        "price_at_analysis": 245.0,
        "entry_zone": [240, 246], "stop_loss": 232, "take_profit": [260, 275],
        "horizon_days": 14,
        "timestamp": "2025-06-15T00:00:00+00:00",
        "rubric_version": "1.0.0",
    }
    return {**base, "timestamp_epoch": T0, **overrides}


def pred_with_ts(**overrides) -> dict:
    import common
    p = make_pred(**overrides)
    p["timestamp"] = common.iso_utc(T0)
    return p


def bar(day: int, o: float, h: float, l: float, c: float) -> dict:
    return {"ts": T0 + day * DAY, "open": o, "high": h, "low": l, "close": c,
            "volume": 1000.0}


class TestLongTradePlan:
    def test_win_fill_then_tp(self):
        bars = [bar(1, 247, 248, 244, 246),   # fills at 246 (low <= entry_hi)
                bar(2, 246, 255, 245, 254),
                bar(3, 254, 261, 253, 258)]   # TP1 260 touched
        out = vp.evaluate_prediction(pred_with_ts(), bars, [], T0 + 20 * DAY)
        assert out["status"] == "WIN"
        assert out["fill_price"] == 246
        assert out["exit_price"] == 260
        assert out["r_multiple"] == 1.0
        assert out["direction_correct"] is True

    def test_loss_sl_first(self):
        bars = [bar(1, 245, 246, 240, 241),   # fills
                bar(2, 241, 243, 231, 233)]   # SL 232 touched
        out = vp.evaluate_prediction(pred_with_ts(), bars, [], T0 + 20 * DAY)
        assert out["status"] == "LOSS"
        assert out["exit_price"] == 232
        assert out["r_multiple"] == -1.0

    def test_same_bar_both_touched_is_loss(self):
        bars = [bar(1, 245, 246, 240, 241),
                bar(2, 241, 262, 231, 250)]   # touches TP AND SL -> LOSS
        out = vp.evaluate_prediction(pred_with_ts(), bars, [], T0 + 20 * DAY)
        assert out["status"] == "LOSS"

    def test_never_filled(self):
        bars = [bar(d, 250, 255, 248, 252) for d in range(1, 15)]  # never dips
        out = vp.evaluate_prediction(pred_with_ts(), bars, [], T0 + 20 * DAY)
        assert out["status"] == "NOT_FILLED"
        assert out["return_pct"] is None

    def test_flat_at_horizon_end(self):
        bars = [bar(d, 245, 248, 243, 247) for d in range(1, 15)]
        out = vp.evaluate_prediction(pred_with_ts(), bars, [], T0 + 20 * DAY)
        assert out["status"] == "FLAT"
        assert out["exit_price"] == 247
        assert out["return_pct"] is not None

    def test_open_before_horizon_end(self):
        bars = [bar(1, 245, 248, 243, 247)]
        out = vp.evaluate_prediction(pred_with_ts(), bars, [], T0 + 2 * DAY)
        assert out["status"] == "OPEN"

    def test_gap_down_fills_at_open(self):
        bars = [bar(1, 238, 258, 236, 250)]  # opens below zone
        out = vp.evaluate_prediction(pred_with_ts(), bars, [], T0 + 20 * DAY)
        assert out["fill_price"] == 238  # filled at open, not entry_hi

    def test_gap_through_sl_exits_at_open(self):
        bars = [bar(1, 245, 246, 240, 241),   # fills at 245
                bar(2, 228, 233, 226, 230)]   # opens BELOW SL 232
        out = vp.evaluate_prediction(pred_with_ts(), bars, [], T0 + 20 * DAY)
        assert out["status"] == "LOSS"
        assert out["exit_price"] == 228        # open, not the SL price
        assert out["r_multiple"] < -1.0        # loss never understated


class TestShortTradePlan:
    def test_short_win(self):
        pred = pred_with_ts(direction="short", entry_zone=[240, 246],
                            stop_loss=252, take_profit=[225, 210])
        bars = [bar(1, 238, 242, 236, 240),   # high >= entry_lo -> fills at 240
                bar(2, 240, 241, 224, 226)]   # TP 225 touched
        out = vp.evaluate_prediction(pred, bars, [], T0 + 20 * DAY)
        assert out["status"] == "WIN"
        assert out["fill_price"] == 240
        assert out["exit_price"] == 225

    def test_short_loss(self):
        pred = pred_with_ts(direction="short", entry_zone=[240, 246],
                            stop_loss=252, take_profit=[225, 210])
        bars = [bar(1, 238, 242, 236, 240),
                bar(2, 240, 253, 239, 251)]   # SL 252 touched
        out = vp.evaluate_prediction(pred, bars, [], T0 + 20 * DAY)
        assert out["status"] == "LOSS"


class TestDirectionalOnly:
    def test_long_no_plan_resolved_up(self):
        pred = pred_with_ts(question_type="Q2_long_hold")
        for k in ("entry_zone", "stop_loss", "take_profit"):
            del pred[k]
        bars = [bar(d, 245, 250, 244, 249) for d in range(1, 15)]
        bars[-1] = bar(14, 260, 266, 259, 265)
        out = vp.evaluate_prediction(pred, bars, [], T0 + 20 * DAY)
        assert out["status"] == "RESOLVED_DIRECTIONAL"
        assert out["direction_correct"] is True

    def test_neutral_within_band(self):
        pred = pred_with_ts(direction="neutral",
                            question_type="Q2_long_hold")
        for k in ("entry_zone", "stop_loss", "take_profit"):
            del pred[k]
        bars = [bar(d, 245, 247, 243, 246) for d in range(1, 15)]
        out = vp.evaluate_prediction(pred, bars, [], T0 + 20 * DAY)
        assert out["status"] == "RESOLVED_NEUTRAL"
        assert out["direction_correct"] is True

    def test_pending_before_horizon(self):
        pred = pred_with_ts(question_type="Q2_long_hold")
        for k in ("entry_zone", "stop_loss", "take_profit"):
            del pred[k]
        bars = [bar(1, 245, 250, 244, 249)]
        out = vp.evaluate_prediction(pred, bars, [], T0 + 2 * DAY)
        assert out["status"] == "PENDING"

    def test_tiny_drift_is_noise_not_skill(self):
        pred = pred_with_ts(question_type="Q2_long_hold")
        for k in ("entry_zone", "stop_loss", "take_profit"):
            del pred[k]
        # +0.4% drift at 14d is inside the ~1% noise band
        bars = [bar(d, 245, 247, 244, 246) for d in range(1, 15)]
        out = vp.evaluate_prediction(pred, bars, [], T0 + 20 * DAY)
        assert out["status"] == "RESOLVED_DIRECTIONAL"
        assert out["direction_correct"] is None
        assert out["within_noise_band"] is True

    def test_wrong_direction_beyond_noise_band(self):
        pred = pred_with_ts(question_type="Q2_long_hold")
        for k in ("entry_zone", "stop_loss", "take_profit"):
            del pred[k]
        bars = [bar(d, 245, 247, 234, 236) for d in range(1, 15)]  # -3.7%
        out = vp.evaluate_prediction(pred, bars, [], T0 + 20 * DAY)
        assert out["direction_correct"] is False


class TestHorizonScaledBands:
    def test_noise_band_grows_with_horizon_capped(self):
        assert vp.noise_band_pct(14) == 1.0
        assert vp.noise_band_pct(90) == pytest.approx(2.54, abs=0.01)
        assert vp.noise_band_pct(400) == 3.0  # capped

    def test_neutral_band_grows_with_horizon_capped(self):
        assert vp.neutral_band_pct(30) == 5.0
        assert vp.neutral_band_pct(180) == pytest.approx(12.25, abs=0.01)
        assert vp.neutral_band_pct(2000) == 15.0  # capped

    def test_neutral_180d_allows_wider_drift(self):
        pred = pred_with_ts(direction="neutral", horizon_days=180,
                            question_type="Q2_long_hold")
        for k in ("entry_zone", "stop_loss", "take_profit"):
            del pred[k]
        # +8% over 180d: outside the old fixed 5% band, inside the scaled one
        bars = [bar(d, 245, 250, 244, 264.6) for d in range(1, 20)]
        out = vp.evaluate_prediction(pred, bars, [], T0 + 200 * DAY)
        assert out["direction_correct"] is True

    def test_neutral_14d_band_tighter_than_before(self):
        pred = pred_with_ts(direction="neutral", question_type="Q2_long_hold")
        for k in ("entry_zone", "stop_loss", "take_profit"):
            del pred[k]
        # +4.5% over 14d: inside the old fixed 5%, outside the scaled ~3.4%
        bars = [bar(d, 245, 258, 244, 256) for d in range(1, 15)]
        out = vp.evaluate_prediction(pred, bars, [], T0 + 20 * DAY)
        assert out["direction_correct"] is False


class TestBenchmarkAndNoData:
    def test_no_data(self):
        out = vp.evaluate_prediction(pred_with_ts(), [], [], T0 + 20 * DAY)
        assert out["status"] == "NO_DATA"

    def test_excess_return_computed(self):
        bars = [bar(1, 245, 248, 244, 246),
                bar(2, 246, 261, 245, 259)]  # WIN
        bench = [bar(1, 100, 101, 99, 100), bar(2, 100, 103, 100, 102)]
        out = vp.evaluate_prediction(pred_with_ts(), bars, bench, T0 + 20 * DAY)
        assert out["benchmark_return_pct"] == 2.0
        assert out["excess_return_pct"] == out["return_pct"] - 2.0


class TestSummarize:
    def test_summary_stats(self):
        outcomes = [
            {"status": "WIN", "r_multiple": 2.0, "direction_correct": True,
             "excess_return_pct": 5.0},
            {"status": "LOSS", "r_multiple": -1.0, "direction_correct": False,
             "excess_return_pct": -3.0},
            {"status": "WIN", "r_multiple": 1.5, "direction_correct": True,
             "excess_return_pct": 4.0},
            {"status": "NOT_FILLED", "r_multiple": None,
             "direction_correct": None, "excess_return_pct": None},
            {"status": "FLAT", "r_multiple": 0.5, "direction_correct": True,
             "excess_return_pct": 1.0},
        ]
        stats = vp.summarize(outcomes)
        assert stats["win_rate"] == round(2 / 3, 3)
        assert stats["expectancy_r"] == round((2.0 - 1.0 + 1.5 + 0.5) / 4, 3)
        assert stats["by_status"]["NOT_FILLED"] == 1
        assert stats["sample_warning"] is not None  # n < 50

    def test_allocation_excluded_from_direction_accuracy(self):
        outcomes = [
            {"status": "RESOLVED_DIRECTIONAL", "question_type": "Q2_long_hold",
             "r_multiple": None, "direction_correct": True,
             "excess_return_pct": 2.0},
            {"status": "RESOLVED_NEUTRAL", "question_type": "Q5_allocation",
             "r_multiple": None, "direction_correct": False,
             "excess_return_pct": -9.0},
        ]
        stats = vp.summarize(outcomes)
        assert stats["direction_accuracy"] == 1.0     # Q5 not counted
        assert stats["avg_excess_return_pct"] == 2.0  # Q5 excess not counted
        assert stats["allocation_excluded_n"] == 1

    def test_screened_out_excluded_but_funnel_reported(self):
        outcomes = [
            {"status": "RESOLVED_DIRECTIONAL", "question_type": "Q3_screener",
             "r_multiple": None, "direction_correct": True,
             "excess_return_pct": 3.0, "return_pct": 6.0},
            {"status": "RESOLVED_DIRECTIONAL", "question_type": "Q3_screener",
             "r_multiple": None, "direction_correct": True,
             "excess_return_pct": 1.0, "return_pct": 4.0},
            {"status": "RESOLVED_DIRECTIONAL",
             "question_type": "Q3_screened_out",
             "r_multiple": None, "direction_correct": False,
             "excess_return_pct": -2.0, "return_pct": 1.0},
        ]
        stats = vp.summarize(outcomes)
        assert stats["direction_accuracy"] == 1.0  # counterfactual excluded
        funnel = stats["screener_funnel"]
        assert funnel["picked_n"] == 2
        assert funnel["rejected_n"] == 1
        assert funnel["picked_avg_return_pct"] == 5.0
        assert funnel["rejected_avg_return_pct"] == 1.0
        assert funnel["edge_pct"] == 4.0

    def test_noise_band_exclusions_counted(self):
        outcomes = [
            {"status": "RESOLVED_DIRECTIONAL", "question_type": "Q2_long_hold",
             "r_multiple": None, "direction_correct": None,
             "within_noise_band": True, "excess_return_pct": None},
        ]
        stats = vp.summarize(outcomes)
        assert stats["direction_accuracy"] is None
        assert stats["noise_band_excluded"] == 1
