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
        assert {"total", "actionable"} <= set(body["meta"].keys())
        if body["data"]:
            row = body["data"][0]
            assert {"id", "asset", "status", "days_left",
                    "verifiable_now", "falsification_condition"} <= set(row.keys())

    def test_stats(self):
        r = client.get("/api/stats")
        assert r.status_code == 200
        assert "by_status" in r.json()["data"]

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
