"""Unit tests for the Q6 daily-report watchlist (active-symbol listing)."""
import common
import watchlist as wl

NOW = 1768521600  # 2026-01-16T00:00:00Z
DAY = 86400


def make_pred(**overrides) -> dict:
    base = {
        "id": "2026-01-10-0050.TW-q4",
        "asset": "0050.TW",
        "asset_type": "stock",
        "question_type": "Q4_levels",
        "direction": "long",
        "recommendation_score": 61,
        "confidence_score": 55,
        "price_at_analysis": 105.8,
        "horizon_days": 30,
        "timestamp": common.iso_utc(NOW - 6 * DAY),
    }
    return {**base, **overrides}


class TestIsActive:
    def test_within_horizon_is_active(self):
        assert wl.is_active(make_pred(), NOW, grace_days=0)

    def test_expired_horizon_is_inactive(self):
        rec = make_pred(timestamp=common.iso_utc(NOW - 40 * DAY))
        assert not wl.is_active(rec, NOW, grace_days=0)

    def test_grace_days_keeps_recently_expired(self):
        rec = make_pred(timestamp=common.iso_utc(NOW - 32 * DAY))
        assert not wl.is_active(rec, NOW, grace_days=0)
        assert wl.is_active(rec, NOW, grace_days=3)

    def test_screened_out_never_watched(self):
        rec = make_pred(question_type="Q3_screened_out")
        assert not wl.is_active(rec, NOW, grace_days=0)


class TestBuildWatchlist:
    def test_groups_by_symbol_and_joins_status(self):
        preds = [
            make_pred(),
            make_pred(id="2026-01-14-0050.TW-q6",
                      question_type="Q6_daily",
                      timestamp=common.iso_utc(NOW - 2 * DAY)),
            make_pred(id="2026-01-12-3030.TW-q4", asset="3030.TW",
                      direction="neutral",
                      timestamp=common.iso_utc(NOW - 4 * DAY)),
        ]
        outcomes = [{"id": "2026-01-10-0050.TW-q4", "status": "OPEN"}]
        doc = wl.build_watchlist(preds, outcomes, NOW)

        assert doc["count"] == 2
        top = doc["symbols"][0]  # sorted by last_analysis desc
        assert top["symbol"] == "0050.TW"
        assert top["active_predictions"] == 2
        assert top["last_question_type"] == "Q6_daily"
        statuses = {p["id"]: p["status"] for p in top["predictions"]}
        assert statuses["2026-01-10-0050.TW-q4"] == "OPEN"
        assert statuses["2026-01-14-0050.TW-q6"] == "UNVERIFIED"

    def test_horizon_end_is_max_across_predictions(self):
        preds = [
            make_pred(),
            make_pred(id="x2", horizon_days=90,
                      timestamp=common.iso_utc(NOW - 2 * DAY)),
        ]
        doc = wl.build_watchlist(preds, [], NOW)
        expected = common.iso_utc(NOW - 2 * DAY + 90 * DAY)[:10]
        assert doc["symbols"][0]["horizon_end"] == expected

    def test_expired_and_counterfactual_excluded(self):
        preds = [
            make_pred(timestamp=common.iso_utc(NOW - 60 * DAY)),
            make_pred(id="cf", question_type="Q3_screened_out"),
        ]
        doc = wl.build_watchlist(preds, [], NOW)
        assert doc["count"] == 0
        assert doc["symbols"] == []

    def test_analyzed_within_scope_guard(self):
        preds = [
            make_pred(),  # analyzed 6 days ago
            make_pred(id="old", asset="2330.TW", horizon_days=180,
                      timestamp=common.iso_utc(NOW - 30 * DAY)),
        ]
        doc = wl.build_watchlist(preds, [], NOW, analyzed_within=14)
        assert doc["count"] == 1
        assert doc["symbols"][0]["symbol"] == "0050.TW"

    def test_malformed_record_skipped(self):
        preds = [make_pred(), {"asset": "BAD.TW", "timestamp": "2026-01-10"}]
        doc = wl.build_watchlist(preds, [], NOW)
        assert doc["count"] == 1

    def test_input_not_mutated(self):
        pred = make_pred()
        snapshot = dict(pred)
        wl.build_watchlist([pred], [], NOW)
        assert pred == snapshot
