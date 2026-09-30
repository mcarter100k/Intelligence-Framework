"""
session_memory.py
─────────────────
Intraday session context accumulator.

Logs nine key indicators on every brief run.
When the brief runs again in the same session,
computes deltas and surfaces direction of travel.

Only tracks what can change a trading decision
within a single session:
  - ADX direction of travel (toward or away from thresholds)
  - ATR ratio trend (expanding or contracting)
  - Regime classification changes (the most important event)
  - H4 structure direction (holding or breaking)

Everything else — weekly context, MA readings, COT,
currency strength — does not move intraday and is
not tracked here.
"""

import csv
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List

from regime_detection import _ADX_TRANSITION_HIGH, _ADX_RANGING_THRESHOLD, PAIRS

LOG_FILE = "session_context_log.csv"
PRUNE_DAYS = 30

FIELDNAMES = [
    "timestamp", "instrument", "adx_d1", "adx_h4",
    "atr_ratio", "regime_d1", "regime_h4",
    "structure_d1", "filter_allowed",
]


def log_session_snapshot(regime: dict, instrument: str,
                         market_open: bool = True) -> None:
    """
    Log current session snapshot. Called after every get_regime().
    Prunes entries older than PRUNE_DAYS on each write.
    Never raises — logging failure never breaks the brief.
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
        }
        _append_row(row)
        _prune_old_entries()
    except Exception:
        pass


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

        # Filter change — the most important event
        filter_now   = str(current["filter_allowed"]).lower() == "true"
        filter_prior = str(previous["filter_allowed"]).lower() == "true"
        filter_changed = filter_now != filter_prior

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
        summary  = _build_summary(
            minutes_ago, regime_changed, filter_changed,
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


def _build_summary(
    minutes_ago: int, regime_changed: bool, filter_changed: bool,
    adx_trend: str, atr_trend: str, adx_note: str, atr_note: str,
    current: dict, previous: dict,
) -> str:
    time_str = (f"{minutes_ago}min ago" if minutes_ago < 60
                else f"{minutes_ago//60}h {minutes_ago%60}min ago")

    # Regime flip — most important, surfaces first
    if filter_changed:
        if str(current["filter_allowed"]).lower() == "true":
            return (f"Since {time_str}: CONDITIONS IMPROVED — "
                    f"framework may now allow a trade. Re-read the full brief.")
        else:
            return (f"Since {time_str}: CONDITIONS DETERIORATED — "
                    f"framework moved to stand aside.")

    if regime_changed:
        return (f"Since {time_str}: Regime changed "
                f"({previous['regime_d1']} → {current['regime_d1']}). "
                f"Re-evaluate.")

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
    try:
        from exclusions import filter_rows
        rows = filter_rows(rows, "session_context_log.csv")
    except Exception:
        pass
    return rows


def _append_row(row: dict) -> None:
    exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def _prune_old_entries() -> None:
    if not os.path.exists(LOG_FILE):
        return
    cutoff = (datetime.now(timezone.utc).date() - timedelta(days=PRUNE_DAYS)).isoformat()
    with open(LOG_FILE, newline="") as f:
        rows = list(csv.DictReader(f))
    fresh = [r for r in rows if r["timestamp"][:10] >= cutoff]
    if len(fresh) < len(rows):
        with open(LOG_FILE, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(fresh)
