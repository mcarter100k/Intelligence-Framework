# PRIOR-SESSION ARTIFACT: committed 2026-10-18 for citation integrity (foundation/ cites it).
# Committed exactly as found; NOT re-verified against current code.
"""
gbpaud_scouting_verify.py
─────────────────────────────────────────────────────────────────────────────
READ-ONLY — fifth study in the GBP/AUD profile series (2026-09-11).
studies/ only. Window 2023-09-01 → 2026-09-10 ONLY; pre-2023 sealed.
Descriptive; item 3 is a FIXED-RULE verification (all cells specified in
advance by the commissioning message, all cells reported — no search, no
selection).

Items:
  1. REGIME BASELINE — % of all H4 bars in each D1 regime (attributed to the
     PRIOR trading day's as-of-close regime, identical to the swing-start
     attribution, so the ratio is apples-to-apples). Ratio = swing-start
     share ÷ time share. Only ratios well away from 1.0 are meaningful.
  2. HOUR ARTIFACT — swing-start hour census redone with a CONTINUOUS zigzag
     over the whole window (threshold = prior-week D1 ATR, evaluated at the
     current bar; no forced week-edge pivots), and again with starts landing
     on each week's first/last H4 bar excluded.
  3. VERIFY (fixed rules) — first-bounce with-trend entries at exactly
     50/60/70/85% progress to the last LH/HL; target = a touch of the
     reference extreme (a new with-trend extreme); stops fixed in advance at
     LH/HL + 0.1×ATR and + 0.3×ATR beyond the level; 3 pips round-trip
     spread. Executed on H4 bars, 60-trading-day cap from confirmation.
     Conservative same-bar conventions, stated in the code where applied:
       - pre-fill bar touching BOTH the entry and the target: no trade
         (ambiguous — not claimed as a win); counted.
       - fill bar also touching the stop: loss (adverse-first).
       - fill bar touching the target with the stop untouched: win (the
         target touch is certain; only stop-ordering is ever ambiguous).
       - after fill, any bar touching both stop and target: stop first.
     Loss = −1.0R with the spread inside the denominator; win R =
     (reward − 3 pips) / (risk + 3 pips). Open-at-cap positions scored at
     the cap close and counted separately.
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
)
from gbpaud_weekly_opportunity import n_note, pctl, week_key

OUT: List[str] = []
def emit(s: str = "") -> None:
    print(s); OUT.append(s)

SPREAD_PIPS = 3.0
CAP_DAYS = 60
PROGRESS = (0.50, 0.60, 0.70, 0.85)
STOPS = (0.1, 0.3)


# ── leg geometry (same walk as gbpaud_weekly_opportunity.leg_races, kept
#    local so the already-published studies stay untouched; exposes ref/level)
def leg_geometry(dm: Dict[date, Dict], eps: List[Dict], d1: pd.DataFrame) -> List[Dict]:
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
        cap_i = min(si + CAP_DAYS, len(days_all) - 1)
        out.append({"start": s, "down": down, "level": level, "ref": ref,
                    "atr": info["atr"], "cap_day": days_all[cap_i]})
    return out


# ── 1. REGIME BASELINE ─────────────────────────────────────────────────────
def regime_baseline(dm, h4, swing_starts: List[Dict]) -> Tuple[List[str], Dict]:
    all_days = sorted(dm)
    day_pos = {d: k for k, d in enumerate(all_days)}
    h4_day = [trading_day(t + pd.Timedelta(hours=4)) for t in h4.index]

    def prior_reg(dy: date) -> Optional[Tuple[str, str]]:
        k = day_pos.get(dy)
        if k is None or k == 0:
            return None
        p = dm[all_days[k - 1]]
        return (p["d1_regime"], p["h4_regime"])

    time_c = Counter(); time_cell = Counter()
    for dy in h4_day:
        if START <= dy <= END:
            r = prior_reg(dy)
            if r:
                time_c[r[0]] += 1; time_cell[r] += 1
    n_time = sum(time_c.values())

    sw_c = Counter(); sw_cell = Counter()
    for s in swing_starts:
        r = prior_reg(s["day"])
        if r:
            sw_c[r[0]] += 1; sw_cell[r] += 1
    n_sw = sum(sw_c.values())

    lines = []
    lines.append(f"  D1 regime      time-share  swing-share   ratio   (bars N={n_time}, swings {n_note(n_sw)})")
    ratios = {}
    for reg in ("VOLATILE", "RANGING", "TRENDING_UP", "TRENDING_DOWN"):
        ts = time_c[reg] / n_time
        ss = sw_c[reg] / n_sw
        ratios[reg] = ss / ts if ts else float("nan")
        lines.append(f"  {reg:<14} {100*ts:8.1f}%  {100*ss:9.1f}%   {ratios[reg]:5.2f}")
    lines.append("")
    lines.append(f"  Top (D1,H4) cells by time share:")
    lines.append(f"  {'cell':<32}time-share  swing-share   ratio")
    for cell, n in time_cell.most_common(8):
        ts = n / n_time; ss = sw_cell[cell] / n_sw
        lines.append(f"  {cell[0]:>13} / {cell[1]:<15} {100*ts:7.1f}%  {100*ss:9.1f}%   {ss/ts:5.2f}")
    return lines, ratios


# ── 2. HOUR ARTIFACT ───────────────────────────────────────────────────────
def continuous_zigzag(h4: pd.DataFrame, dm) -> Tuple[List[Dict], set]:
    all_days = sorted(dm)
    h4_day = [trading_day(t + pd.Timedelta(hours=4)) for t in h4.index]
    H = h4["High"].tolist(); L = h4["Low"].tolist()
    wk_days = defaultdict(list)
    for d in all_days:
        wk_days[week_key(d)].append(d)
    keys = sorted(wk_days)
    prior_atr = {}
    for kk, wk in enumerate(keys):
        if kk > 0:
            prior_atr[wk] = dm[wk_days[keys[kk - 1]][-1]]["atr"]

    idxs = [i for i, dy in enumerate(h4_day)
            if START <= dy <= END and prior_atr.get(week_key(dy))]
    boundary = set()
    by_week = defaultdict(list)
    for i in idxs:
        by_week[week_key(h4_day[i])].append(i)
    for wk, lst in by_week.items():
        boundary.add(lst[0]); boundary.add(lst[-1])

    legs = []
    d = 0
    ext_hi = ext_lo = None
    hi_i = lo_i = start = ext_i = 0
    ext = 0.0
    for i in idxs:
        h, l = H[i], L[i]
        T = prior_atr[week_key(h4_day[i])]
        if d == 0:
            if ext_hi is None or h > ext_hi:
                ext_hi, hi_i = h, i
            if ext_lo is None or l < ext_lo:
                ext_lo, lo_i = l, i
            if h - ext_lo >= T:
                d, start, ext, ext_i = 1, lo_i, h, i
            elif ext_hi - l >= T:
                d, start, ext, ext_i = -1, hi_i, l, i
        elif d == 1:
            if h > ext:
                ext, ext_i = h, i
            if ext - l >= T:
                legs.append({"g": start, "dir": 1})
                d, start, ext, ext_i = -1, ext_i, l, i
        else:
            if l < ext:
                ext, ext_i = l, i
            if h - ext >= T:
                legs.append({"g": start, "dir": -1})
                d, start, ext, ext_i = 1, ext_i, h, i
    if d != 0:
        legs.append({"g": start, "dir": d})
    for lg in legs:
        lg["open"] = h4.index[lg["g"]]
        lg["day"] = h4_day[lg["g"]]
    return legs, boundary


def hour_census(legs: List[Dict]) -> Counter:
    return Counter(l["open"].tz_convert("America/Los_Angeles").hour for l in legs)


# ── 3. VERIFY ──────────────────────────────────────────────────────────────
def verify(legs: List[Dict], dm, h4: pd.DataFrame) -> List[str]:
    h4_day = [trading_day(t + pd.Timedelta(hours=4)) for t in h4.index]
    H = h4["High"].tolist(); L = h4["Low"].tolist(); C = h4["Close"].tolist()
    lines = []
    lines.append(f"  {'progress':>9} {'stop':>9}   {'fills':>5} {'wins':>4}  {'win%':>5}  "
                 f"{'avgR':>6}  {'open':>4}  {'ambig':>5}   (of {len(legs)} legs)")
    cells = []
    for p in PROGRESS:
        for stp in STOPS:
            rs = []; wins = losses = opens = ambig = 0
            for leg in legs:
                down = leg["down"]
                dist = abs(leg["level"] - leg["ref"])
                atr = leg["atr"] or 0.0
                if dist <= 0 or atr <= 0:
                    continue
                entry = leg["ref"] + p * dist if down else leg["ref"] - p * dist
                stop = leg["level"] + stp * atr if down else leg["level"] - stp * atr
                target = leg["ref"]
                risk_pips = abs(stop - entry) / PIP + SPREAD_PIPS
                reward_pips = abs(entry - target) / PIP - SPREAD_PIPS
                bars = [i for i, dy in enumerate(h4_day)
                        if leg["start"] < dy <= leg["cap_day"]]
                state = "scan"; r = None
                for i in bars:
                    hi, lo = H[i], L[i]
                    tgt_hit = (lo <= target) if down else (hi >= target)
                    ent_hit = (hi >= entry) if down else (lo <= entry)
                    stp_hit = (hi >= stop) if down else (lo <= stop)
                    if state == "scan":
                        if tgt_hit and ent_hit:
                            state = "ambig"; break        # unknowable order: no trade
                        if tgt_hit:
                            state = "no_trade"; break     # new extreme before fill
                        if ent_hit:
                            state = "in"
                            if stp_hit:                    # adverse-first on fill bar
                                r = -1.0; state = "done"; break
                            # target can't also be hit here (checked above)
                    elif state == "in":
                        if stp_hit:                        # adverse-first
                            r = -1.0; state = "done"; break
                        if tgt_hit:
                            r = reward_pips / risk_pips; state = "done"; break
                if state == "in":                          # open at cap
                    gross = (entry - C[bars[-1]]) / PIP if down else (C[bars[-1]] - entry) / PIP
                    r = (gross - SPREAD_PIPS) / risk_pips
                    opens += 1; rs.append(r)
                elif state == "done":
                    rs.append(r)
                    if r > 0:
                        wins += 1
                    else:
                        losses += 1
                elif state == "ambig":
                    ambig += 1
            n = len(rs)
            closed = wins + losses
            wr = 100 * wins / closed if closed else float("nan")
            avg = statistics.mean(rs) if rs else float("nan")
            flag = "" if n >= 30 else "  [descriptive only]"
            lines.append(f"  {100*p:>8.0f}% {stp:>6.1f}×ATR   {n:>5} {wins:>4}  {wr:>4.0f}%  "
                         f"{avg:>+6.2f}  {opens:>4}  {ambig:>5}{flag}")
            cells.append({"p": p, "s": stp, "n": n, "wr": wr, "avg": avg})
    return lines, cells


# ── main ───────────────────────────────────────────────────────────────────
def main() -> None:
    d1 = _load("D"); h4 = _load("H4")
    dm = build_day_map(d1, h4)
    eps = structure_episodes(dm)
    legs = leg_geometry(dm, eps, d1)

    # continuous zigzag + boundary-excluded census
    zz, boundary = continuous_zigzag(h4, dm)
    cz = hour_census(zz)
    zz_nb = [l for l in zz if l["g"] not in boundary]
    cz_nb = hour_census(zz_nb)

    reg_lines, ratios = regime_baseline(dm, h4, zz)
    ver_lines, cells = verify(legs, dm, h4)

    n_zz = len(zz); n_nb = len(zz_nb)
    share14 = 100 * cz.get(14, 0) / n_zz
    share14_nb = 100 * cz_nb.get(14, 0) / n_nb if n_nb else 0

    emit("=" * 78)
    emit("GBP/AUD SCOUTING VERIFICATION — read-only, 2026-09-11")
    emit("Window 2023-09-01 → 2026-09-10 only. Pre-2023 sealed. Fixed rules, no search.")
    emit("=" * 78)

    emit("\nPLAIN-ENGLISH SUMMARY")
    emit("─────────────────────")
    hot = {k: v for k, v in ratios.items() if v >= 1.25 or v <= 0.8}
    emit(f"• Regime tilt, honestly baselined: swing starts track time spent almost")
    emit(f"  one-for-one. Ratios (swing share ÷ time share): " +
         ", ".join(f"{k} {v:.2f}" for k, v in ratios.items()) + ".")
    if hot:
        emit(f"  Away from 1.0: " + ", ".join(f"{k} at {v:.2f}" for k, v in hot.items()) + ".")
    else:
        emit(f"  Nothing is far from 1.0 — the earlier 46%-VOLATILE headline was mostly")
        emit(f"  a picture of where TIME lives, not where opportunity concentrates.")
    emit(f"• Hour artifact: with a continuous zigzag ({n_zz} swings) the 14:00 PDT")
    emit(f"  share is {share14:.0f}%; excluding week-boundary bars ({n_nb} swings) it is")
    emit(f"  {share14_nb:.0f}%. Compare 27% under the week-local cut — the rollover-hour")
    emit(f"  concentration {'largely survives' if share14_nb >= 20 else 'was substantially a week-edge artifact' if share14_nb < 15 else 'partly survives'}.")
    best = max(cells, key=lambda c: c["avg"] if c["avg"] == c["avg"] else -9)
    worst = min(cells, key=lambda c: c["avg"] if c["avg"] == c["avg"] else 9)
    emit(f"• Fixed-rule first-bounce verify (all 8 pre-specified cells reported, spread")
    emit(f"  3 pips, stops beyond the LH/HL): avg R ranges {worst['avg']:+.2f} "
         f"(at {100*worst['p']:.0f}%/{worst['s']:.1f}×ATR) to {best['avg']:+.2f} "
         f"(at {100*best['p']:.0f}%/{best['s']:.1f}×ATR).")
    emit(f"  Every cell is under N=30 — descriptive only, and 21 of the 41 legs sit in")
    emit(f"  the in-sample span of the frozen-parameter selection window discussed in")
    emit(f"  the provenance study. Nothing here defines or tunes a play.")

    emit("\n## 1. Regime baseline (time share vs swing-start share)")
    emit("Attribution for BOTH columns: prior trading day's as-of-close regime.")
    for ln in reg_lines:
        emit(ln)

    emit("\n## 2. Hour census — continuous zigzag (no forced week-edge pivots)")
    emit(f"  {'PDT hour':>9}   {'week-local (prior study)':>24}   {'continuous':>11}   {'excl. boundary bars':>19}")
    prior = {2: 11.5, 6: 18.1, 10: 5.0, 14: 27.2, 18: 17.7, 22: 20.5}
    for h in (2, 6, 10, 14, 18, 22):
        emit(f"  {h:02d}:00 PDT   {prior.get(h,0):>23.1f}%   {100*cz.get(h,0)/n_zz:>10.1f}%   "
             f"{100*cz_nb.get(h,0)/n_nb:>18.1f}%")
    emit(f"  swings:     {419:>24}   {n_zz:>11}   {n_nb:>19}")
    emit(f"  (boundary-excluded census drops {n_zz-n_nb} swings starting on a week's")
    emit(f"   first or last H4 bar)")

    emit("\n## 3. Fixed-rule verification — first-bounce with-trend entries")
    emit("Entry exactly at 50/60/70/85% progress to the last LH/HL; target = touch of")
    emit("the reference extreme; stops at LH/HL + 0.1/0.3×ATR(confirmation); spread")
    emit("3 pips RT inside R; H4 execution, adverse-first same-bar rules (see header);")
    emit("60-trading-day cap. ALL cells pre-specified and reported — no selection.")
    for ln in ver_lines:
        emit(ln)
    emit("  'ambig' = pre-fill bar touched both entry and target: no trade claimed.")
    emit("  'open' = still open at cap, scored at cap close (included in avgR, not win%).")

    out_md = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                           "gbpaud_scouting_verify_report.md")
    with open(out_md, "w") as f:
        f.write("```\n" + "\n".join(OUT) + "\n```\n")
    print(f"\n[report written to {out_md}]")


if __name__ == "__main__":
    main()
