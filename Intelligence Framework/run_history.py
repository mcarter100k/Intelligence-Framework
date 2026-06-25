"""
run_history.py
──────────────
Cross-run intelligence layer.

Stores the last 10 framework runs in run_history.json and
detects patterns across them:

  - State persistence  : how many consecutive runs same primary state
  - Alignment trend    : is conviction building or fading?
  - Price trajectory   : how fast is price moving toward trigger?
  - Session handoff    : did London set up what Tokyo is holding?
  - Grade progression  : is setup improving or deteriorating?
  - Invalidation proximity : is price approaching the stop level?

Called by market_brain.py — output appears in the NOW section
between live price and the decision context.
"""

from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

HISTORY_FILE = Path(__file__).parent / "run_history.json"
MAX_HISTORY  = 10   # keep last 10 runs


def save_run(run_data: Dict) -> None:
    """
    Append current run to history file.
    Called at the end of every framework run.
    run_data should be the same dict saved to last_run.json.
    """
    try:
        history = load_history()
        history.append(run_data)
        # Keep only last MAX_HISTORY runs
        if len(history) > MAX_HISTORY:
            history = history[-MAX_HISTORY:]
        HISTORY_FILE.write_text(json.dumps(history, indent=2))
    except Exception:
        pass


def load_history() -> List[Dict]:
    """Load run history. Returns empty list if file doesn't exist."""
    try:
        if HISTORY_FILE.exists():
            return json.loads(HISTORY_FILE.read_text())
    except Exception:
        pass
    return []


def get_cross_run_intelligence(current: Dict) -> Dict:
    """
    Analyse run history against current run.
    Returns a dict with pattern findings for display.

    Keys:
        state_runs          : int — how many consecutive runs same primary state
        alignment_trend     : str — "BUILDING", "FADING", "STABLE", "INSUFFICIENT_DATA"
        alignment_history   : list of recent alignment scores
        price_trajectory    : str — direction + rate toward trigger
        pips_per_run        : float — average pip movement per run
        grade_trend         : str — "IMPROVING", "DEGRADING", "STABLE"
        session_context     : str — what previous session established
        invalidation_proximity : int or None — pips from invalidation level
        trigger_proximity   : int or None — pips from trigger
        runs_available      : int — how many historical runs exist
        summary             : list of plain-English insight strings
    """
    history = load_history()

    result = {
        "state_runs":              1,
        "alignment_trend":         "INSUFFICIENT_DATA",
        "alignment_history":       [],
        "price_trajectory":        "unknown",
        "pips_per_run":            None,
        "grade_trend":             "INSUFFICIENT_DATA",
        "session_context":         "",
        "invalidation_proximity":  None,
        "trigger_proximity":       None,
        "runs_available":          len(history),
        "summary":                 [],
    }

    if not history:
        result["summary"].append("First run — no history to compare yet")
        return result

    cur_state    = current.get("primary_state", "")
    cur_align    = current.get("conviction_score", 0) or 0
    cur_price    = float(current.get("price", 0) or 0)
    cur_grade    = current.get("grade", "")
    cur_trigger  = current.get("trigger_price")
    cur_inv      = current.get("invalidation", "")
    cur_session  = current.get("session", "")

    try:
        cur_inv_price = float(cur_inv) if cur_inv else None
    except (ValueError, TypeError):
        cur_inv_price = None

    # ── State persistence ─────────────────────────────────────────────────────
    consecutive = 1
    for run in reversed(history):
        if run.get("primary_state", "") == cur_state:
            consecutive += 1
        else:
            break
    result["state_runs"] = consecutive

    # ── Alignment trend ───────────────────────────────────────────────────────
    recent_aligns = [r.get("conviction_score", 0) or 0 for r in history[-4:]]
    recent_aligns.append(cur_align)
    result["alignment_history"] = recent_aligns

    if len(recent_aligns) >= 3:
        first_half = sum(recent_aligns[:len(recent_aligns)//2]) / (len(recent_aligns)//2)
        second_half = sum(recent_aligns[len(recent_aligns)//2:]) / (len(recent_aligns) - len(recent_aligns)//2)
        diff = second_half - first_half
        if diff >= 5:
            result["alignment_trend"] = "BUILDING"
        elif diff <= -5:
            result["alignment_trend"] = "FADING"
        else:
            result["alignment_trend"] = "STABLE"

    # ── Price trajectory toward trigger ───────────────────────────────────────
    recent_prices = [float(r.get("price", 0) or 0) for r in history[-3:] if r.get("price")]
    recent_prices.append(cur_price)

    if len(recent_prices) >= 2 and cur_trigger:
        price_changes = [recent_prices[i+1] - recent_prices[i]
                         for i in range(len(recent_prices)-1)]
        avg_change = sum(price_changes) / len(price_changes)
        pips_per_run = round(avg_change * 10000, 1)
        result["pips_per_run"] = pips_per_run

        # Distance to trigger
        if cur_trigger and cur_price:
            pips_to_trigger = round(abs(cur_trigger - cur_price) * 10000)
            result["trigger_proximity"] = pips_to_trigger

            # How many runs at current pace to reach trigger?
            if avg_change != 0:
                runs_to_trigger = abs((cur_trigger - cur_price) / avg_change)
                direction = "toward" if (
                    (cur_trigger > cur_price and avg_change > 0) or
                    (cur_trigger < cur_price and avg_change < 0)
                ) else "away from"

                if direction == "toward" and runs_to_trigger <= 3:
                    result["price_trajectory"] = (
                        f"Moving {direction} trigger at {pips_per_run:+.0f} pips/run "
                        f"— trigger zone in ~{runs_to_trigger:.1f} runs"
                    )
                elif direction == "toward":
                    result["price_trajectory"] = (
                        f"Drifting {direction} trigger ({pips_per_run:+.0f} pips/run)"
                    )
                else:
                    result["price_trajectory"] = (
                        f"Moving {direction} trigger ({pips_per_run:+.0f} pips/run) "
                        f"— setup not activating yet"
                    )
            else:
                result["price_trajectory"] = "Price flat across recent runs"

    # ── Invalidation proximity ────────────────────────────────────────────────
    if cur_inv_price and cur_price:
        pips_from_inv = round(abs(cur_price - cur_inv_price) * 10000)
        result["invalidation_proximity"] = pips_from_inv

    # ── Grade trend ───────────────────────────────────────────────────────────
    grade_order = {"A+": 5, "A": 4, "B+": 3, "B": 2, "C": 1, "": 0}
    recent_grades = [r.get("grade", "") for r in history[-3:]]
    recent_grades.append(cur_grade)
    recent_grade_scores = [grade_order.get(g, 0) for g in recent_grades if g]

    if len(recent_grade_scores) >= 2:
        grade_delta = recent_grade_scores[-1] - recent_grade_scores[0]
        if grade_delta > 0:
            result["grade_trend"] = "IMPROVING"
        elif grade_delta < 0:
            result["grade_trend"] = "DEGRADING"
        else:
            result["grade_trend"] = "STABLE"

    # ── Session handoff context ───────────────────────────────────────────────
    if history:
        prev = history[-1]
        prev_session = prev.get("session", "")
        prev_state   = prev.get("primary_state", "")
        if prev_session and prev_session != cur_session:
            result["session_context"] = (
                f"{prev_session} established: {prev_state[:40]}"
                if prev_state else prev_session
            )

    # ── Build summary insights ────────────────────────────────────────────────
    summary = []

    # State persistence insight
    if consecutive >= 7 and result.get("alignment_trend") == "STABLE":
        summary.append(
            f"Setup has not developed in {consecutive} runs with flat conviction "
            f"({' → '.join(str(a) for a in recent_aligns[-3:])}). "
            f"The conditions that would activate it have not appeared. "
            f"Consider whether the thesis is stale — a fresh catalyst or session change is needed before this setup is worth watching."
        )
    elif consecutive >= 3:
        summary.append(
            f"Setup held for {consecutive} consecutive runs — "
            f"{'maturing and reliable' if consecutive <= 6 else 'extended — re-evaluate if still valid'}"
        )
    elif consecutive == 2:
        summary.append("Setup consistent across last 2 runs")

    # Alignment insight
    if result["alignment_trend"] == "BUILDING":
        summary.append(
            f"Conviction BUILDING: {' → '.join(str(a) for a in recent_aligns[-3:])} "
            f"— setup strengthening"
        )
    elif result["alignment_trend"] == "FADING":
        summary.append(
            f"Conviction FADING: {' → '.join(str(a) for a in recent_aligns[-3:])} "
            f"— setup losing momentum"
        )

    # Price trajectory insight
    if result["price_trajectory"] and result["price_trajectory"] != "unknown":
        summary.append(result["price_trajectory"])

    # Grade trend insight
    if result["grade_trend"] == "IMPROVING":
        grade_str = " → ".join(g for g in recent_grades[-3:] if g)
        summary.append(f"Grade improving: {grade_str}")
    elif result["grade_trend"] == "DEGRADING":
        grade_str = " → ".join(g for g in recent_grades[-3:] if g)
        summary.append(f"Grade degrading: {grade_str} — reassess position")

    # Invalidation proximity warning
    if result["invalidation_proximity"] is not None:
        if result["invalidation_proximity"] < 50:
            summary.append(
                f"⚠️  Only {result['invalidation_proximity']} pips from invalidation — "
                f"risk is compressed, size down or wait"
            )
        elif result["invalidation_proximity"] < 100:
            summary.append(
                f"Invalidation at {result['invalidation_proximity']} pips — "
                f"adequate stop room"
            )

    # Session handoff
    if result["session_context"]:
        summary.append(f"Previous session ({result['session_context']})")

    if not summary:
        summary.append("No significant pattern detected across recent runs")

    result["summary"] = summary

    # ── Synthesis line — forward insight when conditions converge (Priority 6) ──
    synthesis = ""
    _val_verdict  = current.get("value_verdict", "")
    _sweep_conf   = current.get("sweep_confirmed", False)
    _cur_bias     = current.get("bias", "")

    # Check prior run for sweep
    _prior_sweep = history[-1].get("sweep_confirmed", False) if history else False

    _premium = "PREMIUM" in str(_val_verdict)
    _discount = "DISCOUNT" in str(_val_verdict)
    _aligning = result["alignment_trend"] == "BUILDING"
    _grade_ok = result["grade_trend"] in ("IMPROVING", "STABLE")

    if _aligning and (_sweep_conf or _prior_sweep) and _premium and _cur_bias == "BEARISH":
        synthesis = (
            "Conviction rising, sweep confirmed, price in premium — "
            "short setup maturing. Watch for rejection at current level."
        )
    elif _aligning and (_sweep_conf or _prior_sweep) and _discount and _cur_bias == "BULLISH":
        synthesis = (
            "Conviction rising, sweep confirmed, price at discount — "
            "long setup maturing. Watch for bullish engulf at current level."
        )
    elif _aligning and _premium and _cur_bias == "BEARISH":
        synthesis = (
            "Conviction building and price extended into premium — "
            "setup is approaching actionable. Await sweep confirmation."
        )
    elif _aligning and _discount and _cur_bias == "BULLISH":
        synthesis = (
            "Conviction building and price at discount — "
            "long bias strengthening. Await sweep or fakeout confirmation."
        )

    result["synthesis"] = synthesis
    return result


def format_cross_run_block(intelligence: Dict, width: int = 66) -> str:
    """Format the cross-run intelligence block for display."""
    runs = intelligence.get("runs_available", 0)
    if runs == 0:
        return ""

    lines = []
    sep = "-" * width

    lines.append(sep)
    lines.append("  CROSS-RUN INTELLIGENCE")
    lines.append(sep)

    state_runs = intelligence.get("state_runs", 1)
    align_hist = intelligence.get("alignment_history", [])
    align_trend = intelligence.get("alignment_trend", "")
    grade_trend = intelligence.get("grade_trend", "")
    trig_prox   = intelligence.get("trigger_proximity")
    inv_prox    = intelligence.get("invalidation_proximity")

    # State persistence
    if state_runs > 1:
        lines.append(f"  State held  : {state_runs} consecutive runs")

    # Alignment history
    if align_hist:
        hist_str = " → ".join(str(a) for a in align_hist)
        trend_label = {
            "BUILDING": "↑ building",
            "FADING":   "↓ fading",
            "STABLE":   "→ stable",
        }.get(align_trend, "")
        lines.append(f"  Conviction  : {hist_str}  {trend_label}")

    # Grade trend
    if grade_trend and grade_trend != "INSUFFICIENT_DATA":
        lines.append(f"  Grade trend : {grade_trend}")

    # Proximity
    if trig_prox is not None:
        lines.append(f"  To trigger  : {trig_prox} pips")
    if inv_prox is not None:
        lines.append(f"  To invalidation: {inv_prox} pips")

    # Summary insights
    summary = intelligence.get("summary", [])
    if summary:
        lines.append("")
        for s in summary:
            if len(s) > width - 4:
                words = s.split()
                current_line = "  → "
                first = True
                for word in words:
                    if len(current_line) + len(word) + 1 > width:
                        lines.append(current_line.rstrip())
                        current_line = "    " + word + " "
                        first = False
                    else:
                        current_line += word + " "
                if current_line.strip():
                    lines.append(current_line.rstrip())
            else:
                lines.append(f"  → {s}")

    # Synthesis line — forward insight when conditions converge (Priority 6)
    synthesis = intelligence.get("synthesis", "")
    if synthesis:
        lines.append("")
        words = synthesis.split()
        current_line = "  ◆ "
        for word in words:
            if len(current_line) + len(word) + 1 > width:
                lines.append(current_line.rstrip())
                current_line = "    " + word + " "
            else:
                current_line += word + " "
        if current_line.strip():
            lines.append(current_line.rstrip())

    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    # Test with dummy data
    dummy = {
        "primary_state":    "PULLBACK OPPORTUNITY — SHORT SETUP BUILDING",
        "conviction_score": 67,
        "price":            1.9033,
        "grade":            "B+",
        "trigger_price":    1.9165,
        "invalidation":     "1.9293",
        "session":          "Tokyo",
        "bias":             "BEARISH",
    }
    intel = get_cross_run_intelligence(dummy)
    print(format_cross_run_block(intel))
    print(f"Runs available: {intel['runs_available']}")
    print(f"Summary: {intel['summary']}")
