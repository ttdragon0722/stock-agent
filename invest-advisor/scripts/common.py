"""Shared infrastructure for invest-advisor scripts.

Paths, SQLite schema management, JSONL helpers, time utilities.
All writes go through these helpers so the LLM never composes SQL directly.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Windows consoles default to legacy codepages (cp950 etc.) — force UTF-8
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

SKILL_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = SKILL_ROOT / "data"
REPORTS_DIR = DATA_DIR / "reports"
MARKET_DB = DATA_DIR / "market.db"
NEWS_DB = DATA_DIR / "news_cache.db"
PREDICTIONS_FILE = DATA_DIR / "predictions.jsonl"
OUTCOMES_FILE = DATA_DIR / "outcomes.jsonl"
EVENTS_FILE = DATA_DIR / "events.json"

RUBRIC_VERSION = "1.3.0"

# Benchmarks used for excess-return comparison (see references/scoring-rubric.md)
BENCHMARK_BY_ASSET_TYPE = {"stock": "SPY", "crypto": "BTCUSDT"}

MARKET_SCHEMA = """
CREATE TABLE IF NOT EXISTS ohlcv (
  symbol      TEXT NOT NULL,
  timeframe   TEXT NOT NULL,
  ts          INTEGER NOT NULL,
  open REAL, high REAL, low REAL, close REAL, volume REAL,
  source      TEXT,
  fetched_at  INTEGER,
  PRIMARY KEY (symbol, timeframe, ts)
);
CREATE TABLE IF NOT EXISTS fundamentals (
  symbol      TEXT NOT NULL,
  metric      TEXT NOT NULL,
  value       REAL,
  as_of       INTEGER NOT NULL,
  expires_at  INTEGER,
  source_url  TEXT,
  PRIMARY KEY (symbol, metric, as_of)
);
CREATE TABLE IF NOT EXISTS asset_profiles (
  symbol      TEXT PRIMARY KEY,
  asset_type  TEXT,
  name        TEXT,
  sector      TEXT,
  profile_md  TEXT,
  updated_at  INTEGER
);
CREATE TABLE IF NOT EXISTS non_trading_days (
  market TEXT NOT NULL,
  date   TEXT NOT NULL,
  PRIMARY KEY (market, date)
);
CREATE TABLE IF NOT EXISTS chips (
  symbol         TEXT NOT NULL,
  date           TEXT NOT NULL,
  foreign_net    INTEGER,
  trust_net      INTEGER,
  dealer_net     INTEGER,
  total_net      INTEGER,
  margin_balance INTEGER,
  margin_change  INTEGER,
  short_balance  INTEGER,
  short_change   INTEGER,
  source         TEXT,
  fetched_at     INTEGER,
  PRIMARY KEY (symbol, date)
);
"""

NEWS_SCHEMA = """
CREATE TABLE IF NOT EXISTS news_items (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol       TEXT NOT NULL,
  headline     TEXT,
  summary      TEXT,
  sentiment    TEXT,
  published_at INTEGER,
  source_url   TEXT,
  fetched_at   INTEGER NOT NULL,
  expires_at   INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_news_symbol ON news_items(symbol, expires_at);
"""


def utc_now() -> int:
    return int(time.time())


def iso_utc(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def iso_to_epoch(s: str) -> int:
    return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())


def roc_to_iso(roc: str) -> str:
    """ROC calendar date '1150709' -> '2026-07-09' (TWSE/TPEx payloads)."""
    digits = roc.strip()
    if not digits.isdigit() or len(digits) != 7:
        raise ValueError(f"expected 7-digit ROC date, got: {roc!r}")
    return f"{int(digits[:3]) + 1911}-{digits[3:5]}-{digits[5:7]}"


def roc_ym_to_iso(roc_ym: str) -> str:
    """ROC year-month '11505' -> '2026-05' (monthly revenue payloads)."""
    digits = roc_ym.strip()
    if not digits.isdigit() or len(digits) != 5:
        raise ValueError(f"expected 5-digit ROC year-month, got: {roc_ym!r}")
    return f"{int(digits[:3]) + 1911}-{digits[3:5]}"


# 官方 API 對無資料欄位常見的佔位符;JSON null 也視為缺值
_NUMBER_PLACEHOLDERS = {"", "--", "—", "N/A", "None", "null", "不適用"}


def _normalize_number(value) -> str | None:
    """None/佔位符 -> None;其餘回傳去逗號字串。"""
    if value is None:
        return None
    s = str(value).replace(",", "").strip()
    return None if s in _NUMBER_PLACEHOLDERS else s


def parse_int(value) -> int:
    """官方 API 整數欄位:缺值/佔位符視為 0,無法解析者同缺值。"""
    s = _normalize_number(value)
    if s is None:
        return 0
    try:
        return int(s)
    except ValueError:
        return 0


def parse_float(value) -> float:
    """官方 API 浮點欄位:缺值/佔位符視為 0.0,無法解析者同缺值。"""
    s = _normalize_number(value)
    if s is None:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def http_get_json(url: str, timeout: int = 20,
                  relax_ssl_strict: bool = False):
    """GET a JSON endpoint with a browser UA.

    relax_ssl_strict: TPEx's certificate lacks a Subject Key Identifier,
    which Python 3.13's default VERIFY_X509_STRICT rejects; the chain is
    still fully verified with the flag cleared.
    """
    import ssl
    import urllib.request
    ctx = ssl.create_default_context()
    if relax_ssl_strict:
        ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
    req = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8-sig"))


def get_market_db(path: Path | None = None) -> sqlite3.Connection:
    db_path = Path(path) if path else MARKET_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.executescript(MARKET_SCHEMA)
    return con


def get_news_db(path: Path | None = None) -> sqlite3.Connection:
    db_path = Path(path) if path else NEWS_DB
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    con.executescript(NEWS_SCHEMA)
    return con


def load_bars(con: sqlite3.Connection, symbol: str, timeframe: str,
              limit: int | None = None) -> list[dict]:
    """Return OHLCV bars for a symbol/timeframe sorted by ascending ts."""
    sql = ("SELECT ts, open, high, low, close, volume FROM ohlcv "
           "WHERE symbol = ? AND timeframe = ? ORDER BY ts ASC")
    rows = con.execute(sql, (symbol.upper(), timeframe)).fetchall()
    if limit:
        rows = rows[-limit:]
    return [
        {"ts": r[0], "open": r[1], "high": r[2], "low": r[3],
         "close": r[4], "volume": r[5]}
        for r in rows
    ]


def read_jsonl(path: Path) -> list[dict]:
    if not Path(path).exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                eprint(f"WARN: {path}:{lineno} invalid JSON skipped ({e})")
    return records


def append_jsonl(path: Path, record: dict) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_jsonl(path: Path, records: list[dict]) -> None:
    """Full rewrite — only for DERIVED files (outcomes.jsonl), never predictions.jsonl."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_json(path: Path, default=None):
    """Read a whole-file JSON document; missing/corrupt file -> default."""
    p = Path(path)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        eprint(f"WARN: {p} unreadable JSON, using default ({e})")
        return default


def write_json_atomic(path: Path, obj) -> None:
    """Write a JSON document atomically (tmp file + os.replace)."""
    import os
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    os.replace(tmp, p)


def eprint(*args) -> None:
    print(*args, file=sys.stderr)


def print_json(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))
