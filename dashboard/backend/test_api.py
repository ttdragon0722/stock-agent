"""API tests using FastAPI TestClient (no server needed)."""
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestReadEndpoints:
    def test_health(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_predictions_envelope(self):
        r = client.get("/api/predictions")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert isinstance(body["data"], list)
        assert {"total", "actionable", "unfilled"} <= set(body["meta"].keys())
        if body["data"]:
            row = body["data"][0]
            assert {"id", "asset", "asset_type", "status", "days_left",
                    "verifiable_now", "falsification_condition", "filled",
                    "unfilled"} <= set(row.keys())

    def test_predictions_unfilled_split_by_market(self):
        body = client.get("/api/predictions").json()
        meta = body["meta"]["unfilled"]
        assert {"total", "stock", "crypto"} <= set(meta.keys())
        unfilled_rows = [r for r in body["data"] if r["unfilled"]]
        assert meta["total"] == len(unfilled_rows)
        assert meta["stock"] == sum(
            1 for r in unfilled_rows if r["asset_type"] == "stock")
        assert meta["crypto"] == sum(
            1 for r in unfilled_rows if r["asset_type"] == "crypto")
        for row in unfilled_rows:
            assert row["entry_zone"]          # 沒有交易計畫不可能是未成交掛單
            assert row["resolved"] is False   # 已結案不算等待成交中
            assert row["filled"] is not True

    def test_stats_split_by_market(self):
        r = client.get("/api/stats")
        assert r.status_code == 200
        data = r.json()["data"]
        assert {"all", "stock", "crypto"} <= set(data.keys())
        for market in ("all", "stock", "crypto"):
            assert "by_status" in data[market]
            assert "win_rate" in data[market]
        # 市場分割不能遺漏或重複計數(缺 asset_type 的舊紀錄只在 all)
        assert data["stock"]["total"] + data["crypto"]["total"] \
            <= data["all"]["total"]

    def test_reports_list(self):
        r = client.get("/api/reports")
        assert r.status_code == 200
        assert isinstance(r.json()["data"], list)

    def test_report_content_roundtrip(self):
        listing = client.get("/api/reports").json()["data"]
        if not listing:
            return  # no reports yet — nothing to round-trip
        name = listing[0]["name"]
        r = client.get(f"/api/reports/{name}")
        assert r.status_code == 200
        assert r.json()["data"]["markdown"]

    def test_events(self):
        r = client.get("/api/events")
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert {"schema_version", "important_events",
                "key_dates"} <= set(body["data"].keys())
        assert isinstance(body["data"]["important_events"], list)
        assert isinstance(body["data"]["key_dates"], list)
        assert {"total_events", "total_key_dates"} <= set(body["meta"].keys())

    def test_events_symbol_filter(self):
        r = client.get("/api/events", params={"symbol": "3030.TW"})
        assert r.status_code == 200
        data = r.json()["data"]
        assert all(e["symbol"] == "3030.TW"
                   for e in data["important_events"])
        assert all(d["symbol"] == "3030.TW" for d in data["key_dates"])

    def test_calibration(self):
        r = client.get("/api/calibration")
        assert r.status_code == 200
        data = r.json()["data"]
        assert "confidence_calibration" in data
        assert data["sample_warning"] in (True, False)


class TestReportPathGuard:
    def test_rejects_traversal(self):
        for bad in ("..%2Fsecrets.md", "a/../b.md", "x.txt"):
            r = client.get(f"/api/reports/{bad}")
            assert r.status_code in (400, 404)

    def test_missing_report_404(self):
        assert client.get("/api/reports/nope.md").status_code == 404
