"""Unit tests for the real-holdings tracker (portfolio.py).

Tests operate on in-memory docs and a temp SQLite market.db — never the
user's real data/portfolio.json.
"""
import common
import portfolio as pf


def make_doc(*positions: dict) -> dict:
    doc = pf.empty_doc()
    return {**doc, "positions": list(positions)}


class TestSetPosition:
    def test_set_new_symbol(self):
        doc = pf.set_position(pf.empty_doc(), "0050.TW", 70, 101.9)
        assert len(doc["positions"]) == 1
        p = doc["positions"][0]
        assert p["symbol"] == "0050.TW"
        assert p["shares"] == 70
        assert p["avg_cost"] == 101.9
        assert doc["updated_at"] is not None

    def test_set_uppercases_symbol(self):
        doc = pf.set_position(pf.empty_doc(), "3030.tw", 20, 300)
        assert doc["positions"][0]["symbol"] == "3030.TW"

    def test_set_replaces_existing_not_blends(self):
        doc = pf.set_position(pf.empty_doc(), "0050.TW", 70, 101.9)
        doc = pf.set_position(doc, "0050.TW", 100, 99.0)
        assert len(doc["positions"]) == 1
        assert doc["positions"][0]["shares"] == 100
        assert doc["positions"][0]["avg_cost"] == 99.0

    def test_set_does_not_mutate_input(self):
        original = pf.empty_doc()
        pf.set_position(original, "0050.TW", 70, 101.9)
        assert original["positions"] == []

    def test_whole_shares_stay_int(self):
        doc = pf.set_position(pf.empty_doc(), "0050.TW", 70.0, 101.9)
        assert isinstance(doc["positions"][0]["shares"], int)

    def test_fractional_shares_kept(self):
        doc = pf.set_position(pf.empty_doc(), "BTCUSDT", 0.25, 100000,
                              asset_type="crypto")
        assert doc["positions"][0]["shares"] == 0.25

    def test_rejects_non_positive_shares(self):
        try:
            pf.set_position(pf.empty_doc(), "0050.TW", 0, 100)
            assert False, "expected ValueError"
        except ValueError:
            pass

    def test_rejects_negative_cost(self):
        try:
            pf.set_position(pf.empty_doc(), "0050.TW", 10, -1)
            assert False, "expected ValueError"
        except ValueError:
            pass


class TestAddLot:
    def test_add_to_empty_is_a_set(self):
        doc = pf.add_lot(pf.empty_doc(), "3413.TW", 20, 324)
        assert doc["positions"][0]["shares"] == 20
        assert doc["positions"][0]["avg_cost"] == 324

    def test_add_blends_weighted_average(self):
        doc = pf.set_position(pf.empty_doc(), "0050.TW", 70, 100.0)
        doc = pf.add_lot(doc, "0050.TW", 30, 110.0)
        p = doc["positions"][0]
        assert p["shares"] == 100
        # (70*100 + 30*110) / 100 = 103.0
        assert p["avg_cost"] == 103.0

    def test_add_does_not_mutate_input(self):
        doc = pf.set_position(pf.empty_doc(), "0050.TW", 70, 100.0)
        snapshot = doc["positions"][0]["shares"]
        pf.add_lot(doc, "0050.TW", 30, 110.0)
        assert doc["positions"][0]["shares"] == snapshot


class TestRemove:
    def test_remove_drops_symbol(self):
        doc = make_doc({"symbol": "0050.TW", "shares": 70, "avg_cost": 101.9})
        doc = pf.remove_position(doc, "0050.TW")
        assert doc["positions"] == []

    def test_remove_is_case_insensitive(self):
        doc = make_doc({"symbol": "0050.TW", "shares": 70, "avg_cost": 101.9})
        assert pf.remove_position(doc, "0050.tw")["positions"] == []

    def test_remove_missing_is_noop(self):
        doc = make_doc({"symbol": "0050.TW", "shares": 70, "avg_cost": 101.9})
        assert len(pf.remove_position(doc, "3030.TW")["positions"]) == 1


class TestPricingAndSnapshot:
    def _seed_bar(self, con, symbol, close, ts=1784854800):
        con.execute(
            "INSERT OR REPLACE INTO ohlcv "
            "(symbol, timeframe, ts, open, high, low, close, volume, source, fetched_at) "
            "VALUES (?, '1d', ?, ?, ?, ?, ?, 0, 'test', 0)",
            (symbol.upper(), ts, close, close, close, close))
        con.commit()

    def test_price_position_computes_pnl(self, tmp_path):
        con = common.get_market_db(tmp_path / "m.db")
        self._seed_bar(con, "0050.TW", 101.65)
        priced = pf.price_position(
            con, {"symbol": "0050.TW", "shares": 70, "avg_cost": 101.9})
        assert priced["priced"] is True
        assert priced["cost_basis"] == round(70 * 101.9, 2)
        assert priced["market_value"] == round(70 * 101.65, 2)
        assert priced["unrealized_pnl"] == round(70 * (101.65 - 101.9), 2)
        con.close()

    def test_price_position_unpriced_when_no_bar(self, tmp_path):
        con = common.get_market_db(tmp_path / "m.db")
        priced = pf.price_position(
            con, {"symbol": "9999.TW", "shares": 10, "avg_cost": 50})
        assert priced["priced"] is False
        assert priced["market_value"] is None
        con.close()

    def test_snapshot_totals_and_weights(self, tmp_path):
        con = common.get_market_db(tmp_path / "m.db")
        self._seed_bar(con, "0050.TW", 100.0)
        self._seed_bar(con, "3030.TW", 300.0)
        doc = make_doc(
            {"symbol": "0050.TW", "shares": 100, "avg_cost": 90.0},   # mv 10000
            {"symbol": "3030.TW", "shares": 10, "avg_cost": 300.0},   # mv 3000
        )
        snap = pf.build_snapshot(doc, con)
        assert snap["totals"]["market_value"] == 13000.0
        assert snap["totals"]["cost_basis"] == round(100 * 90 + 10 * 300, 2)
        # 0050 weight = 10000/13000
        w = {p["symbol"]: p["weight_pct"] for p in snap["positions"]}
        assert w["0050.TW"] == round(10000 / 13000 * 100, 2)
        con.close()

    def test_snapshot_reports_unpriced(self, tmp_path):
        con = common.get_market_db(tmp_path / "m.db")
        self._seed_bar(con, "0050.TW", 100.0)
        doc = make_doc(
            {"symbol": "0050.TW", "shares": 10, "avg_cost": 90.0},
            {"symbol": "9999.TW", "shares": 5, "avg_cost": 50.0},
        )
        snap = pf.build_snapshot(doc, con)
        assert snap["unpriced_symbols"] == ["9999.TW"]
        con.close()


class TestRoundTrip:
    def test_save_and_load(self, tmp_path):
        path = tmp_path / "portfolio.json"
        doc = pf.set_position(pf.empty_doc(), "0050.TW", 70, 101.9)
        common.write_json_atomic(path, doc)
        loaded = pf.load_portfolio(path)
        assert loaded["positions"][0]["shares"] == 70

    def test_load_missing_returns_empty(self, tmp_path):
        loaded = pf.load_portfolio(tmp_path / "nope.json")
        assert loaded["positions"] == []
