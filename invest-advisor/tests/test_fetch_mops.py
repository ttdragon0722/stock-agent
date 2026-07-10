"""Unit tests for fetch_mops.py (重大訊息 + 月營收,官方一手資料)."""
import fetch_mops as fm


TWSE_ANNOUNCEMENTS = [
    {"出表日期": "1150710", "發言日期": "1150709", "發言時間": "70003",
     "公司代號": "1721", "公司名稱": "三晃", "主旨 ": "公告更名",
     "符合條款": "第51款", "事實發生日": "1150629", "說明": "詳細說明文字"},
    {"出表日期": "1150710", "發言日期": "1150709", "發言時間": "203945",
     "公司代號": "2330", "公司名稱": "台積電", "主旨 ": "澄清媒體報導",
     "符合條款": "第53款", "事實發生日": "1150709", "說明": "x" * 900},
]

TPEX_ANNOUNCEMENTS = [
    {"Date": "1150710", "發言日期": "1150709", "發言時間": "203945",
     "SecuritiesCompanyCode": "6488", "CompanyName": "環球晶",
     "主旨": "本公司與客戶美光科技簽訂合作意向書",
     "符合條款": "第10款", "事實發生日": "1150709", "說明": "契約內容"},
]

REVENUE_ROWS = [
    {"出表日期": "1150617", "資料年月": "11505", "公司代號": "2330",
     "公司名稱": "台積電", "產業別": "半導體",
     "營業收入-當月營收": "12,612,013", "營業收入-上月營收": "12213195",
     "營業收入-去年當月營收": "12619495",
     "營業收入-上月比較增減(%)": "3.2654", "營業收入-去年同月增減(%)": "-0.0592",
     "累計營業收入-當月累計營收": "58084626",
     "累計營業收入-去年累計營收": "60273039",
     "累計營業收入-前期比較增減(%)": None, "備註": ""},
]


class TestFilterAnnouncements:
    def test_twse_match_and_normalize(self):
        out = fm.filter_announcements(TWSE_ANNOUNCEMENTS, "2330")
        assert len(out) == 1
        assert out[0]["date"] == "2026-07-09"
        assert out[0]["subject"] == "澄清媒體報導"
        assert out[0]["matched_clause"] == "第53款"

    def test_detail_truncated(self):
        out = fm.filter_announcements(TWSE_ANNOUNCEMENTS, "2330")
        assert len(out[0]["detail"]) <= fm.DETAIL_MAX_CHARS + 1

    def test_tpex_key_variant(self):
        out = fm.filter_announcements(TPEX_ANNOUNCEMENTS, "6488")
        assert len(out) == 1
        assert "美光" in out[0]["subject"]

    def test_no_match(self):
        assert fm.filter_announcements(TWSE_ANNOUNCEMENTS, "0000") == []


class TestParseRevenue:
    def test_found_with_commas_and_null(self):
        out = fm.parse_revenue(REVENUE_ROWS, "2330")
        assert out["year_month"] == "2026-05"
        assert out["revenue_thousand_twd"] == 12_612_013
        assert out["mom_pct"] == 3.27
        assert out["yoy_pct"] == -0.06
        assert out["cum_yoy_pct"] == 0.0  # JSON null → 0,不得炸掉

    def test_not_found_returns_none(self):
        assert fm.parse_revenue(REVENUE_ROWS, "0000") is None


class TestFieldNullSafety:
    def test_null_value_becomes_empty_string(self):
        rows = [{**TWSE_ANNOUNCEMENTS[1], "說明": None}]
        out = fm.filter_announcements(rows, "2330")
        assert out[0]["detail"] == ""  # 不得出現字面 "None"


class TestDatasetUrls:
    def test_twse(self):
        urls = fm.dataset_urls("2330.TW")
        assert "t187ap04_L" in urls["announcements"]
        assert "t187ap05_L" in urls["revenue"]

    def test_tpex(self):
        urls = fm.dataset_urls("6488.TWO")
        assert "t187ap04_O" in urls["announcements"]
        assert "t187ap05_O" in urls["revenue"]
