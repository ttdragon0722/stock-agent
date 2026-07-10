"""invest-advisor dashboard API (FastAPI).

Read-only views over the skill's data layer (predictions / outcomes /
reports) plus one action endpoint that runs outcome verification.
The skill remains the single writer; this backend never mutates
predictions.jsonl.

Run:
  uvicorn main:app --reload --port 8787   (from dashboard/backend/)
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Reuse the skill's own modules — single source of truth for paths & logic.
SKILL_SCRIPTS = (Path(__file__).resolve().parents[2]
                 / "invest-advisor" / "scripts")
sys.path.insert(0, str(SKILL_SCRIPTS))

import calibration_report as cal  # noqa: E402
import common  # noqa: E402
import dashboard as dash  # noqa: E402
import verify_predictions as vp  # noqa: E402

VERIFY_TIMEOUT_SECONDS = 300

app = FastAPI(title="invest-advisor dashboard API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _load_rows() -> list[dict]:
    predictions = common.read_jsonl(common.PREDICTIONS_FILE)
    outcomes = common.read_jsonl(common.OUTCOMES_FILE)
    return dash.build_rows(predictions, outcomes, common.utc_now())


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "data_dir": str(common.DATA_DIR)}


@app.get("/api/predictions")
def predictions() -> dict:
    rows = _load_rows()
    return {"success": True, "data": rows, "error": None,
            "meta": {"total": len(rows),
                     "actionable": dash.count_actionable(rows)}}


@app.get("/api/stats")
def stats() -> dict:
    outcomes = common.read_jsonl(common.OUTCOMES_FILE)
    return {"success": True, "data": vp.summarize(outcomes), "error": None}


@app.get("/api/reports")
def reports() -> dict:
    common.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(common.REPORTS_DIR.glob("*.md"), reverse=True)
    data = [{"name": f.name, "size": f.stat().st_size,
             "modified": common.iso_utc(int(f.stat().st_mtime))}
            for f in files]
    return {"success": True, "data": data, "error": None}


@app.get("/api/reports/{name}")
def report_content(name: str) -> dict:
    # path-traversal guard: only bare .md filenames inside REPORTS_DIR
    if "/" in name or "\\" in name or ".." in name or not name.endswith(".md"):
        raise HTTPException(status_code=400, detail="invalid report name")
    path = common.REPORTS_DIR / name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="report not found")
    return {"success": True,
            "data": {"name": name,
                     "markdown": path.read_text(encoding="utf-8")},
            "error": None}


@app.get("/api/calibration")
def calibration() -> dict:
    predictions = common.read_jsonl(common.PREDICTIONS_FILE)
    outcomes = common.read_jsonl(common.OUTCOMES_FILE)
    joined = cal.join_records(predictions, outcomes)
    resolved = [r for r in joined if r["status"] in ("WIN", "LOSS")]
    with_returns = [r for r in joined
                    if r["status"] in ("WIN", "LOSS", "FLAT",
                                       "RESOLVED_DIRECTIONAL")]
    pairs = [(r["confidence_score"] / 100, 1 if r["status"] == "WIN" else 0)
             for r in resolved]
    return {"success": True, "data": {
        "resolved_count": len(resolved),
        "brier": cal.brier_score(pairs),
        "brier_baseline": cal.brier_score([(0.5, o) for _, o in pairs]),
        "confidence_calibration": cal.confidence_calibration(resolved),
        "recommendation_monotonicity":
            cal.recommendation_monotonicity(with_returns),
        "regime_split": cal.regime_split(joined),
        "sample_warning": len(resolved) < 50,
    }, "error": None}


@app.post("/api/verify")
def run_verification(fetch: bool = True) -> dict:
    """Run outcome verification (optionally auto-fetching OHLCV first)."""
    cmd = [sys.executable, str(SKILL_SCRIPTS / "verify_predictions.py")]
    if fetch:
        cmd.append("--fetch")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              encoding="utf-8", cwd=str(SKILL_SCRIPTS),
                              timeout=VERIFY_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="verification timed out")
    if proc.returncode != 0:
        raise HTTPException(status_code=500,
                            detail=f"verify failed: {proc.stderr[-2000:]}")
    try:
        summary = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500,
                            detail="verify produced unparseable output")
    return {"success": True,
            "data": {"summary": summary, "log": proc.stderr[-2000:]},
            "error": None}
