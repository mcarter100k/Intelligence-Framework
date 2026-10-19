"""
session_memory.py
─────────────────
Intraday session context accumulator.

Logs seven readings on every open-market brief run.
When the brief runs again in the same session,
computes deltas and surfaces direction of travel.

Only tracks what can change a trading decision
within a single session:
  - ADX direction of travel (toward or away from thresholds)
  - ATR ratio trend (expanding or contracting)
  - Regime classification changes (the most important event)
  - Daily price structure (holding or breaking)

Everything else — weekly context, MA readings, COT,
currency strength — does not move intraday and is
not tracked here.
"""

import csv
import os
from datetime import datetime, timezone
from typing import Optional, Dict, List

from exclusions import filter_rows
from ledger_io import append_row, locked, migrate_header
from regime_detection import _ADX_TRANSITION_HIGH, _ADX_RANGING_THRESHOLD, PAIRS

LOG_FILE = "session_context_log.csv"

FIELDNAMES = [
    "timestamp", "instrument", "adx_d1", "adx_h4",
    "atr_ratio", "regime_d1", "regime_h4",
    "structure_d1", "filter_allowed",
    # decision_logic_spec.md: filter_allowed changed meaning on 2026-09-30
    # (it now includes the official decision), so a flip is only compared
    # between rows written under the same rules. BLANK on older rows.
    "logic_version",
]


def log_session_snapshot(regime: dict, instrument: str,
                         market_open: bool = True) -> None:
    """
    Log current session snapshot. Called after every get_regime().
    APPEND-ONLY (docs/specs/safe_ledger_writes_spec.md): the former 30-day
    prune deleted evidence, including the 2026-07-29 synthetic row whose
    origin can now never be checked. The 30-day view lives in the reader
    (_get_today_rows reads today only), not in deletion.
    Never raises — logging failure never breaks the brief — but a failure is
    printed to stderr, which the brief wrapper keeps in the day log.
    Skips logging when market is closed — closed-market deltas are noise.
    """
    if not market_open:
        return
    try:
        timestamp = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ")
        row = {
            "timestamp":    timestamp,
            "instrument":   instrument,
            "adx_d1":       regime.get("adx", 0.0),
            "adx_h4":       regime.get("adx_h4", 0.0),
            "atr_ratio":    regime.get("atr_vs_avg", 1.0),
            "regime_d1":    regime.get("regime_d1", ""),
            "regime_h4":    regime.get("regime_h4", ""),
            "structure_d1": regime.get("structure", ""),
            "filter_allowed": regime.get("filter_allowed", False),
            "logic_version":  regime.get("logic_version", ""),
        }
        _append_row(row)
    except Exception as exc:
        import sys
        print(f"session snapshot NOT logged for {instrument}: "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)


def get_session_delta(instrument: str) -> Optional[Dict]:
    """
    Compare current session state to the previous reading today.

    Returns None if this is the first reading of the day.
    Returns a delta dict with:
      prior_timestamp  : when the previous reading was taken
      minutes_ago      : how long ago
      adx_d1_prior     : previous D1 ADX
      adx_d1_delta     : change in D1 ADX
      adx_h4_prior     : previous H4 ADX
      adx_h4_delta     : change in H4 ADX
      atr_ratio_prior  : previous ATR ratio
      atr_ratio_delta  : change in ATR ratio
      regime_changed   : bool — did composite regime change?
      regime_d1_prior  : previous D1 regime
      regime_h4_prior  : previous H4 regime
      structure_changed: bool — did D1 structure change?
      structure_prior  : previous D1 structure
      filter_changed   : bool — did filter_allowed change?
      filter_prior     : previous filter_allowed value

      adx_trend        : "RISING" | "FALLING" | "STABLE"
      adx_note         : plain English description
      atr_trend        : "EXPANDING" | "CONTRACTING" | "STABLE"
      atr_note         : plain English description
      summary          : one-line plain English session summary
    """
    try:
        today_rows = _get_today_rows(instrument)
        if len(today_rows) < 2:
            return None  # First reading of the day

        current  = today_rows[-1]
        previous = today_rows[-2]

        # Time delta
        prior_ts  = datetime.fromisoformat(
            previous["timestamp"].replace("Z", "+00:00"))
        now_ts    = datetime.fromisoformat(
            current["timestamp"].replace("Z", "+00:00"))
        minutes_ago = int((now_ts - prior_ts).total_seconds() / 60)

        # ADX deltas
        adx_d1_now   = float(current["adx_d1"])
        adx_d1_prior = float(previous["adx_d1"])
        adx_d1_delta = round(adx_d1_now - adx_d1_prior, 1)

        adx_h4_now   = float(current["adx_h4"])
        adx_h4_prior = float(previous["adx_h4"])
        adx_h4_delta = round(adx_h4_now - adx_h4_prior, 1)

        # ATR delta
        atr_now   = float(current["atr_ratio"])
        atr_prior = float(previous["atr_ratio"])
        atr_delta = round(atr_now - atr_prior, 3)

        # Regime changes
        regime_d1_changed = current["regime_d1"] != previous["regime_d1"]
        regime_h4_changed = current["regime_h4"] != previous["regime_h4"]
        regime_changed    = regime_d1_changed or regime_h4_changed

        # Structure change
        structure_changed = current["structure_d1"] != previous["structure_d1"]

        # Filter change — the most important event. Only between rows written
        # under the same decision rules: across a rule change the flip is the
        # rules, not the market, and must not alert (decision_logic_spec).
        filter_now   = str(current["filter_allowed"]).lower() == "true"
        filter_prior = str(previous["filter_allowed"]).lower() == "true"
        same_rules   = ((current.get("logic_version") or "") ==
                        (previous.get("logic_version") or ""))
        filter_changed = same_rules and filter_now != filter_prior

        # ADX trend classification
        if abs(adx_d1_delta) < 0.5:
            adx_trend = "STABLE"
        elif adx_d1_delta > 0:
            adx_trend = "RISING"
        else:
            adx_trend = "FALLING"

        # ATR trend classification
        if abs(atr_delta) < 0.05:
            atr_trend = "STABLE"
        elif atr_delta > 0:
            atr_trend = "EXPANDING"
        else:
            atr_trend = "CONTRACTING"

        # Build notes
        adx_note = _adx_note(adx_d1_now, adx_d1_prior,
                              adx_d1_delta, adx_trend, instrument)
        atr_note = _atr_note(atr_now, atr_prior,
                              atr_delta, atr_trend, instrument)
        # Which timeframes changed, from the flags computed above — the ONE
        # comparison (regime_change_message_spec review F1).
        regime_changes = [tf for tf, changed in (("D1", regime_d1_changed),
                                                 ("H4", regime_h4_changed))
                          if changed]
        summary  = _build_summary(
            minutes_ago, regime_changes, filter_changed,
            adx_trend, atr_trend, adx_note, atr_note,
            current, previous,
        )

        return {
            "prior_timestamp":   previous["timestamp"],
            "minutes_ago":       minutes_ago,
            "adx_d1_prior":      adx_d1_prior,
            "adx_d1_now":        adx_d1_now,
            "adx_d1_delta":      adx_d1_delta,
            "adx_h4_prior":      adx_h4_prior,
            "adx_h4_now":        adx_h4_now,
            "adx_h4_delta":      adx_h4_delta,
            "atr_ratio_prior":   atr_prior,
            "atr_ratio_now":     atr_now,
            "atr_ratio_delta":   atr_delta,
            "regime_changed":    regime_changed,
            "regime_d1_prior":   previous["regime_d1"],
            "regime_h4_prior":   previous["regime_h4"],
            "structure_changed": structure_changed,
            "structure_prior":   previous["structure_d1"],
            "filter_changed":    filter_changed,
            "filter_prior":      filter_prior,
            "filter_now":        filter_now,
            "adx_trend":         adx_trend,
            "adx_note":          adx_note,
            "atr_trend":         atr_trend,
            "atr_note":          atr_note,
            "summary":           summary,
        }
    except Exception:
        return None


# ── Internal helpers ──────────────────────────────────────────────────────────

def _adx_note(now: float, prior: float, delta: float,
              trend: str, instrument: str) -> str:
    thresh = _ADX_TRANSITION_HIGH

    if trend == "STABLE":
        if now < _ADX_RANGING_THRESHOLD:
            return f"Daily strength stable and low ({now:.0f}) — sideways market"
        elif now < thresh:
            return (f"Daily strength stable in transition zone "
                    f"({now:.0f}) — no edge yet")
        else:
            return f"Daily strength stable and trending ({now:.0f})"

    direction = "rising" if delta > 0 else "falling"

    if now >= thresh and prior < thresh:
        return (f"Daily strength just crossed the trend threshold "
                f"({prior:.0f} → {now:.0f}) — conditions may be tradeable")

    if now < thresh and prior >= thresh:
        return (f"Daily strength dropped below trend threshold "
                f"({prior:.0f} → {now:.0f}) — trend losing conviction")

    if now < thresh and trend == "RISING":
        remaining = thresh - now
        return (f"Daily strength {direction} ({prior:.0f} → {now:.0f}), "
                f"{remaining:.0f} points from trend threshold")

    if now >= thresh and trend == "FALLING":
        return (f"Daily strength {direction} ({prior:.0f} → {now:.0f}) "
                f"— trend weakening but still active")

    return (f"Daily strength {direction} "
            f"({prior:.0f} → {now:.0f})")


def _atr_note(now: float, prior: float, delta: float,
              trend: str, instrument: str) -> str:
    pair_cfg     = PAIRS.get(instrument, PAIRS["GBP_AUD"])
    spike_thresh = pair_cfg.atr_spike_multiplier
    comp_min     = pair_cfg.atr_compression_min   # 0.0 means no compression filter

    if trend == "STABLE":
        return f"Volatility stable ({now:.2f}x)"

    direction = "expanding" if delta > 0 else "contracting"

    # Approaching spike
    if now < spike_thresh and trend == "EXPANDING":
        remaining = spike_thresh - now
        if remaining < 0.1:
            return (f"Volatility {direction} ({prior:.2f}x → {now:.2f}x) "
                    f"— approaching spike threshold, watch closely")
        return f"Volatility {direction} ({prior:.2f}x → {now:.2f}x)"

    # Crossed spike threshold
    if now >= spike_thresh and prior < spike_thresh:
        return (f"Volatility just crossed spike threshold "
                f"({prior:.2f}x → {now:.2f}x) — conditions degraded")

    # Compression (only for pairs with a compression threshold set)
    if comp_min > 0:
        if now < comp_min and trend == "CONTRACTING":
            return (f"Volatility compressing ({prior:.2f}x → {now:.2f}x) "
                    f"— approaching pre-intervention coil zone")
        if now < comp_min and prior >= comp_min:
            return (f"Volatility entered compression zone "
                    f"({prior:.2f}x → {now:.2f}x) — BoJ risk elevated")

    return f"Volatility {direction} ({prior:.2f}x → {now:.2f}x)"


_NO_DATA = ("", "UNAVAILABLE", "UNKNOWN", "NONE")


def _regime_change_text(regime_changes: list, current: dict, previous: dict) -> str:
    """'D1: A → B; H4: C → D' for the timeframes that changed. Raw tokens —
    the brief's _plain() words them ('daily chart', 'trending up'). A blank or
    unavailable reading is a data gap, not a regime: 'no data this run'."""
    key = {"D1": "regime_d1", "H4": "regime_h4"}
    def val(row, tf):
        v = (row.get(key[tf]) or "").strip()
        return "no data this run" if v.upper() in _NO_DATA else v
    return "; ".join(f"{tf}: {val(previous, tf)} → {val(current, tf)}"
                     for tf in regime_changes)


def _build_summary(
    minutes_ago: int, regime_changes: list, filter_changed: bool,
    adx_trend: str, atr_trend: str, adx_note: str, atr_note: str,
    current: dict, previous: dict,
) -> str:
    time_str = (f"{minutes_ago}min ago" if minutes_ago < 60
                else f"{minutes_ago//60}h {minutes_ago%60}min ago")

    changes = _regime_change_text(regime_changes, current, previous)
    # A filter flip that coincides with a regime change names it too, so the
    # session line and the regime alert agree (review F6).
    also = f" Regime changed — {changes}." if changes else ""

    # Regime flip — most important, surfaces first
    if filter_changed:
        if str(current["filter_allowed"]).lower() == "true":
            return (f"Since {time_str}: CONDITIONS IMPROVED — "
                    f"framework may now allow a trade.{also} Re-read the full brief.")
        else:
            return (f"Since {time_str}: CONDITIONS DETERIORATED — "
                    f"framework moved to stand aside.{also}")

    if changes:
        # Name each timeframe that actually changed (regime_change_message_
        # spec): the message used to print the D1 pair only — an H4-only
        # change read "no clear direction → no clear direction". An em dash,
        # not parentheses: _plain() adds its own "(…)" to some tokens.
        return (f"Since {time_str}: Regime changed — {changes}. Re-evaluate.")

    # No regime change — surface the most notable delta
    if adx_trend != "STABLE":
        return f"Since {time_str}: {adx_note}"

    if atr_trend != "STABLE":
        return f"Since {time_str}: {atr_note}"

    return f"Since {time_str}: Conditions unchanged."


def _get_today_rows(instrument: str) -> List[Dict]:
    if not os.path.exists(LOG_FILE):
        return []
    today = datetime.now(timezone.utc).date().isoformat()
    rows = []
    with open(LOG_FILE, newline="") as f:
        for row in csv.DictReader(f):
            if (row["instrument"] == instrument and
                    row["timestamp"].startswith(today)):
                rows.append(row)
    # Excluded rows never take part in a delta comparison (exclusions.py).
    # The 2026-09-16 contamination proved why: a synthetic filter_allowed
    # made the next honest run render "conditions deteriorated" and fire an
    # alert for a flip that never happened. This read feeds comparisons
    # only — nothing is written back — so filtering here is safe.
    return filter_rows(rows, "session_context_log.csv")


def _append_row(row: dict) -> None:
    """Append under the lock, migrating an older header first: append_row
    writes no header to an existing file, so a row with a new column under
    the old header would land misaligned."""
    with locked(LOG_FILE):
        if os.path.exists(LOG_FILE):
            migrate_header(LOG_FILE, FIELDNAMES)   # additive; values verbatim
        append_row(LOG_FILE, FIELDNAMES, row)     # locked + fsynced (ledger_io)
