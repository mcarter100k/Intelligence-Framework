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
It never raises — if the journal is missing or corrupt, it returns ACTIVE
so the watcher can log the issue and decide what to do.

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

    trades_today, realized_loss_pct = _read_today_stats(journal_path)

    # Check 1: daily loss limit
    if realized_loss_pct >= MAX_DAILY_LOSS_PCT:
        remaining = 0.0
        return _result(
            STATUS_HALTED,
            (
                f"Daily loss limit reached: -{realized_loss_pct:.2f}% "
                f"(limit: {MAX_DAILY_LOSS_PCT}%). "
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

def _read_today_stats(journal_path: Union[str, Path]) -> tuple[int, float]:
    """
    Read the journal and return (trades_taken_today, total_loss_pct_today).

    Rules:
      - Only rows where date == today are counted.
      - Only rows where trade_taken == "YES" are counted.
      - Only rows with a non-empty pnl_r are counted as closed trades.
        (Open trades — pnl_r is blank — are excluded from the loss total.)
      - pnl_r is stored as a signed percentage: -1.1 means lost 1.1% of account.
        Positive pnl_r values (wins) reduce the net loss.

    Returns (0, 0.0) if journal is missing, empty, or unreadable.
    """
    path = Path(journal_path)
    if not path.exists():
        return 0, 0.0

    today_str = date.today().isoformat()
    trades_today = 0
    net_pnl = 0.0  # positive = net gain, negative = net loss

    try:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("date", "") != today_str:
                    continue
                if row.get("trade_taken", "").upper() != "YES":
                    continue

                pnl_str = row.get("pnl_r", "").strip()
                if not pnl_str:
                    # Open trade — count toward trade count but not P&L yet
                    trades_today += 1
                    continue

                try:
                    pnl = float(pnl_str)
                    trades_today += 1
                    net_pnl += pnl
                except ValueError:
                    # Unreadable pnl_r value — count trade, skip P&L
                    trades_today += 1

    except Exception:
        return 0, 0.0

    # Realized loss is the absolute value of the negative portion.
    # If net_pnl is positive (e.g., +2.1 from a big win), realized_loss_pct = 0.
    realized_loss_pct = max(0.0, -net_pnl)
    return trades_today, realized_loss_pct


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
