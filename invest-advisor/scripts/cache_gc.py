"""TTL garbage collection for local caches.

Removes:
  - news_cache.db  : news_items past expires_at
  - market.db      : asset_profiles not updated within PROFILE_TTL_DAYS,
                     fundamentals past expires_at
Never touches: ohlcv (immutable history), predictions.jsonl, outcomes.jsonl.

Usage:
  python cache_gc.py [--dry-run]
"""
from __future__ import annotations

import argparse
import sys

import common

PROFILE_TTL_DAYS = 30


def gc_news(con, now: int, dry_run: bool) -> int:
    count = con.execute(
        "SELECT COUNT(*) FROM news_items WHERE expires_at < ?", (now,)
    ).fetchone()[0]
    if not dry_run and count:
        con.execute("DELETE FROM news_items WHERE expires_at < ?", (now,))
        con.commit()
    return count


def gc_market(con, now: int, dry_run: bool) -> dict:
    profile_cutoff = now - PROFILE_TTL_DAYS * 86400
    stale_profiles = con.execute(
        "SELECT COUNT(*) FROM asset_profiles WHERE updated_at < ?",
        (profile_cutoff,)).fetchone()[0]
    stale_fundamentals = con.execute(
        "SELECT COUNT(*) FROM fundamentals "
        "WHERE expires_at IS NOT NULL AND expires_at < ?", (now,)).fetchone()[0]
    if not dry_run:
        if stale_profiles:
            con.execute("DELETE FROM asset_profiles WHERE updated_at < ?",
                        (profile_cutoff,))
        if stale_fundamentals:
            con.execute("DELETE FROM fundamentals "
                        "WHERE expires_at IS NOT NULL AND expires_at < ?",
                        (now,))
        con.commit()
    return {"asset_profiles": stale_profiles,
            "fundamentals": stale_fundamentals}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true",
                        help="report what would be deleted, delete nothing")
    parser.add_argument("--market-db", default=None)
    parser.add_argument("--news-db", default=None)
    args = parser.parse_args()

    now = common.utc_now()
    result = {"dry_run": args.dry_run, "deleted": {}}

    news_con = common.get_news_db(args.news_db)
    try:
        result["deleted"]["news_items"] = gc_news(news_con, now, args.dry_run)
        if not args.dry_run:
            news_con.execute("VACUUM")
    finally:
        news_con.close()

    market_con = common.get_market_db(args.market_db)
    try:
        result["deleted"].update(gc_market(market_con, now, args.dry_run))
        if not args.dry_run:
            market_con.execute("VACUUM")
    finally:
        market_con.close()

    common.print_json(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
