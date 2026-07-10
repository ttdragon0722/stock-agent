"""Unit tests for calibration statistics."""
import pytest

import calibration_report as cal


class TestBrier:
    def test_perfect_predictions(self):
        pairs = [(1.0, 1), (0.0, 0), (1.0, 1)]
        assert cal.brier_score(pairs) == 0.0

    def test_worst_predictions(self):
        pairs = [(1.0, 0), (0.0, 1)]
        assert cal.brier_score(pairs) == 1.0

    def test_baseline_50(self):
        pairs = [(0.5, 1), (0.5, 0)]
        assert cal.brier_score(pairs) == 0.25

    def test_empty(self):
        assert cal.brier_score([]) is None


class TestConfidenceCalibration:
    def test_bucketing_and_win_rate(self):
        rows = [
            {"confidence_score": 75, "status": "WIN"},
            {"confidence_score": 78, "status": "LOSS"},
            {"confidence_score": 55, "status": "WIN"},
        ]
        table = cal.confidence_calibration(rows)
        b7080 = next(r for r in table if r["bucket"] == "[70-79]")
        assert b7080["n"] == 2
        assert b7080["actual_win_rate"] == 50.0
        b5060 = next(r for r in table if r["bucket"] == "[50-59]")
        assert b5060["n"] == 1
        assert b5060["actual_win_rate"] == 100.0

    def test_empty_buckets_are_none(self):
        table = cal.confidence_calibration([])
        assert all(r["actual_win_rate"] is None for r in table)


class TestMonotonicity:
    def test_avg_return_per_bucket(self):
        rows = [
            {"recommendation_score": 85, "return_pct": 10.0},
            {"recommendation_score": 90, "return_pct": 6.0},
            {"recommendation_score": 65, "return_pct": 2.0},
            {"recommendation_score": 30, "return_pct": -4.0},
        ]
        table = cal.recommendation_monotonicity(rows)
        top = next(r for r in table if r["bucket"] == "[80-100]")
        assert top["avg_return_pct"] == 8.0
        low = next(r for r in table if r["bucket"] == "[1-39]")
        assert low["avg_return_pct"] == -4.0


class TestRegime:
    @pytest.mark.parametrize("bench,expected", [
        (5.0, "bull"), (-5.0, "bear"), (1.0, "sideways"), (None, "unknown"),
    ])
    def test_classify(self, bench, expected):
        assert cal.classify_regime(bench) == expected

    def test_regime_split_win_rates(self):
        rows = [
            {"benchmark_return_pct": 6.0, "status": "WIN"},
            {"benchmark_return_pct": 7.0, "status": "LOSS"},
            {"benchmark_return_pct": -6.0, "status": "WIN"},
        ]
        table = cal.regime_split(rows)
        bull = next(r for r in table if r["regime"] == "bull")
        assert bull["n"] == 2 and bull["win_rate"] == 50.0
        bear = next(r for r in table if r["regime"] == "bear")
        assert bear["win_rate"] == 100.0


class TestJoinAndReport:
    def test_join_merges_prediction_fields(self):
        preds = [{"id": "a", "confidence_score": 70,
                  "recommendation_score": 80, "asset": "TSLA"}]
        outs = [{"id": "a", "status": "WIN", "return_pct": 5.0}]
        joined = cal.join_records(preds, outs)
        assert joined[0]["asset"] == "TSLA"
        assert joined[0]["status"] == "WIN"

    def test_join_skips_orphan_outcomes(self):
        outs = [{"id": "ghost", "status": "WIN"}]
        assert cal.join_records([], outs) == []

    def test_build_report_renders(self):
        preds = [{"id": "a", "confidence_score": 70,
                  "recommendation_score": 80, "asset": "TSLA",
                  "rubric_version": "1.0.0"}]
        outs = [{"id": "a", "status": "WIN", "return_pct": 5.0,
                 "benchmark_return_pct": 2.0}]
        report = cal.build_report(cal.join_records(preds, outs), "2026-07-04")
        assert "Brier Score" in report
        assert "樣本不足" in report  # n < 50 warning present
