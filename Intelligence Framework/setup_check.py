"""
setup_check.py
──────────────
Pre-trade evidence stack (spec: docs/specs/setup_check_spec.md, team approved
2026-07-31). READS the decision path, NEVER modifies it — no snapshots logged,
no regime state written. Scope: GBP_AUD and GBP_JPY only.

Usage:
    python3 setup_check.py GBP_JPY LONG [--target 215.50] [--no-confirm]

Six lines, plain English (banned-token rules apply):
  BIAS   auto      weekly + daily direction (get_regime)
  REGIME auto      regime + session delta + official decision state; trading
                   against the framework's read is FLAGGED, never blocked
  PLAY   suggested pattern from H4/H1/15m state (entry_confirmation reused
                   as-is) → base-break / coil-break / first-pullback /
                   retest-fade / none-named
  CLOCK  auto      news gate + JPY intervention-zone flag (storylines marker)
  FUEL   suggested direction vs storylines.md per leg — AGREES / CONFLICTS /
                   stale warning. Never generated.
  RISK   auto      nearest structural invalidation, pips, R to --target,
                   MAX_STOP_ATR_MULTIPLE breach flag (trade_management math)

SOFT GATE: always logs to pre_trade_journal.csv (gitignored, append-only,
ledger rules). Blanks / overrides / conflicts are flagged in the record,
never blocked.

PLAY pattern mapping (deterministic, suggested-only — the human confirms):
  coil-break     volatility compressed (< 0.90x normal) + direction-aligned
                 15-minute confirmation candle
  base-break     price at the range extreme in the trade direction
                 (range_position >= 0.75 long / <= 0.25 short) + hourly aligned
  first-pullback daily or 4-hour trending WITH the trade + price pulled back
                 to a known level (near_key_level)
  retest-fade    trade direction AGAINST the 4-hour trend + at a known level
  none-named     anything else
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

_DIR = os.path.dirname(os.path.abspath(__file__))
JOURNAL_FILE    = os.path.join(_DIR, "pre_trade_journal.csv")
STORYLINES_FILE = os.path.join(_DIR, "storylines.md")
STORYLINES_STALE_DAYS = 8

_JOURNAL_FIELDS = [
    "stack_id", "timestamp", "instrument", "direction", "target",
    "bias", "regime", "play", "play_marker", "clock",
    "fuel", "fuel_marker", "risk",
    "framework_direction", "framework_grade", "against_framework",
    "stop_price", "stop_pips", "r_to_target", "stop_atr_multiple",
    "breach_max_stop",
]

_PAIR_LEGS = {"GBP_AUD": ("GBP", "AUD"), "GBP_JPY": ("GBP", "JPY")}


# ── storylines.md parsing (read-only; never generated) ─────────────────────────

def parse_storylines(path: str = STORYLINES_FILE,
                     now: Optional[datetime] = None) -> Dict:
    """Returns {available, stale, age_days, views: {CCY: bullish|bearish|neutral},
    intervention_watch: bool}. Lenient parser; missing file → available=False."""
    out = {"available": False, "stale": False, "age_days": None,
           "views": {}, "intervention_watch": False}
    if not os.path.exists(path):
        return out
    now = now or datetime.now(timezone.utc)
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return out
    out["available"] = True
    m = re.search(r"updated:\s*(\d{4}-\d{2}-\d{2})", text)
    if m:
        try:
            hdr = datetime.strptime(m.group(1), "%Y-%m-%d").replace(
                tzinfo=timezone.utc)
            out["age_days"] = (now - hdr).days
            out["stale"] = out["age_days"] > STORYLINES_STALE_DAYS
        except ValueError:
            out["stale"] = True
    else:
        out["stale"] = True                     # no dated header = untrusted
    for ccy in ("GBP", "AUD", "JPY"):
        mm = re.search(rf"^{ccy}:\s*(bullish|bearish|neutral)\b",
                       text, re.M | re.I)
        if mm:
            out["views"][ccy] = mm.group(1).lower()
    # intervention marker counts only on UNcommented lines
    for line in text.splitlines():
        if "INTERVENTION-WATCH" in line and not line.strip().startswith(
                ("<!--", "#", ">")):
            out["intervention_watch"] = True
    return out


def _fuel_line(instrument: str, direction: str, st: Dict) -> Tuple[str, str]:
    """FUEL: storyline agreement per leg. Returns (text, marker)."""
    if not st["available"]:
        return ("no storylines file — fundamental view unrecorded", "blank")
    if st["stale"]:
        age = f"{st['age_days']} days old" if st["age_days"] is not None \
            else "undated"
        return (f"storylines file is STALE ({age}; refresh before trusting) "
                f"— not counted as evidence", "stale")
    base, quote = _PAIR_LEGS[instrument]
    want_base  = "bullish" if direction == "LONG" else "bearish"
    want_quote = "bearish" if direction == "LONG" else "bullish"
    vb = st["views"].get(base, "unrecorded")
    vq = st["views"].get(quote, "unrecorded")
    conflicts = []
    supports  = []
    for ccy, view, want in ((base, vb, want_base), (quote, vq, want_quote)):
        if view == want:
            supports.append(f"{ccy} {view}")
        elif view in ("bullish", "bearish"):
            conflicts.append(f"{ccy} {view} (trade needs {want})")
    if conflicts:
        return (f"CONFLICTS with storylines: {'; '.join(conflicts)}", "conflict")
    if len(supports) == 2:
        return (f"storylines AGREE: {', '.join(supports)}", "agrees")
    return (f"storylines neutral/unrecorded on "
            f"{base}={vb}, {quote}={vq} — no fundamental push either way",
            "neutral")


# ── PLAY pattern (suggested; deterministic mapping documented above) ───────────

def _play_line(direction: str, regime: Dict, entry) -> Tuple[str, str]:
    atr_ratio = float(regime.get("atr_vs_avg", 1.0) or 1.0)
    rng_pos   = regime.get("range_position")
    h4        = regime.get("regime_h4", "UNKNOWN")
    d1        = regime.get("regime_d1", "UNKNOWN")
    with_h4   = (direction == "LONG" and "UP" in h4) or \
                (direction == "SHORT" and "DOWN" in h4)
    with_d1   = (direction == "LONG" and "UP" in d1) or \
                (direction == "SHORT" and "DOWN" in d1)
    eng_dir   = bool(getattr(entry, "engulfing_detected", False))
    near_lvl  = bool(getattr(entry, "near_key_level", False))
    h1_ok     = bool(getattr(entry, "h1_confirmed", False))

    if atr_ratio < 0.90 and eng_dir:
        name = "coil-break"
        why  = (f"volatility squeezed to {atr_ratio:.2f}x normal with a "
                f"15-minute confirmation candle in your direction")
    elif rng_pos is not None and (
            (direction == "LONG" and rng_pos >= 0.75) or
            (direction == "SHORT" and rng_pos <= 0.25)) and h1_ok:
        name = "base-break"
        why  = "price is pressing the range edge in your direction with the hourly aligned"
    elif (with_d1 or with_h4) and near_lvl:
        name = "first-pullback"
        why  = "trend in your direction and price has pulled back to a known level"
    elif (not with_h4) and near_lvl and h4 in ("TRENDING_UP", "TRENDING_DOWN"):
        name = "retest-fade"
        why  = "you are fading the 4-hour trend at a known level — counter-trend by definition"
    else:
        name = "none-named"
        why  = "current structure does not match a named playbook pattern"
    return (f"{name} — {why}", name)


# ── The stack ──────────────────────────────────────────────────────────────────

def build_stack(instrument: str, direction: str,
                target: Optional[float] = None,
                regime: Optional[Dict] = None,
                entry=None,
                storylines: Optional[Dict] = None,
                delta: Optional[Dict] = None,
                decision: Optional[Dict] = None) -> Dict:
    """Assemble the six lines + journal fields. All heavy inputs injectable
    for tests; live callers pass none and we fetch (read-only)."""
    if regime is None:
        from regime_detection import get_regime
        regime = get_regime(instrument)
    if decision is None:
        from official_decision import get_official_decision
        decision = get_official_decision(regime)
    if entry is None:
        from entry_confirmation import get_entry_brief
        entry = get_entry_brief(instrument, direction)
    if storylines is None:
        storylines = parse_storylines()
    if delta is None:
        try:
            from session_memory import get_session_delta
            delta = get_session_delta(instrument)      # read-only
        except Exception:
            delta = None

    from decision_brief import _plain
    from regime_detection import PAIRS
    pip = PAIRS[instrument].pip_size if instrument in PAIRS else 0.0001
    price = float(regime.get("current_price", 0) or 0)

    # LINE 1 — BIAS
    bias = (f"weekly {_plain(regime.get('weekly_context', 'UNKNOWN'))}; "
            f"daily {_plain(regime.get('regime_d1', 'UNKNOWN'))} "
            f"(trend strength {float(regime.get('adx', 0) or 0):.0f}/100)")

    # LINE 2 — REGIME (+ against-framework flag, information not a block)
    fw_dir   = decision.get("direction", "NO TRADE")
    fw_grade = decision.get("grade", "C")
    against  = fw_dir in ("NO TRADE", "") or \
               (fw_dir in ("LONG", "SHORT") and fw_dir != direction)
    delta_txt = ""
    if delta and delta.get("summary"):
        delta_txt = f"; since last run: {_plain(delta['summary'])}"
    regime_line = (f"4-hour {_plain(regime.get('regime_h4', 'UNKNOWN'))}"
                   f"{delta_txt}; framework decision right now: "
                   f"{fw_dir} (rating {fw_grade})")
    if against:
        regime_line += (" — ⚠ YOU ARE TRADING AGAINST THE FRAMEWORK'S READ. "
                        "That is information, not a block: know why you "
                        "disagree before you act.")

    # LINE 3 — PLAY (suggested)
    play, play_name = _play_line(direction, regime, entry)

    # LINE 4 — CLOCK
    ng = regime.get("news_gate") or {}
    if ng.get("gating"):
        clock = (f"major release ahead — {ng.get('event')} in "
                 f"{ng.get('minutes_until')} minutes; expect violent "
                 f"repricing")
    elif not ng.get("active", False):
        clock = ng.get("note") or "news calendar unavailable — event risk unchecked"
    else:
        clock = "no high-impact release inside the next 2 hours"
    if instrument == "GBP_JPY" and storylines.get("intervention_watch"):
        clock += ("; ⚠ INTERVENTION WATCH — storylines flag price in the "
                  "historical Ministry-of-Finance response zone")

    # LINE 5 — FUEL (suggested; never generated)
    fuel, fuel_marker = _fuel_line(instrument, direction, storylines)

    # LINE 6 — RISK (trade_management math, wired live)
    from trade_management import MAX_STOP_ATR_MULTIPLE, get_management_plan
    if direction == "LONG":
        stop = getattr(entry, "h1_entry_level", 0.0) or 0.0
        if not stop or stop >= price:
            stop = float(regime.get("latest_sl") or 0.0)
    else:
        stop = getattr(entry, "h1_entry_level", 0.0) or 0.0
        if not stop or stop <= price:
            stop = float(regime.get("latest_sh") or 0.0)
    risk_fields = {"stop_price": "", "stop_pips": "", "r_to_target": "",
                   "stop_atr_multiple": "", "breach_max_stop": ""}
    if not stop or not price or \
            (direction == "LONG" and stop >= price) or \
            (direction == "SHORT" and stop <= price):
        risk = ("no clean structural invalidation found on the hourly or "
                "daily — define your stop by hand before trading")
    else:
        dist_price = abs(price - stop)
        dist_pips  = dist_price / pip
        atr_price  = float(regime.get("atr", 0) or 0)
        mult       = (dist_price / atr_price) if atr_price > 0 else None
        risk = (f"structural invalidation {stop:.4f} "
                f"({dist_pips:.0f} pips away)")
        risk_fields.update({"stop_price": round(stop, 5),
                            "stop_pips": round(dist_pips, 1)})
        if mult is not None:
            risk_fields["stop_atr_multiple"] = round(mult, 2)
            breach = mult > MAX_STOP_ATR_MULTIPLE
            risk_fields["breach_max_stop"] = breach
            if breach:
                risk += (f"; ⚠ stop is {mult:.1f}x the daily range — wider "
                         f"than the {MAX_STOP_ATR_MULTIPLE}x maximum, "
                         f"size down or find closer structure")
        if target is not None:
            plan = get_management_plan(price, stop, target, direction,
                                       instrument=instrument)
            if plan.get("valid"):
                risk += (f"; target {target:.4f} pays "
                         f"{plan['rr']:.1f}R ({plan['effective_rr']:.1f}R "
                         f"after spread)")
                risk_fields["r_to_target"] = plan["rr"]
            else:
                risk += (f"; target {target:.4f} REJECTED: "
                         f"{'; '.join(plan.get('errors', ['invalid']))}")
                risk_fields["r_to_target"] = "invalid"

    ts = datetime.now(timezone.utc)
    return {
        "stack_id": f"{ts.strftime('%Y%m%dT%H%M%SZ')}_{instrument}_{direction}",
        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "instrument": instrument, "direction": direction,
        "target": target if target is not None else "",
        "bias": bias, "regime": regime_line,
        "play": play, "play_name": play_name, "play_marker": "auto",
        "clock": clock, "fuel": fuel, "fuel_marker": fuel_marker,
        "risk": risk,
        "framework_direction": fw_dir, "framework_grade": fw_grade,
        "against_framework": against,
        **risk_fields,
    }


def render(stack: Dict) -> str:
    w = 62
    lines = [
        "═" * w,
        f"  PRE-TRADE STACK  {stack['instrument'].replace('_', '/')} "
        f"{stack['direction']}"
        + (f"  → target {stack['target']}" if stack["target"] != "" else ""),
        "═" * w,
        f"  1 BIAS    {stack['bias']}",
        f"  2 REGIME  {stack['regime']}",
        f"  3 PLAY    {stack['play']}",
        f"  4 CLOCK   {stack['clock']}",
        f"  5 FUEL    {stack['fuel']}",
        f"  6 RISK    {stack['risk']}",
        "═" * w,
    ]
    return "\n".join(lines)


# ── Soft gate: confirm + journal (always logs, never blocks) ───────────────────

def _confirm(label: str, marker_now: str, no_confirm: bool) -> str:
    """One keystroke: Enter/y = accept, o = override note, b = blank."""
    if no_confirm or not sys.stdin.isatty():
        return marker_now if marker_now != "auto" else "auto"
    try:
        k = input(f"  {label} — [Enter]=accept  o=override  b=blank: ").strip().lower()
    except EOFError:
        return "auto"
    if k == "o":
        return "overridden"
    if k == "b":
        return "blank"
    return "confirmed"


def append_journal(stack: Dict, path: str = JOURNAL_FILE) -> None:
    """Append-only ledger write (gitignored). Never edits existing rows."""
    exists = os.path.exists(path)
    row = {k: stack.get(k, "") for k in _JOURNAL_FIELDS}
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_JOURNAL_FIELDS)
        if not exists:
            w.writeheader()
        w.writerow(row)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Pre-trade evidence stack (soft gate — always logs, never blocks)")
    p.add_argument("instrument", choices=["GBP_AUD", "GBP_JPY"])
    p.add_argument("direction", choices=["LONG", "SHORT"])
    p.add_argument("--target", type=float, default=None)
    p.add_argument("--no-confirm", action="store_true",
                   help="skip interactive confirms (markers logged as auto)")
    a = p.parse_args(argv)

    stack = build_stack(a.instrument, a.direction, target=a.target)
    print(render(stack))

    # Interactive confirm on the two SUGGESTED lines (3 PLAY, 5 FUEL)
    stack["play_marker"] = _confirm("PLAY", "auto", a.no_confirm)
    stack["fuel_marker"] = _confirm(
        "FUEL", stack["fuel_marker"], a.no_confirm) \
        if stack["fuel_marker"] in ("agrees", "neutral") else stack["fuel_marker"]

    append_journal(stack)
    print(f"\n  logged → pre_trade_journal.csv  (stack_id {stack['stack_id']})")
    if stack["against_framework"]:
        print("  note: framework disagreement is IN the record.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
