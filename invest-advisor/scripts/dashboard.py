"""Generate a self-contained HTML dashboard for predictions & reports.

Shows every prediction with its outcome status, horizon countdown, and a
"verifiable now" flag; lists saved decision reports; surfaces aggregate stats.
Output: data/dashboard.html (open in any browser). No dependencies.
(dashboard.html is a view artifact, NOT a report — data/reports/ holds
reports only, see references/report-templates.md 存檔規範.)

Usage:
  python dashboard.py            # write HTML, print path
  python dashboard.py --text     # also print a compact terminal table
"""
from __future__ import annotations

import argparse
import html
import sys
from datetime import datetime, timezone

import common

RESOLVED_STATUSES = {"WIN", "LOSS", "FLAT", "NOT_FILLED",
                     "RESOLVED_DIRECTIONAL", "RESOLVED_NEUTRAL"}
STATUS_COLORS = {
    "WIN": "#1a7f37", "LOSS": "#cf222e", "FLAT": "#9a6700",
    "NOT_FILLED": "#57606a", "OPEN": "#0969da", "PENDING": "#57606a",
    "NO_DATA": "#cf222e", "RESOLVED_DIRECTIONAL": "#1a7f37",
    "RESOLVED_NEUTRAL": "#9a6700", "未驗證": "#57606a",
}


# ------------------------------------------------------------- rows (pure)

def build_rows(predictions: list[dict], outcomes: list[dict],
               now_ts: int) -> list[dict]:
    """Join predictions with outcomes and compute horizon fields."""
    outcome_by_id = {o["id"]: o for o in outcomes}
    rows = []
    for pred in predictions:
        outcome = outcome_by_id.get(pred.get("id"), {})
        analysis_ts = common.iso_to_epoch(pred["timestamp"])
        horizon_end = analysis_ts + int(pred["horizon_days"]) * 86400
        days_left = max(0, -(-(horizon_end - now_ts) // 86400))  # ceil
        status = outcome.get("status", "未驗證")
        resolved = status in RESOLVED_STATUSES
        rows.append({
            "id": pred.get("id"),
            "asset": pred["asset"],
            "question_type": pred.get("question_type", "?"),
            "direction": pred["direction"],
            "recommendation_score": pred.get("recommendation_score"),
            "confidence_score": pred.get("confidence_score"),
            "price_at_analysis": pred.get("price_at_analysis"),
            "entry_zone": pred.get("entry_zone"),
            "stop_loss": pred.get("stop_loss"),
            "take_profit": pred.get("take_profit"),
            "risk_reward": pred.get("risk_reward"),
            "logged": pred["timestamp"][:10],
            "horizon_end": common.iso_utc(horizon_end)[:10],
            "days_left": days_left,
            "status": status,
            "return_pct": outcome.get("return_pct"),
            "excess_return_pct": outcome.get("excess_return_pct"),
            "resolved": resolved,
            "verifiable_now": (now_ts >= horizon_end or status == "NO_DATA")
                              and not resolved,
        })
    return sorted(rows, key=lambda r: r["logged"], reverse=True)


def count_actionable(rows: list[dict]) -> int:
    return sum(1 for r in rows if r["verifiable_now"])


# ---------------------------------------------------------------- render

def _fmt(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, list):
        return "~".join(str(v) for v in value)
    return str(value)


def render_html(rows: list[dict], report_files: list[str],
                now_iso: str) -> str:
    actionable = count_actionable(rows)
    banner = (f'<div class="banner warn">⏰ 有 <b>{actionable}</b> 筆預測已到期'
              f'或缺資料,可執行:<code>python verify_predictions.py --fetch'
              f'</code></div>' if actionable else
              '<div class="banner ok">✅ 目前沒有待驗證的到期預測</div>')

    body_rows = []
    for r in rows:
        color = STATUS_COLORS.get(r["status"], "#57606a")
        due = ("可驗證" if r["verifiable_now"]
               else ("已結案" if r["resolved"] else f'{r["days_left"]} 天'))
        body_rows.append(
            "<tr>"
            f'<td>{html.escape(str(r["id"]))}</td>'
            f'<td><b>{html.escape(r["asset"])}</b></td>'
            f'<td>{html.escape(r["question_type"].split("_")[0])}</td>'
            f'<td>{html.escape(r["direction"])}</td>'
            f'<td>{_fmt(r["recommendation_score"])}/{_fmt(r["confidence_score"])}</td>'
            f'<td>{_fmt(r["price_at_analysis"])}</td>'
            f'<td>{_fmt(r["entry_zone"])}</td>'
            f'<td>{_fmt(r["stop_loss"])}</td>'
            f'<td>{_fmt(r["take_profit"])}</td>'
            f'<td>{_fmt(r["risk_reward"])}</td>'
            f'<td>{r["logged"]} → {r["horizon_end"]}</td>'
            f'<td><span class="badge" style="background:{color}">'
            f'{html.escape(r["status"])}</span></td>'
            f'<td>{due}</td>'
            f'<td>{_fmt(r["return_pct"])}</td>'
            "</tr>")

    report_items = "".join(
        f'<li><a href="{html.escape(name)}">{html.escape(name)}</a></li>'
        for name in report_files) or "<li>(尚無報告)</li>"

    return f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8">
<title>invest-advisor Dashboard</title>
<style>
 body{{font-family:system-ui,'Microsoft JhengHei',sans-serif;margin:2rem;
      background:#fff;color:#1f2328;max-width:1200px}}
 @media (prefers-color-scheme:dark){{body{{background:#0d1117;color:#e6edf3}}
   table,th,td{{border-color:#30363d!important}} .banner{{filter:brightness(.85)}}}}
 h1{{font-size:1.4rem}} table{{border-collapse:collapse;width:100%;font-size:.85rem}}
 th,td{{border:1px solid #d0d7de;padding:.35rem .5rem;text-align:left;
       white-space:nowrap}}
 .badge{{color:#fff;border-radius:.6rem;padding:.1rem .5rem;font-size:.75rem}}
 .banner{{padding:.6rem 1rem;border-radius:.5rem;margin:1rem 0}}
 .warn{{background:#fff8c5;border:1px solid #d4a72c;color:#4d2d00}}
 .ok{{background:#dafbe1;border:1px solid #1a7f37;color:#0f5323}}
 .wrap{{overflow-x:auto}} code{{background:rgba(128,128,128,.15);
   padding:.1rem .3rem;border-radius:.3rem}}
 footer{{margin-top:2rem;font-size:.75rem;opacity:.6}}
</style></head><body>
<h1>📈 invest-advisor Dashboard</h1>
<p>產出時間:{now_iso}(UTC)｜預測共 {len(rows)} 筆</p>
{banner}
<h2>預測日誌</h2>
<div class="wrap"><table>
<tr><th>ID</th><th>標的</th><th>題型</th><th>方向</th><th>推薦/信心</th>
<th>分析價</th><th>進場區</th><th>SL</th><th>TP</th><th>R:R</th>
<th>期間</th><th>狀態</th><th>到期</th><th>報酬%</th></tr>
{"".join(body_rows)}
</table></div>
<h2>決策報告</h2>
<ul>{report_items}</ul>
<footer>本頁由 dashboard.py 產生;所有內容非投資建議。重新產生:
<code>python dashboard.py</code></footer>
</body></html>"""


def render_text(rows: list[dict]) -> str:
    lines = [f'{"ID":32} {"狀態":12} {"到期":8} 報酬%']
    for r in rows:
        due = ("可驗證" if r["verifiable_now"]
               else ("已結案" if r["resolved"] else f'{r["days_left"]}天'))
        lines.append(f'{str(r["id"]):32} {r["status"]:12} {due:8} '
                     f'{_fmt(r["return_pct"])}')
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", action="store_true",
                        help="also print a compact terminal table")
    parser.add_argument("--out", default=None, help="override output path")
    args = parser.parse_args()

    predictions = common.read_jsonl(common.PREDICTIONS_FILE)
    outcomes = common.read_jsonl(common.OUTCOMES_FILE)
    now = common.utc_now()
    rows = build_rows(predictions, outcomes, now)

    common.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_files = sorted(
        (p.name for p in common.REPORTS_DIR.glob("*.md")), reverse=True)

    now_iso = datetime.fromtimestamp(now, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M")
    out_path = args.out or str(common.DATA_DIR / "dashboard.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(render_html(rows, report_files, now_iso))

    if args.text:
        print(render_text(rows))
    actionable = count_actionable(rows)
    print(f"Dashboard written to {out_path}")
    print(f"預測 {len(rows)} 筆,其中 {actionable} 筆可驗證"
          + (" → 執行 python verify_predictions.py --fetch" if actionable else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
