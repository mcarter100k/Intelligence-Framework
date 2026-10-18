# PRIOR-SESSION ARTIFACT: committed 2026-10-18 for citation integrity (foundation/ cites it).
# Committed exactly as found; NOT re-verified against current code.
"""
gbpaud_profile_followup.py
─────────────────────────────────────────────────────────────────────────────
READ-ONLY FOLLOW-UP to studies/gbpaud_personality_profile.py (2026-09-11).
studies/ only. No specs, no ledgers, no parameter changes.

Items:
  1. PROVENANCE — which data window set THRUST_PULLBACK's frozen parameters
     (computed from the cached H4 series + structure_engine_study.py facts;
     the sweep ran 2026-07-29 on 4900 H4 bars ending 2026-07-28).
  2. BREAK SPLIT — overshoot beyond first breaches of confirmed D1 swing
     extremes, split failed-≤3d vs held, pips and ×D1 ATR (ATR as of the
     day BEFORE the breach — known at breach time, no peek), p50/75/90.
  3. DOCTRINE ASSUMPTION — after a D1 trend label confirms, race between
     (a) the counter-trend bounce breaching the last confirmed LH/HL and
     (b) a new with-trend extreme beyond the move's reference extreme.
     Reference extreme = extreme low/high between the LH/HL pivot bar and
     the confirmation day. Resolution capped at 60 trading days. Bounce
     depth = adverse excursion from the reference extreme up to resolution,
     ÷ ATR(confirmation day).
  4. TREND LEGS — with-trend pips per Sep-year: mean, total, share from top
     2 legs; confirmation→MFE vs confirmation→label-flip give-back.
  5. RELEASES — retention classes recomputed at day 1 / day 3 / day 5.
     Surprise-sign split: NOT EXECUTABLE — no historical consensus source
     exists in this repo (calendar.csv holds only the current day) and
     3 years × 7 series of consensus figures cannot be verifiably
     reconstructed here. Stated, not faked.
  6. HISTORY — earliest available OANDA GBP_AUD D1/H4 candle (probe only;
     pre-window years remain UNTOUCHED for future out-of-sample testing).
"""
from __future__ import annotations

import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _p in (_ROOT, _os.path.join(_ROOT, "shadow"), _os.path.dirname(_os.path.abspath(__file__))):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

import statistics
from collections import Counter
from datetime import date, timedelta
from typing import Dict, List, Optional

import pandas as pd

from gbpaud_personality_profile import (
    CACHE, END, PIP, START, _load, build_day_map, release_calendar,
    structure_episodes, trading_day, year_segments,
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


# ── 1. PROVENANCE ───────────────────────────────────────────────────────────
def provenance(h4: pd.DataFrame) -> None:
    emit("## 1. Provenance of THRUST_PULLBACK's frozen parameters")
    emit("Selection: studies/structure_engine_study.py v2 grid sweep —")
    emit("  N ∈ {6,8,12,18} × X ∈ {1.5,2.0,2.5,3.0} × thrust ∈ {0.5,0.75,1.0,1.25}×ATR,")
    emit("  3 detector variants; RANGE_ONLY N=18 X=3.0 thrust=1.0 chosen (validation_log")
    emit("  2026-07-29 pivot entry). PB_ZONE=0.25 and PB_WINDOW=10 were FIXED constants")
    emit("  of the sweep (never searched), carried into the frozen spec as")
    emit("  TP_PULLBACK_ATR / TP_PULLBACK_BARS.")
    emit("Run date: 2026-07-29 (commit 5def001 “v2 study run”); data = 4900 H4 bars +")
    emit("  1300 D1 bars ending at the last completed session, 2026-07-28.")
    # exact window from the cached H4 series
    cutoff = pd.Timestamp("2026-07-28T22:00:00Z")
    upto = h4[h4.index < cutoff]
    if len(upto) >= 4900:
        first = upto.index[-4900]
        emit(f"  → selection window ≈ {first.date()} → 2026-07-28 "
             f"(4900 H4 bars, computed from the cached series)")
        sel_start = trading_day(first + pd.Timedelta(hours=4))
    else:
        emit(f"  → cache holds only {len(upto)} bars before the cutoff; window starts "
             f"at/before {upto.index[0].date()}")
        sel_start = trading_day(upto.index[0] + pd.Timedelta(hours=4))
    emit("")
    emit(f"PLAINLY: the profile window 2023-09-01 → 2026-09-10 overlaps the parameter-")
    emit(f"selection window for everything from {max(START, sel_start)} through 2026-07-28.")
    emit("Only 2026-07-29 → 2026-09-10 (~31 trading days) is out-of-sample with respect")
    emit("to parameter selection. Of the 22 walk-forward episodes in the profile study,")
    emit("21 fall inside the selection window (IN-SAMPLE) and 1 (2026-09-02 LONG, −1.0R)")
    emit("is out-of-sample. The profile's play-test numbers therefore measure how the")
    emit("chosen cell behaved on largely the SAME data that chose it — a ceiling, not an")
    emit("estimate of forward edge. The live shadow ledger (N from the 2026-09-10 fix)")
    emit("remains the only honest forward test.")


# ── 2. BREAK SPLIT ─────────────────────────────────────────────────────────
def overshoot_events_x(dm: Dict[date, Dict]) -> List[Dict]:
    """Same event definition as the profile study, plus ×ATR using the ATR of
    the day BEFORE the breach (known at breach time)."""
    all_days = sorted(dm)
    out = []
    last_hi = last_lo = None
    for k, d in enumerate(all_days):
        if k == 0:
            continue
        prev = dm[all_days[k - 1]]
        for side, level in (("high", prev["latest_sh"]), ("low", prev["latest_sl"])):
            if level is None:
                continue
            breached = dm[d]["high"] > level if side == "high" else dm[d]["low"] < level
            already = (level == last_hi) if side == "high" else (level == last_lo)
            if not breached or already:
                continue
            if side == "high":
                last_hi = level
            else:
                last_lo = level
            fwd = all_days[k:k + 5]
            over = (max(dm[x]["high"] for x in fwd) - level) if side == "high" \
                else (level - min(dm[x]["low"] for x in fwd))
            f3 = all_days[k:k + 3]
            failed = any((dm[x]["close"] < level) if side == "high"
                         else (dm[x]["close"] > level) for x in f3)
            atr_prev = prev["atr"]
            out.append({"day": d, "side": side, "pips": over / PIP,
                        "x_atr": (over / atr_prev) if atr_prev else None,
                        "failed_3d": failed})
    return out


def break_split(dm: Dict[date, Dict]) -> None:
    emit("\n## 2. Break split — overshoot beyond confirmed swing extremes,")
    emit("failed (closed back inside ≤3 days) vs held. ATR basis: D1 ATR(14) of the")
    emit("day before the breach.")
    evs = overshoot_events_x(dm)

    def row(label: str, rows: List[Dict]) -> None:
        if not rows:
            emit(f"    {label:<28} no events"); return
        p = [e["pips"] for e in rows]; x = [e["x_atr"] for e in rows]
        emit(f"    {label:<28} {n_note(len(rows)):<24} "
             f"pips p50/p75/p90 {pctl(p,50):4.0f}/{pctl(p,75):4.0f}/{pctl(p,90):4.0f}   "
             f"×ATR {pctl(x,50):.2f}/{pctl(x,75):.2f}/{pctl(x,90):.2f}")

    def block(name: str, rows: List[Dict]) -> None:
        fail = [e for e in rows if e["failed_3d"]]
        held = [e for e in rows if not e["failed_3d"]]
        emit(f"  {name}  ({n_note(len(rows))}; failed {len(fail)} / held {len(held)}"
             f" — {100*len(fail)/len(rows):.0f}% failed)" if rows else f"  {name} — no events")
        row("failed ≤3d", fail)
        row("held", held)
        row("all", rows)

    block("POOLED 2023-09→2026-09", evs)
    for nm, a, b in year_segments():
        block(nm, [e for e in evs if a <= e["day"] <= b])


# ── 3. DOCTRINE ASSUMPTION ─────────────────────────────────────────────────
def doctrine(dm: Dict[date, Dict], eps: List[Dict], d1: pd.DataFrame) -> None:
    emit("\n## 3. Doctrine assumption — does the first counter-trend bounce breach the")
    emit("last confirmed LH (downtrend) / HL (uptrend) before a new with-trend extreme?")
    emit("Race from the confirmation day (label-flip day s): breach of the LH/HL level")
    emit("vs a new extreme beyond the move's reference extreme (extreme between the")
    emit("LH/HL pivot bar and day s). Cap 60 trading days. Bounce depth = adverse")
    emit("excursion from the reference extreme until resolution, ÷ ATR(day s).")

    days_all = [trading_day(t + pd.Timedelta(hours=24)) for t in d1.index]
    H = d1["High"].tolist(); L = d1["Low"].tolist()
    day_idx = {dy: i for i, dy in enumerate(days_all)}

    results = []
    skipped_no_level = skipped_no_pivot = 0
    for e in eps:
        if e["label"] not in ("UPTREND", "DOWNTREND"):
            continue
        s = e["start"]
        info = dm[s]
        down = e["label"] == "DOWNTREND"
        level = info["latest_sh"] if down else info["latest_sl"]   # LH / HL
        if level is None:
            skipped_no_level += 1
            continue
        si = day_idx[s]
        # locate the LH/HL pivot bar (most recent bar before s printing that price)
        piv = None
        for i in range(si - 1, max(si - 120, -1), -1):
            v = H[i] if down else L[i]
            if abs(v - level) < 1e-9:
                piv = i
                break
        if piv is None:
            skipped_no_pivot += 1   # engine's half-partition fallback level
            continue
        ref = min(L[piv:si + 1]) if down else max(H[piv:si + 1])
        outcome, depth = "unresolved", 0.0
        for t in range(si + 1, min(si + 61, len(H))):
            adverse = (H[t] - ref) if down else (ref - L[t])
            depth = max(depth, adverse)
            breach = H[t] > level if down else L[t] < level
            newext = L[t] < ref if down else H[t] > ref
            if breach and newext:
                outcome = "same_day_both"; break
            if breach:
                outcome = "breach_first"; break
            if newext:
                outcome = "new_extreme_first"; break
        atr_s = info["atr"] or 1e-9
        results.append({"start": s, "label": e["label"], "outcome": outcome,
                        "depth_x_atr": depth / atr_s, "day": s})

    c = Counter(r["outcome"] for r in results)
    emit(f"  Legs examined: {len(results)} ({n_note(len(results))}); "
         f"skipped {skipped_no_level} (no confirmed LH/HL), "
         f"{skipped_no_pivot} (level from engine fallback, no real pivot bar)")
    tot = len(results) or 1
    for k in ("new_extreme_first", "breach_first", "same_day_both", "unresolved"):
        emit(f"    {k:<18} {c[k]:>3}  ({100*c[k]/tot:.0f}%)")
    resolved = [r for r in results if r["outcome"] in ("breach_first", "new_extreme_first")]
    if resolved:
        br = sum(1 for r in resolved if r["outcome"] == "breach_first")
        emit(f"  Of resolved races ({n_note(len(resolved))}): bounce breached the LH/HL "
             f"BEFORE a new with-trend extreme in {100*br/len(resolved):.0f}% of legs.")
    d_all = [r["depth_x_atr"] for r in results]
    if d_all:
        emit(f"  Bounce depth ×ATR (all examined, {n_note(len(d_all))}): "
             f"p50 {pctl(d_all,50):.1f} / p75 {pctl(d_all,75):.1f} / p90 {pctl(d_all,90):.1f}")
    for lab in ("UPTREND", "DOWNTREND"):
        sub = [r for r in results if r["label"] == lab]
        if sub:
            cc = Counter(r["outcome"] for r in sub)
            dd = [r["depth_x_atr"] for r in sub]
            emit(f"    {lab:<10} {n_note(len(sub)):<24} breach_first {cc['breach_first']}, "
                 f"new_extreme_first {cc['new_extreme_first']}, other "
                 f"{len(sub)-cc['breach_first']-cc['new_extreme_first']}; "
                 f"depth ×ATR p50 {pctl(dd,50):.1f} / p75 {pctl(dd,75):.1f} / p90 {pctl(dd,90):.1f}")


# ── 4. TREND LEGS ──────────────────────────────────────────────────────────
def trend_legs(dm: Dict[date, Dict], eps: List[Dict]) -> None:
    emit("\n## 4. Trend legs — with-trend pips per Sep-year; concentration; MFE vs flip")
    emit("With-trend net = signed net over the label run. MFE = best extreme during the")
    emit("run vs the confirmation base (prev close before the run's first day).")
    legs = [e for e in eps if e["label"] in ("UPTREND", "DOWNTREND")]
    for e in legs:
        base = dm[e["days"][0]]["prev_close"]
        up = e["label"] == "UPTREND"
        e["wt_net"] = e["net_pips"] if up else -e["net_pips"]
        e["wt_mfe"] = ((e["hi"] - base) if up else (base - e["lo"])) / PIP
    for nm, a, b in year_segments():
        grp = [e for e in legs if a <= e["start"] <= b]
        if not grp:
            emit(f"  {nm}: no legs"); continue
        nets = [e["wt_net"] for e in grp]
        mfes = [e["wt_mfe"] for e in grp]
        top2 = sorted(nets, reverse=True)[:2]
        tot = sum(nets)
        emit(f"  {nm}  ({n_note(len(grp))})")
        emit(f"    with-trend net: total {tot:+.0f} pips, mean {statistics.mean(nets):+.0f}, "
             f"median {statistics.median(nets):+.0f}")
        emit(f"    top-2 legs contribute {sum(top2):+.0f} pips "
             f"(total of all others: {tot-sum(top2):+.0f}) — "
             f"share undefined as % when total ≤ 0; stated in pips")
        emit(f"    confirmation→MFE: total {sum(mfes):+.0f} pips "
             f"(median {statistics.median(mfes):+.0f}) vs confirmation→flip total {tot:+.0f}")
        emit(f"    → give-back from best point to label flip: "
             f"{sum(mfes)-tot:.0f} pips ({100*(sum(mfes)-tot)/max(sum(mfes),1e-9):.0f}% of MFE)")
    nets = [e["wt_net"] for e in legs]; mfes = [e["wt_mfe"] for e in legs]
    emit(f"  POOLED ({n_note(len(legs))}): with-trend net total {sum(nets):+.0f} pips; "
         f"MFE total {sum(mfes):+.0f} pips; give-back {sum(mfes)-sum(nets):.0f} pips "
         f"({100*(sum(mfes)-sum(nets))/sum(mfes):.0f}% of MFE)")


# ── 5. RELEASES at day 1 / 3 / 5 ───────────────────────────────────────────
def releases(dm: Dict[date, Dict]) -> None:
    emit("\n## 5. Release reactions at day 1 / day 3 / day 5")
    emit("retention_k = (close(d+k) − close(d−1)) / (close(d0) − close(d−1));")
    emit("EXT ≥ 1.0, HELD 0.5–1.0, RT < 0.5.")
    all_days = sorted(dm)
    idx = {d: k for k, d in enumerate(all_days)}
    rows = []
    for name, d0, conf in release_calendar():
        k = idx.get(d0)
        if k is None or k + 5 >= len(all_days):
            continue
        base = dm[d0]["prev_close"]
        m0 = dm[d0]["close"] - base
        if abs(m0) < 1e-9:
            continue
        r = {"event": name}
        for kk in (1, 3, 5):
            ret = (dm[all_days[k + kk]]["close"] - base) / m0
            r[f"c{kk}"] = "EXT" if ret >= 1.0 else ("HELD" if ret >= 0.5 else "RT")
        rows.append(r)
    emit(f"  {'event':<11}{'N':>4}   day1 EXT/HELD/RT      day3 EXT/HELD/RT      day5 EXT/HELD/RT")
    for ev in ("RBA", "BoE", "AU_CPI_q", "UK_CPI", "US_CPI", "NFP", "US_ISM_mfg"):
        rs = [r for r in rows if r["event"] == ev]
        if not rs:
            continue
        cells = []
        for kk in (1, 3, 5):
            c = Counter(r[f"c{kk}"] for r in rs)
            cells.append(f"{100*c['EXT']/len(rs):3.0f}/{100*c['HELD']/len(rs):3.0f}/{100*c['RT']/len(rs):3.0f}%")
        flag = "" if len(rs) >= 30 else "  [descriptive only]"
        emit(f"  {ev:<11}{len(rs):>4}   {cells[0]:<21} {cells[1]:<21} {cells[2]}{flag}")
    emit("")
    emit("  Surprise-sign split: NOT EXECUTABLE from this repo. calendar.csv holds only")
    emit("  the current day's rows; there is no historical actual-vs-consensus source,")
    emit("  and 3 years × 7 series of consensus figures cannot be verifiably")
    emit("  reconstructed here. If a consensus export (e.g. investing.com /")
    emit("  ForexFactory CSV) is provided, the split runs on this same code path.")


# ── 6. HISTORY DEPTH (probe only) ──────────────────────────────────────────
def history_probe() -> None:
    emit("\n## 6. OANDA GBP_AUD history depth (probe only — NOT analyzed)")
    try:
        import requests
        from oanda_feed import _base_url, _headers
        for gran in ("D", "H4"):
            r = requests.get(f"{_base_url()}/v3/instruments/GBP_AUD/candles",
                             headers=_headers(), timeout=30,
                             params={"granularity": gran, "price": "M",
                                     "from": "1990-01-01T00:00:00Z", "count": 3})
            r.raise_for_status()
            c = r.json().get("candles", [])
            if c:
                first = c[0]["time"][:10]
                emit(f"  {gran}: earliest candle {first}")
            else:
                emit(f"  {gran}: no candles returned")
    except Exception as exc:
        emit(f"  probe failed: {type(exc).__name__}: {exc}")
    emit("  Pre-2023-09 years remain UNTOUCHED by this and the prior study (only the")
    emit("  warm-up tails back to 2022-06 D1 / 2023-05 H4 were fetched, used solely to")
    emit("  seed trailing windows). They stay reserved as out-of-sample data for any")
    emit("  future frozen spec.")


def main() -> None:
    emit("=" * 78)
    emit("GBP/AUD PROFILE — READ-ONLY FOLLOW-UP, 2026-09-11")
    emit("=" * 78)
    d1 = _load("D"); h4 = _load("H4")
    dm = build_day_map(d1, h4)
    eps = structure_episodes(dm)
    provenance(h4)
    break_split(dm)
    doctrine(dm, eps, d1)
    trend_legs(dm, eps)
    releases(dm)
    history_probe()
    out_md = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                           "gbpaud_profile_followup_report.md")
    with open(out_md, "w") as f:
        f.write("```\n" + "\n".join(OUT) + "\n```\n")
    print(f"\n[report written to {out_md}]")


if __name__ == "__main__":
    main()
