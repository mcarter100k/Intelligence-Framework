"""
trade_receiver.py
─────────────────
Persistent background server that catches every GBP/AUD trade event
from the MT5 TradeLogger EA and writes outcomes back into the framework.

Run once before you start trading:
    python3 trade_receiver.py

Keep it running in a terminal tab all session.
Press Ctrl+C to stop — it prints a summary when it exits.

What it does automatically:
  - On trade OPEN  : stores entry price, direction, matches to nearest
                     framework run (within 2 hours), records the grade
                     that was active when you entered
  - On trade CLOSE : calculates pips gained/lost, labels WIN/LOSS/BE,
                     writes the result back into run_journal.csv so the
                     template matcher and calibration engine can use it
"""

from __future__ import annotations

import csv
import json
import os
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────

_DIR          = Path(__file__).parent
TRADES_FILE   = _DIR / "trades.csv"
JOURNAL_FILE  = _DIR / "run_journal.csv"
PORT          = 5001

# pip multiplier for GBP/AUD (4-decimal pair)
_PIP = 10_000

# ── In-memory open positions ───────────────────────────────────────────────────
# key = position_id (string), value = dict with entry details
_open: dict[str, dict] = {}
_lock = threading.Lock()


# ── HTTP server ────────────────────────────────────────────────────────────────

class _Handler(BaseHTTPRequestHandler):

    def do_POST(self):
        if self.path != "/trade":
            self._send(404, "Not found")
            return
        n    = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(n)
        try:
            _handle_event(json.loads(body))
            self._send(200, "OK")
        except Exception as exc:
            print(f"[receiver] Error processing event: {exc}")
            self._send(500, str(exc))

    def do_GET(self):
        if self.path == "/status":
            with _lock:
                payload = json.dumps({
                    "status":          "running",
                    "open_positions":  len(_open),
                    "position_ids":    list(_open.keys()),
                })
            self._send(200, payload, "application/json")

        elif self.path == "/stats":
            stats = _compute_stats()
            self._send(200, json.dumps(stats, indent=2), "application/json")

        else:
            self._send(404, "Not found")

    def _send(self, code: int, body: str, ct: str = "text/plain"):
        self.send_response(code)
        self.send_header("Content-Type", ct)
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *_):
        pass  # silence default access log


# ── Event processing ───────────────────────────────────────────────────────────

def _handle_event(data: dict):
    event  = data.get("type", "")
    pos_id = str(data.get("position_id", data.get("ticket", "")))
    sym    = data.get("symbol", "")

    if event == "ping":
        print("[receiver] MT5 TradeLogger EA is connected and active")
        return

    if event == "OPEN":
        # direction of the OPENING deal = direction of the trade
        raw_dir   = data.get("direction", "BUY")
        direction = "LONG" if raw_dir == "BUY" else "SHORT"
        open_time = _parse_time(data.get("time", ""))

        run_ts, grade, conviction, regime = _match_journal(open_time)

        entry = {
            "open_ticket":  data.get("ticket"),
            "position_id":  pos_id,
            "symbol":       sym,
            "direction":    direction,
            "open_price":   data.get("price"),
            "volume":       data.get("volume"),
            "open_time":    data.get("time", ""),
            "journal_run":  run_ts,
            "grade":        grade,
            "conviction":   conviction,
            "regime":       regime,
        }
        with _lock:
            _open[pos_id] = entry

        print(f"[receiver] OPEN   {sym} {direction} @ {data.get('price'):.5f}"
              f"  grade={grade or '?'}  run={run_ts[:16] if run_ts else 'no match'}")

    elif event == "CLOSE":
        with _lock:
            pending = _open.pop(pos_id, None)

        close_price = data.get("price", 0.0)
        profit      = data.get("profit",     0.0)
        commission  = data.get("commission", 0.0)
        swap        = data.get("swap",        0.0)
        net         = round(profit + commission + swap, 2)

        if pending is None:
            # Close with no tracked open (framework started after trade opened)
            raw_dir   = data.get("direction", "SELL")
            # Close direction is opposite of trade direction
            direction = "LONG" if raw_dir == "SELL" else "SHORT"
            close_time = _parse_time(data.get("time", ""))
            run_ts, grade, conviction, regime = _match_journal(close_time)
            pending = {
                "open_ticket": None, "position_id": pos_id,
                "symbol": sym, "direction": direction,
                "open_price": None, "volume": data.get("volume"),
                "open_time": "", "journal_run": run_ts,
                "grade": grade, "conviction": conviction, "regime": regime,
            }

        open_price = pending.get("open_price")
        direction  = pending.get("direction", "LONG")

        pips = None
        if open_price and close_price:
            raw_pips = (close_price - open_price) * _PIP
            pips     = round(raw_pips if direction == "LONG" else -raw_pips, 1)

        outcome = "WIN" if net > 0 else "LOSS" if net < 0 else "BE"

        row = {
            "close_time":    data.get("time", ""),
            "open_time":     pending["open_time"],
            "position_id":   pos_id,
            "symbol":        sym,
            "direction":     direction,
            "open_price":    open_price or "",
            "close_price":   close_price,
            "volume":        pending.get("volume", ""),
            "pips":          pips if pips is not None else "",
            "profit":        profit,
            "commission":    commission,
            "swap":          swap,
            "net":           net,
            "outcome":       outcome,
            "grade":         pending.get("grade", ""),
            "conviction":    pending.get("conviction", ""),
            "regime":        pending.get("regime", ""),
            "journal_run":   pending.get("journal_run", ""),
        }

        _write_trade(row)
        _update_journal(pending.get("journal_run", ""), row)

        pips_str = f"{pips:+.1f} pips" if pips is not None else "pips unknown"
        icon     = "✅" if outcome == "WIN" else "❌" if outcome == "LOSS" else "〰"
        print(f"[receiver] CLOSE  {sym} {direction}  {pips_str}  "
              f"{icon} {outcome}  net {net:+.2f}")


# ── Journal matching ───────────────────────────────────────────────────────────

def _match_journal(trade_dt: datetime | None) -> tuple[str, str, str, str]:
    """
    Find the closest run_journal.csv row within 2 hours of trade_dt.
    Returns (run_timestamp, grade, conviction, regime).
    """
    if trade_dt is None or not JOURNAL_FILE.exists():
        return "", "", "", ""

    best_ts   = ""
    best_gap  = float("inf")
    best_grade = best_conv = best_reg = ""

    try:
        with open(JOURNAL_FILE, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                ts = row.get("time_utc", "")
                dt = row.get("date", "")
                if not ts or not dt:
                    continue
                try:
                    run_dt = datetime.strptime(f"{dt} {ts[:5]}", "%Y-%m-%d %H:%M")
                    gap    = abs((trade_dt - run_dt).total_seconds())
                    if gap < best_gap and gap < 7_200:
                        best_gap   = gap
                        best_ts    = f"{dt} {ts[:5]}"
                        best_grade = row.get("grade", row.get("action", ""))
                        best_conv  = row.get("conviction_score", "")
                        best_reg   = row.get("regime", "")
                except ValueError:
                    continue
    except Exception:
        pass

    return best_ts, best_grade, best_conv, best_reg


# ── Persistence ────────────────────────────────────────────────────────────────

_TRADE_FIELDS = [
    "close_time", "open_time", "position_id", "symbol", "direction",
    "open_price", "close_price", "volume", "pips",
    "profit", "commission", "swap", "net", "outcome",
    "grade", "conviction", "regime", "journal_run",
    "balance_open", "balance_close", "return_pct",
]


def _write_trade(row: dict):
    """Append closed trade to trades.csv."""
    new_file = not TRADES_FILE.exists()
    with open(TRADES_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_TRADE_FIELDS, extrasaction="ignore")
        if new_file:
            w.writeheader()
        w.writerow(row)


def _update_journal(run_ts: str, trade: dict):
    """
    Write trade outcome back into the matching run_journal.csv row.
    Adds columns traded / trade_pips / trade_outcome / trade_net
    if they don't exist yet.
    """
    if not run_ts or not JOURNAL_FILE.exists():
        return

    outcome_cols = ["traded", "trade_pips", "trade_outcome", "trade_net"]
    prefix       = run_ts[:16]  # "YYYY-MM-DD HH:MM"

    try:
        rows: list[dict] = []
        fieldnames: list[str] = []
        updated = False

        with open(JOURNAL_FILE, newline="", encoding="utf-8") as f:
            reader     = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            for col in outcome_cols:
                if col not in fieldnames:
                    fieldnames.append(col)
            for row in reader:
                ts = f"{row.get('date','')} {row.get('time_utc','')[:5]}"
                if ts.startswith(prefix) and not updated:
                    row["traded"]        = "YES"
                    row["trade_pips"]    = trade.get("pips", "")
                    row["trade_outcome"] = trade.get("outcome", "")
                    row["trade_net"]     = trade.get("net", "")
                    updated = True
                rows.append(row)

        if updated:
            with open(JOURNAL_FILE, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                w.writeheader()
                w.writerows(rows)
            print(f"[receiver] Journal updated for run {prefix}")

    except Exception as exc:
        print(f"[receiver] Could not update journal: {exc}")


# ── Stats ──────────────────────────────────────────────────────────────────────

def _compute_stats() -> dict:
    """Read trades.csv and return summary statistics."""
    if not TRADES_FILE.exists():
        return {"message": "No trades logged yet"}

    wins = losses = be = 0
    win_pips = loss_pips = 0.0
    by_grade: dict[str, dict] = {}

    with open(TRADES_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            outcome = row.get("outcome", "")
            pips    = _safe_float(row.get("pips"))
            grade   = row.get("grade") or "?"

            if grade not in by_grade:
                by_grade[grade] = {"wins": 0, "losses": 0, "total_pips": 0.0}

            if outcome == "WIN":
                wins += 1
                if pips: win_pips += pips
                by_grade[grade]["wins"] += 1
            elif outcome == "LOSS":
                losses += 1
                if pips: loss_pips += abs(pips)
                by_grade[grade]["losses"] += 1
            else:
                be += 1

            if pips:
                by_grade[grade]["total_pips"] += pips

    total    = wins + losses + be
    win_rate = round(100 * wins / (wins + losses), 1) if (wins + losses) else 0
    avg_win  = round(win_pips / wins, 1)    if wins    else 0
    avg_loss = round(loss_pips / losses, 1) if losses  else 0
    prac_rr  = round(avg_win / avg_loss, 2) if avg_loss else None

    return {
        "total_trades": total,
        "wins": wins, "losses": losses, "breakeven": be,
        "win_rate_pct": win_rate,
        "avg_win_pips":  avg_win,
        "avg_loss_pips": avg_loss,
        "practical_rr":  prac_rr,
        "by_grade": {
            g: {
                "trades":    s["wins"] + s["losses"],
                "wins":      s["wins"],
                "losses":    s["losses"],
                "win_rate":  round(100 * s["wins"] / (s["wins"] + s["losses"]), 1)
                             if (s["wins"] + s["losses"]) else 0,
                "total_pips": round(s["total_pips"], 1),
            }
            for g, s in sorted(by_grade.items())
        },
    }


def print_stats():
    s = _compute_stats()
    if "message" in s:
        print(f"\n  {s['message']}")
        return

    print(f"\n  {'─'*50}")
    print(f"  TRADE PERFORMANCE SUMMARY")
    print(f"  {'─'*50}")
    print(f"  Total trades  : {s['total_trades']}")
    print(f"  Wins / Losses : {s['wins']} / {s['losses']}   "
          f"({s['win_rate_pct']}% win rate)")
    print(f"  Avg win       : +{s['avg_win_pips']} pips")
    print(f"  Avg loss      : -{s['avg_loss_pips']} pips")
    if s["practical_rr"]:
        rr = s["practical_rr"]
        rr_note = ("good" if rr >= 1.5 else "acceptable" if rr >= 1.0 else "needs improvement")
        print(f"  Practical R:R : {rr}  ({rr_note})")

    if s["by_grade"]:
        print(f"\n  By setup grade:")
        for grade, g in s["by_grade"].items():
            if g["trades"] == 0:
                continue
            pips_str = f"{g['total_pips']:+.1f} pips total"
            print(f"    {grade:<4}  {g['trades']:>3} trades  "
                  f"{g['win_rate']:>5.1f}% wins  {pips_str}")
    print(f"  {'─'*50}\n")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_time(raw: str) -> datetime | None:
    """Parse MT5 time string '2026.04.25 09:30:00' or '2026-04-25T09:30:00'."""
    for fmt in ("%Y.%m.%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(raw[:19], fmt)
        except ValueError:
            continue
    return None


def _safe_float(val) -> float | None:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ── Entry point ────────────────────────────────────────────────────────────────

def start_server(port: int = PORT) -> HTTPServer:
    server = HTTPServer(("localhost", port), _Handler)
    return server


if __name__ == "__main__":
    print(f"  {'═'*50}")
    print(f"  TRADE RECEIVER — Intelligence Framework")
    print(f"  {'═'*50}")
    print(f"  Listening on http://localhost:{PORT}")
    print(f"  Waiting for MT5 TradeLogger EA...")
    print(f"  (Ctrl+C to stop)\n")

    try:
        srv = start_server(PORT)
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")
        print_stats()
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"  Port {PORT} is already in use — receiver is already running.")
        else:
            raise
