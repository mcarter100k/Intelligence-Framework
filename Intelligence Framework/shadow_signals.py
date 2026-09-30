"""
shadow_signals.py
─────────────────
Shadow-signal harness. Signals are LOGGED, NEVER TRADED. Nothing here is wired
into official_decision's tradeable path — this module only observes and records,
so that forward data can eventually give the first honestly-validated answer.

Why this exists: three historical premises (compression-precedes-moves,
fakeout-then-go, structural-precursor) were all refuted at honest N this session
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

import csv
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

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
    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)
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
# v1 RETIRED 2026-09-09 (validation_log 2026-09-09; docs/specs/
# early_momentum_v2_spec.md). Defect: the stale-swing stop could land on the
# NON-adverse side of entry (SHORT entered above the last swing high) —
# unscoreable by construction, guaranteed -1.0R at entry. v1's ledger rows are
# preserved under their original id; its one valid row is Episode 1 = -1.0R.
# v2 = byte-identical trigger and parameters + ONE guard: when the swing
# exists but gives no valid adverse-side stop, NO FIRE (no fallback
# substitution — that ambiguous state is exactly what v1 mis-scored).
# Frozen 2026-09-09; any further change starts EARLY_MOMENTUM_v3.
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
    # ATR/bar alignment (2026-09-10 fix): compute_atr_series returns
    # n - period values — atr[i] is the ATR as of bar i + off, so the live
    # feed (n=300, off=14) made atr[b] with a BAR index raise IndexError on
    # every call from go-live, silently swallowed upstream into "no signal".
    # _atr_at maps a bar index to its ATR. Alignment only — every spec
    # parameter (frozen 2026-07-29) is UNCHANGED, so no new candidate id.
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
            # A candidate error must NEVER render as "no signal" — that is
            # how THRUST_PULLBACK logged a can't-fire as a no-setup from
            # go-live to 2026-09-10. Loud path: machine ##ALERT## line on
            # stderr; the wrapper routes it to the day log + a notification
            # and records a health FAILURE, so the daily UNHEALTHY alert
            # repeats until the candidate is fixed. The other candidates
            # still run — one broken check never silences the rest.
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
            if check_news_gate(instrument).get("gating"):
                for s in out:
                    s["extra"] = (f"{s['extra']}|" if s.get("extra") else "") + \
                                 "news_window=true"
        except Exception:
            pass
    return out


# ── Logging (dedup by candidate+instrument+timestamp) ───────────────────────────
def _ensure_file():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=_FIELDS).writeheader()
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
    try:
        with open(LOG_FILE, newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None or list(reader.fieldnames) == _FIELDS:
                return
            rows = list(reader)
    except Exception:
        return                              # unreadable: leave it alone
    with open(LOG_FILE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in _FIELDS})


def log_shadow_signals(signals: List[Dict]) -> int:
    if not signals:
        return 0
    _ensure_file()
    seen = set()
    with open(LOG_FILE, newline="") as f:
        for row in csv.DictReader(f):
            seen.add((row["candidate_id"], row["instrument"], row["timestamp"]))
    written = 0
    with open(LOG_FILE, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_FIELDS)
        for s in signals:
            key = (s["candidate_id"], s["instrument"], s["timestamp"])
            if key in seen:
                continue
            row = {k: "" for k in _FIELDS}
            row.update(s)
            row["outcome_filled"] = False
            w.writerow(row)
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
        return {"logged": 0, "graded": 0, "wins": 0, "avg_net": 0.0}
    logged = graded = wins = 0
    nets = []
    try:
        from exclusions import excluded_ids, is_excluded as _is_excl
        _excl = excluded_ids("shadow_signal_log.csv")
    except Exception:
        _excl, _is_excl = set(), None
    with open(LOG_FILE, newline="") as f:
        for r in csv.DictReader(f):
            if r["candidate_id"] != candidate_id:
                continue
            if instrument and r["instrument"] != instrument:
                continue
            if is_invalid_spec(r):
                continue                   # unscoreable by construction
            if _excl and _is_excl is not None and \
                    _is_excl(r, "shadow_signal_log.csv", _excl):
                continue                   # registry exclusion (exclusions.py)
            logged += 1
            if str(r.get("outcome_filled")) == "True":
                graded += 1
                # The definitive outcome is R-multiple — it respects the
                # stop. hit_stop=True => LOSS, always: a stopped trade lost
                # 1R no matter where price sat 30 bars later; counting its
                # net-at-horizon as a win is clairvoyance, not performance
                # (validation_log 2026-09-09, tally correction). The
                # founding exhibit is exactly this shape: -1.0R with net
                # +529. net_30bars_pips stays in the ledger as a DIAGNOSTIC
                # (the loss autopsy needs it to spot noise-stops) but never
                # determines win/loss.
                try:
                    if float(r["r_multiple"]) > 0:
                        wins += 1
                except (ValueError, TypeError):
                    pass
                try:
                    nets.append(float(r["net_30bars_pips"]))
                except (ValueError, TypeError):
                    pass
    return {"logged": logged, "graded": graded, "wins": wins,
            "avg_net": round(sum(nets) / len(nets), 1) if nets else 0.0}


def latest_pending_signal(instrument: str) -> Optional[Dict]:
    """Most recent ungraded shadow signal for the pair (for the brief narrative).
    Returns candidate_id / direction / entry / timestamp, or None."""
    if not os.path.exists(LOG_FILE):
        return None
    latest = None
    with open(LOG_FILE, newline="") as f:
        for r in csv.DictReader(f):
            if r["instrument"] != instrument or str(r.get("outcome_filled")) == "True":
                continue
            if is_invalid_spec(r):
                continue                   # never surfaced to the brief
            latest = r                      # append order → last ungraded = newest
    if not latest:
        return None
    try:
        return {"candidate_id": latest["candidate_id"], "direction": latest["direction"],
                "entry": float(latest["entry"]), "stop": float(latest["stop"]),
                "timestamp": latest["timestamp"]}
    except (ValueError, KeyError):
        return None


def episode_count(candidate_id: str, instrument: Optional[str] = None) -> int:
    """Collapse fires whose 30-bar (HORIZON) outcome horizons OVERLAP into one
    episode. The 30/60 review gates count independent EPISODES, not raw rows —
    a candidate that fires on 8 consecutive H4 bars of the same move is one
    piece of evidence, not eight. Counting methodology only; trigger/grading
    specs are unchanged and remain frozen."""
    if not os.path.exists(LOG_FILE):
        return 0
    from collections import defaultdict
    try:
        from exclusions import excluded_ids, is_excluded as _is_excl
        _excl = excluded_ids("shadow_signal_log.csv")
    except Exception:
        _excl, _is_excl = set(), None
    by_inst = defaultdict(list)
    with open(LOG_FILE, newline="") as f:
        for r in csv.DictReader(f):
            if r["candidate_id"] != candidate_id:
                continue
            if instrument and r["instrument"] != instrument:
                continue
            if is_invalid_spec(r):
                continue                   # not evidence — excluded before collapse
            if _excl and _is_excl is not None and \
                    _is_excl(r, "shadow_signal_log.csv", _excl):
                continue                   # registry exclusion (exclusions.py)
            try:
                by_inst[r["instrument"]].append(
                    datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")))
            except Exception:
                continue
    span = HORIZON * 4 * 3600          # 30 H4 bars, in seconds
    total = 0
    for times in by_inst.values():
        times.sort()
        eps, start = 1, times[0]
        for t in times[1:]:
            if (t - start).total_seconds() >= span:
                eps += 1
                start = t
        total += eps
    return total


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


def backfill_loss_species(instrument: str) -> int:
    """Classify already-graded VALID losing rows whose loss_species is
    empty, via the same definitions (fresh H4 fetch; count=500 reaches ~83
    days). Manual/one-time path — scheduled runs classify at grading time.
    Returns rows classified."""
    if not os.path.exists(LOG_FILE):
        return 0
    from oanda_feed import get_h4_bars, is_configured
    if not is_configured():
        return 0
    df = get_h4_bars(pair=instrument.replace("_", ""), count=500)
    if df is None or df.empty:
        return 0
    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)
    H = [float(v) for v in df["High"].values]
    L = [float(v) for v in df["Low"].values]
    C = [float(v) for v in df["Close"].values]
    T = [t.strftime("%Y-%m-%dT%H:%M:%SZ") for t in df.index]
    pip = PAIRS[instrument].pip_size if instrument in PAIRS else 0.0001
    ts_to_idx = {t: i for i, t in enumerate(T)}

    _migrate_header()
    with open(LOG_FILE, newline="") as f:
        rows = list(csv.DictReader(f))
    changed = 0
    for r in rows:
        if r["instrument"] != instrument or str(r.get("outcome_filled")) != "True":
            continue
        if r.get("loss_species") or is_invalid_spec(r):
            continue
        try:
            r_mult = float(r["r_multiple"])
        except (TypeError, ValueError):
            continue
        if r_mult >= 0:
            continue                       # wins are not autopsied
        ei = ts_to_idx.get(r["timestamp"])
        if ei is None or ei + HORIZON >= len(C):
            continue
        entry = float(r["entry"]); stop = float(r["stop"])
        risk = abs(entry - stop) or 1e-9
        fut_h = H[ei + 1:ei + 1 + HORIZON]; fut_l = L[ei + 1:ei + 1 + HORIZON]
        mfe_price = float(r["mfe_pips"]) * pip
        species = _classify_loss(
            r["direction"], entry, stop, risk, r.get("extra", ""),
            str(r.get("hit_stop")) == "True", mfe_price, fut_h, fut_l,
            ei, C, float(r.get("atr") or 0.0))
        if species:
            r["loss_species"] = species
            changed += 1
    if changed:
        with open(LOG_FILE, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=_FIELDS)
            w.writeheader()
            w.writerows([{k: r.get(k, "") for k in _FIELDS} for r in rows])
    return changed


# ── Grading (called by run_outcome_check) ───────────────────────────────────────
def grade_pending_shadow(instrument: str) -> int:
    if not os.path.exists(LOG_FILE):
        return 0
    from oanda_feed import get_h4_bars, is_configured
    if not is_configured():
        return 0
    df = get_h4_bars(pair=instrument.replace("_", ""), count=500)
    if df is None or df.empty:
        return 0
    if hasattr(df.columns, "levels"):
        df.columns = df.columns.get_level_values(0)
    H = [float(v) for v in df["High"].values]
    L = [float(v) for v in df["Low"].values]
    C = [float(v) for v in df["Close"].values]
    T = [t.strftime("%Y-%m-%dT%H:%M:%SZ") for t in df.index]
    pip = PAIRS[instrument].pip_size if instrument in PAIRS else 0.0001
    ts_to_idx = {t: i for i, t in enumerate(T)}

    with open(LOG_FILE, newline="") as f:
        rows = list(csv.DictReader(f))
    filled = skipped_invalid = 0
    for r in rows:
        if r["instrument"] != instrument or str(r.get("outcome_filled")) == "True":
            continue
        if is_invalid_spec(r):
            skipped_invalid += 1           # never scored as R (see is_invalid_spec)
            continue
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
        with open(LOG_FILE, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=_FIELDS)
            w.writeheader(); w.writerows(rows)
    return filled


# ── Brief integration ───────────────────────────────────────────────────────────
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
        eps = episode_count(s["candidate_id"], instrument)
        tally = (f"{t['logged']} rows / {eps} episodes, {t['graded']} graded, "
                 f"{t['wins']} wins, {t['avg_net']:+.0f} avg pips" if t["graded"] else
                 f"{t['logged']} rows / {eps} episodes, 0 graded yet")
        print(f"    {s['candidate_id']:<16} {s['direction']:<5} @ {s['entry']}  "
              f"stop {s['stop']}")
        print(f"      tally: {tally}   (flag N={FLAG_N}, review N={REVIEW_N})")
