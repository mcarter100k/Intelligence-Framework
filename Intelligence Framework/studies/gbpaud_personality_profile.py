# PRIOR-SESSION ARTIFACT: committed 2026-10-18 for citation integrity (foundation/ cites it).
# Committed exactly as found; NOT re-verified against current code.
"""
gbpaud_personality_profile.py
─────────────────────────────────────────────────────────────────────────────
READ-ONLY STUDY — GBP/AUD 3-year personality profile (2023-09-01 → 2026-09-10).

Commissioned 2026-09-11. studies/ only: no protected modules touched, no
ledger writes, no parameter tuning. Companion report:
studies/gbpaud_personality_profile_report.md

Sections
  0. PRECONDITION — compute_atr_series alignment verified (len = n-14,
     atr[-1] IS the last bar; by-index reads use off = len(C)-len(atr)).
     Asserted at runtime below; the study aborts if it ever fails.
  1. DATA — OANDA GBP_AUD D1 + H4 (+H1 for hour-of-day), cached CSVs in
     studies/data_cache/ (refetched with paged from/to requests if absent).
  2. SEGMENTS — Sep–Sep years, calendar years, D1 structure episodes
     (existing structure engine _detect_structure, live-parity trailing
     220-bar windows, as-of-day-close, no lookahead into later bars).
  3. DESCRIPTION per segment — net change/high/low, median D1 ATR, composite
     regime-cell shares, confirmed D1 trend legs, % time ranging, overshoot
     distribution beyond prior confirmed swing extremes, share of daily
     range by PDT hour, release reactions (day-0 vs day-3).
  4. FROZEN PLAY TEST — THRUST_PULLBACK exactly as frozen 2026-07-29 in
     shadow_signals.py (no parameter touched), walk-forward at H4 cadence,
     non-overlapping episodes, graded by the live grading rule (HORIZON=30
     H4 bars, r=-1.0 on stop hit else net/risk), loss species via the live
     _classify_loss. NO REFITTING — the spec is executed, not searched.
  5. Honest N — every grouped result carries its N; N<30 is labeled
     "descriptive only".

Definitions the numbers depend on (stated once, used everywhere):
  trading day   : NY-close convention. A timestamp belongs to trading day D
                  if its America/New_York time is ≤ 17:00 on D, else D+1.
                  OANDA candles are NY-17:00 aligned, so each D1 bar maps to
                  exactly one weekday label.
  day-level regime cell : (D1 regime, H4 regime) via regime_detection
                  _classify_ex with live-parity inputs — D1: trailing 220
                  closed D1 bars through that day's close; H4: trailing 120
                  closed H4 bars through that day's close. ADX/ATR-ratio/
                  structure/slope derived exactly as get_regime() derives
                  them. Descriptive as-of-close labels (a day is described
                  by data that includes its own close — description, not
                  prediction).
  trend leg     : maximal run of consecutive days whose as-of-close D1
                  structure label is UPTREND (or DOWNTREND). Net pips =
                  close(last day) − close(day before the run), signed with
                  the leg direction.
  overshoot event : first breach of the latest CONFIRMED D1 swing high/low,
                  where "latest confirmed" is taken from the structure
                  engine as of the PRIOR day's close (no lookahead).
                  Overshoot = max excursion beyond the level over days
                  t..t+4, in pips. "Failed ≤3d" = a daily close back inside
                  the level on day t, t+1 or t+2.
  release day-0 : the D1 bar whose trading day equals the release's
                  calendar date (all releases studied here print between
                  00:30 and 15:00 UTC — inside that trading day).
                  retention = (close(d+3) − close(d-1)) / (close(d0) −
                  close(d-1)). EXTENDED ≥ 1.0, HELD 0.5–1.0, ROUND-TRIP
                  < 0.5 (includes reversals).
"""
from __future__ import annotations

import os as _os, sys as _sys  # studies path bootstrap (root + shadow)
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _p in (_ROOT, _os.path.join(_ROOT, "shadow")):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

import math
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd

from regime_detection import (
    PAIRS, _classify_ex, _compute_adx, _detect_structure,
    compute_atr_series, get_composite_regime,
)
from shadow_signals import (
    HORIZON, check_thrust_pullback, _classify_loss,
)

PAIR   = PAIRS["GBP_AUD"]
PIP    = PAIR.pip_size
CACHE  = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data_cache")
START  = date(2023, 9, 1)
END    = date(2026, 9, 10)

OUT_LINES: List[str] = []
def emit(s: str = "") -> None:
    print(s)
    OUT_LINES.append(s)


# ── 0. PRECONDITION ─────────────────────────────────────────────────────────
def verify_atr_alignment() -> None:
    import random
    rnd = random.Random(7)
    n = 300
    C = [1.9]; H = [1.905]; L = [1.895]
    for _ in range(n - 1):
        c = C[-1] + rnd.uniform(-0.01, 0.01)
        C.append(c); H.append(c + rnd.uniform(0, .008)); L.append(c - rnd.uniform(0, .008))
    atr = compute_atr_series(H, L, C)
    assert len(atr) == n - 14, "ATR length contract broken"
    # independent Wilder re-derivation of the LAST bar's ATR
    tr = [max(H[i]-L[i], abs(H[i]-C[i-1]), abs(L[i]-C[i-1])) for i in range(1, n)]
    a = sum(tr[:14]) / 14
    for t in tr[14:]:
        a = (a * 13 + t) / 14
    assert abs(atr[-1] - a) < 1e-12, "atr[-1] is not the last bar's ATR"
    # no lookahead: truncation must not change earlier values
    atr2 = compute_atr_series(H[:-5], L[:-5], C[:-5])
    assert all(abs(x - y) < 1e-12 for x, y in zip(atr2, atr)), "lookahead"
    emit("PRECONDITION PASS — compute_atr_series returns len(C)-14 values; "
         "atr[-1] maps to the LAST bar; by-index reads use "
         "atr[b - (len(C)-len(atr))] (off=14), matching _atr_at in "
         "shadow_signals.py. No lookahead contamination.")


# ── 1. DATA ─────────────────────────────────────────────────────────────────
def _load(gran: str) -> pd.DataFrame:
    path = _os.path.join(CACHE, f"gbpaud_{gran}.csv")
    if not _os.path.exists(path):
        _refetch(gran, path)
    df = pd.read_csv(path, parse_dates=["time"], index_col="time")
    return df.sort_index()


def _refetch(gran: str, path: str) -> None:
    """Paged from/to fetch, parsing identical to oanda_feed._get_bars."""
    import time as _time
    import requests
    from oanda_feed import _base_url, _headers
    starts = {"D": "2022-06-01T00:00:00Z", "H4": "2023-05-01T00:00:00Z",
              "H1": "2023-08-25T00:00:00Z"}
    end = "2026-09-11T00:00:00Z"
    url = f"{_base_url()}/v3/instruments/GBP_AUD/candles"
    import requests
    rows, frm = [], starts[gran]
    while True:
        r = requests.get(url, headers=_headers(), timeout=30, params={
            "granularity": gran, "price": "M", "from": frm, "count": 5000})
        r.raise_for_status()
        candles = r.json().get("candles", [])
        new = 0
        for c in candles:
            if not c.get("complete", True):
                continue
            if rows and c["time"] <= rows[-1]["time"]:
                continue
            if c["time"] > end:
                break
            m = c["mid"]
            rows.append({"time": c["time"], "Open": float(m["o"]),
                         "High": float(m["h"]), "Low": float(m["l"]),
                         "Close": float(m["c"]), "Volume": int(c.get("volume", 0))})
            new += 1
        if not candles or new == 0 or rows[-1]["time"] >= end:
            break
        frm = rows[-1]["time"]
        _time.sleep(0.3)
    df = pd.DataFrame(rows)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df.set_index("time").sort_index().to_csv(path)


def trading_day(ts: pd.Timestamp) -> date:
    ny = ts.tz_convert("America/New_York")
    d = ny.date()
    if (ny.hour, ny.minute) > (17, 0):
        d = d + timedelta(days=1)
    return d


# ── 2/3. Day map: per-day live-parity classification ────────────────────────
D1_WIN, H4_WIN = 220, 120   # live parity: get_regime uses 220 D1 / 120 H4

def _tf_regime(h: List[float], l: List[float], c: List[float]) -> Tuple[str, str, Dict, float, float]:
    """(regime, subtype, structure_dict, adx, atr_ratio) — derivation copied
    from get_regime(): atr_ratio = last ATR / mean of last 20 ATR values,
    slope +1/-1 from structure else 10-bar close delta."""
    adx = _compute_adx(h, l, c)
    atr_s = compute_atr_series(h, l, c)
    avg20 = sum(atr_s[-20:]) / min(20, len(atr_s))
    atr_ratio = round(atr_s[-1] / avg20, 2) if avg20 > 0 else 1.0
    sd = _detect_structure(h, l, c)
    st = sd["structure"]
    if st == "UPTREND":
        slope = 1.0
    elif st == "DOWNTREND":
        slope = -1.0
    else:
        slope = c[-1] - c[-11] if len(c) >= 11 else 0.0
    regime, subtype = _classify_ex(adx, atr_ratio, slope, instrument="GBP_AUD",
                                   pair=PAIR, structure=st)
    return regime, subtype, sd, adx, atr_ratio


def build_day_map(d1: pd.DataFrame, h4: pd.DataFrame) -> Dict[date, Dict]:
    d1 = d1.copy()
    d1["day"] = [trading_day(t + pd.Timedelta(hours=24)) for t in d1.index]  # close ts
    h4_days = [trading_day(t + pd.Timedelta(hours=4)) for t in h4.index]
    d1H = d1["High"].tolist(); d1L = d1["Low"].tolist(); d1C = d1["Close"].tolist()
    days = d1["day"].tolist()
    h4H = h4["High"].tolist(); h4L = h4["Low"].tolist(); h4C = h4["Close"].tolist()

    # full-history aligned ATR for the daily ATR description
    atr_full = compute_atr_series(d1H, d1L, d1C)
    off = len(d1C) - len(atr_full)

    # index of last H4 bar belonging to each day (h4_days is monotone)
    last_h4_idx: Dict[date, int] = {}
    for i, dy in enumerate(h4_days):
        last_h4_idx[dy] = i

    out: Dict[date, Dict] = {}
    h4_keys = sorted(last_h4_idx)
    for i, dy in enumerate(days):
        if dy < START or dy > END or i < D1_WIN - 1:
            continue
        lo = i - D1_WIN + 1
        d1r, d1sub, d1sd, d1adx, _ = _tf_regime(d1H[lo:i+1], d1L[lo:i+1], d1C[lo:i+1])
        # latest H4 bar at or before this day's close
        j = None
        if dy in last_h4_idx:
            j = last_h4_idx[dy]
        else:  # D1 day with no H4 rows (shouldn't happen) — nearest prior day
            import bisect
            k = bisect.bisect_right(h4_keys, dy) - 1
            j = last_h4_idx[h4_keys[k]] if k >= 0 else None
        h4r = "UNAVAILABLE"; h4sub = ""
        if j is not None and j >= H4_WIN - 1:
            h4r, h4sub, _, _, _ = _tf_regime(h4H[j-H4_WIN+1:j+1],
                                             h4L[j-H4_WIN+1:j+1],
                                             h4C[j-H4_WIN+1:j+1])
        comp = get_composite_regime(d1r, h4r)
        out[dy] = {
            "i": i, "open": d1["Open"].iloc[i], "high": d1H[i], "low": d1L[i],
            "close": d1C[i], "prev_close": d1C[i-1],
            "atr": atr_full[i - off] if i >= off else None,
            "d1_regime": d1r, "d1_subtype": d1sub, "h4_regime": h4r,
            "structure": d1sd["structure"],
            "latest_sh": d1sd["latest_sh"], "latest_sl": d1sd["latest_sl"],
            "composite": comp["composite"], "exec_mode": comp["execution_mode"],
        }
    return out


# ── Segments ────────────────────────────────────────────────────────────────
def year_segments() -> List[Tuple[str, date, date]]:
    return [
        ("SepY1 2023-09→2024-08", date(2023, 9, 1),  date(2024, 8, 31)),
        ("SepY2 2024-09→2025-08", date(2024, 9, 1),  date(2025, 8, 31)),
        ("SepY3 2025-09→2026-09-10", date(2025, 9, 1), END),
    ]

def calendar_segments() -> List[Tuple[str, date, date]]:
    return [
        ("Cal2023 (Sep–Dec, partial)", date(2023, 9, 1), date(2023, 12, 31)),
        ("Cal2024",                    date(2024, 1, 1), date(2024, 12, 31)),
        ("Cal2025",                    date(2025, 1, 1), date(2025, 12, 31)),
        ("Cal2026 (→Sep 10, partial)", date(2026, 1, 1), END),
    ]


def structure_episodes(day_map: Dict[date, Dict]) -> List[Dict]:
    eps = []
    cur = None
    for dy in sorted(day_map):
        st = day_map[dy]["structure"]
        if cur is None or st != cur["label"]:
            if cur:
                eps.append(cur)
            cur = {"label": st, "start": dy, "end": dy, "days": [dy]}
        else:
            cur["end"] = dy; cur["days"].append(dy)
    if cur:
        eps.append(cur)
    for e in eps:
        first, last = e["days"][0], e["days"][-1]
        e["n_days"] = len(e["days"])
        base = day_map[first]["prev_close"]
        e["net_pips"] = (day_map[last]["close"] - base) / PIP
        e["hi"] = max(day_map[d]["high"] for d in e["days"])
        e["lo"] = min(day_map[d]["low"] for d in e["days"])
    return eps


# ── 3. Descriptive blocks ───────────────────────────────────────────────────
def seg_days(day_map, a: date, b: date) -> List[date]:
    return [d for d in sorted(day_map) if a <= d <= b]

def _n_note(n: int) -> str:
    return f"N={n}" + ("" if n >= 30 else "  [descriptive only]")

def describe_segment(name: str, day_map, days: List[date], eps: List[Dict],
                     h1_shares: Dict[date, Dict[int, float]]) -> None:
    if not days:
        emit(f"\n### {name} — no days in range"); return
    first, last = days[0], days[-1]
    dm = day_map
    net = (dm[last]["close"] - dm[first]["prev_close"]) / PIP
    hi = max(dm[d]["high"] for d in days); lo = min(dm[d]["low"] for d in days)
    atrs = [dm[d]["atr"] / PIP for d in days if dm[d]["atr"]]
    emit(f"\n### {name}  ({first} → {last}, {_n_note(len(days))} trading days)")
    emit(f"- Net change: {net:+.0f} pips  (close {dm[first]['prev_close']:.4f} → {dm[last]['close']:.4f})")
    emit(f"- High {hi:.4f} / Low {lo:.4f}  (range {(hi-lo)/PIP:.0f} pips)")
    emit(f"- Median D1 ATR(14): {statistics.median(atrs):.0f} pips "
         f"(p25 {statistics.quantiles(atrs, n=4)[0]:.0f} / p75 {statistics.quantiles(atrs, n=4)[2]:.0f})")

    # composite regime cells
    cells = Counter((dm[d]["d1_regime"], dm[d]["h4_regime"]) for d in days)
    emit(f"- Regime cells (D1,H4), % of days ({_n_note(len(days))}):")
    for (c1, c4), n in cells.most_common():
        emit(f"    {c1:>13} / {c4:<13} {100*n/len(days):5.1f}%  (n={n})")
    rangy = sum(1 for d in days if dm[d]["d1_regime"] == "RANGING")
    trans = sum(1 for d in days if dm[d]["structure"] == "TRANSITIONAL")
    emit(f"- % days D1 regime RANGING: {100*rangy/len(days):.1f}%   "
         f"% days D1 structure TRANSITIONAL: {100*trans/len(days):.1f}%")

    # trend legs intersecting segment (counted if leg START is inside)
    legs = [e for e in eps if e["label"] in ("UPTREND", "DOWNTREND")
            and first <= e["start"] <= last]
    if legs:
        ln = [e["n_days"] for e in legs]
        pips = [e["net_pips"] if e["label"] == "UPTREND" else -e["net_pips"] for e in legs]
        emit(f"- Confirmed D1 trend legs starting in segment ({_n_note(len(legs))}): "
             f"{sum(1 for e in legs if e['label']=='UPTREND')} up / "
             f"{sum(1 for e in legs if e['label']=='DOWNTREND')} down")
        emit(f"    length days: median {statistics.median(ln):.0f} "
             f"(min {min(ln)}, max {max(ln)})   with-trend net pips: median "
             f"{statistics.median(pips):+.0f} (min {min(pips):+.0f}, max {max(pips):+.0f})")
    else:
        emit("- Confirmed D1 trend legs: none started in segment")

    # overshoot events
    ovs = overshoot_events(dm, days)
    if ovs:
        o = [x["overshoot_pips"] for x in ovs]
        fails = sum(1 for x in ovs if x["failed_3d"])
        q = statistics.quantiles(o, n=4) if len(o) >= 4 else [min(o), statistics.median(o), max(o)]
        emit(f"- Overshoot beyond prior confirmed swing extreme ({_n_note(len(ovs))} events): "
             f"median {statistics.median(o):.0f} pips (p25 {q[0]:.0f} / p75 {q[2]:.0f}, "
             f"max {max(o):.0f}); closed back inside ≤3 days: {100*fails/len(ovs):.0f}%")
    else:
        emit("- Overshoot events: none")

    # hour-of-day range share (PDT)
    shares = defaultdict(list)
    for d in days:
        if d in h1_shares:
            for h, s in h1_shares[d].items():
                shares[h].append(s)
    if shares:
        avg = {h: 100 * statistics.mean(v) for h, v in shares.items()}
        top = sorted(avg.items(), key=lambda kv: -kv[1])[:5]
        emit("- Share of daily range by PDT hour (avg % of summed H1 ranges; top 5): "
             + ", ".join(f"{h:02d}:00 {p:.1f}%" for h, p in top))
        emit("    full 24h profile: "
             + " ".join(f"{h:02d}h={avg.get(h,0):.1f}" for h in range(24)))


def overshoot_events(dm: Dict[date, Dict], days: List[date]) -> List[Dict]:
    """First breach of the latest confirmed swing extreme known as of the
    PRIOR day's close; overshoot measured over days t..t+4."""
    all_days = sorted(dm)
    idx = {d: k for k, d in enumerate(all_days)}
    out = []
    last_hi_level = last_lo_level = None
    for d in days:
        k = idx[d]
        if k == 0:
            continue
        prev = dm[all_days[k-1]]
        for side, level in (("high", prev["latest_sh"]), ("low", prev["latest_sl"])):
            if level is None:
                continue
            breached = dm[d]["high"] > level if side == "high" else dm[d]["low"] < level
            already = (level == last_hi_level) if side == "high" else (level == last_lo_level)
            if not breached or already:
                continue
            if side == "high":
                last_hi_level = level
            else:
                last_lo_level = level
            fwd = all_days[k:k+5]
            if side == "high":
                over = max(dm[x]["high"] for x in fwd) - level
            else:
                over = level - min(dm[x]["low"] for x in fwd)
            f3 = all_days[k:k+3]
            failed = any((dm[x]["close"] < level) if side == "high"
                         else (dm[x]["close"] > level) for x in f3)
            out.append({"day": d, "side": side, "level": level,
                        "overshoot_pips": over / PIP, "failed_3d": failed})
    return out


def build_h1_shares(h1: pd.DataFrame) -> Dict[date, Dict[int, float]]:
    """Per trading day: fraction of the day's summed H1 true ranges landing
    in each PDT (America/Los_Angeles) clock hour of the bar's open."""
    days = [trading_day(t + pd.Timedelta(hours=1)) for t in h1.index]
    hours = [t.tz_convert("America/Los_Angeles").hour for t in h1.index]
    rng = (h1["High"] - h1["Low"]).tolist()
    per_day: Dict[date, Dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for d, h, r in zip(days, hours, rng):
        per_day[d][h] += r
    out = {}
    for d, hh in per_day.items():
        tot = sum(hh.values())
        if tot > 0:
            out[d] = {h: v / tot for h, v in hh.items()}
    return out


# ── Release calendar ────────────────────────────────────────────────────────
def release_calendar() -> List[Tuple[str, date, str]]:
    """(event_type, calendar/trading date, source_confidence).
    verified = fetched from the publishing institution 2026-09-11.
    known    = well-established published schedule (from analyst memory).
    rule     = generated from the release's standing schedule rule."""
    ev: List[Tuple[str, date, str]] = []

    rba = {  # 14:30 Sydney announcement
        "known": ["2023-09-05", "2023-10-03", "2023-11-07", "2023-12-05",
                  "2024-02-06", "2024-03-19", "2024-05-07", "2024-06-18",
                  "2024-08-06", "2024-09-24", "2024-11-05", "2024-12-10",
                  "2025-02-18", "2025-04-01", "2025-05-20", "2025-07-08",
                  "2025-08-12", "2025-09-30", "2025-11-04", "2025-12-09"],
        "verified": ["2026-02-03", "2026-03-17", "2026-05-05", "2026-06-16",
                     "2026-08-11"],
    }
    boe = {  # 12:00 London
        "known": ["2023-09-21", "2023-11-02", "2023-12-14",
                  "2024-02-01", "2024-03-21", "2024-05-09", "2024-06-20",
                  "2024-08-01", "2024-09-19", "2024-11-07", "2024-12-19",
                  "2025-02-06", "2025-03-20", "2025-05-08", "2025-06-19",
                  "2025-08-07", "2025-09-18", "2025-11-06", "2025-12-18"],
        "verified": ["2026-02-05", "2026-03-19", "2026-04-30", "2026-06-18",
                     "2026-07-30"],
    }
    au_cpi_q = {  # 11:30 Sydney, quarterly (monthly indicator excluded — see report)
        "known": ["2023-10-25", "2024-01-31", "2024-04-24", "2024-07-31",
                  "2024-10-30", "2025-01-29", "2025-04-30", "2025-07-30",
                  "2025-10-29"],
        "rule": ["2026-01-28", "2026-04-29", "2026-07-29"],
    }
    us_cpi = {  # 08:30 ET — verified from BLS archive (incl. 2025 shutdown gap)
        "verified": ["2023-09-13", "2023-10-12", "2023-11-14", "2023-12-12",
                     "2024-01-11", "2024-02-13", "2024-03-12", "2024-04-10",
                     "2024-05-15", "2024-06-12", "2024-07-11", "2024-08-14",
                     "2024-09-11", "2024-10-10", "2024-11-13", "2024-12-11",
                     "2025-01-15", "2025-02-12", "2025-03-12", "2025-04-10",
                     "2025-05-13", "2025-06-11", "2025-07-15", "2025-08-12",
                     "2025-09-11", "2025-10-24", "2025-12-18",
                     "2026-01-13", "2026-02-13", "2026-03-11", "2026-04-10",
                     "2026-05-12", "2026-06-10", "2026-07-14", "2026-08-12"],
    }
    nfp = {  # 08:30 ET — verified from BLS archive/schedule
        "verified": ["2023-09-01", "2023-10-06", "2023-11-03", "2023-12-08",
                     "2024-01-05", "2024-02-02", "2024-03-08", "2024-04-05",
                     "2024-05-03", "2024-06-07", "2024-07-05", "2024-08-02",
                     "2024-09-06", "2024-10-04", "2024-11-01", "2024-12-06",
                     "2025-01-10", "2025-02-07", "2025-03-07", "2025-04-04",
                     "2025-05-02", "2025-06-06", "2025-07-03", "2025-08-01",
                     "2025-09-05", "2025-11-20", "2025-12-16",
                     "2026-01-09", "2026-02-11", "2026-03-06", "2026-04-03",
                     "2026-05-08", "2026-06-05", "2026-07-02", "2026-08-07",
                     "2026-09-04"],
    }
    uk_cpi = {"rule": _uk_cpi_rule_dates()}          # Wednesday, day 14–20
    ism = {"rule": _ism_rule_dates()}                # first US business day

    for name, d in (("RBA", rba), ("BoE", boe), ("AU_CPI_q", au_cpi_q),
                    ("US_CPI", us_cpi), ("NFP", nfp), ("UK_CPI", uk_cpi),
                    ("US_ISM_mfg", ism)):
        for conf, dates in d.items():
            for s in dates:
                dd = s if isinstance(s, date) else datetime.strptime(s, "%Y-%m-%d").date()
                if START <= dd <= END:
                    ev.append((name, dd, conf))
    return ev


def _uk_cpi_rule_dates() -> List[date]:
    out = []
    d = date(2023, 9, 1)
    while d <= END:
        for day in range(14, 21):
            x = date(d.year, d.month, day)
            if x.weekday() == 2:               # Wednesday
                out.append(x); break
        d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return out


def _ism_rule_dates() -> List[date]:
    out = []
    d = date(2023, 9, 1)
    while d <= END:
        x = date(d.year, d.month, 1)
        while x.weekday() >= 5 or (x.month, x.day) in ((1, 1), (7, 4)) or \
              (x.month == 9 and x.weekday() == 0 and x.day <= 7):  # Labor Day
            x += timedelta(days=1)
        out.append(x)
        d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
    return out


def release_reactions(day_map, events) -> List[Dict]:
    all_days = sorted(day_map)
    idx = {d: k for k, d in enumerate(all_days)}
    out = []
    for name, d0, conf in events:
        if d0 not in idx:
            continue
        k = idx[d0]
        if k + 3 >= len(all_days):
            continue
        dm0 = day_map[d0]
        base = dm0["prev_close"]
        move0 = dm0["close"] - base
        if abs(move0) < 1e-9:
            continue
        d3 = all_days[k + 3]
        ret = (day_map[d3]["close"] - base) / move0
        cls = "EXTENDED" if ret >= 1.0 else ("HELD" if ret >= 0.5 else "ROUND_TRIP")
        out.append({"event": name, "day": d0, "conf": conf,
                    "move0_pips": move0 / PIP, "range0_pips": (dm0["high"]-dm0["low"])/PIP,
                    "retention": ret, "class": cls})
    return out


def emit_release_table(reactions: List[Dict], day_map, segs) -> None:
    emit("\n## Release reactions (day-0 close-to-close vs day-3 retention)")
    emit("Classes: EXTENDED (retention ≥ 1.0), HELD (0.5–1.0), ROUND_TRIP (< 0.5,")
    emit("includes full reversals). Date sources: verified / known / rule — see script.")
    med_rng = statistics.median((day_map[d]["high"]-day_map[d]["low"])/PIP for d in day_map)
    emit(f"(median D1 range over full window: {med_rng:.0f} pips)")
    for ev in ("RBA", "BoE", "AU_CPI_q", "UK_CPI", "US_CPI", "NFP", "US_ISM_mfg"):
        rs = [r for r in reactions if r["event"] == ev]
        if not rs:
            continue
        c = Counter(r["class"] for r in rs)
        m0 = statistics.median(abs(r["move0_pips"]) for r in rs)
        rg = statistics.median(r["range0_pips"] for r in rs)
        emit(f"- {ev:<10} {_n_note(len(rs)):<26} |move0| med {m0:>4.0f} pips, "
             f"day-0 range med {rg:>4.0f} pips  →  "
             f"EXT {100*c['EXTENDED']/len(rs):3.0f}%  HELD {100*c['HELD']/len(rs):3.0f}%  "
             f"RT {100*c['ROUND_TRIP']/len(rs):3.0f}%")
        for nm, a, b in segs:
            ss = [r for r in rs if a <= r["day"] <= b]
            if ss:
                cc = Counter(r["class"] for r in ss)
                emit(f"      {nm[:26]:<28} {_n_note(len(ss)):<24} "
                     f"EXT {cc['EXTENDED']:>2} HELD {cc['HELD']:>2} RT {cc['ROUND_TRIP']:>2}")


# ── 4. FROZEN PLAY: THRUST_PULLBACK walk-forward ────────────────────────────
CTX_BARS = 300   # live parity: _load_ctx fetches count=300 H4 bars

def walk_forward_tp(h4: pd.DataFrame, day_map: Dict[date, Dict]) -> Tuple[List[Dict], int]:
    H = h4["High"].tolist(); L = h4["Low"].tolist()
    C = h4["Close"].tolist(); O = h4["Open"].tolist()
    T = list(h4.index)
    bar_day = [trading_day(t + pd.Timedelta(hours=4)) for t in T]
    all_days = sorted(day_map)
    day_pos = {d: k for k, d in enumerate(all_days)}

    def prev_day_cell(dy: date) -> Tuple[str, str]:
        k = day_pos.get(dy)
        if k is None:
            older = [d for d in all_days if d < dy]
            if not older:
                return ("?", "?")
            p = older[-1]
        elif k == 0:
            return ("?", "?")
        else:
            p = all_days[k-1]
        return (day_map[p]["d1_regime"], day_map[p]["h4_regime"])

    episodes: List[Dict] = []
    raw_fires = 0
    busy_until = -1
    start_i = next(i for i, d in enumerate(bar_day) if d >= START)
    start_i = max(start_i, CTX_BARS - 1)
    for i in range(start_i, len(C)):
        if bar_day[i] > END:
            break
        lo = i - CTX_BARS + 1
        w = slice(lo, i + 1)
        ctx = {"O": O[w], "H": H[w], "L": L[w], "C": C[w], "T": T[w],
               "atr": compute_atr_series(H[w], L[w], C[w]), "pip": PIP,
               "adx": 0.0, "adx_slope": 0.0, "struct": "", "sd": {}}
        sig = check_thrust_pullback("GBP_AUD", ctx)
        if not sig:
            continue
        raw_fires += 1
        if i <= busy_until:
            continue                      # same opportunity window — one episode
        busy_until = i + HORIZON
        # grade exactly like grade_pending_shadow
        entry = C[i]; stop = float(sig["stop"]); direction = sig["direction"]
        risk = abs(entry - stop) or 1e-9
        graded = i + HORIZON < len(C)
        rec = {"i": i, "time": T[i], "day": bar_day[i], "direction": direction,
               "entry": entry, "stop": stop, "graded": graded,
               "cell": prev_day_cell(bar_day[i])}
        if graded:
            fut_h = H[i+1:i+1+HORIZON]; fut_l = L[i+1:i+1+HORIZON]
            exit_c = C[i+HORIZON]
            if direction == "LONG":
                mfe = max(fut_h) - entry; mae = entry - min(fut_l)
                hit = min(fut_l) <= stop; net = exit_c - entry
            else:
                mfe = entry - min(fut_l); mae = max(fut_h) - entry
                hit = max(fut_h) >= stop; net = entry - exit_c
            r = -1.0 if hit else round(net / risk, 2)
            species = ""
            if r < 0:
                atr_fire = ctx["atr"][-1]
                species = _classify_loss(direction, entry, stop, risk, "",
                                         hit, mfe, fut_h, fut_l, i, C, atr_fire)
            rec.update({"hit": hit, "r": r, "mfe_pips": mfe / PIP,
                        "mae_pips": mae / PIP, "net_pips": net / PIP,
                        "loss_species": species})
        episodes.append(rec)
    return episodes, raw_fires


def emit_tp_results(episodes: List[Dict], raw_fires: int, segs) -> None:
    emit("\n## Frozen play walk-forward — THRUST_PULLBACK (spec frozen 2026-07-29)")
    emit("Executed byte-identical to shadow_signals.py (TP_BOX_N=18, TP_BOX_X=3.0,")
    emit("TP_BODY_ATR=1.0, TP_PULLBACK_ATR=0.25, TP_PULLBACK_BARS=10, HORIZON=30 H4")
    emit("bars, stop = far box edge, r=-1.0 on stop touch else net/risk at horizon).")
    emit("Walk-forward at every closed H4 bar over a trailing 300-bar window (live")
    emit("_load_ctx shape). Episodes are non-overlapping: after a fire, further")
    emit("fires inside its 30-bar horizon are the same opportunity, not counted.")
    emit(f"Raw bar-level fires: {raw_fires}.  Episodes: {len(episodes)} "
         f"({sum(1 for e in episodes if not e['graded'])} still inside horizon, ungraded).")
    graded = [e for e in episodes if e["graded"]]

    def block(label: str, rows: List[Dict]) -> None:
        if not rows:
            emit(f"  {label:<30} no episodes"); return
        rs = [e["r"] for e in rows]
        wins = sum(1 for r in rs if r > 0)
        eq = mdd = peak = 0.0
        for r in rs:
            eq += r; peak = max(peak, eq); mdd = max(mdd, peak - eq)
        hits = sum(1 for e in rows if e["hit"])
        noise = sum(1 for e in rows if e.get("loss_species") == "stopped_then_reversed")
        emit(f"  {label:<30} {_n_note(len(rows)):<26} win {100*wins/len(rs):3.0f}%  "
             f"avgR {statistics.mean(rs):+.2f}  medR {statistics.median(rs):+.2f}  "
             f"maxDD {mdd:.1f}R  stops hit {hits} (noise-stops {noise})")

    block("ALL (graded)", graded)
    for nm, a, b in segs:
        block(nm, [e for e in graded if a <= e["day"] <= b])
    emit("  — by direction —")
    for d in ("LONG", "SHORT"):
        block(d, [e for e in graded if e["direction"] == d])
    emit("  — by regime cell at fire (D1,H4 as of prior day close) —")
    cells = Counter(e["cell"] for e in graded)
    for cell, _ in cells.most_common():
        block(f"{cell[0]}/{cell[1]}", [e for e in graded if e["cell"] == cell])
    emit("  — loss species (graded losers) —")
    sp = Counter(e.get("loss_species") for e in graded if e["r"] < 0)
    for s, n in sp.most_common():
        emit(f"    {s or '(unclassified)'}: {n}")
    emit("\n  Episode list (graded):")
    for e in graded:
        emit(f"    {e['time'].strftime('%Y-%m-%d %H:%M')}Z {e['direction']:<5} "
             f"entry {e['entry']:.4f} stop {e['stop']:.4f} "
             f"r {e['r']:+.2f} {'STOP' if e['hit'] else '    '} "
             f"mfe {e['mfe_pips']:>5.0f} mae {e['mae_pips']:>5.0f} "
             f"cell {e['cell'][0]}/{e['cell'][1]} {e.get('loss_species','')}")


# ── main ────────────────────────────────────────────────────────────────────
def main() -> None:
    emit("=" * 78)
    emit("GBP/AUD 3-YEAR PERSONALITY PROFILE — read-only study, 2026-09-11")
    emit("Window: 2023-09-01 → 2026-09-10 (trading days, NY-close convention; "
         "clock times reported in PDT)")
    emit("=" * 78)

    emit("\n## 0. Precondition")
    verify_atr_alignment()

    emit("\n## 1. Data")
    d1 = _load("D"); h4 = _load("H4"); h1 = _load("H1")
    d1_days = [trading_day(t + pd.Timedelta(hours=24)) for t in d1.index]
    in_win = [d for d in d1_days if START <= d <= END]
    weekdays = set()
    d = START
    while d <= END:
        if d.weekday() < 5:
            weekdays.add(d)
        d += timedelta(days=1)
    missing = sorted(weekdays - set(in_win))
    h4_days = [trading_day(t + pd.Timedelta(hours=4)) for t in h4.index]
    h4_in = [x for x in h4_days if START <= x <= END]
    h1_days = [trading_day(t + pd.Timedelta(hours=1)) for t in h1.index]
    h1_in = [x for x in h1_days if START <= x <= END]
    emit(f"- D1: {len(in_win)} trading days in window "
         f"(full fetch {len(d1)} bars from {d1.index[0].date()} for the 220-bar warm-up)")
    emit(f"- Missing weekdays vs Mon–Fri calendar: {len(missing)} — "
         + (", ".join(str(x) for x in missing) if len(missing) <= 20 else "first 20: "
            + ", ".join(str(x) for x in missing[:20])))
    emit(f"- H4: {len(h4_in)} bars in window (fetch {len(h4)} from {h4.index[0].date()}; "
         f"expected ≈6/trading day → {len(h4_in)/max(1,len(in_win)):.2f}/day)")
    h4_counts = Counter(h4_in)
    short_days = sorted(d for d, n in h4_counts.items() if n < 5)
    emit(f"- H4 days with <5 bars: {len(short_days)}"
         + (f" — {', '.join(str(x) for x in short_days[:15])}" if short_days else ""))
    emit(f"- H1: {len(h1_in)} bars in window ({len(h1_in)/max(1,len(in_win)):.1f}/day; "
         f"24 expected on full days)")

    emit("\n## 2. Day map (live-parity per-day classification)")
    day_map = build_day_map(d1, h4)
    emit(f"- Classified {len(day_map)} trading days with trailing 220-bar D1 / "
         f"120-bar H4 windows (get_regime derivation, as-of-day-close).")
    eps = structure_episodes(day_map)
    emit(f"- D1 structure episodes: {len(eps)} "
         f"({sum(1 for e in eps if e['label']=='UPTREND')} up, "
         f"{sum(1 for e in eps if e['label']=='DOWNTREND')} down, "
         f"{sum(1 for e in eps if e['label']=='TRANSITIONAL')} transitional)")

    h1_shares = build_h1_shares(h1)

    emit("\n" + "=" * 78)
    emit("## 3a. Sep–Sep year segments")
    for nm, a, b in year_segments():
        describe_segment(nm, day_map, seg_days(day_map, a, b), eps, h1_shares)

    emit("\n" + "=" * 78)
    emit("## 3b. Calendar-year segments")
    for nm, a, b in calendar_segments():
        describe_segment(nm, day_map, seg_days(day_map, a, b), eps, h1_shares)

    emit("\n" + "=" * 78)
    emit("## 3c. D1 structure episodes (grouped by label; every episode ≥5 days listed)")
    for label in ("UPTREND", "DOWNTREND", "TRANSITIONAL"):
        grp = [e for e in eps if e["label"] == label]
        if not grp:
            continue
        ln = [e["n_days"] for e in grp]
        np_ = [e["net_pips"] for e in grp]
        emit(f"\n### {label} episodes ({_n_note(len(grp))})")
        emit(f"- length days: median {statistics.median(ln):.0f} (min {min(ln)}, max {max(ln)})"
             f"   net pips: median {statistics.median(np_):+.0f}")
        for e in grp:
            if e["n_days"] >= 5:
                emit(f"    {e['start']} → {e['end']}  {e['n_days']:>3}d  "
                     f"net {e['net_pips']:+6.0f} pips  hi {e['hi']:.4f} lo {e['lo']:.4f}")

    emit("\n" + "=" * 78)
    reactions = release_reactions(day_map, release_calendar())
    emit_release_table(reactions, day_map, year_segments())

    emit("\n" + "=" * 78)
    episodes, raw = walk_forward_tp(h4, day_map)
    emit_tp_results(episodes, raw, year_segments())

    emit("\n" + "=" * 78)
    emit("Caveats (honesty section)")
    emit("- Day-level regime cells are as-of-day-close descriptions; play-test cell")
    emit("  attribution uses the PRIOR day's D1 regime + prior-close H4 regime (no peek).")
    emit("- UK_CPI and US_ISM_mfg dates are rule-derived (Wednesday 14th–20th / first")
    emit("  business day); RBA/BoE 2023-25 and AU quarterly CPI are known published")
    emit("  schedules; US CPI/NFP and all 2026 CB dates verified from the institutions")
    emit("  on 2026-09-11. AU monthly CPI indicator is EXCLUDED (dates not verifiable")
    emit("  here in bulk; quarterly print is the dominant mover).")
    emit("- Walk-forward evaluates the frozen check at every closed H4 bar; the live")
    emit("  harness samples it at brief cadence, so live would catch a subset of these")
    emit("  episodes. Spec parameters and grading are byte-identical to the shadow path.")
    emit("- OANDA mid prices; no spread/slippage. Shadow-ledger convention retained.")

    out_md = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                           "gbpaud_personality_profile_report.md")
    with open(out_md, "w") as f:
        f.write("```\n" + "\n".join(OUT_LINES) + "\n```\n")
    print(f"\n[report written to {out_md}]")


if __name__ == "__main__":
    main()
