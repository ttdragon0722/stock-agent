"""Unit tests for fetch_chips.py parsing/aggregation (台股籌碼面)."""
import pytest

import common
import fetch_chips as fc


T86_FIELDS = ["證券代號", "證券名稱",
              "外陸資買進股數(不含外資自營商)", "外陸資賣出股數(不含外資自營商)",
              "外陸資買賣超股數(不含外資自營商)",
              "外資自營商買進股數", "外資自營商賣出股數", "外資自營商買賣超股數",
              "投信買進股數", "投信賣出股數", "投信買賣超股數",
              "自營商買賣超股數",
              "自營商買進股數(自行買賣)", "自營商賣出股數(自行買賣)",
              "自營商買賣超股數(自行買賣)",
              "自營商買進股數(避險)", "自營商賣出股數(避險)", "自營商買賣超股數(避險)",
              "三大法人買賣超股數"]

T86_PAYLOAD = {
    "stat": "OK",
    "fields": T86_FIELDS,
    "data": [
        ["2330", "台積電          ", "16,267,509", "29,016,050", "-12,748,541",
         "0", "0", "0", "361,457", "318,232", "43,225", "89,863",
         "392,405", "391,500", "905", "636,358", "547,400", "88,958",
         "-12,615,453"],
    ],
}

MARGIN_TABLE = {
    "title": "115年07月09日 融資融券彙總 (全部)",
    "fields": ["代號", "名稱", "買進", "賣出", "現金償還", "前日餘額",
               "今日餘額", "次一營業日限額", "買進", "賣出", "現券償還",
               "前日餘額", "今日餘額", "次一營業日限額", "資券互抵", "註記"],
    "data": [["2330", "台積電", "1,064", "272", "14", "32,283", "33,061",
              "6,483,092", "14", "0", "0", "85", "71", "6,483,092",
              "0", " "]],
}

MARGIN_PAYLOAD = {
    "stat": "OK",
    "tables": [{"title": "信用交易統計", "fields": [], "data": []},
               MARGIN_TABLE],
}

TPEX_3INSTI_ROWS = [
    {"Date": "1150709", "SecuritiesCompanyCode": "6488", "CompanyName": "環球晶",
     "ForeignInvestorsInclude MainlandAreaInvestors-Difference": "-120,000",
     "SecuritiesInvestmentTrustCompanies-Difference": "5000",
     "Dealers-Difference": "-3,000",
     "TotalDifference": "-118,000"},
]


class TestParseNumbers:
    def test_commas_and_negative(self):
        assert common.parse_int("16,267,509") == 16_267_509
        assert common.parse_int("-3,000") == -3_000

    def test_none_and_blank_are_zero(self):
        assert common.parse_int(None) == 0
        assert common.parse_int("") == 0
        assert common.parse_int("   ") == 0

    def test_placeholders_are_zero(self):
        for junk in ("--", "—", "N/A", "null", "None", "不適用"):
            assert common.parse_int(junk) == 0, junk

    def test_parse_float(self):
        assert common.parse_float("3.2654") == pytest.approx(3.2654)
        assert common.parse_float(None) == 0.0
        assert common.parse_float("--") == 0.0
        assert common.parse_float("1,234.5") == pytest.approx(1234.5)


class TestRocToIso:
    def test_date(self):
        assert common.roc_to_iso("1150709") == "2026-07-09"

    def test_year_month(self):
        assert common.roc_ym_to_iso("11505") == "2026-05"

    def test_bad_input_raises(self):
        with pytest.raises(ValueError):
            common.roc_to_iso("07-09")


class TestMarketFor:
    def test_twse(self):
        assert fc.market_for("2330.TW") == "twse"

    def test_tpex(self):
        assert fc.market_for("6488.TWO") == "tpex"

    def test_non_taiwan_raises(self):
        with pytest.raises(ValueError):
            fc.market_for("TSLA")


class TestParseT86:
    def test_found(self):
        out = fc.parse_t86(T86_PAYLOAD, "2330")
        assert out == {"foreign_net": -12_748_541, "trust_net": 43_225,
                       "dealer_net": 89_863, "total_net": -12_615_453}

    def test_lookup_is_by_field_name_not_position(self):
        """官方調整欄位順序時必須仍解析正確(靜默錯位是最危險失效)。"""
        fields = list(T86_FIELDS)
        row = list(T86_PAYLOAD["data"][0])
        # 把「三大法人買賣超股數」搬到最前面(代號之後)
        fields.insert(1, fields.pop(18))
        row.insert(1, row.pop(18))
        out = fc.parse_t86({"stat": "OK", "fields": fields, "data": [row]},
                           "2330")
        assert out["total_net"] == -12_615_453
        assert out["foreign_net"] == -12_748_541

    def test_missing_expected_field_raises(self):
        fields = [f for f in T86_FIELDS if f != "投信買賣超股數"]
        payload = {"stat": "OK", "fields": fields, "data": []}
        with pytest.raises(ValueError, match="T86"):
            fc.parse_t86(payload, "2330")

    def test_short_row_skipped(self):
        payload = {"stat": "OK", "fields": T86_FIELDS,
                   "data": [["2330", "台積電"]]}
        assert fc.parse_t86(payload, "2330") is None

    def test_not_found_returns_none(self):
        assert fc.parse_t86(T86_PAYLOAD, "0000") is None

    def test_non_ok_stat_returns_none(self):
        assert fc.parse_t86({"stat": "很抱歉,沒有符合條件的資料!"}, "2330") is None


class TestParseMargin:
    def test_found(self):
        out = fc.parse_margin(MARGIN_PAYLOAD, "2330")
        assert out == {"margin_balance": 33_061, "margin_change": 778,
                       "short_balance": 71, "short_change": -14}

    def test_table_located_by_title_not_position(self):
        payload = {"stat": "OK", "tables": [MARGIN_TABLE]}
        assert fc.parse_margin(payload, "2330")["margin_balance"] == 33_061

    def test_no_margin_table_returns_none(self):
        payload = {"stat": "OK",
                   "tables": [{"title": "信用交易統計", "fields": [], "data": []}]}
        assert fc.parse_margin(payload, "2330") is None

    def test_changed_field_structure_raises(self):
        broken = {**MARGIN_TABLE, "fields": ["代號", "名稱", "前日餘額", "今日餘額"]}
        with pytest.raises(ValueError, match="MI_MARGN"):
            fc.parse_margin({"stat": "OK", "tables": [broken]}, "2330")

    def test_placeholder_values_treated_as_zero(self):
        table = {**MARGIN_TABLE,
                 "data": [["0050", "元大台灣50", "--", "--", "--", "--", "--",
                           "--", "--", "--", "--", "--", "--", "--", "--", " "]]}
        out = fc.parse_margin({"stat": "OK", "tables": [table]}, "0050")
        assert out == {"margin_balance": 0, "margin_change": 0,
                       "short_balance": 0, "short_change": 0}

    def test_not_found_returns_none(self):
        assert fc.parse_margin(MARGIN_PAYLOAD, "0000") is None


class TestParseTpex3Insti:
    def test_found(self):
        date_iso, out = fc.parse_tpex_3insti(TPEX_3INSTI_ROWS, "6488")
        assert date_iso == "2026-07-09"
        assert out == {"foreign_net": -120_000, "trust_net": 5_000,
                       "dealer_net": -3_000, "total_net": -118_000}

    def test_null_value_treated_as_zero(self):
        rows = [{**TPEX_3INSTI_ROWS[0], "Dealers-Difference": None}]
        _, out = fc.parse_tpex_3insti(rows, "6488")
        assert out["dealer_net"] == 0

    def test_not_found_returns_none(self):
        assert fc.parse_tpex_3insti(TPEX_3INSTI_ROWS, "0000") is None


class TestNonTradingCache:
    def test_today_never_marked(self):
        """當日資料可能尚未發布,不得永久標記休市。"""
        assert not fc.should_mark_non_trading("2026-07-10", "2026-07-10")
        assert fc.should_mark_non_trading("2026-07-09", "2026-07-10")
        assert not fc.should_mark_non_trading("2026-07-11", "2026-07-10")

    def test_mark_and_load(self, tmp_path):
        con = common.get_market_db(tmp_path / "m.db")
        try:
            fc.mark_non_trading(con, "twse", "2026-07-04")
            fc.mark_non_trading(con, "twse", "2026-07-04")  # idempotent
            assert fc.load_non_trading(con, "twse") == {"2026-07-04"}
            assert fc.load_non_trading(con, "tpex") == set()
        finally:
            con.close()


class TestUpsertAndSummary:
    def test_upsert_idempotent_and_cumulative(self, tmp_path):
        con = common.get_market_db(tmp_path / "m.db")
        try:
            for day, net in [("2026-07-07", 100), ("2026-07-08", -30),
                             ("2026-07-09", 50)]:
                row = {"foreign_net": net, "trust_net": 10, "dealer_net": 0,
                       "total_net": net + 10}
                fc.upsert_chips(con, "2330.TW", day, row, "twse", 1_780_000_000)
                fc.upsert_chips(con, "2330.TW", day, row, "twse", 1_780_000_000)
            rows = fc.load_chips(con, "2330.TW")
            assert len(rows) == 3
            assert rows[-1]["date"] == "2026-07-09"
            summary = fc.summarize(rows)
            assert summary["days_available"] == 3
            assert summary["foreign_net_5d"] == 120
            assert summary["trust_net_5d"] == 30
        finally:
            con.close()
