"""Unit tests for cache_news.py (news_cache.db 寫入/讀取)."""
import pytest

import cache_news as cn
import common


def valid_item() -> dict:
    return {
        "symbol": "2330.TW",
        "headline": "台積電法說會釋出樂觀展望",
        "summary": "Q2 財報超預期,上修全年資本支出",
        "sentiment": "positive",
        "published_at": "2026-07-09T08:00:00Z",
        "source_url": "https://example.com/news/1",
    }


@pytest.fixture
def con(tmp_path):
    c = common.get_news_db(tmp_path / "news.db")
    yield c
    c.close()


NOW = 1_780_000_000


class TestValidate:
    def test_valid_item_passes(self):
        assert cn.validate_item(valid_item()) == []

    def test_missing_required_fields(self):
        for field in ("symbol", "headline", "source_url"):
            item = valid_item()
            del item[field]
            assert any(field in e for e in cn.validate_item(item)), field

    def test_bad_sentiment_rejected(self):
        item = {**valid_item(), "sentiment": "bullish"}
        assert any("sentiment" in e for e in cn.validate_item(item))

    def test_blank_headline_rejected(self):
        item = {**valid_item(), "headline": "   "}
        assert any("headline" in e for e in cn.validate_item(item))

    def test_published_at_optional(self):
        item = valid_item()
        del item["published_at"]
        assert cn.validate_item(item) == []

    def test_published_at_epoch_int_ok(self):
        item = {**valid_item(), "published_at": 1_780_000_000}
        assert cn.validate_item(item) == []

    def test_published_at_without_timezone_rejected(self):
        item = {**valid_item(), "published_at": "2026-07-09T08:00:00"}
        assert any("published_at" in e for e in cn.validate_item(item))

    def test_published_at_garbage_rejected(self):
        item = {**valid_item(), "published_at": "N/A"}
        assert any("published_at" in e for e in cn.validate_item(item))


class TestSaveRecall:
    def test_save_then_recall(self, con):
        saved = cn.save_items(con, [valid_item()], NOW, ttl_hours=24)
        assert saved == 1
        items = cn.recall_items(con, "2330.tw", NOW + 3600)
        assert len(items) == 1
        assert items[0]["headline"] == valid_item()["headline"]
        assert items[0]["source_url"] == valid_item()["source_url"]

    def test_expired_items_not_recalled(self, con):
        cn.save_items(con, [valid_item()], NOW, ttl_hours=24)
        assert cn.recall_items(con, "2330.TW", NOW + 25 * 3600) == []

    def test_duplicate_headline_skipped_while_fresh(self, con):
        assert cn.save_items(con, [valid_item()], NOW, ttl_hours=24) == 1
        assert cn.save_items(con, [valid_item()], NOW + 60, ttl_hours=24) == 0

    def test_non_dict_item_raises_valueerror(self, con):
        with pytest.raises(ValueError, match="item\\[1\\]"):
            cn.save_items(con, [valid_item(), "not a dict"], NOW, ttl_hours=24)
        assert cn.recall_items(con, "2330.TW", NOW) == []

    def test_invalid_item_raises_saves_nothing(self, con):
        bad = {**valid_item(), "sentiment": "moon"}
        with pytest.raises(ValueError):
            cn.save_items(con, [valid_item(), bad], NOW, ttl_hours=24)
        assert cn.recall_items(con, "2330.TW", NOW) == []

    def test_recall_filters_by_symbol(self, con):
        other = {**valid_item(), "symbol": "TSLA"}
        cn.save_items(con, [valid_item(), other], NOW, ttl_hours=24)
        assert len(cn.recall_items(con, "TSLA", NOW)) == 1

    def test_iso_published_at_stored_as_epoch(self, con):
        cn.save_items(con, [valid_item()], NOW, ttl_hours=24)
        item = cn.recall_items(con, "2330.TW", NOW)[0]
        assert item["published_at"] == common.iso_to_epoch("2026-07-09T08:00:00Z")
