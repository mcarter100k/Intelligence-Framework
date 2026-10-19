# PRIOR-SESSION ARTIFACT: committed 2026-10-18 for citation integrity (foundation/ cites it).
# Committed exactly as found; NOT re-verified against current code.
"""
gbpaud_secondplay_scouting.py
─────────────────────────────────────────────────────────────────────────────
READ-ONLY — fourth study in the GBP/AUD profile series (2026-09-11).
studies/ only. Window 2023-09-01 → 2026-09-10 ONLY (pre-2023 sealed pending
the framework-chat history-split ruling).

Items:
  1. GEOMETRY FIX — the depth-conditioned breach table re-cut by bounce
     PROGRESS toward the level: progress = bounce depth ÷ that leg's own
     LH/HL distance (both from the same reference extreme, same ATR basis
     cancels out). Thresholds 50/70/85/95%. This removes the "deep bounce is
     mechanically near the level" confound: at each threshold the question
     is "given the bounce retraced ≥ p of the way to the level, did the
     level break before a new with-trend extreme?" Breach legs exceed 100%
     progress by construction; day-granularity OHLC cannot order intraday
     ties (stated).
  2. SECOND-PLAY SCOUTING — descriptive census of the ≥1× D1 ATR H4 zigzag
     swings (the weekly study's opportunity units). HINDSIGHT-DEFINED:
     a zigzag swing is only knowable as ≥1 ATR after it has completed, so
     every number here describes where opportunity LIVED, not a signal that
     could have been taken at the swing start. Reported per swing start:
       (a) regime cell — PRIOR trading day's (D1,H4) as-of-close cell
           (the live-parity, no-peek attribution used throughout);
       (b) PDT clock hour of the swing-start H4 bar's open;
       (c) share starting within 2 hours of a tracked release (release set
           and date confidence identical to the profile study), against the
           all-H4-bars baseline share — without the baseline the swing
           share is uninterpretable;
       (d) share falling in weeks that had NO first-bounce entry (the 75%
           of weeks the confirmed-trend play leaves empty), against that
           same weeks baseline.
"""
from __future__ import annotations

import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _p in (_ROOT, _os.path.join(_ROOT, "shadow"), _os.path.dirname(_os.path.abspath(__file__))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

import statistics
from bisect import bisect_left
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Tuple
from zoneinfo import ZoneInfo

import pandas as pd

from gbpaud_personality_profile import (
    END, PIP, START, _load, build_day_map, release_calendar,
    structure_episodes, trading_day, year_segments,
)
from gbpaud_weekly_opportunity import leg_races, n_note, pctl, week_key

OUT: List[str] = []
def emit(s: str = "") -> None:
    print(s); OUT.append(s)


# ── 1. GEOMETRY FIX ─────────────────────────────────────────────────────────
def geometry_fix(races: List[Dict]) -> None:
    emit("\n## 1. Breach rate by bounce PROGRESS toward the level")
    emit("progress = bounce depth ÷ that leg's LH/HL distance (same reference")
    emit("extreme; the ATR basis cancels). Breach = level broken before a new")
    emit("with-trend extreme, 60-day cap. Day-granularity OHLC cannot order")
    emit("intraday ties; depth includes the resolution day's excursion.")
    resolved = [r for r in races if r["outcome"] != "unresolved"]
    for r in resolved:
        r["progress"] = r["depth_x_atr"] / r["level_dist_x_atr"] if r["level_dist_x_atr"] else None
    resolved = [r for r in resolved if r["progress"] is not None]
    base = [r for r in resolved if r["outcome"] in ("breach_first", "same_day_both")]
    emit(f"  Base rate (all resolved, {n_note(len(resolved))}): "
         f"{100*len(base)/len(resolved):.0f}% breach")
    emit(f"  {'progress ≥':>12}   {'N':>3}   breached   rate")
    for p in (0.50, 0.70, 0.85, 0.95):
        sub = [r for r in resolved if r["progress"] >= p]
        if not sub:
            emit(f"  {100*p:>10.0f}%   {0:>3}   —          no legs reached this progress")
            continue
        b = sum(1 for r in sub if r["outcome"] in ("breach_first", "same_day_both"))
        flag = "" if len(sub) >= 30 else "   [descriptive only]"
        emit(f"  {100*p:>10.0f}%   {len(sub):>3}   {b:>3}       {100*b/len(sub):4.0f}%{flag}")
    nb = sorted(r["progress"] for r in resolved
                if r["outcome"] == "new_extreme_first")
    emit(f"  Progress reached by NON-breach legs ({n_note(len(nb))}): "
         f"p25/p50/p75 = {100*pctl(nb,25):.0f}%/{100*pctl(nb,50):.0f}%/{100*pctl(nb,75):.0f}%")


# ── zigzag with leg detail ─────────────────────────────────────────────────
def zigzag_legs(H: List[float], L: List[float], T: float) -> List[Tuple[int, int, int]]:
    """(start_idx, end_idx, direction) for every leg with amplitude ≥ T,
    terminal leg included (it begins with a ≥T counter-move)."""
    legs = []
    if not H or T <= 0:
        return legs
    d = 0
    ext_hi, ext_lo = H[0], L[0]
    hi_i = lo_i = 0
    start = ext_i = 0
    ext = 0.0
    for j, (h, l) in enumerate(zip(H, L)):
        if d == 0:
            if h > ext_hi:
                ext_hi, hi_i = h, j
            if l < ext_lo:
                ext_lo, lo_i = l, j
            if h - ext_lo >= T:
                d, start, ext, ext_i = 1, lo_i, h, j
            elif ext_hi - l >= T:
                d, start, ext, ext_i = -1, hi_i, l, j
        elif d == 1:
            if h > ext:
                ext, ext_i = h, j
            if ext - l >= T:
                legs.append((start, ext_i, 1))
                d, start, ext, ext_i = -1, ext_i, l, j
        else:
            if l < ext:
                ext, ext_i = l, j
            if h - ext >= T:
                legs.append((start, ext_i, -1))
                d, start, ext, ext_i = 1, ext_i, h, j
    if d != 0:
        legs.append((start, ext_i, d))
    return legs


# ── release datetimes (UTC) ────────────────────────────────────────────────
_REL_TIME = {
    "RBA":        (time(14, 30), ZoneInfo("Australia/Sydney")),
    "BoE":        (time(12, 0),  ZoneInfo("Europe/London")),
    "AU_CPI_q":   (time(11, 30), ZoneInfo("Australia/Sydney")),
    "UK_CPI":     (time(7, 0),   ZoneInfo("Europe/London")),
    "US_CPI":     (time(8, 30),  ZoneInfo("America/New_York")),
    "NFP":        (time(8, 30),  ZoneInfo("America/New_York")),
    "US_ISM_mfg": (time(10, 0),  ZoneInfo("America/New_York")),
}

def release_datetimes() -> List[pd.Timestamp]:
    out = []
    for name, d, _conf in release_calendar():
        t, tz = _REL_TIME[name]
        out.append(pd.Timestamp(datetime.combine(d, t, tzinfo=tz)).tz_convert("UTC"))
    return sorted(out)


def near_release(open_ts: pd.Timestamp, rels: List[pd.Timestamp],
                 buffer_h: float = 2.0) -> bool:
    """Bar interval [open, open+4h) within buffer_h hours of any release."""
    lo = open_ts - pd.Timedelta(hours=buffer_h)
    hi = open_ts + pd.Timedelta(hours=4 + buffer_h)
    i = bisect_left(rels, lo)
    return i < len(rels) and rels[i] < hi


# ── 2. SECOND-PLAY SCOUTING ────────────────────────────────────────────────
def scouting(dm: Dict[date, Dict], h4: pd.DataFrame, races: List[Dict]) -> None:
    emit("\n## 2. Second-play scouting — census of ≥1× D1 ATR H4 swings")
    emit("HINDSIGHT-DEFINED throughout: a swing is only knowable after it completes.")
    all_days = sorted(dm)
    day_pos = {d: k for k, d in enumerate(all_days)}
    h4_day = [trading_day(t + pd.Timedelta(hours=4)) for t in h4.index]
    h4H = h4["High"].tolist(); h4L = h4["Low"].tolist()

    by_week: Dict[Tuple[int, int], List[int]] = defaultdict(list)
    for i, dy in enumerate(h4_day):
        if START <= dy <= END:
            by_week[week_key(dy)].append(i)
    wk_days: Dict[Tuple[int, int], List[date]] = defaultdict(list)
    for d in all_days:
        wk_days[week_key(d)].append(d)

    # prior-week ATR per week (same rule as the weekly study)
    keys = sorted(wk_days)
    prior_atr = {}
    for kk, wk in enumerate(keys):
        if kk > 0:
            prior_atr[wk] = dm[wk_days[keys[kk - 1]][-1]]["atr"]

    swings = []
    for wk, idxs in sorted(by_week.items()):
        T = prior_atr.get(wk)
        if T is None or len(wk_days[wk]) < 3:
            continue
        legs = zigzag_legs([h4H[i] for i in idxs], [h4L[i] for i in idxs], T)
        for s, e, dr in legs:
            g = idxs[s]
            swings.append({"week": wk, "g": g, "dir": dr,
                           "open": h4.index[g], "day": h4_day[g]})
    emit(f"  Swings found: {n_note(len(swings))} across {len(prior_atr)} weeks "
         f"(same zigzag as the weekly study's counts).")

    # (a) regime cell at swing start — prior day's as-of-close cell
    cells = Counter(); d1_reg = Counter(); unattributed = 0
    for s in swings:
        k = day_pos.get(s["day"])
        if k is None or k == 0:
            unattributed += 1
            continue
        p = dm[all_days[k - 1]]
        cells[(p["d1_regime"], p["h4_regime"])] += 1
        d1_reg[p["d1_regime"]] += 1
    n_attr = sum(d1_reg.values())
    emit(f"\n  (a) Regime cell at swing start (prior day close, no peek; "
         f"{n_note(n_attr)}, {unattributed} unattributed at window edge)")
    emit(f"      D1 regime:  " + "   ".join(
        f"{k} {100*v/n_attr:.0f}%" for k, v in d1_reg.most_common()))
    emit(f"      Top (D1,H4) cells:")
    for (c1, c4), v in cells.most_common(8):
        emit(f"        {c1:>13} / {c4:<13} {100*v/n_attr:5.1f}%  (n={v})")

    # (b) PDT hour of swing-start bar open
    hrs = Counter(s["open"].tz_convert("America/Los_Angeles").hour for s in swings)
    emit(f"\n  (b) PDT hour of swing-start H4 bar open ({n_note(len(swings))}):")
    for h, v in sorted(hrs.items()):
        emit(f"        {h:02d}:00 PDT  {100*v/len(swings):5.1f}%  (n={v})")

    # (c) within 2h of a tracked release, vs all-bars baseline
    rels = release_datetimes()
    near = sum(1 for s in swings if near_release(s["open"], rels))
    all_bars = [h4.index[i] for i, dy in enumerate(h4_day) if START <= dy <= END]
    base = sum(1 for t in all_bars if near_release(t, rels))
    emit(f"\n  (c) Swing starts within 2h of a tracked release: "
         f"{100*near/len(swings):.0f}% ({near}/{len(swings)})")
    emit(f"      Baseline — ALL H4 bars in window within 2h of a release: "
         f"{100*base/len(all_bars):.0f}% ({base}/{len(all_bars)})")
    emit(f"      (release set + date confidence identical to the profile study;")
    emit(f"       release local times: RBA/AU_CPI Sydney, BoE/UK_CPI London,")
    emit(f"       US prints New York — DST handled per event)")

    # (d) share in weeks with no first-bounce entry
    entry_weeks = {week_key(r["entry_day"]) for r in races
                   if r.get("entry_day") is not None}
    wk_all = set(prior_atr) & {wk for wk in wk_days if len(wk_days[wk]) >= 3}
    empty_weeks = {wk for wk in wk_all if wk not in entry_weeks}
    in_empty = sum(1 for s in swings if s["week"] in empty_weeks)
    emit(f"\n  (d) Swings in weeks with NO first-bounce entry: "
         f"{100*in_empty/len(swings):.0f}% ({in_empty}/{len(swings)})")
    emit(f"      Baseline — share of weeks that are entry-empty: "
         f"{100*len(empty_weeks)/len(wk_all):.0f}% ({len(empty_weeks)}/{len(wk_all)})")

    return


def main() -> None:
    emit("=" * 78)
    emit("GBP/AUD SECOND-PLAY SCOUTING — read-only, 2026-09-11")
    emit("Window 2023-09-01 → 2026-09-10 only. Pre-2023 sealed.")
    emit("=" * 78)
    d1 = _load("D"); h4 = _load("H4")
    dm = build_day_map(d1, h4)
    eps = structure_episodes(dm)
    races = leg_races(dm, eps, d1)
    # summary is emitted AFTER computation; placeholder list index
    geometry_fix(races)
    scouting(dm, h4, races)
    out_md = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                           "gbpaud_secondplay_scouting_report.md")
    with open(out_md, "w") as f:
        f.write("```\n" + "\n".join(OUT) + "\n```\n")
    print(f"\n[report written to {out_md}]")


if __name__ == "__main__":
    main()
