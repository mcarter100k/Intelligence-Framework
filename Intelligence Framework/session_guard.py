"""
session_guard.py
────────────────
Protects your capital by enforcing two hard daily limits:

  1. MAX_DAILY_LOSS_PCT  — if you have lost this % of your account today,
                           no more trades are allowed for the rest of the day.
  2. MAX_TRADES_PER_SESSION — if you have taken this many trades today,
                              the session is closed regardless of P&L.

Plain English: this is the circuit breaker. The most dangerous time to trade
               is after a loss — your judgment is compromised. The machine
               enforces the rule your emotions will try to override.

Nothing in here talks to OANDA or the internet. It only reads the journal.
It never raises. A genuinely ABSENT journal (start of day, no trades yet)
returns ACTIVE; a journal that exists but is CORRUPT/unreadable returns HALTED
(fail-closed) — a broken circuit breaker must stop trading, not permit it.

Usage:
    from session_guard import get_session_status, can_trade

    status = get_session_status(journal_path, account_balance=10_000)
    if not can_trade(journal_path, account_balance=10_000):
        print("Session halted — stand aside")
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path
from typing import Union

# ── Hard limits ────────────────────────────────────────────────────────────────
# These are imported by risk_config.HARD_LIMITS too — single source of truth.
MAX_DAILY_LOSS_PCT:     float = 2.0   # % of account — halt trading for the day
MAX_TRADES_PER_SESSION: int   = 2     # trades — session closed after this many


# ── Status constants ───────────────────────────────────────────────────────────
STATUS_ACTIVE:         str = "ACTIVE"
STATUS_HALTED:         str = "HALTED"
STATUS_SESSION_CLOSED: str = "SESSION_CLOSED"


def get_session_status(
    journal_path: Union[str, Path],
    account_balance: float,
) -> dict:
    """
    Read today's journal entries and return the current session status.

    Plain English: look at what trades were taken today, add up the losses,
                   count the trades, and decide if we're still allowed to trade.

    Returns a dict with:
      status             : ACTIVE | HALTED | SESSION_CLOSED
      reason             : plain-English explanation
      trades_today       : how many completed trades taken today
      realized_loss_pct  : total % loss from closed trades today
      remaining_capacity : % of daily loss limit still available (0 if halted)
    """
    if account_balance <= 0:
        return _result(STATUS_HALTED, "Account balance is zero or negative — cannot trade",
                       0, 0.0, 0.0)

    trades_today, realized_loss_pct, ok = _read_today_stats(journal_path)

    # Fail CLOSED: an unreadable/corrupt journal means we cannot verify the
    # day's limits, so we must stand aside rather than assume all-clear.
    if not ok:
        return _result(
            STATUS_HALTED,
            ("Trade journal is unreadable/corrupt — cannot verify daily limits. "
             "Standing down until it is fixed (fail-safe)."),
            0, 0.0, 0.0,
        )

    # Check 1: daily loss limit
    if realized_loss_pct >= MAX_DAILY_LOSS_PCT:
        remaining = 0.0
        return _result(
            STATUS_HALTED,
            (
                f"Daily drawdown limit reached: -{realized_loss_pct:.2f}% "
                f"peak-to-trough (limit: {MAX_DAILY_LOSS_PCT}%). "
                f"No more trades today. Come back tomorrow with a fresh slate."
            ),
            trades_today,
            realized_loss_pct,
            remaining,
        )

    # Check 2: trade count limit
    if trades_today >= MAX_TRADES_PER_SESSION:
        remaining = max(0.0, MAX_DAILY_LOSS_PCT - realized_loss_pct)
        return _result(
            STATUS_SESSION_CLOSED,
            (
                f"Maximum trades per session reached: {trades_today} of "
                f"{MAX_TRADES_PER_SESSION}. "
                f"Over-trading is an account killer. Session closed."
            ),
            trades_today,
            realized_loss_pct,
            remaining,
        )

    # All clear
    remaining = max(0.0, MAX_DAILY_LOSS_PCT - realized_loss_pct)
    return _result(
        STATUS_ACTIVE,
        (
            f"Trading permitted. "
            f"{trades_today} of {MAX_TRADES_PER_SESSION} trades taken today. "
            f"{remaining:.2f}% of daily loss limit remaining."
        ),
        trades_today,
        realized_loss_pct,
        remaining,
    )


def can_trade(
    journal_path: Union[str, Path],
    account_balance: float,
) -> bool:
    """
    Single boolean: True = trading is permitted, False = stand aside.

    Plain English: the watcher calls this first. If it returns False,
                   no alert fires, no matter how good the setup looks.
    """
    status = get_session_status(journal_path, account_balance)
    return status["status"] == STATUS_ACTIVE


# ── Internal helpers ──────────────────────────────────────────────────────────

def _read_today_stats(journal_path: Union[str, Path]) -> tuple[int, float, bool]:
    """
    Read the journal and return (trades_today, realized_loss_pct, ok).

    realized_loss_pct is the maximum peak-to-trough DRAWDOWN of today's realized
    equity curve, in %. An intraday swing of +2% then −3% registers as a 3%
    drawdown (not netted away to −1%), so the daily limit reflects the worst
    the account was actually down today.

    Rules:
      - Only rows where date == today (local, matching the journal) are counted.
      - Only rows where trade_taken == "YES" are counted.
      - pnl_r is a signed percentage: -1.1 means lost 1.1% of account.
      - Open trades (blank pnl_r) count toward the trade count, not the curve.

    `ok` is False ONLY when the journal exists but cannot be parsed (corrupt) →
    the caller fails CLOSED. A genuinely absent journal is the normal
    start-of-day state → (0, 0.0, True).
    """
    path = Path(journal_path)
    if not path.exists():
        return 0, 0.0, True            # no journal yet — nothing taken today

    today_str = date.today().isoformat()
    trades_today = 0
    cum    = 0.0   # running realized P&L through the day (file order ≈ chrono)
    peak   = 0.0   # highest running P&L so far
    max_dd = 0.0   # largest peak-to-trough drawdown seen

    try:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return 0, 0.0, True        # empty file — no trades yet today
            required = {"date", "trade_taken", "pnl_r"}
            if not required.issubset(set(reader.fieldnames)):
                # Header exists but lacks the columns we rely on — the journal
                # format is wrong/corrupt. Cannot verify limits → fail closed.
                return 0, 0.0, False
            for row in reader:
                if row.get("date", "") != today_str:
                    continue
                if row.get("trade_taken", "").upper() != "YES":
                    continue

                trades_today += 1
                pnl_str = row.get("pnl_r", "").strip()
                if not pnl_str:
                    continue           # open trade — no realized P&L yet
                try:
                    pnl = float(pnl_str)
                except ValueError:
                    continue           # unreadable single value — skip its P&L
                cum   += pnl
                peak   = max(peak, cum)
                max_dd = max(max_dd, peak - cum)

    except Exception:
        # File exists but could not be parsed — corrupt. Fail CLOSED.
        return 0, 0.0, False

    return trades_today, round(max_dd, 4), True


def _result(
    status: str,
    reason: str,
    trades_today: int,
    realized_loss_pct: float,
    remaining_capacity: float,
) -> dict:
    return {
        "status":             status,
        "reason":             reason,
        "trades_today":       trades_today,
        "realized_loss_pct":  round(realized_loss_pct, 4),
        "remaining_capacity": round(remaining_capacity, 4),
    }
