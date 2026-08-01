"""
trade_logger.py
───────────────
Manual trade journal — pure CLI, pure append-only ledger
(spec: docs/specs/trade_logger_repair_spec.md, team approved + amended
2026-07-31; replaces the pre-rebuild version that depended on a deleted
bridge module).

  python3 trade_logger.py open    →  log a trade entry (OPEN row)
  python3 trade_logger.py close   →  log a trade exit  (CLOSE row)
  python3 trade_logger.py list    →  show open positions

Ledger: trades.csv (gitignored, append-only). TWO-ROW CONVENTION — every
trade is an OPEN row at entry time and a CLOSE row at exit time, linked by
position_id. Closing NEVER edits the OPEN row; open positions are derived
(OPEN rows with no matching CLOSE row). No pending-state file.

Links to the pre-trade evidence stack: the optional stack_id column points at
a pre_trade_journal.csv row (setup_check.py); the most recent matching stack
for the same instrument+direction is offered as the default.

`trade_log.csv` (the April-era framework-snapshot file) is historical
evidence — untouched by this tool.
"""
from __future__ import annotations

import csv
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional

_DIR         = os.path.dirname(os.path.abspath(__file__))
TRADES_FILE  = os.path.join(_DIR, "trades.csv")
_STACK_FILE  = os.path.join(_DIR, "pre_trade_journal.csv")

INSTRUMENTS = ("GBP_AUD", "GBP_JPY")

# Pinned schema (docs/specs/trade_logger_repair_spec.md)
FIELDS = [
    "row_type", "position_id", "timestamp_utc", "instrument", "direction",
    "open_price", "stop", "target", "close_price", "size", "pips", "outcome",
    "balance_open", "balance_close", "return_pct", "stack_id", "rationale",
]


# ── Ledger primitives (append-only) ────────────────────────────────────────────

def _read_rows(path: Optional[str] = None) -> List[Dict]:
    path = path or TRADES_FILE
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _append_row(row: Dict, path: Optional[str] = None) -> None:
    path = path or TRADES_FILE
    exists = os.path.exists(path)
    out = {k: row.get(k, "") for k in FIELDS}
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            w.writeheader()
        w.writerow(out)


def open_positions(path: Optional[str] = None) -> List[Dict]:
    """OPEN rows with no matching CLOSE row — derived, never stored."""
    path = path or TRADES_FILE
    rows = _read_rows(path)
    closed = {r["position_id"] for r in rows if r["row_type"] == "CLOSE"}
    return [r for r in rows
            if r["row_type"] == "OPEN" and r["position_id"] not in closed]


def _next_position_id(instrument: str, path: Optional[str] = None) -> str:
    path = path or TRADES_FILE
    prefix = instrument.replace("_", "")
    nums = [int(r["position_id"].rsplit("-", 1)[-1])
            for r in _read_rows(path)
            if r["row_type"] == "OPEN"
            and r["position_id"].startswith(prefix + "-")
            and r["position_id"].rsplit("-", 1)[-1].isdigit()]
    return f"{prefix}-{(max(nums) + 1) if nums else 1:03d}"


def latest_matching_stack(instrument: str, direction: str,
                          path: Optional[str] = None) -> Optional[str]:
    """Most recent pre_trade_journal stack_id for this instrument+direction —
    offered as the default link at open time."""
    path = path or _STACK_FILE
    if not os.path.exists(path):
        return None
    match = None
    try:
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if (r.get("instrument") == instrument
                        and r.get("direction") == direction):
                    match = r.get("stack_id") or match
    except Exception:
        return None
    return match


def _pip_size(instrument: str) -> float:
    from trade_management import _pip_factor      # instrument-correct pips
    return 1.0 / _pip_factor(instrument)


# ── Prompts (plain English) ────────────────────────────────────────────────────

def _ask(prompt: str, options: Optional[List[str]] = None,
         default: str = "", allow_blank: bool = False) -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        raw = input(f"  {prompt}{suffix}: ").strip()
        if not raw:
            if default:
                return default
            if allow_blank:
                return ""
            continue
        if options and raw.upper() not in [o.upper() for o in options]:
            print(f"  Please enter one of: {' / '.join(options)}")
            continue
        return raw.upper() if options else raw


def _ask_float(prompt: str, allow_blank: bool = False) -> Optional[float]:
    while True:
        raw = input(f"  {prompt}: ").strip()
        if not raw and allow_blank:
            return None
        try:
            return float(raw)
        except ValueError:
            print("  Enter a number (e.g. 217.450) — or leave blank to skip."
                  if allow_blank else "  Enter a number (e.g. 217.450)")


# ── Open ──────────────────────────────────────────────────────────────────────

def log_open() -> None:
    print(f"\n  {'─' * 52}\n  LOG TRADE OPEN\n  {'─' * 52}")
    instrument = _ask("Instrument (GBP_AUD or GBP_JPY)", list(INSTRUMENTS))
    direction  = _ask("Direction (LONG = buy, SHORT = sell)", ["LONG", "SHORT"])
    entry      = _ask_float("Entry price (e.g. 217.450)")
    stop       = _ask_float("Stop price — where the idea is wrong")
    target     = _ask_float("Target price (blank if none yet)", allow_blank=True)
    size       = _ask_float("Size in lots (0.0 for a paper trade)")
    bal        = _ask_float("Account balance before (blank to skip)",
                            allow_blank=True)

    default_stack = latest_matching_stack(instrument, direction) or ""
    stack_id = _ask("Pre-trade stack id (Enter = most recent match, '-' = none)",
                    default=default_stack, allow_blank=True)
    if stack_id == "-":
        stack_id = ""
    rationale = _ask("One-line rationale — why this trade", allow_blank=True)

    pid = _next_position_id(instrument)
    _append_row({
        "row_type": "OPEN", "position_id": pid,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "instrument": instrument, "direction": direction,
        "open_price": entry, "stop": stop,
        "target": target if target is not None else "",
        "size": size,
        "balance_open": bal if bal is not None else "",
        "stack_id": stack_id, "rationale": rationale,
    })
    print(f"\n  OPEN row appended → trades.csv   position id: {pid}")
    if stack_id:
        print(f"  linked to pre-trade stack: {stack_id}")
    print(f"  To close later:  python3 trade_logger.py close\n")


# ── Close ─────────────────────────────────────────────────────────────────────

def log_close() -> None:
    open_rows = open_positions()
    if not open_rows:
        print("\n  No open positions. Log one first: python3 trade_logger.py open\n")
        return

    print(f"\n  {'─' * 52}\n  LOG TRADE CLOSE\n  {'─' * 52}\n  Open positions:")
    for r in open_rows:
        print(f"    {r['position_id']}  {r['instrument']}  {r['direction']}"
              f"  @ {r['open_price']}  (opened {r['timestamp_utc'][:16]})")
    print()

    by_id = {r["position_id"].upper(): r for r in open_rows}
    default_id = open_rows[-1]["position_id"] if len(open_rows) == 1 else ""
    while True:
        pid = _ask("Position id to close", default=default_id).upper()
        if pid in by_id:
            break
        print(f"  '{pid}' is not an open position — see the list above.")
    o = by_id[pid]

    close_price = _ask_float("Exit price")
    bal_close   = _ask_float("Account balance after (blank to skip)",
                             allow_blank=True)

    pip = _pip_size(o["instrument"])
    raw = (close_price - float(o["open_price"])) / pip
    pips = round(raw if o["direction"] == "LONG" else -raw, 1) + 0.0  # no -0.0
    outcome = "WIN" if pips > 0 else "LOSS" if pips < 0 else "BE"

    return_pct = ""
    try:
        bo = float(o.get("balance_open") or "")
        if bal_close is not None and bo:
            return_pct = round((bal_close - bo) / bo * 100, 2)
    except ValueError:
        pass

    _append_row({
        "row_type": "CLOSE", "position_id": pid,
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "instrument": o["instrument"], "direction": o["direction"],
        "open_price": o["open_price"], "stop": o["stop"],
        "target": o["target"], "close_price": close_price,
        "size": o["size"], "pips": pips, "outcome": outcome,
        "balance_open": o.get("balance_open", ""),
        "balance_close": bal_close if bal_close is not None else "",
        "return_pct": return_pct,
        "stack_id": o.get("stack_id", ""), "rationale": o.get("rationale", ""),
    })
    icon = "✅" if outcome == "WIN" else "❌" if outcome == "LOSS" else "〰"
    print(f"\n  {icon} {outcome}  {pips:+.1f} pips   CLOSE row appended → "
          f"trades.csv (OPEN row untouched — two-row ledger)\n")


# ── List ──────────────────────────────────────────────────────────────────────

def log_list() -> None:
    open_rows = open_positions()
    if not open_rows:
        print("\n  No open positions.\n")
        return
    print(f"\n  {'─' * 52}\n  OPEN POSITIONS ({len(open_rows)})\n  {'─' * 52}")
    for r in open_rows:
        print(f"  {r['position_id']}  {r['instrument']}  {r['direction']}"
              f"  @ {r['open_price']}  stop {r['stop']}"
              f"{('  target ' + r['target']) if r['target'] else ''}"
              f"  size {r['size']}")
        if r.get("stack_id"):
            print(f"    stack: {r['stack_id']}")
        if r.get("rationale"):
            print(f"    why:   {r['rationale']}")
    print()


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    cmd = args[0] if args else ""
    if cmd == "open":
        log_open()
    elif cmd == "close":
        log_close()
    elif cmd == "list":
        log_list()
    else:
        print("\n  Usage: python3 trade_logger.py open | close | list\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
