"""Unit tests for outcome-verification first-touch logic."""
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
