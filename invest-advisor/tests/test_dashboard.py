"""Unit tests for dashboard row computation and rendering."""
import dashboard as db

DAY = 86400
T0 = 1750000000


def make_pred(**overrides) -> dict:
    import common
    base = {
        "id": "p1", "asset": "TSLA", "question_type": "Q1_short_entry",
        "direction": "long", "recommendation_score": 70,
        "confidence_score": 60, "price_at_analysis": 100.0,
        "horizon_days": 14, "timestamp": common.iso_utc(T0),
        "risk_reward": 2.0,
    }
    return {**base, **overrides}


class TestBuildRows:
    def test_pending_not_expired(self):
        rows = db.build_rows([make_pred()], [], T0 + 3 * DAY)
        assert rows[0]["status"] == "未驗證"
        assert rows[0]["verifiable_now"] is False
        assert rows[0]["days_left"] == 11

    def test_expired_unverified_is_actionable(self):
        rows = db.build_rows([make_pred()], [], T0 + 20 * DAY)
        assert rows[0]["verifiable_now"] is True
        assert rows[0]["days_left"] == 0
        assert db.count_actionable(rows) == 1

    def test_resolved_not_actionable(self):
        outcomes = [{"id": "p1", "status": "WIN", "return_pct": 6.5,
                     "excess_return_pct": 4.0}]
        rows = db.build_rows([make_pred()], outcomes, T0 + 20 * DAY)
        assert rows[0]["status"] == "WIN"
        assert rows[0]["resolved"] is True
        assert rows[0]["verifiable_now"] is False
        assert rows[0]["return_pct"] == 6.5

    def test_no_data_is_actionable_even_before_expiry(self):
        outcomes = [{"id": "p1", "status": "NO_DATA"}]
        rows = db.build_rows([make_pred()], outcomes, T0 + 3 * DAY)
        assert rows[0]["verifiable_now"] is True

    def test_sorted_newest_first(self):
        import common
        old = make_pred(id="old")
        new = make_pred(id="new", timestamp=common.iso_utc(T0 + 30 * DAY))
        rows = db.build_rows([old, new], [], T0 + 40 * DAY)
        assert rows[0]["id"] == "new"

    def test_falsification_condition_carried(self):
        pred = make_pred(falsification_condition="日線收破 232")
        rows = db.build_rows([pred], [], T0)
        assert rows[0]["falsification_condition"] == "日線收破 232"

    def test_falsification_condition_missing_is_none(self):
        rows = db.build_rows([make_pred()], [], T0)
        assert rows[0]["falsification_condition"] is None


class TestRender:
    def test_html_contains_asset_and_banner(self):
        rows = db.build_rows([make_pred()], [], T0 + 20 * DAY)
        page = db.render_html(rows, ["r1.md"], "2026-07-04 10:00")
        assert "TSLA" in page
        assert "verify_predictions.py --fetch" in page
        assert "r1.md" in page

    def test_html_ok_banner_when_nothing_due(self):
        rows = db.build_rows([make_pred()], [], T0 + 3 * DAY)
        page = db.render_html(rows, [], "2026-07-04 10:00")
        assert "沒有待驗證" in page

    def test_html_escapes_content(self):
        rows = db.build_rows([make_pred(asset="<script>")], [], T0)
        page = db.render_html(rows, [], "now")
        assert "<script>" not in page.split("<table>")[1]

    def test_html_shows_falsification_condition(self):
        pred = make_pred(falsification_condition="日線收破 232")
        rows = db.build_rows([pred], [], T0)
        page = db.render_html(rows, [], "now")
        assert "失效條件" in page
        assert "日線收破 232" in page

    def test_html_escapes_falsification_condition(self):
        pred = make_pred(falsification_condition="<img onerror=x>")
        rows = db.build_rows([pred], [], T0)
        page = db.render_html(rows, [], "now")
        assert "<img" not in page.split("<table>")[1]

    def test_text_mode(self):
        rows = db.build_rows([make_pred()], [], T0 + 20 * DAY)
        assert "可驗證" in db.render_text(rows)
