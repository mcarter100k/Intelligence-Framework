"""
trade_management.py
───────────────────
Systematic trade management: when to move stop, take partial profits, and trail.

These rules remove the hardest in-trade decisions — the ones where most edge
is lost. Once you're in a trade the framework hands you a written plan.
Follow it regardless of how the trade feels.

Rules (applied in sequence as trade moves in your favor):
  Step 1  @ +1R   : move stop to breakeven, close 50% of position
  Step 2  @ +1.5R : begin trailing stop (0.5R behind price)
  Step 3  @ target: close remaining position

Invalidation: price closes back through the key entry level on the 15m.
              The setup is dead regardless of P&L — exit immediately.

Grade notes:
  A+/A  : consider skipping the Step 1 partial — let full size run to target
  B+/B  : always take Step 1 partial — protect the trade on imperfect setups
"""

from __future__ import annotations
from typing import Optional


# ── Management parameters ──────────────────────────────────────────────────────
# Wired live-core via setup_check.py (docs/specs/setup_check_spec.md).
MAX_STOP_ATR_MULTIPLE = 1.5  # INFORMED PRIOR — a structural stop wider than
                             # this many daily ATRs is flagged as oversized
SPREAD_PIPS           = 4.0  # typical broker round-trip (from quarantined
MIN_RR_AFTER_SPREAD   = 1.5  # HARD_LIMITS — informed priors, self-contained)
BREAKEVEN_R    = 1.0   # move stop to entry when trade reaches this R
PARTIAL_PCT    = 50    # % of position to close at Step 1
TRAIL_START_R  = 1.5   # begin trailing after this R
TRAIL_GAP_R    = 0.5   # trailing stop stays this many R behind current price


def _pip_factor(instrument: str) -> float:
    """Pips per price unit: JPY crosses are 2-dp (×100), others 4-dp (×10000)."""
    return 100.0 if instrument.replace("_", "").endswith("JPY") else 10_000.0


def _price_decimals(instrument: str) -> int:
    return 3 if instrument.replace("_", "").endswith("JPY") else 5


def get_management_plan(
    entry: float,
    stop: float,
    target: float,
    direction: str,
    grade: str = "B+",
    key_level: Optional[float] = None,
    instrument: str = "GBP_AUD",
) -> dict:
    """
    Build the full trade management plan at the moment the entry alert fires.

    Plain English: the moment you get an alert, this function tells you EXACTLY
                   where to move your stop, when to take profits, and when the
                   trade idea is dead. Write these levels down before you click.

    Args:
        entry     : fill price (where you entered the trade)
        stop      : initial stop-loss price (structure-based, from entry_confirmation)
        target    : full take-profit price (next key level from the framework)
        direction : "LONG" or "SHORT"
        grade     : setup grade — affects the management note (A+ vs B+)
        key_level : the S/R level that triggered the entry. A 15m close back
                    through this level means the setup is invalid.

    Returns dict:
        breakeven_price     : move stop here when trade reaches +1R
        partial_exit_price  : close PARTIAL_PCT% of position here (+1R)
        trail_start_price   : begin trailing stop here (+1.5R)
        trail_stop_at_start : where to place the trailing stop when it starts
        invalidation_price  : 15m close through this = setup is dead
        r_pips              : 1R in pips (the unit of all steps)
        full_target_price   : original target (full exit)
        plan_text           : formatted block ready to print in the alert
    """
    # ── Validate geometry before building a plan ──────────────────────────────
    # Never emit a clean-looking plan for an incoherent trade (stop on the wrong
    # side, target closer than the stop, etc.).
    errors = []
    if direction not in ("LONG", "SHORT"):
        errors.append(f"Unknown direction '{direction}' — expected LONG or SHORT")
    risk   = abs(entry - stop)
    reward = abs(target - entry)
    if risk == 0:
        errors.append("Stop equals entry — zero risk, cannot compute R")
    if direction == "LONG":
        if stop >= entry:
            errors.append(f"LONG stop ({stop}) must be BELOW entry ({entry})")
        if target <= entry:
            errors.append(f"LONG target ({target}) must be ABOVE entry ({entry})")
    elif direction == "SHORT":
        if stop <= entry:
            errors.append(f"SHORT stop ({stop}) must be ABOVE entry ({entry})")
        if target >= entry:
            errors.append(f"SHORT target ({target}) must be BELOW entry ({entry})")
    rr = round(reward / risk, 2) if risk > 0 else 0.0

    # Effective reward:risk AFTER spread — the framework's real tradeability
    # floor. Spread widens the effective stop and eats into the reward. This is
    # the only place the 1.5 floor is enforced. Constants are LOCAL (lifted from
    # the quarantined risk_config's HARD_LIMITS — informed priors): this module
    # is live-core via setup_check and must not import from shadow/, nor depend
    # on shadow/'s conftest happening to be on sys.path.
    _spread_price = SPREAD_PIPS / _pip_factor(instrument)
    _rr_floor     = MIN_RR_AFTER_SPREAD
    eff_reward    = max(0.0, reward - _spread_price)
    eff_risk      = risk + _spread_price
    effective_rr  = round(eff_reward / eff_risk, 2) if eff_risk > 0 else 0.0
    if not errors and effective_rr < _rr_floor:
        errors.append(
            f"Effective R:R after spread {effective_rr}:1 is below the "
            f"{_rr_floor}:1 minimum — not worth the spread"
        )

    if errors:
        return {
            "valid":        False,
            "errors":       errors,
            "rr":           rr,
            "effective_rr": effective_rr,
            "r_pips":       round(risk * _pip_factor(instrument), 1),
            "plan_text":    "⚠️  INVALID TRADE PLAN — not tradeable:\n  - " +
                            "\n  - ".join(errors),
        }

    r_price = risk
    r_pips  = round(r_price * _pip_factor(instrument), 1)
    _dec    = _price_decimals(instrument)

    if direction == "LONG":
        be_price         = round(entry + BREAKEVEN_R   * r_price, _dec)
        partial_price    = be_price
        trail_start      = round(entry + TRAIL_START_R * r_price, _dec)
        trail_stop_init  = round(trail_start - TRAIL_GAP_R * r_price, _dec)
    else:  # SHORT
        be_price         = round(entry - BREAKEVEN_R   * r_price, _dec)
        partial_price    = be_price
        trail_start      = round(entry - TRAIL_START_R * r_price, _dec)
        trail_stop_init  = round(trail_start + TRAIL_GAP_R * r_price, _dec)

    # Invalidation: key level if provided, otherwise fall back to stop
    invalidation = key_level if key_level is not None else stop

    plan_text = _format_plan(
        direction, entry, stop, target,
        be_price, partial_price, trail_start, trail_stop_init,
        invalidation, r_pips, grade, _dec,
    )

    return {
        "valid":               True,
        "rr":                  rr,
        "effective_rr":        effective_rr,
        "breakeven_price":     be_price,
        "partial_exit_price":  partial_price,
        "trail_start_price":   trail_start,
        "trail_stop_at_start": trail_stop_init,
        "invalidation_price":  invalidation,
        "r_pips":              r_pips,
        "full_target_price":   target,
        "plan_text":           plan_text,
    }


# ── Internal formatting ────────────────────────────────────────────────────────

def _format_plan(
    direction: str,
    entry: float,
    stop: float,
    target: float,
    be_price: float,
    partial_price: float,
    trail_start: float,
    trail_stop_init: float,
    invalidation: float,
    r_pips: float,
    grade: str,
    dec: int = 5,
) -> str:
    close_dir = "below" if direction == "LONG" else "above"
    lines = [
        f"  TRADE MANAGEMENT PLAN",
        f"  {'─'*52}",
        f"  1R = {r_pips:.0f} pips",
        f"  {'─'*52}",
        f"  Step 1  →  {partial_price:.{dec}f}  (+1R)",
        f"    Move stop to breakeven : {entry:.{dec}f}",
        f"    Close {PARTIAL_PCT}% of position    (profit locked in)",
        f"",
        f"  Step 2  →  {trail_start:.{dec}f}  (+1.5R)",
        f"    Begin trailing — place stop at {trail_stop_init:.{dec}f}",
        f"    Keep moving stop {TRAIL_GAP_R}R behind price from here",
        f"",
        f"  Step 3  →  {target:.{dec}f}  (full target)",
        f"    Close remaining position",
        f"  {'─'*52}",
        f"  Setup dead if: 15m candle closes {close_dir} {invalidation:.{dec}f}",
    ]

    if grade in ("A+", "A"):
        lines.append(
            f"  Grade {grade}: Strong setup — consider skipping Step 1 partial "
            f"and holding full size to target"
        )
    elif grade in ("B+", "B"):
        lines.append(
            f"  Grade {grade}: Always take Step 1 partial — protect the trade"
        )

    return "\n".join(lines)
