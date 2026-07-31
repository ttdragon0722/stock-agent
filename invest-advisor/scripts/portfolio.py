"""Real-holdings tracker for the invest-advisor skill (真實持倉系統).

Stores the user's ACTUAL positions in data/portfolio.json — a private,
git-ignored document (real money, never committed). Every write rebuilds the
whole document immutably and saves atomically via common.write_json_atomic.

Latest market price is read from market.db (the same 1d bars fetch_ohlcv
maintains); this script never hits the network — run fetch_ohlcv.py first if
you want fresh prices. Unrealised P&L is derived, never stored.

This is the single source of truth for "使用者目前實際持有什麼" so Q5/Q6
reports stop guessing the budget. It does NOT place orders and is NOT advice.

Usage:
  python portfolio.py                                   # show positions + live P&L (JSON)
  python portfolio.py --set 0050.TW --shares 70 --cost 101.9   # set/replace a position
  python portfolio.py --add 3030.TW --shares 20 --cost 300     # add lot (weighted-avg cost)
  python portfolio.py --remove 3413.TW                         # drop a position
  python portfolio.py --set 0050.TW --shares 70 --cost 101.9 --note "7/23 兩批"

Output (--show, default): JSON {generated_at, base_currency, price_source,
  totals:{cost_basis, market_value, unrealized_pnl, unrealized_pnl_pct},
  positions:[{symbol, asset_type, shares, avg_cost, cost_basis, last_close,
    price_ts, market_value, unrealized_pnl, unrealized_pnl_pct, weight_pct,
    note, priced}]}
"""
from __future__ import annotations

import argparse

import common

PORTFOLIO_FILE = common.DATA_DIR / "portfolio.json"
SCHEMA_VERSION = 1


def empty_doc() -> dict:
    return {"schema_version": SCHEMA_VERSION, "base_currency": "TWD",
            "updated_at": None, "positions": []}


def load_portfolio(path=PORTFOLIO_FILE) -> dict:
    doc = common.read_json(path, default=None)
    if not isinstance(doc, dict) or "positions" not in doc:
        return empty_doc()
    return doc


def _positions_without(positions: list[dict], symbol: str) -> list[dict]:
    """New list with `symbol` removed (case-insensitive) — never mutates input."""
    sym = symbol.upper()
    return [p for p in positions if p.get("symbol", "").upper() != sym]


def _find(positions: list[dict], symbol: str) -> dict | None:
    sym = symbol.upper()
    for p in positions:
        if p.get("symbol", "").upper() == sym:
            return p
    return None


def set_position(doc: dict, symbol: str, shares: float, cost: float,
                 asset_type: str = "stock", note: str | None = None) -> dict:
    """Return a NEW doc with `symbol` set to an exact (shares, avg_cost)."""
    if shares <= 0:
        raise ValueError(f"shares must be positive, got {shares}")
    if cost < 0:
        raise ValueError(f"cost must be non-negative, got {cost}")
    existing = _find(doc["positions"], symbol) or {}
    entry = {
        "symbol": symbol.upper(),
        "asset_type": asset_type or existing.get("asset_type", "stock"),
        "shares": _num(shares),
        "avg_cost": round(cost, 4),
        "note": note if note is not None else existing.get("note", ""),
        "updated_at": common.iso_utc(common.utc_now()),
    }
    positions = _positions_without(doc["positions"], symbol) + [entry]
    return _with_positions(doc, positions)


def add_lot(doc: dict, symbol: str, shares: float, cost: float,
            asset_type: str = "stock", note: str | None = None) -> dict:
    """Return a NEW doc: add a lot, blending into a weighted-average cost."""
    if shares <= 0:
        raise ValueError(f"shares must be positive, got {shares}")
    if cost < 0:
        raise ValueError(f"cost must be non-negative, got {cost}")
    existing = _find(doc["positions"], symbol)
    if not existing:
        return set_position(doc, symbol, shares, cost, asset_type, note)
    old_shares = existing["shares"]
    old_cost = existing["avg_cost"]
    new_shares = old_shares + shares
    blended = (old_shares * old_cost + shares * cost) / new_shares
    return set_position(doc, symbol, new_shares, blended,
                        existing.get("asset_type", asset_type), note)


def remove_position(doc: dict, symbol: str) -> dict:
    return _with_positions(doc, _positions_without(doc["positions"], symbol))


def _with_positions(doc: dict, positions: list[dict]) -> dict:
    """New doc carrying updated positions + refreshed timestamp (immutable)."""
    positions = sorted(positions, key=lambda p: p["symbol"])
    return {**doc, "schema_version": SCHEMA_VERSION,
            "updated_at": common.iso_utc(common.utc_now()),
            "positions": positions}


def _num(x: float) -> float:
    """Keep whole share counts as int for cleaner JSON; fractional stays float."""
    return int(x) if float(x).is_integer() else round(float(x), 4)


def latest_close(con, symbol: str) -> tuple[float | None, int | None]:
    bars = common.load_bars(con, symbol, "1d", limit=1)
    if not bars:
        return None, None
    return bars[-1]["close"], bars[-1]["ts"]


def price_position(con, pos: dict) -> dict:
    """Enrich a stored position with live valuation from market.db (derived)."""
    shares = pos["shares"]
    avg_cost = pos["avg_cost"]
    cost_basis = round(shares * avg_cost, 2)
    close, ts = latest_close(con, pos["symbol"])
    out = {
        "symbol": pos["symbol"],
        "asset_type": pos.get("asset_type", "stock"),
        "shares": shares,
        "avg_cost": avg_cost,
        "cost_basis": cost_basis,
        "note": pos.get("note", ""),
        "last_close": None, "price_ts": None, "market_value": None,
        "unrealized_pnl": None, "unrealized_pnl_pct": None, "priced": False,
    }
    if close is None:
        return out
    market_value = round(shares * close, 2)
    pnl = round(market_value - cost_basis, 2)
    out.update({
        "last_close": round(close, 4),
        "price_ts": common.iso_utc(ts) if ts else None,
        "market_value": market_value,
        "unrealized_pnl": pnl,
        "unrealized_pnl_pct": round(pnl / cost_basis * 100, 2) if cost_basis else None,
        "priced": True,
    })
    return out


def build_snapshot(doc: dict, con) -> dict:
    priced = [price_position(con, p) for p in doc["positions"]]
    cost_basis = round(sum(p["cost_basis"] for p in priced), 2)
    market_value = round(sum(p["market_value"] for p in priced if p["priced"]), 2)
    unpriced = [p["symbol"] for p in priced if not p["priced"]]
    for p in priced:  # portfolio weight by market value (cost basis if unpriced)
        mv = p["market_value"] if p["priced"] else p["cost_basis"]
        p["weight_pct"] = round(mv / market_value * 100, 2) if market_value else None
    pnl = round(market_value - sum(p["cost_basis"] for p in priced if p["priced"]), 2)
    priced_cost = sum(p["cost_basis"] for p in priced if p["priced"])
    return {
        "generated_at": common.iso_utc(common.utc_now()),
        "base_currency": doc.get("base_currency", "TWD"),
        "price_source": "market.db 1d close (run fetch_ohlcv.py for fresh prices)",
        "position_count": len(priced),
        "unpriced_symbols": unpriced,
        "totals": {
            "cost_basis": cost_basis,
            "market_value": market_value,
            "unrealized_pnl": pnl,
            "unrealized_pnl_pct": round(pnl / priced_cost * 100, 2) if priced_cost else None,
        },
        "positions": priced,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Real-holdings tracker (private, git-ignored).")
    ap.add_argument("--set", dest="set_sym", metavar="SYMBOL",
                    help="set/replace a position to an exact (shares, cost)")
    ap.add_argument("--add", dest="add_sym", metavar="SYMBOL",
                    help="add a lot, blending into weighted-average cost")
    ap.add_argument("--remove", dest="remove_sym", metavar="SYMBOL",
                    help="delete a position")
    ap.add_argument("--shares", type=float, help="share count (with --set/--add)")
    ap.add_argument("--cost", type=float, help="per-share cost (with --set/--add)")
    ap.add_argument("--asset-type", default="stock", choices=["stock", "crypto"])
    ap.add_argument("--note", default=None, help="free-text note on the position")
    ap.add_argument("--file", default=None, help="override portfolio.json path")
    ap.add_argument("--show", action="store_true", help="print snapshot (default action)")
    args = ap.parse_args()

    path = args.file or PORTFOLIO_FILE
    doc = load_portfolio(path)

    mutating = args.set_sym or args.add_sym or args.remove_sym
    if mutating:
        if (args.set_sym or args.add_sym) and (args.shares is None or args.cost is None):
            ap.error("--set/--add require both --shares and --cost")
        if args.set_sym:
            doc = set_position(doc, args.set_sym, args.shares, args.cost,
                               args.asset_type, args.note)
        elif args.add_sym:
            doc = add_lot(doc, args.add_sym, args.shares, args.cost,
                          args.asset_type, args.note)
        elif args.remove_sym:
            doc = remove_position(doc, args.remove_sym)
        common.write_json_atomic(path, doc)

    con = common.get_market_db()
    try:
        common.print_json(build_snapshot(doc, con))
    finally:
        con.close()


if __name__ == "__main__":
    main()
