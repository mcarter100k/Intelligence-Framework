"""
calibrate_weights.py

Feedback loop: auto-calibrate regime weights in decision_engine.py
from historical outcome data in run_journal.csv.

HOW IT WORKS:
  1. Read run_journal.csv — find rows with outcome_label = WIN or LOSS
  2. Group by regime (TRENDING_UP / TRENDING_DOWN / RANGING / VOLATILE)
  3. For each regime, use proxy fields to score signal reliability:
       htf_context + direction alignment  → htf signal accuracy
       sweep_confirmed                    → liquidity signal accuracy
       value_verdict + direction          → value context accuracy
       strength_diff + direction          → currency strength accuracy
       vix_regime + direction             → cross-market signal accuracy
  4. Blend learned weights with defaults (prevents overfitting on small samples)
  5. Save to calibrated_weights.json
  6. decision_engine.py loads calibrated weights at startup if file exists

USAGE:
  python calibrate_weights.py          ← run calibration, save weights
  python calibrate_weights.py --report ← print calibration report only

MIN_OUTCOMES_PER_REGIME = 15
  Below this threshold the regime keeps default weights (not enough data).
  Above it, blending starts: 70% learned + 30% default.
"""

from __future__ import annotations
import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

JOURNAL_PATH   = Path(__file__).parent / "run_journal.csv"
WEIGHTS_PATH   = Path(__file__).parent / "calibrated_weights.json"
MIN_OUTCOMES   = 15
LEARN_BLEND    = 0.70   # weight given to learned vs default weights
STALE_DAYS     = 30     # recalibrate if weights file is older than this

_DEFAULT_WEIGHTS: Dict[str, Dict[str, float]] = {
    "TRENDING_UP": {
        "htf": 0.35, "strength": 0.25, "liquidity": 0.15,
        "cross": 0.10, "news": 0.08, "rates": 0.04, "cot": 0.03,
    },
    "TRENDING_DOWN": {
        "htf": 0.35, "strength": 0.25, "liquidity": 0.15,
        "cross": 0.10, "news": 0.08, "rates": 0.04, "cot": 0.03,
    },
    "RANGING": {
        "liquidity": 0.35, "strength": 0.20, "htf": 0.15,
        "cross": 0.12, "news": 0.10, "rates": 0.05, "cot": 0.03,
    },
    "VOLATILE": {
        "news": 0.35, "cross": 0.25, "liquidity": 0.20,
        "strength": 0.12, "htf": 0.05, "rates": 0.02, "cot": 0.01,
    },
}


# ── Public API ────────────────────────────────────────────────────────────────

def load_calibrated_weights() -> Optional[Dict[str, Dict[str, float]]]:
    """
    Load calibrated_weights.json if it exists and is not stale.
    Returns None if the file is absent, stale, or has insufficient data.
    decision_engine.py calls this at startup to override _REGIME_WEIGHTS.
    """
    if not WEIGHTS_PATH.exists():
        return None

    try:
        data = json.loads(WEIGHTS_PATH.read_text())
        from datetime import date, timedelta
        calibrated_on = date.fromisoformat(data.get("last_calibrated", "2000-01-01"))
        if (date.today() - calibrated_on).days > STALE_DAYS:
            return None
        weights = data.get("weights")
        return weights if weights else None
    except Exception:
        return None


def run_calibration(report_only: bool = False) -> Dict:
    """
    Main calibration entry point.
    Reads journal, computes signal accuracy per regime, optionally writes weights.
    Returns a summary dict with per-regime statistics.
    """
    rows = _load_journal()
    if not rows:
        print("Journal is empty — nothing to calibrate.")
        return {}

    labeled = [r for r in rows if r.get("outcome_label", "").strip() in ("WIN", "LOSS")]
    if not labeled:
        print(f"No labeled outcomes found in {len(rows)} journal rows.")
        print("Run label_outcomes.py first to automatically label past runs.")
        return {}

    print(f"\nCalibrating from {len(labeled)} labeled outcomes ({len(rows)} total rows)...\n")

    results: Dict[str, Dict] = {}
    calibrated_weights: Dict[str, Dict[str, float]] = {}

    for regime in _DEFAULT_WEIGHTS:
        regime_rows = [r for r in labeled if r.get("regime", "") == regime]
        stats = _compute_regime_stats(regime, regime_rows)
        results[regime] = stats

        if len(regime_rows) >= MIN_OUTCOMES:
            learned = _build_learned_weights(regime, regime_rows)
            blended = _blend(learned, _DEFAULT_WEIGHTS[regime])
            calibrated_weights[regime] = blended
            _print_regime_report(regime, stats, blended)
        else:
            _print_regime_report(regime, stats, None)

    if not report_only and calibrated_weights:
        _save_weights(calibrated_weights)
        print(f"\n✅ Calibrated weights saved to {WEIGHTS_PATH.name}")
        print(f"   Covers {len(calibrated_weights)} regime(s). "
              f"Default weights used for the rest.\n")
    elif report_only:
        print("\n[report only — no file written]\n")
    else:
        print("\nNo regime has enough data to calibrate yet. "
              f"Need {MIN_OUTCOMES} labeled outcomes per regime.\n")

    return results


# ── Signal scoring ────────────────────────────────────────────────────────────

def _compute_regime_stats(regime: str, rows: List[Dict]) -> Dict:
    """For each signal layer, compute how often it aligned with WIN vs LOSS."""
    if not rows:
        return {"n": 0, "win_rate": 0, "signal_accuracy": {}}

    wins   = [r for r in rows if r.get("outcome_label") == "WIN"]
    losses = [r for r in rows if r.get("outcome_label") == "LOSS"]
    n      = len(rows)
    win_rate = round(len(wins) / n * 100)

    accuracy: Dict[str, float] = {}

    # htf signal: aligned when direction matches htf_context
    accuracy["htf"]      = _signal_accuracy(rows, _htf_aligned)
    # liquidity signal: sweep_confirmed in the right direction
    accuracy["liquidity"] = _signal_accuracy(rows, _sweep_aligned)
    # strength signal: strength_diff sign matches direction
    accuracy["strength"] = _signal_accuracy(rows, _strength_aligned)
    # cross-market: vix_regime in a risk-on/off state that matches direction
    accuracy["cross"]    = _signal_accuracy(rows, _cross_aligned)
    # value context: value_verdict matches direction
    accuracy["value"]    = _signal_accuracy(rows, _value_aligned)

    return {"n": n, "win_rate": win_rate, "signal_accuracy": accuracy}


def _signal_accuracy(rows: List[Dict], check_fn) -> float:
    """Fraction of WIN rows where the signal aligned vs LOSS rows where it aligned."""
    win_rows  = [r for r in rows if r.get("outcome_label") == "WIN"]
    loss_rows = [r for r in rows if r.get("outcome_label") == "LOSS"]

    if not win_rows:
        return 0.5

    win_aligned  = sum(1 for r in win_rows  if check_fn(r))
    loss_aligned = sum(1 for r in loss_rows if check_fn(r)) if loss_rows else 0

    total_aligned = win_aligned + loss_aligned
    if total_aligned == 0:
        return 0.5
    return round(win_aligned / total_aligned, 3)


# ── Per-signal alignment checks ───────────────────────────────────────────────

def _direction(row: Dict) -> str:
    """Derive intended direction from journal bias field."""
    b = row.get("bias", "").upper()
    if b == "BULLISH": return "LONG"
    if b == "BEARISH": return "SHORT"
    return "NEUTRAL"


def _htf_aligned(row: Dict) -> bool:
    ctx = row.get("htf_context", "")
    dir_ = _direction(row)
    bullish_ctx = {"ESTABLISHED_UPTREND", "PULLBACK_IN_UPTREND"}
    bearish_ctx = {"ESTABLISHED_DOWNTREND", "COUNTER_TREND_BOUNCE"}
    return (dir_ == "LONG" and ctx in bullish_ctx) or (dir_ == "SHORT" and ctx in bearish_ctx)


def _sweep_aligned(row: Dict) -> bool:
    conf = row.get("sweep_confirmed", "").upper()
    dir_ = _direction(row)
    return (
        (dir_ == "LONG"  and "BULLISH" in conf and "CONFLICT" not in conf) or
        (dir_ == "SHORT" and "BEARISH" in conf and "CONFLICT" not in conf)
    )


def _strength_aligned(row: Dict) -> bool:
    try:
        diff = float(row.get("strength_diff", 0) or 0)
    except (ValueError, TypeError):
        return False
    dir_ = _direction(row)
    return (dir_ == "LONG" and diff > 5) or (dir_ == "SHORT" and diff < -5)


def _cross_aligned(row: Dict) -> bool:
    vix_r = row.get("vix_regime", "NORMAL").upper()
    dir_  = _direction(row)
    risk_off = vix_r in ("PANIC_BUILDING", )
    risk_on  = vix_r in ("PANIC_FADING", "FEAR_CLEARING")
    return (dir_ == "LONG" and risk_off) or (dir_ == "SHORT" and risk_on)


def _value_aligned(row: Dict) -> bool:
    verdict = row.get("value_verdict", "").upper()
    dir_    = _direction(row)
    return (dir_ == "LONG" and verdict == "BULLISH") or (dir_ == "SHORT" and verdict == "BEARISH")


# ── Weight construction ───────────────────────────────────────────────────────

def _build_learned_weights(regime: str, rows: List[Dict]) -> Dict[str, float]:
    """
    Construct weights proportional to each signal's accuracy score.
    Maps the 5 tracked signals to the 7 weight keys.
    """
    stats    = _compute_regime_stats(regime, rows)
    acc      = stats["signal_accuracy"]
    defaults = _DEFAULT_WEIGHTS.get(regime, {})

    # Map accuracy scores → raw weights (accuracy * default weight = adjusted)
    raw: Dict[str, float] = {}
    for key, default in defaults.items():
        if key in acc:
            raw[key] = acc[key] * default
        elif key == "news":
            raw[key] = acc.get("value", 0.5) * default   # proxy: news ≈ value context
        elif key == "rates":
            raw[key] = default * 0.8  # conservative — rates data is slow-moving
        elif key == "cot":
            raw[key] = default * 0.8  # conservative — COT data is weekly
        else:
            raw[key] = default

    # Normalise to sum to 1
    total = sum(raw.values()) or 1
    return {k: round(v / total, 4) for k, v in raw.items()}


def _blend(learned: Dict[str, float], default: Dict[str, float]) -> Dict[str, float]:
    """Blend learned weights with defaults to prevent overfitting."""
    return {
        k: round(LEARN_BLEND * learned.get(k, default[k]) + (1 - LEARN_BLEND) * default[k], 4)
        for k in default
    }


# ── I/O helpers ───────────────────────────────────────────────────────────────

def _load_journal() -> List[Dict]:
    if not JOURNAL_PATH.exists():
        return []
    try:
        with open(JOURNAL_PATH, newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def _save_weights(weights: Dict) -> None:
    from datetime import date
    payload = {
        "last_calibrated": date.today().isoformat(),
        "min_outcomes_required": MIN_OUTCOMES,
        "blend_ratio": LEARN_BLEND,
        "weights": weights,
    }
    WEIGHTS_PATH.write_text(json.dumps(payload, indent=2))


def _print_regime_report(
    regime: str, stats: Dict, calibrated: Optional[Dict]
) -> None:
    n        = stats.get("n", 0)
    win_rate = stats.get("win_rate", 0)
    acc      = stats.get("signal_accuracy", {})

    print(f"  {regime:15s}  {n:3d} outcomes  win rate: {win_rate}%")
    if n == 0:
        print(f"    No data yet (need {MIN_OUTCOMES} labeled outcomes)")
        return
    for sig, a in acc.items():
        bar = "█" * int(a * 10) + "░" * (10 - int(a * 10))
        print(f"    {sig:<10s} {bar}  {a:.0%}")
    if calibrated:
        print(f"    → Calibrated weights: " +
              ", ".join(f"{k}={v:.3f}" for k, v in calibrated.items()))
    else:
        print(f"    → Using defaults (need {MIN_OUTCOMES - n} more outcomes to calibrate)")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    run_calibration(report_only="--report" in sys.argv)
