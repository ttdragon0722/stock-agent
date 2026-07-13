"""Tests for log_events.py — validation, merge/dedup, sorting, filtering."""
import json

import log_events as le


def _event(**over):
    base = {"symbol": "3030.TW", "date": "2026-07-10",
            "title": "6 月營收 YoY +0.43%", "category": "revenue",
            "impact": "bearish", "description": "連三月減速",
            "source_url": "https://example.com"}
    return {**base, **over}


def _key_date(**over):
    base = {"symbol": "3030.TW", "date": "2026-08-10",
            "label": "7 月營收公告截止", "date_type": "revenue_release",
            "status": "estimated"}
    return {**base, **over}


def _payload(**over):
    base = {"report": "2026-07-13_3030-TW_Q1.md",
            "important_events": [_event()], "key_dates": [_key_date()]}
    return {**base, **over}


class TestValidatePayload:
    def test_valid_payload_passes(self):
        assert le.validate_payload(_payload()) == []

    def test_empty_payload_rejected(self):
        errors = le.validate_payload({"important_events": [], "key_dates": []})
        assert any("neither" in e for e in errors)

    def test_missing_required_field(self):
        bad = _payload(important_events=[_event(title="")])
        assert any("invalid title" in e for e in le.validate_payload(bad))

    def test_bad_date_format(self):
        bad = _payload(important_events=[_event(date="2026/07/10")])
        assert any("YYYY-MM-DD" in e for e in le.validate_payload(bad))

    def test_bad_impact(self):
        bad = _payload(important_events=[_event(impact="up")])
        assert any("impact" in e for e in le.validate_payload(bad))

    def test_bad_time(self):
        bad = _payload(key_dates=[_key_date(time="下午2點")])
        assert any("HH:MM" in e for e in le.validate_payload(bad))

    def test_bad_status(self):
        bad = _payload(key_dates=[_key_date(status="maybe")])
        assert any("status" in e for e in le.validate_payload(bad))

    def test_mandatory_date_types_in_vocabulary(self):
        # report-templates.md 規則 3 的必記時點類型必須在建議詞彙表內,
        # 否則每次萃取都會噴 WARN
        mandatory = {"ex_dividend", "ex_rights", "dividend_pay",
                     "earnings_release", "earnings_call", "revenue_release",
                     "news_release", "policy_announcement", "horizon_end"}
        assert mandatory <= le.KNOWN_DATE_TYPES

    def test_unknown_category_accepted(self):
        # 擴充性:未知詞彙只警告不擋
        ok = _payload(important_events=[_event(category="ai_capex")])
        assert le.validate_payload(ok) == []

    def test_bad_report_name(self):
        bad = _payload(report="not-markdown.txt")
        assert any("report" in e for e in le.validate_payload(bad))

    def test_non_dict_payload(self):
        assert le.validate_payload([1, 2]) == ["payload must be a JSON object"]


class TestMergePayload:
    NOW = "2026-07-13T06:00:00Z"

    def test_merge_into_empty_doc(self):
        doc = le.merge_payload(le.empty_doc(), _payload(), self.NOW)
        assert doc["schema_version"] == le.SCHEMA_VERSION
        assert doc["updated_at"] == self.NOW
        assert len(doc["important_events"]) == 1
        assert len(doc["key_dates"]) == 1
        ev = doc["important_events"][0]
        assert ev["id"] and ev["reports"] == ["2026-07-13_3030-TW_Q1.md"]

    def test_input_not_mutated(self):
        payload = _payload()
        snapshot = json.dumps(payload, sort_keys=True)
        le.merge_payload(le.empty_doc(), payload, self.NOW)
        assert json.dumps(payload, sort_keys=True) == snapshot

    def test_dedup_same_event_unions_reports(self):
        doc = le.merge_payload(le.empty_doc(), _payload(), self.NOW)
        again = _payload(report="2026-07-14_3030-TW_Q1.md")
        doc2 = le.merge_payload(doc, again, self.NOW)
        assert len(doc2["important_events"]) == 1
        assert doc2["important_events"][0]["reports"] == [
            "2026-07-13_3030-TW_Q1.md", "2026-07-14_3030-TW_Q1.md"]

    def test_events_sorted_newest_first(self):
        p = _payload(important_events=[
            _event(date="2026-07-01", title="舊事件"),
            _event(date="2026-07-12", title="新事件")])
        doc = le.merge_payload(le.empty_doc(), p, self.NOW)
        assert [e["date"] for e in doc["important_events"]] == [
            "2026-07-12", "2026-07-01"]

    def test_key_dates_sorted_ascending_with_time(self):
        p = _payload(key_dates=[
            _key_date(date="2026-08-10", label="營收"),
            _key_date(date="2026-07-16", label="法說", time="14:00"),
            _key_date(date="2026-07-16", label="開盤", time="09:00")])
        doc = le.merge_payload(le.empty_doc(), p, self.NOW)
        assert [(d["date"], d.get("time")) for d in doc["key_dates"]] == [
            ("2026-07-16", "09:00"), ("2026-07-16", "14:00"),
            ("2026-08-10", None)]

    def test_key_date_default_status(self):
        p = _payload(key_dates=[{k: v for k, v in _key_date().items()
                                 if k != "status"}])
        doc = le.merge_payload(le.empty_doc(), p, self.NOW)
        assert doc["key_dates"][0]["status"] == "estimated"

    def test_extra_fields_preserved(self):
        p = _payload(important_events=[_event(custom_tag="ai-supply-chain")])
        doc = le.merge_payload(le.empty_doc(), p, self.NOW)
        assert doc["important_events"][0]["custom_tag"] == "ai-supply-chain"


class TestFilterDoc:
    def test_filter_by_symbol(self):
        p = _payload(
            important_events=[_event(), _event(symbol="2330.TW", title="法說")],
            key_dates=[_key_date(symbol="2330.TW")])
        doc = le.merge_payload(le.empty_doc(), p, "2026-07-13T06:00:00Z")
        only = le.filter_doc(doc, "2330.tw")
        assert {e["symbol"] for e in only["important_events"]} == {"2330.TW"}
        assert {d["symbol"] for d in only["key_dates"]} == {"2330.TW"}


class TestRoundTrip:
    def test_write_and_read_events_file(self, tmp_path):
        path = tmp_path / "events.json"
        doc = le.merge_payload(le.empty_doc(), _payload(),
                               "2026-07-13T06:00:00Z")
        import common
        common.write_json_atomic(path, doc)
        loaded = le.read_events_doc(path)
        assert loaded == doc

    def test_missing_file_returns_skeleton(self, tmp_path):
        loaded = le.read_events_doc(tmp_path / "nope.json")
        assert loaded == le.empty_doc()
