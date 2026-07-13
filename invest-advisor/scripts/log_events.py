"""Merge report-extracted events into data/events.json (two-section document).

events.json is a DERIVED view file (rebuilt-in-place, atomic write) with two
sections the dashboard renders graphically:

  1. important_events — 重要事件(已發生/確認的事實,含多空影響)
  2. key_dates       — 關鍵日期和時間(未來時點:財報、營收、除息、法說…)

Records are deduped by a stable content id; re-logging the same event from a
later report updates it in place and unions the `reports` provenance list.
Schema is versioned (schema_version) and unknown extra fields are preserved,
so both sections stay forward-extensible.

Usage:
  python log_events.py --file events_payload.json   # merge a payload
  echo '{...}' | python log_events.py               # same, from stdin
  python log_events.py --show [--symbol 3030.TW]    # print current document
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys

import common

SCHEMA_VERSION = "1.0.0"

IMPACTS = {"bullish", "bearish", "neutral"}
DATE_STATUSES = {"confirmed", "estimated"}

# Recommended vocabularies — free-form strings are accepted (extensibility),
# unknown values only trigger a stderr WARN so typos stay visible.
KNOWN_EVENT_CATEGORIES = {
    "earnings", "revenue", "dividend", "chips", "macro", "policy",
    "corporate", "technical", "industry", "regulation", "other",
}
KNOWN_DATE_TYPES = {
    "earnings_call", "earnings_release", "revenue_release", "ex_dividend",
    "ex_rights", "dividend_pay", "shareholder_meeting", "fed_meeting",
    "cpi_release", "macro_data", "news_release", "policy_announcement",
    "lockup_expiry", "option_expiry", "product_launch", "horizon_end",
    "other",
}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")

EVENT_REQUIRED = {"symbol": str, "date": str, "title": str,
                  "category": str, "impact": str}
KEY_DATE_REQUIRED = {"symbol": str, "date": str, "label": str,
                     "date_type": str}


def empty_doc() -> dict:
    return {"schema_version": SCHEMA_VERSION, "updated_at": None,
            "important_events": [], "key_dates": []}


def make_id(*parts: str) -> str:
    """Stable content id — same symbol/date/title always maps to one record."""
    digest = hashlib.sha1("|".join(p.strip() for p in parts)
                          .encode("utf-8")).hexdigest()
    return digest[:12]


def _check_required(rec: dict, required: dict, where: str) -> list[str]:
    errors = []
    for field, typ in required.items():
        if field not in rec:
            errors.append(f"{where}: missing field: {field}")
        elif not isinstance(rec[field], typ) or not str(rec[field]).strip():
            errors.append(f"{where}: invalid {field}: {rec[field]!r}")
    return errors


def validate_payload(payload: dict) -> list[str]:
    """Return validation errors (empty = valid). Pure function."""
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["payload must be a JSON object"]

    events = payload.get("important_events", [])
    key_dates = payload.get("key_dates", [])
    if not isinstance(events, list) or not isinstance(key_dates, list):
        return ["important_events / key_dates must be arrays"]
    if not events and not key_dates:
        errors.append("payload has neither important_events nor key_dates")
    if "report" in payload and (not isinstance(payload["report"], str)
                                or not payload["report"].endswith(".md")):
        errors.append("report must be a .md filename")

    for i, rec in enumerate(events):
        where = f"important_events[{i}]"
        errs = _check_required(rec, EVENT_REQUIRED, where)
        errors.extend(errs)
        if errs:
            continue
        if not _DATE_RE.match(rec["date"]):
            errors.append(f"{where}: date must be YYYY-MM-DD")
        if rec["impact"] not in IMPACTS:
            errors.append(f"{where}: impact must be one of {sorted(IMPACTS)}")
        if rec["category"] not in KNOWN_EVENT_CATEGORIES:
            common.eprint(f"WARN: {where}: unknown category "
                          f"{rec['category']!r} (accepted; check for typos)")

    for i, rec in enumerate(key_dates):
        where = f"key_dates[{i}]"
        errs = _check_required(rec, KEY_DATE_REQUIRED, where)
        errors.extend(errs)
        if errs:
            continue
        if not _DATE_RE.match(rec["date"]):
            errors.append(f"{where}: date must be YYYY-MM-DD")
        if "time" in rec and not _TIME_RE.match(str(rec["time"])):
            errors.append(f"{where}: time must be HH:MM (24h)")
        if rec.get("status", "estimated") not in DATE_STATUSES:
            errors.append(f"{where}: status must be one of "
                          f"{sorted(DATE_STATUSES)}")
        if rec["date_type"] not in KNOWN_DATE_TYPES:
            common.eprint(f"WARN: {where}: unknown date_type "
                          f"{rec['date_type']!r} (accepted; check for typos)")

    return errors


def _normalize(rec: dict, id_key: str, report: str | None,
               now_iso: str) -> dict:
    """Return a NEW record with id/provenance added (input not mutated)."""
    out = dict(rec)
    out["id"] = make_id(out["symbol"].upper(), out["date"], out[id_key])
    out["symbol"] = out["symbol"].upper()
    out["logged_at"] = now_iso
    out["reports"] = [report] if report else []
    return out


def _merge_section(existing: list[dict], incoming: list[dict]) -> list[dict]:
    """Dedup by id; incoming wins but provenance `reports` lists are unioned."""
    by_id = {r["id"]: r for r in existing if "id" in r}
    for rec in incoming:
        prev = by_id.get(rec["id"])
        if prev:
            reports = list(dict.fromkeys(
                (prev.get("reports") or []) + (rec.get("reports") or [])))
            rec = {**prev, **rec, "reports": reports}
        by_id[rec["id"]] = rec
    return list(by_id.values())


def merge_payload(doc: dict, payload: dict, now_iso: str) -> dict:
    """Merge one validated payload into the document. Returns a NEW doc."""
    report = payload.get("report")
    events = [_normalize(r, "title", report, now_iso)
              for r in payload.get("important_events", [])]
    key_dates = []
    for r in payload.get("key_dates", []):
        rec = _normalize(r, "label", report, now_iso)
        rec.setdefault("status", "estimated")
        key_dates.append(rec)

    merged_events = _merge_section(doc.get("important_events", []), events)
    merged_dates = _merge_section(doc.get("key_dates", []), key_dates)
    # 重要事件:新的在前(feed);關鍵日期:時間軸由近到遠(timeline)
    merged_events.sort(key=lambda r: (r.get("date", ""), r["id"]),
                       reverse=True)
    merged_dates.sort(key=lambda r: (r.get("date", ""),
                                     r.get("time", "99:99"), r["id"]))
    return {**doc, "schema_version": SCHEMA_VERSION, "updated_at": now_iso,
            "important_events": merged_events, "key_dates": merged_dates}


def read_events_doc(path=None) -> dict:
    """Load events.json (or an empty skeleton). Used by the dashboard API."""
    return common.read_json(path or common.EVENTS_FILE, default=empty_doc())


def filter_doc(doc: dict, symbol: str) -> dict:
    """Return a NEW doc containing only records for one symbol."""
    sym = symbol.upper()
    return {**doc,
            "important_events": [r for r in doc.get("important_events", [])
                                 if r.get("symbol") == sym],
            "key_dates": [r for r in doc.get("key_dates", [])
                          if r.get("symbol") == sym]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", help="payload JSON path (else reads stdin)")
    parser.add_argument("--show", action="store_true",
                        help="print current events.json and exit")
    parser.add_argument("--symbol", help="with --show: filter by symbol")
    parser.add_argument("--events-file", default=None,
                        help="override events.json path")
    args = parser.parse_args()
    events_path = args.events_file or common.EVENTS_FILE

    if args.show:
        doc = read_events_doc(events_path)
        common.print_json(filter_doc(doc, args.symbol) if args.symbol else doc)
        return 0

    try:
        raw = (open(args.file, encoding="utf-8-sig").read() if args.file
               else sys.stdin.read())
        payload = json.loads(raw.lstrip("﻿"))
    except (OSError, json.JSONDecodeError) as e:
        common.eprint(f"ERROR: cannot parse input JSON: {e}")
        return 1

    errors = validate_payload(payload)
    if errors:
        common.eprint("VALIDATION FAILED:")
        for e in errors:
            common.eprint(f"  - {e}")
        return 1

    doc = read_events_doc(events_path)
    merged = merge_payload(doc, payload, common.iso_utc(common.utc_now()))
    common.write_json_atomic(events_path, merged)
    common.print_json({
        "merged_events": len(payload.get("important_events", [])),
        "merged_key_dates": len(payload.get("key_dates", [])),
        "total_events": len(merged["important_events"]),
        "total_key_dates": len(merged["key_dates"]),
        "file": str(events_path),
    })
    return 0


if __name__ == "__main__":
    sys.exit(main())
