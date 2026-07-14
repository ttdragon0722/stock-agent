"""Regression tests for fetch_ohlcv incremental logic (partial-bar ts drift)."""
import common
import fetch_ohlcv as fo


def bar(ts: int, close: float = 100.0) -> tuple:
    return ("3030.TW", "1d", ts, close, close, close, close, 1000.0,
            "yahoo", 1_780_000_000)


DAY = 86400
T_OPEN = 1_783_558_800       # 2026-07-09T01:00:00Z 正規開盤 ts
T_PARTIAL = T_OPEN + 16201   # 盤中即時 bar 的漂移 ts(05:30:01Z)


def yahoo_payload(bars: list[dict]) -> dict:
    """組一份最小可用的 Yahoo v8 chart 回應。"""
    return {"chart": {"error": None, "result": [{
        "timestamp": [b["ts"] for b in bars],
        "indicators": {"quote": [{
            k: [b[k] for b in bars] for k in
            ("open", "high", "low", "close", "volume")
        }]},
    }]}}


class TestPlaceholderBarFilter:
    """颱風假/停牌日 Yahoo 會回傳四價相同且零量的 placeholder bar,
    不得入庫(2026-07-10 台股颱風休市即實例)。"""

    def test_flat_zero_volume_bar_skipped(self):
        payload = yahoo_payload([
            {"ts": T_OPEN - DAY, "open": 31.8, "high": 32.15, "low": 31.6,
             "close": 31.88, "volume": 18349402},
            {"ts": T_OPEN, "open": 31.94, "high": 31.94, "low": 31.94,
             "close": 31.94, "volume": None},   # 休市 placeholder
        ])
        rows = fo.parse_yahoo_chart("00918.TW", "1d", payload, 0)
        assert [r[2] for r in rows] == [T_OPEN - DAY]

    def test_limit_locked_bar_with_volume_kept(self):
        """漲停鎖死一價到底但有成交量 → 真實 bar,必須保留。"""
        payload = yahoo_payload([
            {"ts": T_OPEN, "open": 299.0, "high": 299.0, "low": 299.0,
             "close": 299.0, "volume": 5000},
        ])
        rows = fo.parse_yahoo_chart("3030.TW", "1d", payload, 0)
        assert len(rows) == 1


class TestRefetchWindowDedup:
    def test_stray_partial_bar_replaced_by_canonical(self, tmp_path, monkeypatch):
        """昨日存入的盤中 bar(ts 漂移)必須被正規 bar 取代,不得同日兩根。"""
        con = common.get_market_db(tmp_path / "m.db")
        try:
            fo.upsert(con, [bar(T_OPEN - DAY), bar(T_PARTIAL, 299.0)])
            monkeypatch.setattr(
                fo, "fetch_yahoo",
                lambda sym, tf, min_ts, now: [bar(T_OPEN - DAY),
                                              bar(T_OPEN, 299.0)])
            out = fo.fetch_one(con, "3030.TW", "stock", "1d", 500)
            ts_list = [r[0] for r in con.execute(
                "SELECT ts FROM ohlcv WHERE symbol='3030.TW' ORDER BY ts")]
            assert T_PARTIAL not in ts_list      # 漂移 bar 已清除
            assert ts_list == [T_OPEN - DAY, T_OPEN]
            assert out["fetched_rows"] == 2
        finally:
            con.close()

    def test_no_new_bars_is_up_to_date_not_error(self, tmp_path, monkeypatch):
        """已有本地資料時,抓不到新 K 線(假日/未收盤)不是錯誤。"""
        con = common.get_market_db(tmp_path / "m.db")
        try:
            fo.upsert(con, [bar(T_OPEN)])
            monkeypatch.setattr(fo, "fetch_yahoo",
                                lambda sym, tf, min_ts, now: [])
            out = fo.fetch_one(con, "3030.TW", "stock", "1d", 500)
            assert out["fetched_rows"] == 0
            assert out["note"] == "up_to_date"
            assert con.execute(
                "SELECT COUNT(*) FROM ohlcv").fetchone()[0] == 1  # 未誤刪
        finally:
            con.close()

    def test_new_symbol_with_no_data_still_errors(self, tmp_path, monkeypatch):
        con = common.get_market_db(tmp_path / "m.db")
        try:
            monkeypatch.setattr(fo, "fetch_yahoo",
                                lambda sym, tf, min_ts, now: [])
            try:
                fo.fetch_one(con, "ZZZZ.TW", "stock", "1d", 500)
                raised = False
            except ValueError:
                raised = True
            assert raised
        finally:
            con.close()
