"""
trade_logger.py
───────────────
Manual trade logging for Liquid Charts Pro (or any web-based platform).

  python3 main.py log open   →  log a new trade entry
  python3 main.py log close  →  log a trade exit
  python3 main.py log list   →  show all open (pending) trades
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from trade_receiver import (
    _write_trade, _update_journal, _match_journal,
    TRADES_FILE, JOURNAL_FILE, _PIP, _safe_float,
    _compute_stats, print_stats,
)

_DIR          = Path(__file__).parent
_PENDING_FILE = _DIR / "pending_trades.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_pending() -> dict:
    if _PENDING_FILE.exists():
        return json.loads(_PENDING_FILE.read_text())
    return {}


def _save_pending(data: dict):
    _PENDING_FILE.write_text(json.dumps(data, indent=2))


def _next_id(pending: dict) -> str:
    existing = [int(k.split("-")[1]) for k in pending if "-" in k]
    n = max(existing) + 1 if existing else 1
    return f"GBPAUD-{n:03d}"


def _ask(prompt: str, options: list[str] | None = None) -> str:
    while True:
        raw = input(f"  {prompt}: ").strip()
        if not raw:
            continue
        if options:
            if raw.upper() in [o.upper() for o in options]:
                return raw.upper()
            print(f"  Enter one of: {' / '.join(options)}")
        else:
            return raw


def _ask_float(prompt: str) -> float:
    while True:
        raw = input(f"  {prompt}: ").strip()
        try:
            return float(raw)
        except ValueError:
            print("  Enter a number (e.g. 2.0456)")


# ── Open ──────────────────────────────────────────────────────────────────────

def log_open():
    """Record a new trade entry."""
    print(f"\n  {'─'*50}")
    print(f"  LOG TRADE OPEN")
    print(f"  {'─'*50}")
    print(f"  Enter the details from your Liquid Charts Pro trade.\n")

    direction     = _ask("Direction  (LONG = buy, SHORT = sell)", ["LONG", "SHORT"])
    entry_price   = _ask_float("Entry price  (e.g. 2.0456)")
    volume        = _ask_float("Volume / lot size  (e.g. 0.10)")
    balance_open  = _ask_float("Account balance before this trade  (e.g. 1250.00)")

    now     = datetime.utcnow()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # Match to nearest framework run
    run_ts, grade, conviction, regime = _match_journal(now)

    pending = _load_pending()
    trade_id = _next_id(pending)

    pending[trade_id] = {
        "trade_id":     trade_id,
        "direction":    direction,
        "open_price":   entry_price,
        "volume":       volume,
        "open_time":    now_str,
        "journal_run":  run_ts,
        "grade":        grade,
        "conviction":   conviction,
        "regime":       regime,
        "balance_open": balance_open,
    }
    _save_pending(pending)

    print(f"\n  Trade saved  →  ID: {trade_id}")
    print(f"  Direction  : {direction}")
    print(f"  Entry      : {entry_price:.5f}")
    print(f"  Balance    : {balance_open:,.2f}")
    if grade:
        print(f"  Grade at entry : {grade}  (conviction {conviction})")
        print(f"  Regime         : {regime}")
        print(f"  Matched run    : {run_ts}")
    else:
        print(f"  No framework run found within 2 hours — grade will show as unknown")
    print(f"\n  When this trade closes, run:  python3 main.py log close")
    print(f"  Your trade ID is: {trade_id}  (you'll need it to close)\n")


# ── Close ─────────────────────────────────────────────────────────────────────

def log_close():
    """Record a trade exit."""
    pending = _load_pending()

    if not pending:
        print("\n  No open trades found. Log an entry first with: python3 main.py log open\n")
        return

    print(f"\n  {'─'*50}")
    print(f"  LOG TRADE CLOSE")
    print(f"  {'─'*50}")
    print(f"  Your open trades:\n")

    for tid, t in pending.items():
        grade_str = f"  grade={t.get('grade','?')}" if t.get('grade') else ""
        print(f"    {tid}  |  {t['direction']}  @ {t['open_price']:.5f}"
              f"  |  opened {t['open_time'][:16]}{grade_str}")

    print()
    trade_id = _ask("Trade ID to close  (e.g. GBPAUD-001)")
    trade_id = trade_id.upper()

    if trade_id not in pending:
        print(f"\n  Trade ID '{trade_id}' not found. Check the list above.\n")
        return

    entry = pending[trade_id]

    print(f"\n  Closing: {trade_id}  {entry['direction']}  opened @ {entry['open_price']:.5f}\n")

    close_price   = _ask_float("Exit price  (e.g. 2.0512)")
    profit        = _ask_float("Profit/loss in account currency  (e.g. 45.20 or -22.50)")
    balance_close = _ask_float("Account balance after this trade  (e.g. 1295.00)")

    now_str   = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    direction = entry["direction"]
    open_price = entry["open_price"]

    raw_pips   = (close_price - open_price) * _PIP
    pips       = round(raw_pips if direction == "LONG" else -raw_pips, 1)
    outcome    = "WIN" if profit > 0 else "LOSS" if profit < 0 else "BE"
    balance_open = entry.get("balance_open", 0)
    return_pct = round((profit / balance_open) * 100, 2) if balance_open else ""

    row = {
        "close_time":  now_str,
        "open_time":   entry["open_time"],
        "position_id": trade_id,
        "symbol":      "GBPAUD",
        "direction":   direction,
        "open_price":  open_price,
        "close_price": close_price,
        "volume":      entry.get("volume", ""),
        "pips":        pips,
        "profit":      profit,
        "commission":  0,
        "swap":        0,
        "net":         profit,
        "outcome":     outcome,
        "grade":         entry.get("grade", ""),
        "conviction":    entry.get("conviction", ""),
        "regime":        entry.get("regime", ""),
        "journal_run":   entry.get("journal_run", ""),
        "balance_open":  balance_open,
        "balance_close": balance_close,
        "return_pct":    return_pct,
    }

    _write_trade(row)
    _update_journal(entry.get("journal_run", ""), row)

    # Remove from pending
    del pending[trade_id]
    _save_pending(pending)

    icon = "✅" if outcome == "WIN" else "❌" if outcome == "LOSS" else "〰"
    print(f"\n  {icon} {outcome}  |  {pips:+.1f} pips  |  {profit:+.2f} account currency")
    if return_pct != "":
        direction_word = "gained" if profit > 0 else "lost"
        print(f"  Account    : {direction_word} {abs(return_pct):.2f}% of balance  "
              f"({balance_open:,.2f} → {balance_close:,.2f})")
    if entry.get("grade"):
        print(f"  Grade at entry was: {entry['grade']}")
    print(f"  Trade logged to trades.csv\n")

    # Show updated stats if we have enough trades
    stats = _compute_stats()
    if isinstance(stats, dict) and stats.get("total_trades", 0) >= 3:
        print_stats()


# ── List ──────────────────────────────────────────────────────────────────────

def log_list():
    """Show all currently open (pending) trades."""
    pending = _load_pending()

    if not pending:
        print("\n  No open trades.\n")
        return

    print(f"\n  {'─'*50}")
    print(f"  OPEN TRADES  ({len(pending)} pending)")
    print(f"  {'─'*50}")
    for tid, t in pending.items():
        grade_str = f"  grade={t.get('grade','?')}" if t.get('grade') else ""
        regime_str = f"  regime={t.get('regime','?')}" if t.get('regime') else ""
        print(f"  {tid}")
        print(f"    Direction  : {t['direction']}")
        print(f"    Entry      : {t['open_price']:.5f}")
        print(f"    Opened     : {t['open_time'][:16]} UTC")
        print(f"    Volume     : {t.get('volume','?')}")
        if t.get('grade'):
            print(f"    Grade      : {t['grade']}{regime_str}")
        print()
    print(f"  To close a trade: python3 main.py log close\n")


# ── Entry ─────────────────────────────────────────────────────────────────────

def run_log(subcmd: str = ""):
    if subcmd == "open":
        log_open()
    elif subcmd == "close":
        log_close()
    elif subcmd == "list":
        log_list()
    else:
        print("\n  Usage:")
        print("    python3 main.py log open   →  log a trade entry")
        print("    python3 main.py log close  →  log a trade exit")
        print("    python3 main.py log list   →  see all open trades\n")
