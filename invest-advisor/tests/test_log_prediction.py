"""Unit tests for prediction validation / normalization (Layer-3 assertions)."""
import pytest

import common
import log_prediction as lp


def valid_q1() -> dict:
    return {
        "asset": "TSLA",
        "asset_type": "stock",
        "question_type": "Q1_short_entry",
        "direction": "long",
        "recommendation_score": 72,
        "confidence_score": 65,
        "price_at_analysis": 245.30,
        "entry_zone": [240, 246],
        "stop_loss": 232,
        "take_profit": [260, 275],
        "horizon_days": 14,
        "falsification_condition": "daily close below 232",
        "thesis_summary": "earnings catalyst + 4H trendline breakout",
    }


class TestValidate:
    def test_valid_record_passes(self):
        assert lp.validate_prediction(valid_q1()) == []

    def test_missing_field(self):
        rec = valid_q1()
        del rec["falsification_condition"]
        errors = lp.validate_prediction(rec)
        assert any("falsification_condition" in e for e in errors)

    def test_bad_asset_type(self):
        rec = {**valid_q1(), "asset_type": "forex"}
        assert any("asset_type" in e for e in lp.validate_prediction(rec))

    def test_score_out_of_range(self):
        rec = {**valid_q1(), "recommendation_score": 120}
        assert any("recommendation_score" in e
                   for e in lp.validate_prediction(rec))

    def test_q1_requires_trade_plan(self):
        rec = valid_q1()
        del rec["entry_zone"], rec["stop_loss"], rec["take_profit"]
        assert any("requires entry_zone" in e
                   for e in lp.validate_prediction(rec))

    def test_long_sl_above_entry_rejected(self):
        rec = {**valid_q1(), "stop_loss": 250}
        assert any("ordering violated" in e
                   for e in lp.validate_prediction(rec))

    def test_long_tp_below_entry_rejected(self):
        rec = {**valid_q1(), "take_profit": [244]}
        assert any("ordering violated" in e
                   for e in lp.validate_prediction(rec))

    def test_short_ordering(self):
        rec = {**valid_q1(), "direction": "short",
               "entry_zone": [240, 246], "stop_loss": 252,
               "take_profit": [225, 210]}
        assert lp.validate_prediction(rec) == []

    def test_neutral_without_plan_ok(self):
        rec = valid_q1()
        del rec["entry_zone"], rec["stop_loss"], rec["take_profit"]
        rec["direction"] = "neutral"
        rec["question_type"] = "Q2_long_hold"
        assert lp.validate_prediction(rec) == []

    def test_empty_thesis_rejected(self):
        rec = {**valid_q1(), "thesis_summary": "   "}
        assert any("thesis_summary" in e for e in lp.validate_prediction(rec))


class TestComputeRr:
    def test_long_rr(self):
        # entry_mid = 243, risk = 11, reward = 17 -> 1.55
        assert lp.compute_rr("long", [240, 246], 232, [260]) == 1.55

    def test_short_rr(self):
        # entry_mid = 243, risk = 9, reward = 18 -> 2.0
        assert lp.compute_rr("short", [240, 246], 252, [225]) == 2.0

    def test_zero_risk_raises(self):
        with pytest.raises(ValueError):
            lp.compute_rr("long", [240, 246], 243, [260])


class TestNormalize:
    def test_adds_auto_fields_without_mutating_input(self):
        rec = valid_q1()
        original = dict(rec)
        out = lp.normalize_prediction(rec, 1750000000, set())
        assert rec == original  # immutability
        assert out["rubric_version"] == common.RUBRIC_VERSION
        assert out["risk_reward"] == 1.55
        assert out["rr_below_min"] is False
        assert out["id"].endswith("-TSLA-q1")
        assert out["timestamp"].endswith("Z")

    def test_rr_below_min_flagged(self):
        rec = {**valid_q1(), "take_profit": [250, 260]}
        out = lp.normalize_prediction(rec, 1750000000, set())
        assert out["rr_below_min"] is True

    def test_id_dedup(self):
        rec = valid_q1()
        first = lp.normalize_prediction(rec, 1750000000, set())
        second = lp.normalize_prediction(rec, 1750000000, {first["id"]})
        assert second["id"] != first["id"]
        assert second["id"].startswith(first["id"])
