"""Unit tests for recall_history.py (Step 1.5 歷史回顧)."""
import json

import recall_history as rh


def make_pred(asset: str, pid: str, ts: str, direction: str = "long",
              score: int = 70) -> dict:
    return {
        "id": pid, "asset": asset, "asset_type": "stock",
        "question_type": "Q1_short_entry", "direction": direction,
        "recommendation_score": score, "confidence_score": 60,
        "price_at_analysis": 100.0, "horizon_days": 14,
        "falsification_condition": "close below 90",
        "thesis_summary": "test thesis", "timestamp": ts,
        "rubric_version": "1.0.0",
    }


def make_outcome(pid: str, status: str, return_pct=None) -> dict:
    return {"id": pid, "status": status, "return_pct": return_pct,
            "verified_at": "2026-07-09T00:00:00Z"}


class TestSymbolMatch:
    def test_exact_match_case_insensitive(self):
        assert rh.symbol_matches("tsla", "TSLA")
        assert rh.symbol_matches("2330.TW", "2330.tw")

    def test_no_match(self):
        assert not rh.symbol_matches("TSLA", "AAPL")

    def test_no_substring_false_positive(self):
        assert not rh.symbol_matches("0050.TW", "00918.TW")


class TestMatchReports:
    def test_matches_dot_and_dash_variants(self, tmp_path):
        reports = tmp_path / "reports"
        reports.mkdir()
        (reports / "2026-07-09_00918-TW_Q1.md").write_text("x", encoding="utf-8")
        (reports / "2026-07-04_TSLA_Q1.md").write_text("x", encoding="utf-8")
        (reports / "2026-07-04_TW-screener_Q3.md").write_text("x", encoding="utf-8")
        found = rh.match_reports("00918.TW", reports)
        assert len(found) == 1
        assert "00918-TW" in found[0]

    def test_missing_dir_returns_empty(self, tmp_path):
        assert rh.match_reports("TSLA", tmp_path / "nope") == []

    def test_no_prefix_ticker_false_positive(self, tmp_path):
        reports = tmp_path / "reports"
        reports.mkdir()
        (reports / "2026-07-01_GOOGL_Q1.md").write_text("x", encoding="utf-8")
        assert rh.match_reports("GOOG", reports) == []

    def test_matches_symbol_inside_multi_symbol_theme(self, tmp_path):
        reports = tmp_path / "reports"
        reports.mkdir()
        (reports / "2026-07-04_SOL-ONDO_Q1.md").write_text("x", encoding="utf-8")
        assert len(rh.match_reports("SOL", reports)) == 1
        assert len(rh.match_reports("ONDO", reports)) == 1
        assert rh.match_reports("OND", reports) == []

    def test_sorted_newest_first(self, tmp_path):
        reports = tmp_path / "reports"
        reports.mkdir()
        (reports / "2026-07-01_TSLA_Q1.md").write_text("x", encoding="utf-8")
        (reports / "2026-07-09_TSLA_Q4.md").write_text("x", encoding="utf-8")
        found = rh.match_reports("TSLA", reports)
        assert found[0].startswith("2026-07-09")


class TestBuildHistory:
    def test_joins_outcomes_and_sorts_newest_first(self):
        preds = [
            make_pred("TSLA", "a", "2026-07-01T00:00:00Z"),
            make_pred("TSLA", "b", "2026-07-08T00:00:00Z", direction="short"),
            make_pred("AAPL", "c", "2026-07-05T00:00:00Z"),
        ]
        outs = [make_outcome("a", "WIN", 5.2)]
        hist = rh.build_history("TSLA", preds, outs)
        assert hist["prediction_count"] == 2
        assert hist["predictions"][0]["id"] == "b"
        assert hist["predictions"][1]["outcome"]["status"] == "WIN"
        assert hist["predictions"][0]["outcome"] is None
        assert hist["last_direction"] == "short"

    def test_does_not_mutate_inputs(self):
        preds = [make_pred("TSLA", "a", "2026-07-01T00:00:00Z")]
        outs = [make_outcome("a", "WIN", 5.2)]
        snapshot = json.dumps([preds, outs], sort_keys=True)
        rh.build_history("TSLA", preds, outs)
        assert json.dumps([preds, outs], sort_keys=True) == snapshot

    def test_stats_counts(self):
        preds = [make_pred("X", str(i), f"2026-07-0{i+1}T00:00:00Z")
                 for i in range(4)]
        outs = [make_outcome("0", "WIN", 3.0), make_outcome("1", "LOSS", -2.0),
                make_outcome("2", "NOT_FILLED")]
        stats = rh.build_history("X", preds, outs)["stats"]
        assert stats == {"WIN": 1, "LOSS": 1, "NOT_FILLED": 1, "PENDING": 1}

    def test_empty_history(self):
        hist = rh.build_history("ZZZZ", [], [])
        assert hist["prediction_count"] == 0
        assert hist["predictions"] == []
        assert hist["last_direction"] is None


class TestCalibrationFeedback:
    @staticmethod
    def make_pair(pid: str, confidence: int, status: str,
                  question_type: str = "Q1_short_entry"):
        pred = make_pred("X", pid, "2026-07-01T00:00:00Z")
        pred["confidence_score"] = confidence
        pred["question_type"] = question_type
        return pred, make_outcome(pid, status)

    def test_small_sample_disables_feedback(self):
        preds, outs = [], []
        for i in range(5):
            p, o = self.make_pair(str(i), 75, "WIN")
            preds.append(p)
            outs.append(o)
        fb = rh.calibration_feedback(preds, outs)
        assert fb["resolved_n"] == 5
        assert "note" in fb
        assert "overconfident_buckets" not in fb

    def test_overconfident_bucket_flagged(self):
        preds, outs = [], []
        # confidence 75 x20, actual win rate 40% -> gap 35pp >= 15pp
        for i in range(20):
            p, o = self.make_pair(str(i), 75, "WIN" if i < 8 else "LOSS")
            preds.append(p)
            outs.append(o)
        fb = rh.calibration_feedback(preds, outs)
        assert fb["resolved_n"] == 20
        assert fb["overconfident_buckets"] == ["[70-79]"]

    def test_well_calibrated_bucket_not_flagged(self):
        preds, outs = [], []
        # confidence 55 x20, actual win rate 50% -> gap 5pp < 15pp
        for i in range(20):
            p, o = self.make_pair(str(i), 55, "WIN" if i % 2 else "LOSS")
            preds.append(p)
            outs.append(o)
        fb = rh.calibration_feedback(preds, outs)
        assert fb["overconfident_buckets"] == []

    def test_screened_out_excluded(self):
        preds, outs = [], []
        for i in range(20):
            p, o = self.make_pair(str(i), 75, "LOSS",
                                  question_type="Q3_screened_out")
            preds.append(p)
            outs.append(o)
        fb = rh.calibration_feedback(preds, outs)
        assert fb["resolved_n"] == 0
