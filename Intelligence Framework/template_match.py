"""
template_match.py

Historical template matching for GBP/AUD setups.

Compares the current regime fingerprint against every labeled run in
run_journal.csv and returns a base-rate probability: when this exact
pattern appeared historically, what percentage resolved as WIN?

The fingerprint encodes:
  htf_context   — structural HTF regime (dominant driver)
  regime        — market regime (TRENDING/RANGING/VOLATILE)
  direction     — LONG / SHORT / NO TRADE
  sweep         — DOWN / UP / NONE
  macro_quadrant — Dalio growth-inflation quadrant

Matching is scored — partial matches still count, weighted by field importance.
"""

from __future__ import annotations
import csv
from pathlib import Path
from typing import Dict, List, Tuple

JOURNAL_PATH  = Path(__file__).parent / "run_journal.csv"
MIN_OUTCOMES  = 5    # minimum labeled rows before showing win-rate statistics
MATCH_CUTOFF  = 5    # minimum similarity score to count as a "match"

_FIELD_WEIGHTS = {
    "htf_context":    3,
    "regime":         2,
    "direction":      2,
    "sweep":          1,
    "macro_quadrant": 1,
    "session":        1,
}
MAX_SCORE = sum(_FIELD_WEIGHTS.values())  # 10


def build_fingerprint(report: Dict) -> Dict:
    """
    Extract the key state variables from a live report as a comparable fingerprint.
    Direction is taken from the decision engine output.
    """
    layers = report.get("layers", {})
    htf    = layers.get("htf", {})
    liq    = layers.get("liquidity", {})
    reg    = layers.get("regime", {})
    ses    = layers.get("session", {})
    macro  = layers.get("macro", {})
    dec    = report.get("decision", {})

    sweep_down = bool(liq.get("sweep_down"))
    sweep_up   = bool(liq.get("sweep_up"))
    sweep      = "DOWN" if sweep_down and not sweep_up else "UP" if sweep_up and not sweep_down else "NONE"

    return {
        "htf_context":    htf.get("context", ""),
        "regime":         reg.get("regime",  ""),
        "direction":      dec.get("direction", ""),
        "sweep":          sweep,
        "macro_quadrant": macro.get("quadrant", ""),
        "session":        ses.get("session_label") or ses.get("session", ""),
    }


def get_template_match(report: Dict) -> Dict:
    """
    Match current fingerprint against run_journal history.
    Returns statistics if enough labeled outcomes exist.
    """
    fp = build_fingerprint(report)

    if not JOURNAL_PATH.exists():
        return _no_data("No journal file yet — run history will accumulate here")

    rows = _load_journal()
    if not rows:
        return _no_data("Journal is empty — no historical data to compare")

    # Score every row against the current fingerprint
    scored: List[Tuple[int, Dict]] = []
    for row in rows:
        s = _similarity(fp, row)
        if s >= MATCH_CUTOFF:
            scored.append((s, row))

    scored.sort(key=lambda x: x[0], reverse=True)
    total_matches  = len(scored)
    labeled_matches = [(s, r) for s, r in scored if r.get("outcome_label", "").strip() in ("WIN", "LOSS", "NEUTRAL")]

    result = {
        "fingerprint":     fp,
        "total_matches":   total_matches,
        "labeled_matches": len(labeled_matches),
        "win_rate":        None,
        "loss_rate":       None,
        "sample_note":     "",
        "top_matches":     [],
        "message":         "",
    }

    # Top 3 most similar runs for display
    for score, row in scored[:3]:
        result["top_matches"].append({
            "date":      row.get("date", ""),
            "htf":       row.get("htf_context", ""),
            "regime":    row.get("regime", ""),
            "bias":      row.get("bias", ""),
            "outcome":   row.get("outcome_label", "?"),
            "score":     score,
        })

    if len(labeled_matches) < MIN_OUTCOMES:
        result["message"] = (
            f"Found {total_matches} similar setups, {len(labeled_matches)} labeled — "
            f"need {MIN_OUTCOMES} for statistics. Label runs via label_outcomes.py."
        )
        result["sample_note"] = f"{len(labeled_matches)}/{MIN_OUTCOMES} outcomes needed"
        return result

    # ── Compute win rate ──────────────────────────────────────────────────────
    wins    = sum(1 for _, r in labeled_matches if r.get("outcome_label") == "WIN")
    losses  = sum(1 for _, r in labeled_matches if r.get("outcome_label") == "LOSS")
    neutral = sum(1 for _, r in labeled_matches if r.get("outcome_label") == "NEUTRAL")
    total   = len(labeled_matches)

    win_rate  = round(wins  / total * 100)
    loss_rate = round(losses / total * 100)

    result["win_rate"]    = win_rate
    result["loss_rate"]   = loss_rate
    result["sample_note"] = f"{total} similar setups"
    result["message"]     = (
        f"Base rate: {win_rate}% WIN / {loss_rate}% LOSS / "
        f"{round(neutral/total*100)}% NEUTRAL across {total} similar setups"
    )
    return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _similarity(fp: Dict, row: Dict) -> int:
    """Score how similar a journal row is to the current fingerprint."""
    score = 0
    row_direction = "LONG" if row.get("bias") == "BULLISH" else "SHORT" if row.get("bias") == "BEARISH" else "NO TRADE"

    row_fp = {
        "htf_context":    row.get("htf_context", ""),
        "regime":         row.get("regime",  ""),
        "direction":      row_direction,
        "sweep":          _row_sweep(row),
        "macro_quadrant": row.get("macro_quadrant", ""),
        "session":        row.get("session", ""),
    }

    for field, weight in _FIELD_WEIGHTS.items():
        if fp.get(field) and fp[field] == row_fp.get(field):
            score += weight

    return score


def _row_sweep(row: Dict) -> str:
    down = str(row.get("sweep_down", "")).upper() in ("YES", "TRUE", "1")
    up   = str(row.get("sweep_up",   "")).upper() in ("YES", "TRUE", "1")
    if down and not up:   return "DOWN"
    if up   and not down: return "UP"
    return "NONE"


def _load_journal() -> List[Dict]:
    try:
        with open(JOURNAL_PATH, newline="") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def _no_data(msg: str) -> Dict:
    return {
        "fingerprint":     {},
        "total_matches":   0,
        "labeled_matches": 0,
        "win_rate":        None,
        "loss_rate":       None,
        "sample_note":     "",
        "top_matches":     [],
        "message":         msg,
    }
