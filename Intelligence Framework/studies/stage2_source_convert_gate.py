"""
stage2_source_convert_gate.py
─────────────────────────────────────────────────────────────────────────────
STAGE 2 of docs/specs/data_map_spec.md (commits f5eea4f + 67578e5).
Source → convert → feed-overlap check → conversion gate.
OUTPUT: verification numbers ONLY. No price statistics, no performance
figures. STUDY bars are opened here solely for conversion + gate counts.

SOURCING RECORD (2026-09-11):
  - datafeed.dukascopy.com (the raw bi5 feed): HTTP 503 then connection
    timeouts from this network — unreachable at Stage-2 time.
  - HistData.com (named fallback): site reachable, but /get.php returns
    0 bytes for every dataset; the form token is served EMPTY even to a
    fully-rendered headless Chrome DOM — the public download flow is
    non-functional programmatically at Stage-2 time.
  - freeserv.dukascopy.com chart feed (SAME NAMED PROVIDER, Dukascopy,
    public charting endpoint): serving. Hourly candles, bid and ask sides,
    rows = [t_ms, open, high, low, close, volume]. This is the transport
    used; provider identity per spec §2 is unchanged (Dukascopy).

CONVERSION: Dukascopy H1 (UTC-stamped opens) → modern convention:
  trading day = NY-close labeling (open hour ≥ 17:00 America/New_York →
  next calendar day), D1 = aggregate of the day's H1 bars, H4 = aggregates
  of slots ((NY_hour − 17) mod 24) // 4 (opens 17/21/01/05/09/13 NY —
  byte-compatible with the OANDA alignment used everywhere in this repo).
  Mid = (bid + ask) / 2 per field, matching OANDA's price=M.

Requests are paced (12s) — freeserv throttles bursts. All raw pulls cached
under studies/data_cache/freeserv/ so re-runs are idempotent.
"""
from __future__ import annotations

import os as _os, sys as _sys
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _p in (_ROOT, _os.path.join(_ROOT, "shadow")):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

import json
import random
import statistics
import time
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import pandas as pd
import requests

HERE   = _os.path.dirname(_os.path.abspath(__file__))
CACHE  = _os.path.join(HERE, "data_cache")
FCACHE = _os.path.join(CACHE, "freeserv")
_os.makedirs(FCACHE, exist_ok=True)

NY = ZoneInfo("America/New_York")
FREESERV = "https://freeserv.dukascopy.com/2.0/index.php"
PACING_S = 12
PAIRS_FS = {"GBP_AUD": "GBP/AUD", "GBP_JPY": "GBP/JPY"}
PIP = {"GBP_AUD": 0.0001, "GBP_JPY": 0.01}

OUT: List[str] = []
def emit(s: str = "") -> None:
    print(s, flush=True); OUT.append(s)


# ── freeserv paged fetch ────────────────────────────────────────────────────
def fs_fetch_page(instr: str, side: str, end_ms: int, limit: int = 5000) -> List[List[float]]:
    params = {
        "path": "chart/json3", "instrument": instr, "offer_side": side,
        "interval": "1HOUR", "splits": "true", "stocks": "false",
        "init": "false", "time_direction": "P", "timestamp": str(end_ms),
        "limit": str(limit), "jsonp": "_cb",
    }
    for attempt in range(3):
        try:
            r = requests.get(FREESERV, params=params, timeout=90,
                             headers={"User-Agent": "Mozilla/5.0",
                                      "Referer": "https://www.dukascopy.com/"})
            s = r.text
            rows = json.loads(s[s.index("(") + 1:s.rindex(")")])
            return rows
        except Exception:
            time.sleep(60 * (attempt + 1))
    raise RuntimeError(f"freeserv fetch failed: {instr} {side} @{end_ms}")


def fs_fetch_range(pair: str, side: str, start: datetime, end: datetime,
                   tag: str) -> pd.DataFrame:
    """Page backward from end to start; cache as CSV."""
    path = _os.path.join(FCACHE, f"{pair}_{side}_{tag}.csv")
    if _os.path.exists(path):
        return pd.read_csv(path, parse_dates=["time"], index_col="time")
    instr = PAIRS_FS[pair]
    end_ms = int(end.timestamp() * 1000)
    start_ms = int(start.timestamp() * 1000)
    all_rows: Dict[int, List[float]] = {}
    cursor = end_ms
    while True:
        rows = fs_fetch_page(instr, side, cursor)
        rows = [r for r in rows if r[0] < cursor]
        if not rows:
            break
        for r in rows:
            if r[0] >= start_ms:
                all_rows[int(r[0])] = r
        oldest = min(r[0] for r in rows)
        if oldest <= start_ms:
            break
        cursor = int(oldest)
        time.sleep(PACING_S)
    ts = sorted(all_rows)
    df = pd.DataFrame(
        [{"time": pd.Timestamp(t, unit="ms", tz="UTC"),
          "Open": all_rows[t][1], "High": all_rows[t][2],
          "Low": all_rows[t][3], "Close": all_rows[t][4]} for t in ts]
    )
    if not df.empty:
        df = df.set_index("time")
    df.to_csv(path)
    time.sleep(PACING_S)
    return df


def fs_fetch_mid(pair: str, start: datetime, end: datetime, tag: str) -> pd.DataFrame:
    b = fs_fetch_range(pair, "B", start, end, tag)
    a = fs_fetch_range(pair, "A", start, end, tag)
    j = b.join(a, lsuffix="_b", rsuffix="_a", how="inner")
    mid = pd.DataFrame(index=j.index)
    for f in ("Open", "High", "Low", "Close"):
        mid[f] = (j[f + "_b"] + j[f + "_a"]) / 2.0
    return mid


# ── H1 → trading day / H4 slot aggregation ─────────────────────────────────
def _label(open_ts: pd.Timestamp) -> Tuple[date, int]:
    ny = open_ts.tz_convert(NY)
    d = ny.date()
    if ny.hour >= 17:
        d = d + timedelta(days=1)
    slot = ((ny.hour - 17) % 24) // 4
    return d, slot


def aggregate(h1: pd.DataFrame) -> Tuple[Dict[date, List[float]], Dict[Tuple[date, int], List[float]]]:
    """Returns D1[day] = [O,H,L,C,n_h1] and H4[(day,slot)] = [O,H,L,C,n_h1]."""
    d1: Dict[date, List[float]] = {}
    h4: Dict[Tuple[date, int], List[float]] = {}
    for ts, row in zip(h1.index, h1.itertuples(index=False)):
        day, slot = _label(ts)
        o, h, l, c = row.Open, row.High, row.Low, row.Close
        for key, store in ((day, d1), ((day, slot), h4)):
            cur = store.get(key)
            if cur is None:
                store[key] = [o, h, l, c, 1]
            else:
                cur[1] = max(cur[1], h); cur[2] = min(cur[2], l)
                cur[3] = c; cur[4] += 1
    return d1, h4


# ── OANDA reference (overlap window) ────────────────────────────────────────
def oanda_ref(pair: str) -> Tuple[Dict[date, List[float]], Dict[Tuple[date, int], List[float]]]:
    """OANDA D1/H4 for the overlap window, keyed identically."""
    if pair == "GBP_AUD":
        d1 = pd.read_csv(_os.path.join(CACHE, "gbpaud_D.csv"),
                         parse_dates=["time"], index_col="time")
        h4 = pd.read_csv(_os.path.join(CACHE, "gbpaud_H4.csv"),
                         parse_dates=["time"], index_col="time")
    else:
        d1 = pd.read_csv(_os.path.join(CACHE, "gbpjpy_D_overlap.csv"),
                         parse_dates=["time"], index_col="time")
        h4 = pd.read_csv(_os.path.join(CACHE, "gbpjpy_H4_overlap.csv"),
                         parse_dates=["time"], index_col="time")
    d1_out: Dict[date, List[float]] = {}
    for ts, r in zip(d1.index, d1.itertuples(index=False)):
        day, _ = _label(ts)           # D1 open 17:00 NY → labeled next day ✓
        d1_out[day] = [r.Open, r.High, r.Low, r.Close]
    h4_out: Dict[Tuple[date, int], List[float]] = {}
    for ts, r in zip(h4.index, h4.itertuples(index=False)):
        h4_out[_label(ts)] = [r.Open, r.High, r.Low, r.Close]
    return d1_out, h4_out


OVL_START = date(2023, 9, 1)
OVL_END   = date(2026, 9, 10)

def overlap_check(pair: str, fs_d1, fs_h4) -> bool:
    oa_d1, oa_h4 = oanda_ref(pair)
    pip = PIP[pair]
    ok = True
    for tf, fs_map, oa_map in (("D1", fs_d1, oa_d1), ("H4", fs_h4, oa_h4)):
        keys = sorted(set(fs_map) & set(oa_map))
        keys = [k for k in keys
                if OVL_START <= (k if isinstance(k, date) else k[0]) <= OVL_END]
        only_oa = sum(1 for k in oa_map if k not in fs_map and
                      OVL_START <= (k if isinstance(k, date) else k[0]) <= OVL_END)
        diffs = {f: [] for f in range(4)}
        disagree = 0
        for k in keys:
            worst = 0.0
            for f in range(4):
                d = abs(fs_map[k][f] - oa_map[k][f]) / pip
                diffs[f].append(d); worst = max(worst, d)
            if worst > 5.0:
                disagree += 1
        med = {f: statistics.median(diffs[f]) for f in range(4)}
        p95 = {f: sorted(diffs[f])[int(0.95 * (len(diffs[f]) - 1))] for f in range(4)}
        rate = 100 * disagree / len(keys) if keys else float("nan")
        names = ["O", "H", "L", "C"]
        emit(f"  {pair} {tf}: {len(keys)} matched bars ({only_oa} OANDA-only missing from feed)")
        emit("      median |diff| pips  " + "  ".join(f"{names[f]}={med[f]:.2f}" for f in range(4)))
        emit("      p95    |diff| pips  " + "  ".join(f"{names[f]}={p95[f]:.2f}" for f in range(4)))
        emit(f"      disagreement rate (any field > 5 pips): {rate:.2f}%")
        if not (rate <= 2.0 and med[3] <= 1.5):
            ok = False
    return ok


# ── conversion gate (STUDY span) ────────────────────────────────────────────
SPOT_CHECKS = {  # date → pair whose converted range must be elevated (≥2× its year median is NOT
                 # computed — sign check = range > a fixed floor in pips, existence only per spec)
    date(2008, 10, 24): ("GBP_JPY", 400),
    date(2010, 5, 6):   ("GBP_JPY", 200),
    date(2011, 3, 17):  ("GBP_JPY", 200),
    date(2013, 4, 4):   ("GBP_JPY", 200),
}

def conversion_gate(pair: str, d1_map, h4_map, first_day: date, y1: int) -> bool:
    """Full calendar years only carry pass/fail; a partial first year is
    reported and excluded from the verdict (spec §2 coverage rule)."""
    y0 = first_day.year if (first_day.month, first_day.day) == (1, 1) else first_day.year + 1
    if first_day.year < y0:
        part = [d for d in d1_map if d.year == first_day.year]
        emit(f"\n  {pair} — first covered trading day {min(d1_map)} → year "
             f"{first_day.year} is PARTIAL ({len(part)} days), excluded from the verdict")
    emit(f"\n  {pair} — conversion gate, full years {y0}–{y1}")
    emit(f"    year  D1_bars  in[252,262]  6barDays%  shortDays  consistency50")
    rnd = random.Random(11)
    all_pass = True
    for y in range(y0, y1 + 1):
        days = sorted(d for d in d1_map if d.year == y)
        n_d1 = len(days)
        per_day = defaultdict(int)
        for (d, s) in h4_map:
            if d.year == y:
                per_day[d] += 1
        six = sum(1 for d in days if per_day.get(d, 0) == 6)
        pct6 = 100 * six / n_d1 if n_d1 else 0.0
        short = [d for d in days if per_day.get(d, 0) < 6]
        sample = rnd.sample(days, min(50, n_d1)) if n_d1 else []
        bad = 0
        for d in sample:
            hs = [h4_map[(d, s)] for s in range(6) if (d, s) in h4_map]
            if not hs:
                bad += 1; continue
            if abs(d1_map[d][1] - max(h[1] for h in hs)) > 0.5 * PIP[pair] or \
               abs(d1_map[d][2] - min(h[2] for h in hs)) > 0.5 * PIP[pair]:
                bad += 1
        count_ok = 252 <= n_d1 <= 262
        reg_ok = pct6 >= 99.0
        cons_ok = bad == 0
        all_pass = all_pass and count_ok and reg_ok and cons_ok
        emit(f"    {y}  {n_d1:7d}  {'PASS' if count_ok else 'FAIL':>11}  "
             f"{pct6:8.1f}%  {len(short):9d}  {'PASS' if cons_ok else f'FAIL({bad})':>13}")
        if short and len(short) <= 6:
            emit(f"          short days: {', '.join(str(x) for x in short)}")
    # spot checks
    for d, (p, floor_pips) in SPOT_CHECKS.items():
        if p != pair or not (y0 <= d.year <= y1):
            continue
        if d not in d1_map:
            emit(f"    spot {d}: MISSING — FAIL"); all_pass = False; continue
        rng = (d1_map[d][1] - d1_map[d][2]) / PIP[pair]
        okd = rng >= floor_pips
        emit(f"    spot {d}: present, range {'≥' if okd else '<'} {floor_pips} pips floor "
             f"— {'PASS' if okd else 'FAIL'}")
        all_pass = all_pass and okd
    return all_pass


# ── main ────────────────────────────────────────────────────────────────────
def main() -> None:
    study_start = date.fromisoformat(_os.environ.get("STUDY_START", "2005-01-01"))
    emit("=" * 78)
    emit("STAGE 2 — source, convert, gate (verification numbers only)")
    emit(f"STUDY span in force: {study_start} → 2013-12-31 (spec §2 coverage rule)")
    emit("=" * 78)

    ovl_s = datetime(2023, 8, 31, tzinfo=timezone.utc)
    ovl_e = datetime(2026, 9, 11, tzinfo=timezone.utc)
    stu_s = datetime.combine(study_start - timedelta(days=3), datetime.min.time(),
                             tzinfo=timezone.utc)
    stu_e = datetime(2014, 1, 3, tzinfo=timezone.utc)

    phase = _os.environ.get("PHASE", "all")   # overlap | coverage | all

    emit("\n## Feed-overlap check (2023-09-01 → 2026-09-10, Dukascopy-freeserv mid vs OANDA mid)")
    overlap_ok = True
    for pair in ("GBP_AUD", "GBP_JPY"):
        h1 = fs_fetch_mid(pair, ovl_s, ovl_e, "overlap")
        emit(f"  [{pair}: {len(h1)} H1 mid bars fetched for overlap]")
        d1, h4 = aggregate(h1)
        overlap_ok = overlap_check(pair, d1, h4) and overlap_ok
    emit(f"\n  OVERLAP CHECK: {'PASS' if overlap_ok else 'FAIL'} "
         f"(thresholds: disagreement ≤ 2%, median |close diff| ≤ 1.5 pips)")
    if not overlap_ok:
        emit("  Spec §2 failure ladder applies — stopping before any STUDY conversion.")
        _write(); return
    if phase == "overlap":
        _write(); return

    emit("\n## STUDY sourcing — coverage confirmation" +
         ("" if phase != "coverage" else " (fetch + first/last bar only, NO conversion)"))
    fetched = {}
    for pair in ("GBP_AUD", "GBP_JPY"):
        h1 = fs_fetch_mid(pair, stu_s, stu_e, "study")
        fetched[pair] = h1
        emit(f"  {pair}: {len(h1)} H1 mid bars; first {h1.index[0]}  last {h1.index[-1]}")
    if phase == "coverage":
        _write(); return

    emit("\n## STUDY conversion + gate")
    gate_ok = True
    for pair in ("GBP_AUD", "GBP_JPY"):
        h1 = fetched[pair]
        d1, h4 = aggregate(h1)
        # persist converted bars for Stage 3 (cache, untracked)
        rows = [{"day": d, "Open": v[0], "High": v[1], "Low": v[2],
                 "Close": v[3], "n_h1": v[4]} for d, v in sorted(d1.items())]
        pd.DataFrame(rows).to_csv(
            _os.path.join(FCACHE, f"{pair}_study_D1_converted.csv"), index=False)
        rows = [{"day": d, "slot": s, "Open": v[0], "High": v[1], "Low": v[2],
                 "Close": v[3], "n_h1": v[4]} for (d, s), v in sorted(h4.items())]
        pd.DataFrame(rows).to_csv(
            _os.path.join(FCACHE, f"{pair}_study_H4_converted.csv"), index=False)
        first_day = max(study_start, min(d1)) if d1 else study_start
        gate_ok = conversion_gate(pair, d1, h4, first_day, 2013) and gate_ok

    emit(f"\nGATE: {'PASS' if gate_ok else 'FAIL'}")
    emit("No price statistics were computed. Stage 3 remains gated on the team" )
    emit("reviewing these numbers and the gate outcome being recorded in validation_log.")
    _write()


def _write() -> None:
    out_md = _os.path.join(HERE, "stage2_gate_report.md")
    with open(out_md, "w") as f:
        f.write("```\n" + "\n".join(OUT) + "\n```\n")
    print(f"\n[report written to {out_md}]")


if __name__ == "__main__":
    main()
