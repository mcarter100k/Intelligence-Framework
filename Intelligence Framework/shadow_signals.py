"""
shadow_signals.py
─────────────────
Shadow-signal harness. Signals are LOGGED, NEVER TRADED. Nothing here is wired
into official_decision's tradeable path — this module only observes and records,
so that forward data can eventually give the first honestly-validated answer.

Why this exists: three historical premises (compression-precedes-moves,
fakeout-then-go, structural-precursor) were all refuted at honest N by 2026-07-29
(see validation_log.md / precursor_study.py). Every road through the PAST is
exhausted. The evidence that remains is FORWARD. So we specify the two-to-three
surviving "join momentum" candidates, freeze them, and log every fire with a
measured outcome — without trading — until N is large enough to judge.

╔══════════════════════════════════════════════════════════════════════════╗
║ SPEC FREEZE — 2026-07-29                                                   ║
║ The parameters below are FROZEN. Once logging begins they MUST NOT change. ║
║ Any change starts a NEW candidate id (e.g. EARLY_MOMENTUM_v2) with a fresh ║
║ log. No mid-stream tuning — that is how in-sample selection sneaks back in.║
║ Review per candidate: FLAG at N=30 graded outcomes; DECISION REVIEW at 60. ║
╚══════════════════════════════════════════════════════════════════════════╝

Candidates:
  EARLY_MOMENTUM_v2 (GBP/JPY only) — join momentum BEFORE ADX confirms.
      v1 RETIRED 2026-09-09 (stale-swing stop on the wrong side of entry —
      unscoreable rows; validation_log 2026-09-09). v2 = identical trigger
      + stop-validity guard, fresh ledger id, frozen 2026-09-09
      (docs/specs/early_momentum_v2_spec.md).
  THRUST_PULLBACK (both pairs)   — join momentum AFTER it proves itself.
  MOMENTUM_JOIN   (both pairs)   — INFORMED PRIOR, from the precursor outlier
                                   profile of 3 moves; expected weakest; logged
                                   to test honestly, not because we believe it.
"""
from __future__ import annotations

import bisect
import csv
import os
import sys
from datetime import datetime, timedelta, timezone
from statistics import mean, median
from typing import Dict, List, Optional

from exclusions import excluder
from ledger_io import append_row, atomic_write_rows, locked, migrate_header

from regime_detection import (
    _detect_structure, _compute_adx, compute_atr_series, PAIRS,
)

# ── FROZEN SPEC (2026-07-29) ────────────────────────────────────────────────────
FLAG_N   = 30      # flag a candidate for attention at this many graded outcomes
REVIEW_N = 60      # decision review at this many
HORIZON  = 30      # H4 bars over which every candidate's outcome is measured

# EARLY_MOMENTUM (GBP/JPY)
EM_ADX_LO, EM_ADX_HI = 18.0, 25.0

# THRUST_PULLBACK (both)
TP_BOX_N         = 18
TP_BOX_X         = 3.0
TP_BODY_ATR      = 1.0
TP_PULLBACK_ATR  = 0.25
TP_PULLBACK_BARS = 10

# MOMENTUM_JOIN (both)  — INFORMED PRIOR, expected weakest
MJ_ADX_MIN       = 30.0
MJ_ADX_SLOPE_MIN = 8.0
MJ_SLOPE_BARS    = 12
MJ_EXTREME_BARS  = 12
MJ_STOP_ATR      = 1.5

LOG_FILE = "shadow_signal_log.csv"
_FIELDS = [
    "candidate_id", "timestamp", "instrument", "direction", "entry", "stop", "atr",
    "adx", "adx_slope", "structure", "extra",
    # outcome (filled later by grade_pending_shadow)
    "outcome_filled", "bars_elapsed", "mfe_pips", "mae_pips",
    "net_30bars_pips", "hit_stop", "r_multiple",
    # loss autopsy (docs/specs/loss_autopsy_spec.md) — which KIND of loss
    # this was; empty for wins and unclassifiable rows. Added 2026-09-09;
    # the logger migrates the header additively on its next write.
    "loss_species",
]


# ── Context load ────────────────────────────────────────────────────────────────
def _load_ctx(instrument: str, count: int = 300) -> Optional[Dict]:
    from oanda_feed import get_h4_bars, is_configured
    if not is_configured():
        return None
    df = get_h4_bars(pair=instrument.replace("_", ""), count=count)
    if df is None or len(df) < 60:
        return None
    O = [float(v) for v in df["Open"].values]
    H = [float(v) for v in df["High"].values]
    L = [float(v) for v in df["Low"].values]
    C = [float(v) for v in df["Close"].values]
    T = list(df.index)
    atr = compute_atr_series(H, L, C)
    adx_now  = _compute_adx(H, L, C)
    adx_prev = _compute_adx(H[:-MJ_SLOPE_BARS], L[:-MJ_SLOPE_BARS], C[:-MJ_SLOPE_BARS]) \
        if len(C) > MJ_SLOPE_BARS + 30 else adx_now
    sd = _detect_structure(H, L, C)
    pip = PAIRS[instrument].pip_size if instrument in PAIRS else 0.0001
    return {
        "O": O, "H": H, "L": L, "C": C, "T": T, "atr": atr, "pip": pip,
        "adx": adx_now, "adx_slope": adx_now - adx_prev,
        "struct": sd["structure"], "sd": sd,
    }


def _sig(cid, instrument, ctx, direction, entry, stop, extra=""):
    return {
        "candidate_id": cid,
        "timestamp":    ctx["T"][-1].strftime("%Y-%m-%dT%H:%M:%SZ"),
        "instrument":   instrument,
        "direction":    direction,
        "entry":        round(entry, 5),
        "stop":         round(stop, 5),
        "atr":          round(ctx["atr"][-1], 5),
        "adx":          round(ctx["adx"], 1),
        "adx_slope":    round(ctx["adx_slope"], 1),
        "structure":    ctx["struct"],
        "extra":        extra,
    }


# ── Candidate 1: EARLY_MOMENTUM_v2 (GBP/JPY only) ───────────────────────────────
# v2 = v1's trigger and parameters byte-for-byte + ONE guard: a swing that
# gives no valid adverse-side stop means NO FIRE (no substitute stop). v1 was
# retired 2026-09-09 for placing that stop on the wrong side of entry
# (docs/specs/early_momentum_v2_spec.md). FROZEN 2026-09-09: any change
# starts EARLY_MOMENTUM_v3.
def check_early_momentum_v2(instrument: str, ctx: Dict) -> Optional[Dict]:
    if "JPY" not in instrument:
        return None
    if not (EM_ADX_LO <= ctx["adx"] < EM_ADX_HI):
        return None
    if ctx["struct"] == "UPTREND":
        direction, swing = "LONG", ctx["sd"].get("latest_sl")
    elif ctx["struct"] == "DOWNTREND":
        direction, swing = "SHORT", ctx["sd"].get("latest_sh")
    else:
        return None
    entry = ctx["C"][-1]
    if swing is None:
        swing = entry - 1.5 * ctx["atr"][-1] if direction == "LONG" \
            else entry + 1.5 * ctx["atr"][-1]
    elif (direction == "SHORT" and swing <= entry) or \
         (direction == "LONG" and swing >= entry):
        return None                        # stale swing, no valid stop — NO FIRE
    return _sig("EARLY_MOMENTUM_v2", instrument, ctx, direction, entry, swing,
                extra=f"adx={ctx['adx']:.1f} in[{EM_ADX_LO:.0f},{EM_ADX_HI:.0f})")


# ── Candidate 2: THRUST_PULLBACK (both) ─────────────────────────────────────────
def check_thrust_pullback(instrument: str, ctx: Dict) -> Optional[Dict]:
    H, L, C, O, atr = ctx["H"], ctx["L"], ctx["C"], ctx["O"], ctx["atr"]
    n = len(C)
    # atr[] is shorter than the bar list (it starts after the ATR period);
    # _atr_at maps a bar index to its ATR. Alignment fix 2026-09-10, no
    # parameter change, so no new candidate id.
    off = n - len(atr)

    def _atr_at(i: int) -> float:
        return atr[i - off]

    for b in range(n - 1 - TP_PULLBACK_BARS, n - 1):       # break bar candidates
        if b - TP_BOX_N < 0 or b - off < 0:
            continue
        box_hi = max(H[b - TP_BOX_N:b]); box_lo = min(L[b - TP_BOX_N:b])
        if (box_hi - box_lo) > TP_BOX_X * _atr_at(b):
            continue                                        # box not tight enough
        body = abs(C[b] - O[b])
        # up-break then pullback then fresh close-back above the edge
        if C[b] > box_hi and body >= TP_BODY_ATR * _atr_at(b):
            edge = box_hi
            pulled = any(L[k] <= edge + TP_PULLBACK_ATR * _atr_at(b) for k in range(b + 1, n))
            if pulled and C[n - 2] <= edge and C[n - 1] > edge:
                return _sig("THRUST_PULLBACK", instrument, ctx, "LONG",
                            C[n - 1], box_lo, extra=f"box[{box_lo:.5f},{box_hi:.5f}]")
        # down-break mirror
        if C[b] < box_lo and body >= TP_BODY_ATR * _atr_at(b):
            edge = box_lo
            pulled = any(H[k] >= edge - TP_PULLBACK_ATR * _atr_at(b) for k in range(b + 1, n))
            if pulled and C[n - 2] >= edge and C[n - 1] < edge:
                return _sig("THRUST_PULLBACK", instrument, ctx, "SHORT",
                            C[n - 1], box_hi, extra=f"box[{box_lo:.5f},{box_hi:.5f}]")
    return None


# ── Candidate 3: MOMENTUM_JOIN (both) — INFORMED PRIOR, expected weakest ────────
def check_momentum_join(instrument: str, ctx: Dict) -> Optional[Dict]:
    if ctx["adx"] < MJ_ADX_MIN or ctx["adx_slope"] < MJ_ADX_SLOPE_MIN:
        return None
    H, L, C, atr = ctx["H"], ctx["L"], ctx["C"], ctx["atr"]
    if ctx["struct"] == "UPTREND":
        direction = "LONG"
        if H[-1] < max(H[-MJ_EXTREME_BARS:]):              # not a new 12-bar high
            return None
        stop = C[-1] - MJ_STOP_ATR * atr[-1]
    elif ctx["struct"] == "DOWNTREND":
        direction = "SHORT"
        if L[-1] > min(L[-MJ_EXTREME_BARS:]):              # not a new 12-bar low
            return None
        stop = C[-1] + MJ_STOP_ATR * atr[-1]
    else:
        return None
    return _sig("MOMENTUM_JOIN", instrument, ctx, direction, C[-1], stop,
                extra=f"adx={ctx['adx']:.1f} slope={ctx['adx_slope']:+.1f} INFORMED_PRIOR")


_CANDIDATES = [check_early_momentum_v2, check_thrust_pullback, check_momentum_join]


def check_shadow_signals(instrument: str, ctx: Optional[Dict] = None) -> List[Dict]:
    """Return the list of candidate signals firing on the last COMPLETE H4 bar."""
    if ctx is None:
        ctx = _load_ctx(instrument)
    if ctx is None:
        return []
    out = []
    for fn in _CANDIDATES:
        try:
            s = fn(instrument, ctx)
        except Exception as exc:
            # A crashing candidate must never read as "no signal": print an
            # ##ALERT## line; the brief wrapper turns it into a health FAILURE
            # that repeats until fixed. Other candidates still run
            # (validation_log 2026-09-10).
            print(f"##ALERT## SHADOW CANDIDATE ERROR — "
                  f"{getattr(fn, '__name__', str(fn))} {instrument}: "
                  f"{type(exc).__name__}: {exc}", file=sys.stderr)
            s = None
        if s:
            out.append(s)

    # Shadow signals are NOT gated by the news gate — candidates must be graded
    # through real news conditions (docs/specs/news_gate_spec.md item 4). We
    # only stamp context so the review can slice by news window later.
    # Candidate specs and triggers untouched — spec-freeze rules apply.
    if out:
        try:
            from news_gate import check_news_gate
            # "pre_release", not "gating": the gate gained a 30-min
            # post-release buffer on 2026-09-30 (decision_logic_spec D5); the
            # frozen stamp keeps its original meaning — an event 0-120 min
            # ahead — so shadow evidence is never pooled across definitions.
            if check_news_gate(instrument).get("pre_release"):
                for s in out:
                    s["extra"] = (f"{s['extra']}|" if s.get("extra") else "") + \
                                 "news_window=true"
        except Exception:
            pass
    return out


# ── Logging (dedup by candidate+instrument+timestamp) ───────────────────────────
def _ensure_file():
    with locked(LOG_FILE):
        if not os.path.exists(LOG_FILE):
            atomic_write_rows(LOG_FILE, _FIELDS, [])
            return
        _migrate_header()


def _migrate_header():
    """One-time additive migration: when the ledger's header predates a
    column appended to _FIELDS (loss_species, 2026-09-09), rewrite the file
    with the current header, every existing row preserved byte-for-byte in
    its old columns and blank in the new ones. Purely additive — this is
    the logger maintaining its own schema, never an edit of recorded
    values. MUST run before any append, or a 19-field row lands under an
    18-column header."""
    migrate_header(LOG_FILE, _FIELDS)          # shared, locked (ledger_io)


def log_shadow_signals(signals: List[Dict]) -> int:
    if not signals:
        return 0
    # One lock across the dedupe read and the append: two runs logging the
    # same fire at once can no longer both pass the dedupe (ledger_io).
    with locked(LOG_FILE):
        _ensure_file()
        seen = set()
        with open(LOG_FILE, newline="") as f:
            for row in csv.DictReader(f):
                seen.add((row["candidate_id"], row["instrument"], row["timestamp"]))
        written = 0
        for s in signals:
            key = (s["candidate_id"], s["instrument"], s["timestamp"])
            if key in seen:
                continue
            row = {k: "" for k in _FIELDS}
            row.update(s)
            row["outcome_filled"] = False
            # append_row writes the header when the file is empty (review
            # R4: a 0-byte ledger got headerless rows through open("a")).
            append_row(LOG_FILE, _FIELDS, row)
            seen.add(key); written += 1
    return written


# ── Validity guard (grading/reporting layer ONLY — ledger rows never edited) ────
def is_invalid_spec(row: Dict) -> bool:
    """True when the row's stop sits on the NON-adverse side of entry
    (SHORT: stop <= entry; LONG: stop >= entry).

    WHY this exists: for such a row the grader's hit test is trivially true at
    entry (SHORT: max(fut_h) >= stop holds the moment stop <= entry), so the
    row is UNSCOREABLE BY CONSTRUCTION — guaranteed -1.0R whatever the market
    does — not merely mislabeled. First graded exhibit: the 2026-07-29/30
    EARLY_MOMENTUM stale-swing rows (validation_log 2026-09-09; v1 retired,
    docs/specs/early_momentum_v2_spec.md). Invalid rows are excluded from all
    tallies, episode counts, and brief displays, and are never scored as R.
    The flag lives here, at read time; the ledger is append-only evidence and
    keeps its rows verbatim."""
    try:
        entry, stop = float(row["entry"]), float(row["stop"])
    except (KeyError, TypeError, ValueError):
        return True                        # unreadable geometry = not scoreable
    if row.get("direction") == "SHORT":
        return stop <= entry
    if row.get("direction") == "LONG":
        return stop >= entry
    return True                            # unknown direction = not scoreable


# ── Tally for the brief ─────────────────────────────────────────────────────────
def get_shadow_tally(candidate_id: str, instrument: Optional[str] = None) -> Dict:
    if not os.path.exists(LOG_FILE):
        return {"logged": 0, "graded": 0, "wins": 0, "avg_net": 0.0,
                "episodes": 0, "episode_rs": []}
    logged = graded = wins = 0
    nets = []
    is_excluded = excluder("shadow_signal_log.csv")
    with open(LOG_FILE, newline="") as f:
        for r in csv.DictReader(f):
            if r["candidate_id"] != candidate_id:
                continue
            if instrument and r["instrument"] != instrument:
                continue
            if is_invalid_spec(r):
                continue                   # unscoreable by construction
            if is_excluded(r):
                continue                   # registry exclusion (exclusions.py)
            logged += 1
            if str(r.get("outcome_filled")) == "True":
                graded += 1
                # Win/loss is the R-multiple: a stop hit is always a loss,
                # whatever price did by bar 30 (validation_log 2026-09-09).
                # net_30bars_pips is kept only as a diagnostic.
                try:
                    if float(r["r_multiple"]) > 0:
                        wins += 1
                except (ValueError, TypeError):
                    pass
                try:
                    nets.append(float(r["net_30bars_pips"]))
                except (ValueError, TypeError):
                    pass
    episode_rs = [float(r["r_multiple"]) for r in graded_episodes(candidate_id, instrument)]
    return {"logged": logged, "graded": graded, "wins": wins,
            "avg_net": round(sum(nets) / len(nets), 1) if nets else 0.0,
            "episodes": len(episode_rs), "episode_rs": episode_rs}


def latest_pending_signal(instrument: str) -> Optional[Dict]:
    """Most recent ungraded shadow signal for the pair (for the brief narrative).
    Returns candidate_id / direction / entry / timestamp, or None."""
    if not os.path.exists(LOG_FILE):
        return None
    latest = None
    is_excluded = excluder("shadow_signal_log.csv")
    with open(LOG_FILE, newline="") as f:
        for r in csv.DictReader(f):
            if r["instrument"] != instrument or str(r.get("outcome_filled")) == "True":
                continue
            if is_invalid_spec(r):
                continue                   # never surfaced to the brief
            if is_excluded(r):
                continue                   # registry exclusion (exclusions.py)
            latest = r                      # append order → last ungraded = newest
    if not latest:
        return None
    try:
        return {"candidate_id": latest["candidate_id"], "direction": latest["direction"],
                "entry": float(latest["entry"]), "stop": float(latest["stop"]),
                "timestamp": latest["timestamp"]}
    except (ValueError, KeyError):
        return None


def _h4_bar_opens(start: datetime, end: datetime) -> List[datetime]:
    """The H4 bar index between two UTC times, built from the trading
    calendar: six bars per trading day from 17:00 New York, OANDA's
    alignment. It matched OANDA's real H4 index bar for bar over 2023-04-30
    to 2026-10-16 on both pairs (docs/specs/shadow_tally_spec.md). No
    network call."""
    from zoneinfo import ZoneInfo
    from regime_detection import is_trading_day
    ny = ZoneInfo("America/New_York")
    day = (start.astimezone(ny) + timedelta(hours=7)).date() - timedelta(days=1)
    last = (end.astimezone(ny) + timedelta(hours=7)).date() + timedelta(days=1)
    opens = []
    while day <= last:
        if is_trading_day(day):
            prev = day - timedelta(days=1)
            first = datetime(prev.year, prev.month, prev.day, 17, 0, tzinfo=ny)
            opens += [(first + timedelta(hours=4 * k)).astimezone(timezone.utc) for k in range(6)]
        day += timedelta(days=1)
    return sorted(t for t in opens if start <= t <= end)


def graded_episodes(candidate_id: str, instrument: Optional[str] = None) -> List[Dict]:
    """Independent episodes, one row each (its first fire, whose R is the
    episode's R). Only graded, valid, non-excluded rows count: an open row
    is not evidence yet (AUDIT §2 #3). Per instrument, a fire starts a new
    episode once it is HORIZON (30) or more H4 bars after the current
    episode's first fire, counted on the bar index, not the clock (M34; the
    same rule as foundation/tools/episodes.py). The old 120-clock-hour rule
    split episodes across weekends and overcounted."""
    if not os.path.exists(LOG_FILE):
        return []
    from collections import defaultdict
    is_excluded = excluder("shadow_signal_log.csv")
    by_inst = defaultdict(list)
    with open(LOG_FILE, newline="") as f:
        for r in csv.DictReader(f):
            if r["candidate_id"] != candidate_id or (instrument and r["instrument"] != instrument):
                continue
            if str(r.get("outcome_filled")) != "True" or is_invalid_spec(r) or is_excluded(r):
                continue
            try:
                t = datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00"))
                float(r["r_multiple"])
            except (ValueError, TypeError, KeyError):
                continue
            by_inst[r["instrument"]].append((t, r))
    episodes = []
    for fires in by_inst.values():
        fires.sort(key=lambda x: x[0])
        opens = _h4_bar_opens(fires[0][0], fires[-1][0])
        start = None
        for t, r in fires:
            bar = bisect.bisect_right(opens, t) - 1
            if start is None or bar - start >= HORIZON:
                start = bar
                episodes.append(r)
    return sorted(episodes, key=lambda r: r["timestamp"])


# ── Loss autopsy (docs/specs/loss_autopsy_spec.md) ──────────────────────────────
# Species, frozen 2026-09-09, first match wins. Classified only for R-losing
# rows that pass the invalid_spec guard. Triggers untouched.
LOSS_SPECIES = ("event_window", "stopped_then_reversed", "exhaustion_entry",
                "never_onside", "bled_out")
_STR_REVERSAL_R  = 2.0    # post-stop run beyond entry, in R
_EXHAUST_ATR     = 2.0    # entry this many fire-time ATR beyond the 20-bar mean
_EXHAUST_MEAN_N  = 20
_NEVER_ONSIDE_R  = 0.25   # MFE below this = wrong from the first bar


def _classify_loss(direction: str, entry: float, stop: float, risk: float,
                   extra: str, hit: bool, mfe_price: float,
                   fut_h: List[float], fut_l: List[float],
                   ei: int, C: List[float], atr_at_fire: float) -> str:
    """Species of one graded LOSING row. Inputs are all in price units
    (mfe_price = favorable excursion in price, not pips). Returns '' when
    nothing matches cleanly enough to say."""
    try:
        # 1. event_window — the fire-time news stamp owns the tape.
        if "news_window=true" in (extra or ""):
            return "event_window"

        # 2. stopped_then_reversed — right trade, stop inside the noise:
        #    after the stop-hit bar, price ran >= 2R beyond entry our way.
        if hit:
            hit_idx = None
            for i in range(len(fut_h)):
                adverse = fut_h[i] if direction == "SHORT" else fut_l[i]
                if (direction == "SHORT" and adverse >= stop) or \
                   (direction == "LONG" and adverse <= stop):
                    hit_idx = i
                    break
            if hit_idx is not None and hit_idx + 1 < len(fut_h):
                if direction == "SHORT":
                    post_run = entry - min(fut_l[hit_idx + 1:])
                else:
                    post_run = max(fut_h[hit_idx + 1:]) - entry
                if post_run >= _STR_REVERSAL_R * risk:
                    return "stopped_then_reversed"

        # 3. exhaustion_entry — chased an extended move: entry sits >= 2
        #    fire-time ATR beyond the 20-bar mean, in the trade direction.
        if ei >= _EXHAUST_MEAN_N and atr_at_fire > 0:
            mean = sum(C[ei - _EXHAUST_MEAN_N + 1:ei + 1]) / _EXHAUST_MEAN_N
            stretched = (entry - mean) if direction == "LONG" else (mean - entry)
            if stretched >= _EXHAUST_ATR * atr_at_fire:
                return "exhaustion_entry"

        # 4. never_onside — wrong from the first bar.
        if mfe_price < _NEVER_ONSIDE_R * risk:
            return "never_onside"

        # 5. bled_out — the rest: ground into the loss without a story above.
        return "bled_out"
    except Exception:
        return ""                          # never let autopsy break grading


def grade_pending_shadow(instrument: str) -> int:
    """Nightly: score every logged fire whose 30 four-hour bars have passed.
    A bar touching the stop makes it -1R; otherwise R = (close at bar 30 -
    entry) / risk. Records best/worst excursion and, for a loss, its type.
    Skips invalid-stop and excluded rows. A fire older than the 500-bar fetch
    (~83 trading days) is never graded. Rewrites the ledger atomically under
    its lock. Returns the number of rows graded."""
    if not os.path.exists(LOG_FILE):
        return 0
    from oanda_feed import get_h4_bars, is_configured
    if not is_configured():
        return 0
    df = get_h4_bars(pair=instrument.replace("_", ""), count=500)
    if df is None or df.empty:
        return 0
    H = [float(v) for v in df["High"].values]
    L = [float(v) for v in df["Low"].values]
    C = [float(v) for v in df["Close"].values]
    T = [t.strftime("%Y-%m-%dT%H:%M:%SZ") for t in df.index]
    pip = PAIRS[instrument].pip_size if instrument in PAIRS else 0.0001
    ts_to_idx = {t: i for i, t in enumerate(T)}

    # Lock from the ledger read to the write (ledger_io); the H4 fetch
    # above stays outside it, so no network call ever holds the lock.
    with locked(LOG_FILE):
        with open(LOG_FILE, newline="") as f:
            rows = list(csv.DictReader(f))
        # Excluded rows are never graded (exclusions.py). `rows` is written back
        # below, so they are skipped here rather than filtered out of the list —
        # filtering would delete them from an append-only ledger.
        is_excluded = excluder("shadow_signal_log.csv")
        filled = skipped_invalid = 0
        for r in rows:
            if r["instrument"] != instrument or str(r.get("outcome_filled")) == "True":
                continue
            if is_invalid_spec(r):
                skipped_invalid += 1           # never scored as R (see is_invalid_spec)
                continue
            if is_excluded(r):
                continue                       # registry exclusion (exclusions.py)
            ei = ts_to_idx.get(r["timestamp"])
            if ei is None or ei + HORIZON >= len(C):
                continue                                         # window not elapsed / not in fetch
            entry = float(r["entry"]); stop = float(r["stop"]); direction = r["direction"]
            fut_h = H[ei + 1:ei + 1 + HORIZON]; fut_l = L[ei + 1:ei + 1 + HORIZON]
            exit_c = C[ei + HORIZON]
            risk = abs(entry - stop) or 1e-9
            if direction == "LONG":
                mfe = (max(fut_h) - entry) / pip
                mae = (entry - min(fut_l)) / pip
                hit = min(fut_l) <= stop
                net = (exit_c - entry) / pip
            else:
                mfe = (entry - min(fut_l)) / pip
                mae = (max(fut_h) - entry) / pip
                hit = max(fut_h) >= stop
                net = (entry - exit_c) / pip
            r_mult = -1.0 if hit else round((net * pip) / risk, 2)
            r.update({
                "outcome_filled": True, "bars_elapsed": HORIZON,
                "mfe_pips": round(mfe, 1), "mae_pips": round(mae, 1),
                "net_30bars_pips": round(net, 1), "hit_stop": hit, "r_multiple": r_mult,
            })
            # Loss autopsy at the grading seam (docs/specs/loss_autopsy_spec.md):
            # everything needed is in scope; wins stay unclassified.
            if r_mult < 0:
                r["loss_species"] = _classify_loss(
                    direction, entry, stop, risk, r.get("extra", ""), hit,
                    mfe * pip, fut_h, fut_l, ei, C, float(r.get("atr") or 0.0))
            filled += 1
        if skipped_invalid:
            print(f"{instrument}: {skipped_invalid} invalid_spec shadow row(s) "
                  f"skipped — unscoreable by construction, never scored as R")
        if filled:
            atomic_write_rows(LOG_FILE, _FIELDS, rows)
        return filled


# ── Brief integration ───────────────────────────────────────────────────────────
_FUTILITY_N = 20   # docs/specs/futility_rule_spec.md


def tally_lines(t: Dict) -> List[str]:
    """The tally as the trader reads it: independent episodes and average R
    first (median beside it, M8; without the best one, M9). Net pips is a
    diagnostic (M14). No win count: without a breakeven rate beside it, it
    says nothing about expectancy."""
    still_open = t["logged"] - t["graded"]
    gates = (f"(futility check at {_FUTILITY_N} episodes, flag at {FLAG_N}, "
             f"review at {REVIEW_N})")
    rs = t["episode_rs"]
    if not rs:
        return [f"no graded episodes yet ({t['logged']} rows logged, {still_open} still open)", gates]
    per = f"per episode: avg {mean(rs):+.2f}R, median {median(rs):+.2f}R"
    if len(rs) >= 2:
        per += f", without the best one {mean(sorted(rs)[:-1]):+.2f}R"
    eps = "episode" if len(rs) == 1 else "episodes"
    rows = "row" if t["graded"] == 1 else "rows"
    return [f"{len(rs)} independent {eps} from {t['graded']} graded {rows} ({still_open} still open)",
            per,
            f"diagnostic only: avg {t['avg_net']:+.0f} pips at bar 30 over the graded rows",
            gates]


def run_and_report(instrument: str) -> None:
    """Check + log today's shadow signals; print a clearly-marked section ONLY if
    something fired. Zero output otherwise."""
    signals = check_shadow_signals(instrument)
    log_shadow_signals(signals)
    if not signals:
        return
    print()
    print("  " + "─" * 51)
    print("  SHADOW SIGNALS (logged, NOT tradeable — evidence accumulating)")
    print("  " + "─" * 51)
    for s in signals:
        t = get_shadow_tally(s["candidate_id"], instrument)
        print(f"    {s['candidate_id']:<16} {s['direction']:<5} @ {s['entry']}  "
              f"stop {s['stop']}")
        for i, line in enumerate(tally_lines(t)):
            print(("      tally: " if i == 0 else "             ") + line)
