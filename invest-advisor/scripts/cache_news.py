"""Write/read the news sentiment cache (news_cache.db, TTL 24h).

All inserts are validated and parameterized here so the LLM never composes
SQL. Duplicate (symbol, headline) pairs still fresh in cache are skipped.

Usage:
  python cache_news.py --save items.json [--ttl-hours 24]
  python cache_news.py --recall 2330.TW

items.json is a JSON array of:
  {"symbol": "...", "headline": "...", "summary": "...",
   "sentiment": "positive|negative|neutral|mixed",
   "published_at": "ISO8601 or epoch (optional)", "source_url": "https://..."}
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

import common

VALID_SENTIMENTS = ("positive", "negative", "neutral", "mixed")
DEFAULT_TTL_HOURS = 24
REQUIRED_FIELDS = ("symbol", "headline", "sentiment", "source_url")


def validate_item(item: dict) -> list[str]:
    errors = []
    for field in REQUIRED_FIELDS:
        value = item.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"missing or blank required field: {field}")
    sentiment = item.get("sentiment")
    if isinstance(sentiment, str) and sentiment not in VALID_SENTIMENTS:
        errors.append(
            f"sentiment must be one of {VALID_SENTIMENTS}, got: {sentiment!r}")
    errors += _validate_published_at(item.get("published_at"))
    return errors


def _validate_published_at(raw) -> list[str]:
    """Optional field; if a string, it must be timezone-aware ISO8601 —
    naive datetimes would be parsed in local time and corrupt TTL ordering."""
    if raw is None or isinstance(raw, (int, float)):
        return []
    if not isinstance(raw, str):
        return [f"published_at must be epoch or ISO8601 string, got: {raw!r}"]
    has_tz = raw.endswith("Z") or "+" in raw or "-" in raw.split("T")[-1]
    if not has_tz:
        return [f"published_at must include timezone (Z or offset): {raw!r}"]
    try:
        common.iso_to_epoch(raw)
    except ValueError:
        return [f"published_at is not valid ISO8601: {raw!r}"]
    return []


def _published_epoch(item: dict) -> int | None:
    raw = item.get("published_at")
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return int(raw)
    return common.iso_to_epoch(raw)


def save_items(con: sqlite3.Connection, items: list[dict], now: int,
               ttl_hours: int = DEFAULT_TTL_HOURS) -> int:
    """Validate every item first (all-or-nothing), then insert non-duplicates.

    Returns the number of rows actually inserted.
    """
    all_errors = []
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            all_errors.append(f"item[{i}]: must be a JSON object")
            continue
        all_errors += [f"item[{i}]: {e}" for e in validate_item(item)]
    if all_errors:
        raise ValueError("; ".join(all_errors))

    expires_at = now + ttl_hours * 3600
    inserted = 0
    for item in items:
        symbol = item["symbol"].strip().upper()
        headline = item["headline"].strip()
        duplicate = con.execute(
            "SELECT 1 FROM news_items "
            "WHERE symbol = ? AND headline = ? AND expires_at > ?",
            (symbol, headline, now)).fetchone()
        if duplicate:
            continue
        con.execute(
            "INSERT INTO news_items "
            "(symbol, headline, summary, sentiment, published_at, "
            " source_url, fetched_at, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (symbol, headline, (item.get("summary") or "").strip(),
             item["sentiment"], _published_epoch(item),
             item["source_url"].strip(), now, expires_at))
        inserted += 1
    con.commit()
    return inserted


def recall_items(con: sqlite3.Connection, symbol: str, now: int) -> list[dict]:
    """Fresh (non-expired) cached items for a symbol, newest published first."""
    rows = con.execute(
        "SELECT headline, summary, sentiment, published_at, source_url, "
        "       fetched_at, expires_at "
        "FROM news_items WHERE symbol = ? AND expires_at > ? "
        "ORDER BY published_at DESC",
        (symbol.strip().upper(), now)).fetchall()
    return [
        {"headline": r[0], "summary": r[1], "sentiment": r[2],
         "published_at": r[3], "source_url": r[4],
         "fetched_at_iso": common.iso_utc(r[5]),
         "expires_at_iso": common.iso_utc(r[6])}
        for r in rows
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--save", metavar="ITEMS_JSON",
                      help="path to a JSON array of news items to insert")
    mode.add_argument("--recall", metavar="SYMBOL",
                      help="print fresh cached items for a symbol")
    parser.add_argument("--ttl-hours", type=int, default=DEFAULT_TTL_HOURS)
    parser.add_argument("--news-db", default=None)
    args = parser.parse_args()

    now = common.utc_now()
    con = common.get_news_db(args.news_db)
    try:
        if args.save:
            raw = Path(args.save).read_text(encoding="utf-8")
            items = json.loads(raw)
            if not isinstance(items, list):
                raise ValueError("--save file must contain a JSON array")
            inserted = save_items(con, items, now, args.ttl_hours)
            common.print_json({"saved": inserted,
                               "skipped_duplicates": len(items) - inserted})
        else:
            items = recall_items(con, args.recall, now)
            common.print_json({"symbol": args.recall.strip().upper(),
                               "fresh_count": len(items), "items": items})
    except (ValueError, json.JSONDecodeError, OSError) as e:
        common.eprint(f"ERROR: {e}")
        return 1
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
