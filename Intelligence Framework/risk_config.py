"""
risk_config.py
──────────────
Risk framework with explicit A+/A/B+/B grading system.

Grade → Size mapping:
  A+  : 1.5% risk  — everything aligned, rare, high conviction
  A   : 1.0% risk  — most signals aligned, standard execution
  B+  : 0.5% risk  — directional bias clear, one or two things off
  B   : 0.25% risk — direction there but multiple conflicts
  C   : NO TRADE   — too many factors against

The framework assigns a grade based on alignment score + quality factors.
Size is automatic — never decide size manually.
"""

from __future__ import annotations
from typing import Dict, Any, Tuple


# ── Risk Rules ─────────────────────────────────────────────────────────────────
RISK_RULES: Dict[str, Any] = {
    "risk_per_trade_pct":            0.5,    # base risk % (B+ grade)
    "max_open_risk_pct":             2.0,
    "max_daily_loss_pct":            2.0,
    "minimum_quality_to_trade":      "MEDIUM",
    "minimum_alignment_to_trade":    45,
    "event_lockout_hours_before":    2.0,
    "event_lockout_hours_after":     0.5,
    "no_swing_in_tokyo":             True,
    "stop_atr_multiplier":           1.5,
}

# ── Grade thresholds ────────────────────────────────────────────────────────────
# Alignment score + quality factors → grade → size
GRADE_CONFIG = {
    "A+": {
        "min_alignment":  85,
        "min_quality":    "HIGH",
        "risk_pct":       1.5,
        "description":    "Everything aligned — dominant trend, value zone, sweep, session, no news",
        "label":          "🔥 A+ SETUP — MAXIMUM SIZE",
        "frequency":      "Rare — 1-2x per week maximum",
    },
    "A": {
        "min_alignment":  70,
        "min_quality":    "HIGH",
        "risk_pct":       1.0,
        "description":    "Most signals aligned — standard execution, hold it, let it run",
        "label":          "✅ A SETUP — FULL SIZE",
        "frequency":      "3-4x per week on good weeks",
    },
    "B+": {
        "min_alignment":  55,
        "min_quality":    "MEDIUM",
        "risk_pct":       0.5,
        "description":    "Directional bias clear, one or two things off — valid trade, manage actively",
        "label":          "⚡ B+ SETUP — STANDARD SIZE",
        "frequency":      "Most common tradeable setup",
    },
    "B": {
        "min_alignment":  40,
        "min_quality":    "MEDIUM",
        "risk_pct":       0.25,
        "description":    "Direction there but conflicts present — small size, tight stop",
        "label":          "⚠️  B SETUP — REDUCED SIZE",
        "frequency":      "Take only when B+ conditions are close",
    },
    "C": {
        "min_alignment":  0,
        "min_quality":    "LOW",
        "risk_pct":       0.0,
        "description":    "Too many factors against — stand aside",
        "label":          "🚫 C SETUP — NO TRADE",
        "frequency":      "Never trade these",
    },
}


def get_grade(
    alignment: int,
    quality: str,
    is_counter_trend: bool,
    event_risk: bool,
    session: str,
    sweep_confirmed: bool = False,
    is_value_aligned: bool = False,
    htf_conflict: bool = False,
    fakeout_confirmed: bool = False,
    trade_type: str = "auto",
    structural_score: int = 0,
) -> Tuple[str, float, str, str]:
    """
    Assign a setup grade based on all confluence factors.

    Returns:
        grade       : "A+", "A", "B+", "B", "C"
        risk_pct    : recommended risk % for this grade
        label       : display label with emoji
        reason      : plain-English explanation of grade
    """
    # Hard blocks → C immediately
    if event_risk:
        return "C", 0.0, "🚫 NO TRADE — EVENT RISK", f"High-impact event within {RISK_RULES['event_lockout_hours_before']:.0f}h"

    if quality == "DO NOT TRADE":
        return "C", 0.0, "🚫 NO TRADE — DO NOT TRADE", "Quality score too low — stand aside"

    # Normalise session label variations
    _sess = session or ""
    _is_london   = "London" in _sess and "New York" not in _sess
    _is_ny       = "New York" in _sess and "London" not in _sess
    _is_overlap  = "London" in _sess and "New York" in _sess
    _is_tokyo    = "Tokyo" in _sess
    _is_sydney   = "Sydney" in _sess

    if _is_tokyo and RISK_RULES["no_swing_in_tokyo"]:
        # Tokyo is a downgrade — B+ max, never A or A+
        alignment = min(alignment, 69)

    # Swing trades require structural conviction — cap at B+ if structural tier is weak
    if trade_type == "swing" and structural_score < 60 and alignment > 55:
        alignment = min(alignment, 55)
        reasons = reasons if isinstance(reasons, list) else []
        reasons.append("swing grade capped — structural score below 60")

    # Build confluence bonus/penalty on top of alignment score
    adjusted = alignment

    # Bonuses that push toward A+
    if fakeout_confirmed:           adjusted += 7   # confirmed institutional stop hunt aligns
    if sweep_confirmed:             adjusted += 8   # sweep confirmation is high-value
    if is_value_aligned:            adjusted += 5   # correct location matters
    if _is_london or _is_ny:        adjusted += 5   # active session bonus
    if _is_overlap:                 adjusted += 8   # London/NY overlap — highest energy

    # Penalties that push down
    if is_counter_trend:   adjusted -= 10  # fighting the trend costs grade
    if htf_conflict:       adjusted -= 8   # HTF conflict is a red flag

    # Grade assignment — use adjusted score
    reasons = []
    if fakeout_confirmed:  reasons.append("intraday fakeout confirmed ✓")
    if sweep_confirmed:    reasons.append("sweep confirmed ✓")
    if is_value_aligned:   reasons.append("value-aligned entry ✓")
    if _is_london or _is_ny or _is_overlap:
        reasons.append(f"{session} session ✓")
    elif _is_tokyo:
        reasons.append("Tokyo session (downgraded)")
    if is_counter_trend:   reasons.append("counter-trend penalty")
    if htf_conflict:       reasons.append("HTF conflict penalty")

    reason_str = " | ".join(reasons) if reasons else "baseline signals"

    quality_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "DO NOT TRADE": 0}
    q_rank = quality_rank.get(quality, 0)

    # A+ requires both score AND quality
    if adjusted >= 85 and q_rank >= 3:
        grade = "A+"
    elif adjusted >= 70 and q_rank >= 3:
        grade = "A"
    elif adjusted >= 55 and q_rank >= 2:
        grade = "B+"
    elif adjusted >= 40 and q_rank >= 2:
        grade = "B"
    else:
        grade = "C"

    cfg = GRADE_CONFIG[grade]
    return grade, cfg["risk_pct"], cfg["label"], reason_str


def get_size_note(
    quality: str,
    alignment: int,
    is_counter_trend: bool,
    event_risk: bool,
    session: str,
    sweep_confirmed: bool = False,
    is_value_aligned: bool = False,
    htf_conflict: bool = False,
    fakeout_confirmed: bool = False,
) -> Dict[str, Any]:
    """
    Full size note dict — backward compatible with existing market_brain calls.
    Now includes grade information.
    """
    grade, risk_pct, label, reason = get_grade(
        alignment, quality, is_counter_trend, event_risk, session,
        sweep_confirmed, is_value_aligned, htf_conflict, fakeout_confirmed
    )

    cfg = GRADE_CONFIG[grade]
    allowed = grade not in ("C",)

    if not allowed:
        size_note = label
    elif risk_pct > RISK_RULES["risk_per_trade_pct"]:
        size_note = f"{label}  —  {risk_pct}% risk per trade"
    elif risk_pct == RISK_RULES["risk_per_trade_pct"]:
        size_note = f"{label}  —  {risk_pct}% risk per trade"
    else:
        size_note = f"{label}  —  {risk_pct}% risk  (reduced from {RISK_RULES['risk_per_trade_pct']}% standard)"

    return {
        "allowed":      allowed,
        "grade":        grade,
        "risk_pct":     risk_pct,
        "size_note":    size_note,
        "label":        label,
        "reason":       reason,
        "description":  cfg["description"],
        "multiplier":   risk_pct / RISK_RULES["risk_per_trade_pct"] if RISK_RULES["risk_per_trade_pct"] > 0 else 0,
    }


def format_grade_block(grade_info: Dict) -> str:
    """Format the grade block for display in the framework output."""
    grade = grade_info.get("grade", "?")
    risk  = grade_info.get("risk_pct", 0)
    desc  = grade_info.get("description", "")
    why   = grade_info.get("reason", "")

    lines = [
        f"  {grade_info.get('label', grade)}",
        f"  {desc}",
        f"  Why: {why}",
    ]
    if risk > 0:
        lines.append(f"  Risk: {risk}% of account per trade")
    return "\n".join(lines)


def print_risk_rules() -> None:
    r = RISK_RULES
    print()
    print("  RISK RULES")
    print(f"  Base risk/trade : {r['risk_per_trade_pct']}%")
    print(f"  Max open risk   : {r['max_open_risk_pct']}%")
    print(f"  Max daily loss  : {r['max_daily_loss_pct']}%")
    print()
    print("  GRADE SCALE")
    for g, cfg in GRADE_CONFIG.items():
        print(f"  {g:3s}  {cfg['risk_pct']}% risk  —  {cfg['description'][:60]}")
