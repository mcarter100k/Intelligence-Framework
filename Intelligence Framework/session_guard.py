"""
session_guard.py
────────────────
Protects your capital by enforcing hard daily limits:

  1. MAX_DAILY_LOSS_R    — if today's realized trades are down this many R
                           (peak-to-trough), no more trades today.
  2. MAX_DAILY_LOSS_PCT  — same idea in % of account, enforced whenever the
                           ledger's return_pct column carries data.
  3. MAX_TRADES_PER_SESSION — after this many positions today, the session
                           is closed regardless of P&L. Positions sharing a
                           currency leg count as ONE (correlated exposure is
                           one bet, not two).

Plain English: this is the circuit breaker. The most dangerous time to trade
               is after a loss — your judgment is compromised. The machine
               enforces the rule your emotions will try to override.

PROMOTED out of shadow/ 2026-09-09 per
docs/specs/circuit_breaker_promotion_spec.md. The adapter lives HERE, in the
breaker: it reads the live `trades.csv` two-row ledger (OPEN row at entry,
CLOSE row at exit, linked by position_id — see
docs/specs/trade_logger_repair_spec.md). Append-only ledgers are never
modified to fit a consumer. Realized performance is derived per-day in R
from prices: R = direction-signed (close − open) / |open − stop|.
Day boundary is the UTC day — the ledger's timestamp_utc is authoritative.

Nothing in here talks to OANDA or the internet. It only reads the ledger.
It never raises. A genuinely ABSENT ledger (no trades yet) returns ACTIVE;
a ledger that exists but is CORRUPT/unreadable (or has the wrong columns)
returns HALTED (fail-closed) — a broken circuit breaker must stop trading,
not permit it.

Usage:
    from session_guard import get_session_status, can_trade

    status = get_session_status("trades.csv", account_balance=10_000)
    if not can_trade("trades.csv", account_balance=10_000):
        print("Session halted — stand aside")
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Union

# ── Hard limits ────────────────────────────────────────────────────────────────
MAX_DAILY_LOSS_R:       float = 2.0   # R peak-to-trough — halt for the day
MAX_DAILY_LOSS_PCT:     float = 2.0   # % of account — enforced when data exists
MAX_TRADES_PER_SESSION: int   = 2     # leg-grouped positions — session closed

DEFAULT_JOURNAL = "trades.csv"

# Columns the two-row ledger must carry for the breaker to do its job.
_REQUIRED_COLUMNS = {
    "row_type", "position_id", "timestamp_utc", "instrument", "direction",
    "open_price", "stop", "close_price",
}

# ── Status constants ───────────────────────────────────────────────────────────
STATUS_ACTIVE:         str = "ACTIVE"
STATUS_HALTED:         str = "HALTED"
STATUS_SESSION_CLOSED: str = "SESSION_CLOSED"


def get_session_status(
    journal_path: Union[str, Path] = DEFAULT_JOURNAL,
    account_balance: float = 0.0,
) -> dict:
    """
    Read today's ledger rows and return the current session status.

    Plain English: look at what positions were opened and closed today, walk
                   the realized results in order, and decide if we're still
                   allowed to trade.

    Returns a dict with:
      status             : ACTIVE | HALTED | SESSION_CLOSED
      reason             : plain-English explanation
      trades_today       : positions opened today (shared-leg groups = one)
      realized_loss_r    : peak-to-trough drawdown of today's realized R
      realized_loss_pct  : same in % of account (0.0 when the ledger carries
                           no return_pct data today)
      remaining_capacity : R of daily loss limit still available (0 if halted)
    """
    if account_balance <= 0:
        return _result(STATUS_HALTED,
                       "Account balance is zero or negative — cannot trade",
                       0, 0.0, 0.0, 0.0)

    stats = _read_today_stats(journal_path)
    if stats is None:
        # Fail CLOSED: an unreadable/wrong-schema ledger means we cannot
        # verify the day's limits — stand aside rather than assume all-clear.
        return _result(
            STATUS_HALTED,
            ("Trade ledger is unreadable or has the wrong columns — cannot "
             "verify daily limits. Standing down until it is fixed "
             "(fail-safe)."),
            0, 0.0, 0.0, 0.0,
        )
    trades_today, loss_r, loss_pct = stats

    # Check 1: daily loss limits — R always; % whenever the data exists.
    if loss_r >= MAX_DAILY_LOSS_R or loss_pct >= MAX_DAILY_LOSS_PCT:
        unit = (f"-{loss_r:.2f}R" if loss_r >= MAX_DAILY_LOSS_R
                else f"-{loss_pct:.2f}%")
        return _result(
            STATUS_HALTED,
            (f"Daily drawdown limit reached: {unit} peak-to-trough "
             f"(limits: {MAX_DAILY_LOSS_R}R / {MAX_DAILY_LOSS_PCT}%). "
             f"No more trades today. Come back tomorrow with a fresh slate."),
            trades_today, loss_r, loss_pct, 0.0,
        )

    # Check 2: position count (shared currency legs group into one).
    if trades_today >= MAX_TRADES_PER_SESSION:
        return _result(
            STATUS_SESSION_CLOSED,
            (f"Maximum positions per session reached: {trades_today} of "
             f"{MAX_TRADES_PER_SESSION} (positions sharing a currency leg "
             f"count as one). Over-trading is an account killer. "
             f"Session closed."),
            trades_today, loss_r, loss_pct,
            max(0.0, MAX_DAILY_LOSS_R - loss_r),
        )

    remaining = max(0.0, MAX_DAILY_LOSS_R - loss_r)
    return _result(
        STATUS_ACTIVE,
        (f"Trading permitted. {trades_today} of {MAX_TRADES_PER_SESSION} "
         f"positions taken today. {remaining:.2f}R of daily loss limit "
         f"remaining."),
        trades_today, loss_r, loss_pct, remaining,
    )


def can_trade(
    journal_path: Union[str, Path] = DEFAULT_JOURNAL,
    account_balance: float = 0.0,
) -> bool:
    """
    Single boolean: True = trading is permitted, False = stand aside.

    Plain English: the watcher calls this first. If it returns False,
                   no alert fires, no matter how good the setup looks.
    """
    status = get_session_status(journal_path, account_balance)
    return status["status"] == STATUS_ACTIVE


# ── Standing rule: shared currency leg = ONE position ─────────────────────────
def count_leg_grouped_positions(instruments: Iterable[str]) -> int:
    """Count positions where any shared currency leg merges them into one.

    Plain English: long GBP/AUD and short GBP/JPY is one pound bet wearing
    two hats. Against the session's position limit it counts once.

    Grouping is by connected components: GBP_AUD+GBP_JPY share GBP (one);
    add AUD_JPY and all three chain into one. Documented as the standing
    rule in risk_config (adopted 2026-09-09,
    docs/specs/circuit_breaker_promotion_spec.md). Lives here, not in
    risk_config, to keep the import direction one-way.
    """
    groups: List[set] = []
    for inst in instruments:
        legs = set(str(inst).replace("/", "_").split("_")) - {""}
        if not legs:
            continue
        keep = []
        for g in groups:
            if g & legs:
                legs = legs | g          # chain: absorb every touching group
            else:
                keep.append(g)
        keep.append(set(legs))
        groups = keep
    return len(groups)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _read_today_stats(
    journal_path: Union[str, Path],
) -> Optional[Tuple[int, float, float]]:
    """
    Read the two-row ledger; return (positions_today, loss_r, loss_pct)
    or None when the file exists but cannot be trusted (fail closed).

    - positions_today: leg-grouped count of positions whose OPEN row's
      timestamp_utc is today (UTC). An OPEN without a CLOSE still counts —
      an open position is exposure.
    - loss_r: max peak-to-trough drawdown of the running realized-R curve
      over today's CLOSE rows, in file order (append order ≈ chronological).
      R = direction-signed (close − open) / |open − stop|. A close with no
      parseable stop contributes its position to the count but no R (same
      rule as the old guard's unreadable single value).
    - loss_pct: same curve over return_pct where present; 0.0 when today's
      closes carry no return_pct data.

    An intraday swing of +2R then −3R registers as 3R of drawdown (not
    netted to −1R): the limit reflects the worst the day actually was.
    PAPER rows count — a paper session that would have halted a real one is
    information the trader wants.
    """
    path = Path(journal_path)
    if not path.exists():
        return 0, 0.0, 0.0             # no ledger yet — nothing taken today

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    open_instruments: List[str] = []

    cum_r = peak_r = dd_r = 0.0
    cum_p = peak_p = dd_p = 0.0

    try:
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                return 0, 0.0, 0.0     # empty file — no trades yet today
            if not _REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
                return None            # wrong schema — cannot verify limits
            for row in reader:
                ts = (row.get("timestamp_utc") or "").strip()
                if not ts.startswith(today):
                    continue
                rtype = (row.get("row_type") or "").strip().upper()
                if rtype == "OPEN":
                    open_instruments.append(row.get("instrument") or "")
                    continue
                if rtype != "CLOSE":
                    continue
                r = _row_r(row)
                if r is not None:
                    cum_r += r
                    peak_r = max(peak_r, cum_r)
                    dd_r   = max(dd_r, peak_r - cum_r)
                pct = _parse_float(row.get("return_pct"))
                if pct is not None:
                    cum_p += pct
                    peak_p = max(peak_p, cum_p)
                    dd_p   = max(dd_p, peak_p - cum_p)
    except Exception:
        return None                    # exists but unparseable — fail CLOSED

    positions = count_leg_grouped_positions(i for i in open_instruments if i)
    return positions, round(dd_r, 4), round(dd_p, 4)


def _row_r(row: Dict) -> Optional[float]:
    """Realized R of one CLOSE row from prices; None when not computable."""
    o = _parse_float(row.get("open_price"))
    c = _parse_float(row.get("close_price"))
    s = _parse_float(row.get("stop"))
    if o is None or c is None or s is None:
        return None
    risk = abs(o - s)
    if risk <= 0:
        return None                    # no adverse room — unscoreable
    direction = (row.get("direction") or "").strip().upper()
    if direction == "LONG":
        return (c - o) / risk
    if direction == "SHORT":
        return (o - c) / risk
    return None


def _parse_float(v) -> Optional[float]:
    try:
        s = str(v).strip()
        return float(s) if s else None
    except (TypeError, ValueError):
        return None


def _result(
    status: str,
    reason: str,
    trades_today: int,
    realized_loss_r: float,
    realized_loss_pct: float,
    remaining_capacity: float,
) -> dict:
    return {
        "status":             status,
        "reason":             reason,
        "trades_today":       trades_today,
        "realized_loss_r":    round(realized_loss_r, 4),
        "realized_loss_pct":  round(realized_loss_pct, 4),
        "remaining_capacity": round(remaining_capacity, 4),
    }
