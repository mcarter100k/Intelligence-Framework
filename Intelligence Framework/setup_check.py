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

# INFORMED PRIOR (docs/specs/setup_check_plain_english_spec.md, 2026-09-09,
# start 0.3): a structural stop CLOSER than this fraction of the daily range
# sits inside normal noise — it gets hit by accident, not by being wrong.
# Exhibit: Episode 1 (validation_log 2026-09-09) — a 32.9-pip stop on a
# ~100-pip-ATR pair, stopped for -1.0R while the move ran 809.2 pips in the
# signal's direction. Not validated; revisit when graded stops accumulate.
MIN_STOP_ATR_MULTIPLE = 0.3

_JOURNAL_FIELDS = [
    "stack_id", "timestamp", "instrument", "direction", "target",
    "bias", "regime", "play", "play_marker", "clock",
    "fuel", "fuel_marker", "risk",
    "framework_direction", "framework_grade", "against_framework",
    "stop_price", "stop_pips", "r_to_target", "stop_atr_multiple",
    "breach_max_stop",
    # verdict: real column (team ruling 2026-09-09; additive, old rows
    # blank — same logger-managed migration pattern as the shadow ledger's
    # loss_species column)
    "verdict",
]

_PAIR_LEGS = {"GBP_AUD": ("GBP", "AUD"), "GBP_JPY": ("GBP", "JPY")}


# ── storylines.md parsing (read-only; never generated) ─────────────────────────

def parse_storylines(path: str = STORYLINES_FILE,
                     now: Optional[datetime] = None) -> Dict:
    """Returns {available, stale, age_days, views: {CCY: bullish|bearish|neutral},
    intervention_watch: bool}. Lenient parser; missing file → available=False."""
    out = {"available": False, "stale": False, "age_days": None,
           "header_date": None, "views": {}, "intervention_watch": False}
    if not os.path.exists(path):
        return out
    now = now or datetime.now(timezone.utc)
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return out
    out["available"] = True
    # Dated header: "updated: YYYY-MM-DD" (fixture convention) OR
    # "approved YYYY-MM-DD" — the live storylines.md has always written
    # "(approved <date>)"; matching it is additive (spec 2026-09-09) and
    # lets FUEL print "last approved <date>".
    m = re.search(r"(?:updated:|approved)\s*(\d{4}-\d{2}-\d{2})", text)
    if m:
        out["header_date"] = m.group(1)
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
        return ("There is no storyline file this week, so the fundamental "
                "view is unrecorded — that is a blank, and blanks are "
                "honest answers.", "blank")
    if st["stale"]:
        when = (f"last approved {st['header_date']}" if st.get("header_date")
                else "no approval date on it")
        return (f"This week's storyline for this pair is out of date "
                f"({when}) so it can't count as evidence. Refresh it in "
                f"the Sunday session.", "stale")
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
        return (f"Your direction CONFLICTS with the week's storyline: "
                f"{'; '.join(conflicts)}.", "conflict")
    if len(supports) == 2:
        return (f"Your direction AGREES with the week's storyline: "
                f"{' and '.join(supports)}.", "agrees")
    return (f"The storyline is neutral or unrecorded on this pair "
            f"({base} {vb}, {quote} {vq}) — no fundamental push either "
            f"way.", "neutral")


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
        text = (f"This looks like a break of a tight coil — volatility has "
                f"squeezed to {atr_ratio:.2f}x normal and a 15-minute "
                f"candle just confirmed your direction. Agree?")
    elif rng_pos is not None and (
            (direction == "LONG" and rng_pos >= 0.75) or
            (direction == "SHORT" and rng_pos <= 0.25)) and h1_ok:
        name = "base-break"
        text = ("This looks like a push through the range edge — price is "
                "pressing the edge in your direction with the hourly "
                "aligned. Agree?")
    elif (with_d1 or with_h4) and near_lvl:
        name = "first-pullback"
        text = ("This looks like a first pullback after a break — the "
                "trend is with you and price has pulled back to a known "
                "level. Agree?")
    elif (not with_h4) and near_lvl and h4 in ("TRENDING_UP", "TRENDING_DOWN"):
        name = "retest-fade"
        text = ("This looks like a fade of the 4-hour trend at a known "
                "level — counter-trend by definition. Agree?")
    else:
        name = "none-named"
        text = ("This doesn't match any play in the playbook (base break, "
                "coil break, first pullback, retest fade). If you can't "
                "name it, it's a feeling, not a trade.")
    return (text, name)


# ── Plain-English helpers (docs/specs/setup_check_plain_english_spec.md) ──────

def _tf_clause(regime_label: str, subtype: str, structure: str,
               adx: float, quiet_words: bool = False) -> str:
    """One clause describing a timeframe, colleague voice. quiet_words
    switches RANGING to the 4-hour's 'quiet and sideways'."""
    if subtype == "EXHAUSTION":
        from decision_brief import _exhaustion_phrase
        return f"is {_exhaustion_phrase(structure, adx)}."
    n = f"(trend strength {adx:.0f}/100)"
    if regime_label == "TRENDING_UP":
        return f"is trending up {n}."
    if regime_label == "TRENDING_DOWN":
        return f"is trending down {n}."
    if regime_label == "RANGING":
        return (f"is quiet and sideways {n}." if quiet_words
                else f"is moving sideways {n}.")
    return f"hasn't picked a direction yet {n}."


def _delta_sentence(delta) -> str:
    """The session delta as its own sentence. The raw summary already
    begins 'Since Xmin ago:' — the old line prepended 'since last run:'
    on top of it (the duplication this spec fixes)."""
    if not delta or not delta.get("summary"):
        return ""
    summary = str(delta["summary"])
    mins = delta.get("minutes_ago")
    if mins is not None:
        ago = _minutes_phrase(mins) + " ago"
    else:
        m = re.match(r"Since\s+(.+?)\s+ago:", summary)
        ago = (m.group(1) + " ago") if m else "the last read"
    body = re.sub(r"^Since\s+.+?\s+ago:\s*", "", summary).strip()
    if body.lower().startswith("conditions unchanged"):
        return f"Nothing has changed since the last read {ago}. "
    from decision_brief import _plain
    body = body.replace("Regime changed", "the market's character changed")
    return f"Since the last read {ago}: {_plain(body)} "


def _minutes_phrase(minutes) -> str:
    try:
        m = int(minutes)
    except (TypeError, ValueError):
        return "a short while"
    if m < 60:
        return f"{m} minutes"
    return f"{m // 60}h {m % 60:02d}m"


def compute_verdict(stack: Dict) -> str:
    """Advisory synthesis of the six lines — a soft gate, never a block.
    Computed AFTER the confirm prompts so blanks count."""
    blanks = sum(1 for k in ("play_marker", "fuel_marker")
                 if stack.get(k) == "blank")
    noise    = bool(stack.get("stop_in_noise"))
    conflict = stack.get("fuel_assessment") == "conflict"
    against  = bool(stack.get("against_framework"))

    if blanks or noise or conflict:
        parts = []
        if blanks:
            parts.append(f"{blanks} blank line(s)")
        if noise:
            parts.append("stop inside noise")
        if conflict:
            parts.append("against the storyline")
        if against:
            parts.append("against the framework's read")
        return f"VERDICT: {', '.join(parts)}. Nothing here says NOW."

    strong = (stack.get("fuel_assessment") == "agrees"
              and stack.get("stop_found") and not stack.get("stop_breach")
              and stack.get("clock_clear") and not against
              and stack.get("play_name") != "none-named")
    if strong:
        return "VERDICT: Every line supports this. Size per your rules."

    weak = []
    if against:
        weak.append("the framework's read is against you")
    if stack.get("play_name") == "none-named":
        weak.append("no named play")
    if stack.get("fuel_assessment") in ("stale", "neutral"):
        weak.append("the storyline can't back you"
                    if stack.get("fuel_assessment") == "stale"
                    else "the storyline is neutral")
    if not stack.get("stop_found"):
        weak.append("no level to lean on")
    elif stack.get("stop_breach"):
        weak.append("the stop is wider than the maximum")
    if not stack.get("clock_clear"):
        weak.append("the clock is not clear")
    return f"VERDICT: Mixed — {'; '.join(weak) if weak else 'nothing decisive either way'}."


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

    # LINE 1 — BIAS (colleague voice; exhaustion subtypes render honestly,
    # same contract as decision_brief)
    adx_d1 = float(regime.get('adx', 0) or 0)
    bias = (f"The weekly chart shows "
            f"{_plain(regime.get('weekly_context', 'UNKNOWN'))}. "
            f"The daily chart "
            f"{_tf_clause(regime.get('regime_d1', 'UNKNOWN'), regime.get('regime_d1_subtype', ''), regime.get('structure', 'TRANSITIONAL'), adx_d1)}")

    # LINE 2 — REGIME (+ against-framework flag, information not a block)
    fw_dir   = decision.get("direction", "NO TRADE")
    fw_grade = decision.get("grade", "C")
    against  = fw_dir in ("NO TRADE", "") or \
               (fw_dir in ("LONG", "SHORT") and fw_dir != direction)
    adx_h4 = float(regime.get('adx_h4', 0) or 0)
    regime_line = (f"The 4-hour chart "
                   f"{_tf_clause(regime.get('regime_h4', 'UNKNOWN'), regime.get('regime_h4_subtype', ''), regime.get('structure_h4', 'TRANSITIONAL'), adx_h4, quiet_words=True)} "
                   f"{_delta_sentence(delta)}")
    if fw_dir in ("LONG", "SHORT"):
        regime_line += (f"The framework itself says: trade {fw_dir} "
                        f"(rating {fw_grade}).")
    else:
        regime_line += (f"The framework itself says: don't trade right now "
                        f"(rating {fw_grade}).")
    if against:
        regime_line += (" You'd be trading against its read — allowed, but "
                        "know why you disagree before you act.")

    # LINE 3 — PLAY (suggested)
    play, play_name = _play_line(direction, regime, entry)

    # LINE 4 — CLOCK
    ng = regime.get("news_gate") or {}
    clock_clear = False
    if ng.get("gating"):
        clock = (f"{ng.get('event')} in "
                 f"{_minutes_phrase(ng.get('minutes_until'))} — stand aside "
                 f"until after.")
    elif not ng.get("active", False):
        clock = ("The news calendar is out of date or missing — event risk "
                 "is unchecked.")
    else:
        clock = "No major economic release in the next 2 hours."
        clock_clear = True
    if instrument == "GBP_JPY" and storylines.get("intervention_watch"):
        clock += (" ⚠ INTERVENTION WATCH — this week's storyline flags "
                  "price in the historical Ministry-of-Finance response "
                  "zone.")

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
    stop_in_noise = False
    stop_found    = False
    stop_breach   = False
    if not stop or not price or \
            (direction == "LONG" and stop >= price) or \
            (direction == "SHORT" and stop <= price):
        risk = ("No clean level on the hourly or daily would prove this "
                "trade wrong — define your stop by hand before trading.")
    else:
        stop_found = True
        dist_price = abs(price - stop)
        dist_pips  = dist_price / pip
        atr_price  = float(regime.get("atr", 0) or 0)
        atr_pips   = atr_price / pip if pip else 0
        mult       = (dist_price / atr_price) if atr_price > 0 else None
        side       = "above" if direction == "SHORT" else "below"
        risk = (f"The nearest level that would prove this trade wrong is "
                f"{stop:.4f} — {dist_pips:.0f} pips {side} price.")
        risk_fields.update({"stop_price": round(stop, 5),
                            "stop_pips": round(dist_pips, 1)})
        if mult is not None:
            risk_fields["stop_atr_multiple"] = round(mult, 2)
            stop_breach = mult > MAX_STOP_ATR_MULTIPLE
            risk_fields["breach_max_stop"] = stop_breach
            # NOISE FLAG (informed prior, see MIN_STOP_ATR_MULTIPLE above):
            # a stop this close gets hit by accident, not by being wrong.
            stop_in_noise = mult < MIN_STOP_ATR_MULTIPLE
            if stop_in_noise:
                risk += (f" At today's volatility ({atr_pips:.0f}-pip "
                         f"daily range) that's inside normal noise: it "
                         f"would get hit by accident, not by being wrong. "
                         f"Wait for the market to give you a real level "
                         f"that means something.")
            elif stop_breach:
                risk += (f" That stop is {mult:.1f}x the daily range — "
                         f"wider than the {MAX_STOP_ATR_MULTIPLE}x maximum. "
                         f"Size down or find closer structure to lean on.")
        if target is not None:
            plan = get_management_plan(price, stop, target, direction,
                                       instrument=instrument)
            if plan.get("valid"):
                risk += (f" The target at {target:.4f} pays "
                         f"{plan['rr']:.1f} times what you risk "
                         f"({plan['effective_rr']:.1f} after the spread).")
                if stop_in_noise:
                    risk += (" That ratio is flattering only because the "
                             "stop is fake.")
                risk_fields["r_to_target"] = plan["rr"]
            else:
                risk += (f" The target at {target:.4f} does not work: "
                         f"{'; '.join(plan.get('errors', ['invalid']))}.")
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
        # verdict inputs (kept out of _JOURNAL_FIELDS — schema unchanged)
        "fuel_assessment": fuel_marker, "clock_clear": clock_clear,
        "stop_found": stop_found, "stop_in_noise": stop_in_noise,
        "stop_breach": stop_breach,
        **risk_fields,
    }


def render(stack: Dict) -> str:
    w = 62
    lines = [
        "═" * w,
        f"  PRE-TRADE CHECK  {stack['instrument'].replace('_', '/')} "
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

def _confirm(label: str, marker_now: str,
             no_confirm: bool) -> Tuple[str, Optional[str]]:
    """Plain-English prompt. Returns (marker, override_text_or_None).
    'o' now CAPTURES the human's own read (previously the override text was
    lost — spec 2026-09-09); it is stored in the line's journal column."""
    if no_confirm or not sys.stdin.isatty():
        return (marker_now if marker_now != "auto" else "auto"), None
    try:
        k = input(f"  {label} — does that match what you see? "
                  f"Press Enter to agree, o to write your own read, "
                  f"b to leave it blank — blank is an honest answer: "
                  ).strip().lower()
    except EOFError:
        return "auto", None
    if k == "o":
        try:
            text = input("  your read: ").strip()
        except EOFError:
            text = ""
        return "overridden", (text or None)
    if k == "b":
        return "blank", None
    return "confirmed", None


def _migrate_journal_header(path: str) -> None:
    """One-time additive migration (verdict column, 2026-09-09): when the
    journal's header predates a column appended to _JOURNAL_FIELDS, rewrite
    with the current header — every existing row preserved verbatim in its
    old columns, blank in the new one. The logger maintaining its own
    schema, never an edit of recorded values. Must run before any append."""
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None or                     list(reader.fieldnames) == _JOURNAL_FIELDS:
                return
            rows = list(reader)
    except OSError:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_JOURNAL_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: (r.get(k) or "") for k in _JOURNAL_FIELDS})


def append_journal(stack: Dict, path: str = JOURNAL_FILE) -> None:
    """Append-only ledger write (gitignored). Never edits existing rows."""
    exists = os.path.exists(path)
    if exists:
        _migrate_journal_header(path)
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

    # Interactive confirm on the two SUGGESTED lines (3 PLAY, 5 FUEL);
    # an override's text replaces the line in the record.
    stack["play_marker"], ptext = _confirm("PLAY", "auto", a.no_confirm)
    if ptext:
        stack["play"] = ptext
    if stack["fuel_marker"] in ("agrees", "neutral"):
        stack["fuel_marker"], ftext = _confirm(
            "FUEL", stack["fuel_marker"], a.no_confirm)
        if ftext:
            stack["fuel"] = ftext

    # VERDICT — advisory, after the confirms so blanks count; travels in
    # the record inside the synthesis line (journal schema unchanged).
    verdict = compute_verdict(stack)
    print(f"\n  {verdict}")
    stack["verdict"] = verdict

    append_journal(stack)
    print(f"\n  recorded → pre_trade_journal.csv  (id {stack['stack_id']})")
    if stack["against_framework"]:
        print("  note: framework disagreement is IN the record.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
