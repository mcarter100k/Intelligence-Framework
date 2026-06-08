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
BREAKEVEN_R    = 1.0   # move stop to entry when trade reaches this R
PARTIAL_R      = 1.0   # first partial exit at this R (same trigger as breakeven)
PARTIAL_PCT    = 50    # % of position to close at Step 1
TRAIL_START_R  = 1.5   # begin trailing after this R
TRAIL_GAP_R    = 0.5   # trailing stop stays this many R behind current price


def get_management_plan(
    entry: float,
    stop: float,
    target: float,
    direction: str,
    grade: str = "B+",
    key_level: Optional[float] = None,
) -> dict:
    """
    Build the full trade management plan at the moment the entry alert fires.

    Plain English: the moment you get an alert, this function tells you EXACTLY
                   where to move your stop, when to take profits, and when the
                   trade idea is dead. Write these levels down before you click.

    Args:
        entry     : fill price (where you entered the trade)
        stop      : initial stop-loss price (structure-based, from entry_watcher)
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
    r_price = abs(entry - stop)
    r_pips  = round(r_price * 10_000, 1)

    if direction == "LONG":
        be_price         = round(entry + BREAKEVEN_R   * r_price, 5)
        partial_price    = be_price
        trail_start      = round(entry + TRAIL_START_R * r_price, 5)
        trail_stop_init  = round(trail_start - TRAIL_GAP_R * r_price, 5)
    else:  # SHORT
        be_price         = round(entry - BREAKEVEN_R   * r_price, 5)
        partial_price    = be_price
        trail_start      = round(entry - TRAIL_START_R * r_price, 5)
        trail_stop_init  = round(trail_start + TRAIL_GAP_R * r_price, 5)

    # Invalidation: key level if provided, otherwise fall back to stop
    invalidation = key_level if key_level is not None else stop

    plan_text = _format_plan(
        direction, entry, stop, target,
        be_price, partial_price, trail_start, trail_stop_init,
        invalidation, r_pips, grade,
    )

    return {
        "breakeven_price":     be_price,
        "partial_exit_price":  partial_price,
        "trail_start_price":   trail_start,
        "trail_stop_at_start": trail_stop_init,
        "invalidation_price":  invalidation,
        "r_pips":              r_pips,
        "full_target_price":   target,
        "plan_text":           plan_text,
    }


def check_management_action(
    entry: float,
    stop: float,
    current_price: float,
    direction: str,
) -> dict:
    """
    Given where price is right now during an open trade, return the action.

    Plain English: call this while in a trade to check what you should do.
                   The function finds which management rule applies and
                   tells you the exact next step and new stop price.

    Returns dict:
        action    : "HOLD" | "MOVE_BREAKEVEN" | "TRAIL" | "INVALIDATED"
        new_stop  : updated stop (unchanged if HOLD)
        current_r : R multiple the trade is currently at (negative = underwater)
        message   : plain-English instruction
    """
    r_price = abs(entry - stop)
    if r_price == 0:
        return {
            "action": "HOLD", "new_stop": stop,
            "current_r": 0.0,
            "message": "Cannot compute R — stop equals entry price.",
        }

    current_r = (
        (current_price - entry) / r_price if direction == "LONG"
        else (entry - current_price) / r_price
    )
    current_r = round(current_r, 2)

    if current_r <= -1.0:
        return {
            "action":    "INVALIDATED",
            "new_stop":  stop,
            "current_r": current_r,
            "message":   f"At {current_r:.1f}R — stop should have triggered. Trade idea is dead.",
        }

    if current_r >= TRAIL_START_R:
        new_stop = (
            round(current_price - TRAIL_GAP_R * r_price, 5) if direction == "LONG"
            else round(current_price + TRAIL_GAP_R * r_price, 5)
        )
        return {
            "action":    "TRAIL",
            "new_stop":  new_stop,
            "current_r": current_r,
            "message": (
                f"At {current_r:.1f}R — trail active. Move stop to {new_stop:.5f}. "
                f"Continue moving it {TRAIL_GAP_R}R behind price as trade extends."
            ),
        }

    if current_r >= BREAKEVEN_R:
        return {
            "action":    "MOVE_BREAKEVEN",
            "new_stop":  entry,
            "current_r": current_r,
            "message": (
                f"At {current_r:.1f}R — move stop to breakeven ({entry:.5f}). "
                f"Close {PARTIAL_PCT}% of position now. Let the rest run to target."
            ),
        }

    return {
        "action":    "HOLD",
        "new_stop":  stop,
        "current_r": current_r,
        "message": (
            f"At {current_r:.1f}R — hold. Stop stays at {stop:.5f}. "
            f"Move to breakeven when trade reaches +{BREAKEVEN_R}R."
        ),
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
) -> str:
    close_dir = "below" if direction == "LONG" else "above"
    lines = [
        f"  TRADE MANAGEMENT PLAN",
        f"  {'─'*52}",
        f"  1R = {r_pips:.0f} pips",
        f"  {'─'*52}",
        f"  Step 1  →  {partial_price:.5f}  (+1R)",
        f"    Move stop to breakeven : {entry:.5f}",
        f"    Close {PARTIAL_PCT}% of position    (profit locked in)",
        f"",
        f"  Step 2  →  {trail_start:.5f}  (+1.5R)",
        f"    Begin trailing — place stop at {trail_stop_init:.5f}",
        f"    Keep moving stop {TRAIL_GAP_R}R behind price from here",
        f"",
        f"  Step 3  →  {target:.5f}  (full target)",
        f"    Close remaining position",
        f"  {'─'*52}",
        f"  Setup dead if: 15m candle closes {close_dir} {invalidation:.5f}",
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
