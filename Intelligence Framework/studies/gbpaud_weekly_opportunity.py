# PRIOR-SESSION ARTIFACT: committed 2026-10-18 for citation integrity (foundation/ cites it).
# Committed exactly as found; NOT re-verified against current code.
"""
gbpaud_weekly_opportunity.py
─────────────────────────────────────────────────────────────────────────────
READ-ONLY — third study in the GBP/AUD profile series (2026-09-11).
studies/ only. Window 2023-09-01 → 2026-09-10 ONLY (pre-2023 data stays
unopened pending the framework-chat history-split ruling; the cache's
2022-06/2023-05 tails are warm-up for trailing windows, never analyzed).

Items:
  1. WEEKLY RANGE — per ISO week (Mon–Fri trading days): high−low in pips
     and ÷ D1 ATR(14) as of the PRIOR week's last close (known at week open,
     no peek). Median/p25/p75 per Sep-year. Weeks with <3 trading days
     excluded (counted).
  2. OPPORTUNITY COUNT — per week: number of H4 zigzag legs (both
     directions) with amplitude ≥ 1× that same prior-week D1 ATR, computed
     on the week's own H4 bars. A leg counts once its amplitude reaches the
     threshold; the terminal leg counts if it reached it. Distribution and
     % of weeks with zero.
  3. PIP CEILING — HINDSIGHT CEILING, NOT A STRATEGY RESULT. For each
     confirmed D1 leg (same race framework as gbpaud_profile_followup item
     3): entry at the first bounce's adverse extreme (deepest point between
     confirmation and the first new with-trend extreme — or before the
     LH/HL breach when the bounce breaches first), exit at the max
     favorable extreme reached before the LH/HL level is breached (60-day
     cap). Perfect entry and perfect exit are both assumed — this is the
     ceiling of what first-bounce entries could ever have paid. Reported
     per event AND per week (entry-day week; weeks without an entry = 0).
  4. CONDITIONAL BREACH RATE — among legs whose bounce depth reached
     ≥ d × ATR(confirmation day) before the race resolved
     (d ∈ 1.0/1.5/1.85/2.0/2.25): share that went on to breach the last
     confirmed LH/HL before a new with-trend extreme. N stated at each
     depth. Context: the LH/HL level itself sits at a measurable ×ATR
     distance from the reference extreme — reported alongside, because at
     depths near that distance the breach is mechanical.
"""
from __future__ import annotations

import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _p in (_ROOT, _os.path.join(_ROOT, "shadow"), _os.path.dirname(_os.path.abspath(__file__))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

import statistics
from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

from gbpaud_personality_profile import (
    END, PIP, START, _load, build_day_map, structure_episodes, trading_day,
    year_segments,
)

OUT: List[str] = []
def emit(s: str = "") -> None:
    print(s); OUT.append(s)

def pctl(vals: List[float], p: float) -> float:
    v = sorted(vals)
    if len(v) == 1:
        return v[0]
    k = (len(v) - 1) * p / 100.0
    f = int(k)
    return v[f] + (v[min(f + 1, len(v) - 1)] - v[f]) * (k - f)

def n_note(n: int) -> str:
    return f"N={n}" + ("" if n >= 30 else " [descriptive only]")

def week_key(d: date) -> Tuple[int, int]:
    iso = d.isocalendar()
    return (iso[0], iso[1])


# ── weekly frames ───────────────────────────────────────────────────────────
def build_weeks(dm: Dict[date, Dict], h4: pd.DataFrame) -> List[Dict]:
    all_days = sorted(dm)
    by_week: Dict[Tuple[int, int], List[date]] = defaultdict(list)
    for d in all_days:
        by_week[week_key(d)].append(d)
    h4_day = [trading_day(t + pd.Timedelta(hours=4)) for t in h4.index]
    h4H = h4["High"].tolist(); h4L = h4["Low"].tolist()
    h4_by_week: Dict[Tuple[int, int], List[int]] = defaultdict(list)
    for i, dy in enumerate(h4_day):
        if START <= dy <= END:
            h4_by_week[week_key(dy)].append(i)

    weeks = []
    keys = sorted(by_week)
    for kk, wk in enumerate(keys):
        days = by_week[wk]
        prior_atr = None
        if kk > 0:
            prev_last = by_week[keys[kk - 1]][-1]
            prior_atr = dm[prev_last]["atr"]
        hi = max(dm[d]["high"] for d in days)
        lo = min(dm[d]["low"] for d in days)
        idxs = h4_by_week.get(wk, [])
        weeks.append({
            "key": wk, "days": days, "n_days": len(days),
            "last_day": days[-1], "prior_atr": prior_atr,
            "range_pips": (hi - lo) / PIP,
            "range_x_atr": (hi - lo) / prior_atr if prior_atr else None,
            "h4H": [h4H[i] for i in idxs], "h4L": [h4L[i] for i in idxs],
        })
    return weeks


def count_swings(H: List[float], L: List[float], T: float) -> int:
    """Zigzag legs with amplitude ≥ T (both directions). Every counted leg
    reached amplitude ≥ T by construction; the terminal leg is included
    (it begins with a ≥T counter-move)."""
    if not H or T <= 0:
        return 0
    d = 0; legs = 0
    ext_hi, ext_lo = H[0], L[0]
    ext = 0.0
    for h, l in zip(H, L):
        if d == 0:
            ext_hi = max(ext_hi, h); ext_lo = min(ext_lo, l)
            if h - ext_lo >= T:
                d, ext, legs = 1, h, 1
            elif ext_hi - l >= T:
                d, ext, legs = -1, l, 1
        elif d == 1:
            ext = max(ext, h)
            if ext - l >= T:
                d, ext, legs = -1, l, legs + 1
        else:
            ext = min(ext, l)
            if h - ext >= T:
                d, ext, legs = 1, h, legs + 1
    return legs


# ── leg race with first-bounce entry / ceiling ──────────────────────────────
CAP = 60

def leg_races(dm: Dict[date, Dict], eps: List[Dict], d1: pd.DataFrame) -> List[Dict]:
    days_all = [trading_day(t + pd.Timedelta(hours=24)) for t in d1.index]
    H = d1["High"].tolist(); L = d1["Low"].tolist()
    day_idx = {dy: i for i, dy in enumerate(days_all)}
    out = []
    for e in eps:
        if e["label"] not in ("UPTREND", "DOWNTREND"):
            continue
        s = e["start"]; info = dm[s]
        down = e["label"] == "DOWNTREND"
        level = info["latest_sh"] if down else info["latest_sl"]
        if level is None:
            continue
        si = day_idx[s]
        piv = None
        for i in range(si - 1, max(si - 120, -1), -1):
            if abs((H[i] if down else L[i]) - level) < 1e-9:
                piv = i; break
        if piv is None:
            continue
        ref = min(L[piv:si + 1]) if down else max(H[piv:si + 1])
        atr_s = info["atr"] or 1e-9

        # race walk
        n1 = b1 = None          # first new with-trend extreme / first breach
        depth = 0.0
        end_t = min(si + CAP, len(H) - 1)
        for t in range(si + 1, end_t + 1):
            adverse = (H[t] - ref) if down else (ref - L[t])
            if (n1 is None) and (b1 is None):
                depth = max(depth, adverse)
            breach = H[t] > level if down else L[t] < level
            newext = L[t] < ref if down else H[t] > ref
            if b1 is None and breach:
                b1 = t
            if n1 is None and newext:
                n1 = t
            if b1 is not None and n1 is not None:
                break
        if b1 is not None and (n1 is None or b1 <= n1):
            outcome = "breach_first" if (n1 is None or b1 < n1) else "same_day_both"
        elif n1 is not None:
            outcome = "new_extreme_first"
        else:
            outcome = "unresolved"

        # first-bounce entry (hindsight): deepest adverse point in
        # (s, first resolution day]; exit = max favorable from entry day
        # until the breach day (exclusive of post-breach action) or cap.
        stop_t = b1 if b1 is not None else end_t
        bounce_end = min(x for x in (n1, b1, end_t) if x is not None)
        win = range(si + 1, bounce_end + 1)
        ceiling = None; entry_day = None
        if len(list(win)) > 0:
            if down:
                entry_t = max(win, key=lambda t: H[t])
                entry_px = H[entry_t]
                lows = L[entry_t:stop_t + 1]
                ceiling = max(0.0, (entry_px - min(lows)) / PIP) if lows else 0.0
            else:
                entry_t = min(win, key=lambda t: L[t])
                entry_px = L[entry_t]
                highs = H[entry_t:stop_t + 1]
                ceiling = max(0.0, (max(highs) - entry_px) / PIP) if highs else 0.0
            entry_day = days_all[entry_t]
        out.append({"start": s, "label": e["label"], "outcome": outcome,
                    "depth_x_atr": depth / atr_s,
                    "level_dist_x_atr": abs(level - ref) / atr_s,
                    "ceiling_pips": ceiling, "entry_day": entry_day})
    return out


# ── report blocks ───────────────────────────────────────────────────────────
def seg_of(d: date) -> Optional[str]:
    for nm, a, b in year_segments():
        if a <= d <= b:
            return nm
    return None


def main() -> None:
    emit("=" * 78)
    emit("GBP/AUD WEEKLY OPPORTUNITY STUDY — read-only, 2026-09-11")
    emit("Window 2023-09-01 → 2026-09-10 only. Pre-2023 unopened.")
    emit("=" * 78)
    d1 = _load("D"); h4 = _load("H4")
    dm = build_day_map(d1, h4)
    eps = structure_episodes(dm)
    weeks = build_weeks(dm, h4)
    full = [w for w in weeks if w["n_days"] >= 3 and w["prior_atr"]]
    races = leg_races(dm, eps, d1)

    # per-week swing counts + ceiling assignment
    for w in full:
        w["swings"] = count_swings(w["h4H"], w["h4L"], w["prior_atr"])
    ceil_by_week: Dict[Tuple[int, int], float] = defaultdict(float)
    for r in races:
        if r["ceiling_pips"] is not None and r["entry_day"] is not None:
            ceil_by_week[week_key(r["entry_day"])] += r["ceiling_pips"]
    for w in full:
        w["ceiling"] = ceil_by_week.get(w["key"], 0.0)

    excluded = [w for w in weeks if w not in full]

    # ── PLAIN-ENGLISH SUMMARY (auto-generated from the numbers below) ──────
    rp = [w["range_pips"] for w in full]
    rx = [w["range_x_atr"] for w in full]
    sw = [w["swings"] for w in full]
    zero_sw = sum(1 for s in sw if s == 0)
    cl = [w["ceiling"] for w in full]
    zero_cl = sum(1 for c in cl if c == 0)
    ev_cl = [r["ceiling_pips"] for r in races if r["ceiling_pips"] is not None]
    resolved = [r for r in races if r["outcome"] in ("breach_first", "new_extreme_first")]
    emit("\nPLAIN-ENGLISH SUMMARY")
    emit("─────────────────────")
    emit(f"• A normal week travels about {pctl(rp,50):.0f} pips top to bottom "
         f"(middle half: {pctl(rp,25):.0f}–{pctl(rp,75):.0f}), which is roughly "
         f"{pctl(rx,50):.1f}× the daily ATR you knew at the week's open.")
    emit(f"• Opportunity is steady, not scarce: the typical week contains "
         f"{statistics.median(sw):.0f} H4 swings of at least one daily ATR, and only "
         f"{100*zero_sw/len(sw):.0f}% of weeks contain none. The raw material for "
         f"1-ATR trades is there almost every week.")
    emit(f"• The first-bounce ceiling is a different story: it is EMPTY in "
         f"{100*zero_cl/len(cl):.0f}% of weeks (median week = 0 pips), because "
         f"confirmed-trend entries only exist when a leg confirms (~{len(races)} legs "
         f"in ~{len(full)} weeks). When an entry DOES exist, its hindsight ceiling is "
         f"median {pctl(ev_cl,50):.0f} pips per event (middle half "
         f"{pctl(ev_cl,25):.0f}–{pctl(ev_cl,75):.0f}). Perfect entry AND perfect exit "
         f"are assumed — no real result gets near this number.")
    d10 = [r for r in races if r["depth_x_atr"] >= 1.0 and r["outcome"] != "unresolved"]
    d20 = [r for r in races if r["depth_x_atr"] >= 2.0 and r["outcome"] != "unresolved"]
    br = lambda rs: 100 * sum(1 for r in rs if r["outcome"] in ("breach_first", "same_day_both")) / len(rs)
    emit(f"• Depth vs breach: the last confirmed LH/HL sits a median "
         f"{pctl([r['level_dist_x_atr'] for r in races],50):.1f}×ATR from the move's "
         f"extreme. A bounce reaching 1.0×ATR says little ({br(d10):.0f}% eventual "
         f"breach vs {100*sum(1 for r in resolved if r['outcome']=='breach_first')/len(resolved):.0f}% base); by 2.0×ATR the rate is {br(d20):.0f}% — but at that "
         f"depth the bounce is already near the level itself, so this mostly restates "
         f"where the LH/HL sits. Exact rates with N below.")
    emit(f"• Weeks excluded as partial (<3 trading days) or missing prior ATR: "
         f"{len(excluded)}.")

    # ── 1. WEEKLY RANGE ────────────────────────────────────────────────────
    emit("\n## 1. Weekly range (high−low), pips and ×prior-week D1 ATR")
    emit(f"  {'segment':<26}{'N wks':>6}   pips p25/p50/p75      ×ATR p25/p50/p75")
    def wk_seg_rows(sel):
        p = [w["range_pips"] for w in sel]; x = [w["range_x_atr"] for w in sel]
        return (f"{pctl(p,25):5.0f}/{pctl(p,50):5.0f}/{pctl(p,75):5.0f}"
                f"        {pctl(x,25):.1f}/{pctl(x,50):.1f}/{pctl(x,75):.1f}")
    emit(f"  {'POOLED':<26}{len(full):>6}   {wk_seg_rows(full)}")
    for nm, a, b in year_segments():
        sel = [w for w in full if a <= w["last_day"] <= b]
        flag = "" if len(sel) >= 30 else " [descriptive only]"
        emit(f"  {nm:<26}{len(sel):>6}   {wk_seg_rows(sel)}{flag}")

    # ── 2. OPPORTUNITY COUNT ───────────────────────────────────────────────
    emit("\n## 2. H4 swings ≥ 1× D1 ATR per week (week-local zigzag, both directions)")
    emit(f"  {'segment':<26}{'N wks':>6}   p25/p50/p75    %zero   distribution 0/1/2/3/4/5+")
    def sw_rows(sel):
        s = [w["swings"] for w in sel]
        c = Counter(min(x, 5) for x in s)
        dist = "/".join(str(c[k]) for k in range(6))
        return (f"{pctl(s,25):3.0f}/{pctl(s,50):3.0f}/{pctl(s,75):3.0f}"
                f"    {100*sum(1 for x in s if x==0)/len(s):4.0f}%   {dist}")
    emit(f"  {'POOLED':<26}{len(full):>6}   {sw_rows(full)}")
    for nm, a, b in year_segments():
        sel = [w for w in full if a <= w["last_day"] <= b]
        flag = "" if len(sel) >= 30 else " [descriptive only]"
        emit(f"  {nm:<26}{len(sel):>6}   {sw_rows(sel)}{flag}")

    # ── 3. PIP CEILING ─────────────────────────────────────────────────────
    emit("\n## 3. First-bounce pip ceiling — HINDSIGHT CEILING (perfect entry at the")
    emit("bounce extreme, perfect exit at max favorable before LH/HL breach, 60-day")
    emit("cap). Not achievable by any real execution; an upper bound only.")
    emit(f"  Per event ({n_note(len(ev_cl))}): p25/p50/p75 = "
         f"{pctl(ev_cl,25):.0f}/{pctl(ev_cl,50):.0f}/{pctl(ev_cl,75):.0f} pips "
         f"(max {max(ev_cl):.0f}); events with ceiling <50 pips: "
         f"{sum(1 for c in ev_cl if c < 50)}")
    emit(f"  Per week (weeks with no entry count as 0):")
    emit(f"  {'segment':<26}{'N wks':>6}   p25/p50/p75 pips    %zero    mean")
    def cl_rows(sel):
        c = [w["ceiling"] for w in sel]
        return (f"{pctl(c,25):4.0f}/{pctl(c,50):4.0f}/{pctl(c,75):4.0f}"
                f"        {100*sum(1 for x in c if x==0)/len(c):4.0f}%   {statistics.mean(c):5.0f}")
    emit(f"  {'POOLED':<26}{len(full):>6}   {cl_rows(full)}")
    for nm, a, b in year_segments():
        sel = [w for w in full if a <= w["last_day"] <= b]
        flag = "" if len(sel) >= 30 else " [descriptive only]"
        emit(f"  {nm:<26}{len(sel):>6}   {cl_rows(sel)}{flag}")

    # ── 4. CONDITIONAL BREACH RATE ─────────────────────────────────────────
    emit("\n## 4. Breach rate of the last LH/HL once the bounce reached depth d×ATR")
    emit("Depth = adverse excursion from the move's reference extreme before the race")
    emit("resolved; ATR = D1 ATR(14) at the confirmation day. Breach = level broken")
    emit("BEFORE a new with-trend extreme (60-day cap). Base rate for context first.")
    ld = [r["level_dist_x_atr"] for r in races]
    emit(f"  LH/HL distance from reference extreme ({n_note(len(ld))}): "
         f"p25/p50/p75 = {pctl(ld,25):.1f}/{pctl(ld,50):.1f}/{pctl(ld,75):.1f} ×ATR")
    base_b = sum(1 for r in resolved if r["outcome"] == "breach_first")
    emit(f"  Base rate (all resolved races, {n_note(len(resolved))}): "
         f"{100*base_b/len(resolved):.0f}% breach")
    emit(f"  {'depth ≥ d×ATR':>14}   {'N':>3}   breached   rate")
    for d in (1.0, 1.5, 1.85, 2.0, 2.25):
        sub = [r for r in races if r["depth_x_atr"] >= d and r["outcome"] != "unresolved"]
        if not sub:
            emit(f"  {d:>13.2f}   {0:>3}   —          no legs reached this depth")
            continue
        b = sum(1 for r in sub if r["outcome"] in ("breach_first", "same_day_both"))
        flag = "" if len(sub) >= 30 else "   [descriptive only]"
        emit(f"  {d:>13.2f}   {len(sub):>3}   {b:>3}       {100*b/len(sub):4.0f}%{flag}")
    emit("\n  NOTE: at depths at/above the level's own ×ATR distance the breach is")
    emit("  mechanical (the bounce IS at the level), so rates at d ≥ ~2 largely restate")
    emit("  where the LH/HL sits, not an independent probability.")

    out_md = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                           "gbpaud_weekly_opportunity_report.md")
    with open(out_md, "w") as f:
        f.write("```\n" + "\n".join(OUT) + "\n```\n")
    print(f"\n[report written to {out_md}]")


if __name__ == "__main__":
    main()
