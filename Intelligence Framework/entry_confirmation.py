"""
entry_confirmation.py
─────────────────────
Intraday entry confirmation layer. Only runs when the regime brief
shows LONG or SHORT. Fetches H1 and M15 bars and checks whether
the higher-timeframe setup is showing on the lower timeframes.

THRESHOLDS (all unvalidated — logged for Phase 1 review):
  H1 ADX trending threshold : 25 (same as the daily threshold, INFORMED PRIOR)
  H1 ATR spike threshold    : 1.5x (conservative)
  M15                       : structure confirmation only,
                              no ADX regime classification

NOTE: "H1/15min thresholds unvalidated — entries logged for Phase 1 review"
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

_M15_LEVEL_PROXIMITY_PIPS = 25  # pips — M15 must be within this of a key level


def _detect_engulfing(
    highs:  List[float],
    lows:   List[float],
    opens:  List[float],
    closes: List[float],
) -> dict:
    """
    Detect engulfing candle on the most recent two candles (array-based API).
    Returns {"detected": bool, "direction": "LONG"|"SHORT"|"", "pattern": str}.

    # INFORMED PRIOR — engulfing trigger is a precise entry
    # definition, not a validated edge. Outcome logger records
    # trigger usage for future validation.
    """
    if min(len(highs), len(lows), len(opens), len(closes)) < 2:
        return {"detected": False, "direction": "", "pattern": ""}

    prev_body_high = max(opens[-2], closes[-2])
    prev_body_low  = min(opens[-2], closes[-2])

    # Bullish engulfing: current bullish body engulfs previous body entirely
    if (closes[-1] > opens[-1]
            and closes[-1] >= prev_body_high
            and opens[-1]  <= prev_body_low):
        return {"detected": True, "direction": "LONG",
                "pattern": "Bullish engulfing"}

    # Bearish engulfing: current bearish body engulfs previous body entirely
    if (closes[-1] < opens[-1]
            and opens[-1]  >= prev_body_high
            and closes[-1] <= prev_body_low):
        return {"detected": True, "direction": "SHORT",
                "pattern": "Bearish engulfing"}

    return {"detected": False, "direction": "", "pattern": ""}


@dataclass
class EntryBrief:
    instrument:    str
    direction:     str   # LONG / SHORT (inherited from regime brief)

    # H1 fields
    h1_confirmed:    bool   # H4 setup showing on H1
    h1_structure:    str    # UPTREND / DOWNTREND / TRANSITIONAL
    h1_entry_level:  float  # nearest H1 support (long) or resistance (short)

    # M15 fields
    m15_trigger:  bool   # 15min entry trigger active

    # Engulfing + level proximity (ported from entry_watcher)
    engulfing_detected: bool
    near_key_level:     bool
    trigger_basis:      str   # plain English: what fired and why

    # Combined
    entry_ready:  bool   # h1_confirmed AND m15_trigger

    # Formatted output
    precision_brief: str

    error: Optional[str] = None


def get_entry_brief(instrument: str, direction: str) -> EntryBrief:
    """
    Build an entry confirmation brief for the given instrument and direction.

    Args:
        instrument: "GBP_AUD" or "GBP_JPY"
        direction:  "LONG" or "SHORT" (from regime brief)

    Returns:
        EntryBrief dataclass. Never raises — returns safe brief on error.
    """
    try:
        from oanda_feed import get_hourly_bars, get_m15_bars
        from regime_detection import (
            _detect_structure, _compute_adx, PAIRS,
        )

        pair_cfg   = PAIRS.get(instrument, PAIRS["GBP_AUD"])
        oanda_pair = pair_cfg.instrument.replace("_", "")

        # ── Fetch H1 bars ─────────────────────────────────────────────────────
        raw_h1 = get_hourly_bars(pair=oanda_pair, count=72)
        h1_confirmed   = False
        h1_structure   = "TRANSITIONAL"
        h1_entry_level = 0.0
        h1_adx         = 0.0

        if raw_h1 is not None and not raw_h1.empty:
            h1h = [float(v) for v in raw_h1["High"].dropna().values]
            h1l = [float(v) for v in raw_h1["Low"].dropna().values]
            h1c = [float(v) for v in raw_h1["Close"].dropna().values]
            n   = min(len(h1h), len(h1l), len(h1c))
            h1h, h1l, h1c = h1h[:n], h1l[:n], h1c[:n]

            if n >= 42:   # 3 * 14 — same min as D1
                h1_struct  = _detect_structure(h1h, h1l, h1c)
                h1_structure = h1_struct["structure"]
                h1_adx     = _compute_adx(h1h, h1l, h1c)

                # H1 confirmed when structure aligns with direction
                if direction == "LONG" and h1_structure == "UPTREND":
                    h1_confirmed = True
                    h1_entry_level = (h1_struct.get("latest_sl") or
                                      h1l[-1])
                elif direction == "SHORT" and h1_structure == "DOWNTREND":
                    h1_confirmed = True
                    h1_entry_level = (h1_struct.get("latest_sh") or
                                      h1h[-1])
                else:
                    # Structure not aligned — use current price area
                    h1_entry_level = h1c[-1]

        # ── Fetch M15 bars ────────────────────────────────────────────────────
        raw_m15 = get_m15_bars(pair=oanda_pair, count=10)
        m15_trigger        = False
        m15_signal         = ""
        m15_level          = 0.0
        engulfing_detected = False
        near_key_level     = False
        key_level_price    = None
        trigger_basis      = ""
        _eng = {"detected": False, "direction": "", "pattern": ""}

        if raw_m15 is not None and not raw_m15.empty:
            m15h = [float(v) for v in raw_m15["High"].dropna().values]
            m15l = [float(v) for v in raw_m15["Low"].dropna().values]
            m15c = [float(v) for v in raw_m15["Close"].dropna().values]
            m15o = ([float(v) for v in raw_m15["Open"].dropna().values]
                    if "Open" in raw_m15.columns else list(m15c))
            nm   = min(len(m15h), len(m15l), len(m15c), len(m15o))
            m15h, m15l, m15c, m15o = (m15h[:nm], m15l[:nm],
                                       m15c[:nm], m15o[:nm])

            # Engulfing detection (ported from entry_watcher)
            if nm >= 2:
                _eng = _detect_engulfing(m15h, m15l, m15o, m15c)
                engulfing_detected = _eng["detected"]

            # Level proximity check via levels_context, keyed to THIS pair
            # (docs/specs/level_source_repair_spec.md D1+D2). Formerly read
            # last_run.json — an artifact whose only writer was
            # shadow/market_brain.py, quarantined 2026-07-29; it froze at
            # 2026-06-10 and carried one pair's levels with no instrument
            # key, so GBP_JPY could never reach m15_trigger. Asking the
            # live module directly removes both the staleness class and
            # the pair mismatch.
            _level_available = False
            _levels: List[float] = []
            try:
                from levels_context import get_key_levels, levels_as_list
                _levels = levels_as_list(get_key_levels(oanda_pair))
                _level_available = bool(_levels)
            except Exception:
                _level_available = False

            prox = _M15_LEVEL_PROXIMITY_PIPS * pair_cfg.pip_size
            if _level_available and _levels and nm >= 1:
                for _lvl in _levels:
                    if abs(m15c[-1] - _lvl) <= prox:
                        near_key_level  = True
                        key_level_price = _lvl
                        break

            # M15 trigger: engulfing in direction + near key level (both required)
            if nm >= 2:
                if direction == "LONG":
                    m15_level = m15l[-1]
                elif direction == "SHORT":
                    m15_level = m15h[-1]

                _in_dir = (engulfing_detected and
                           _eng["direction"] == direction)

                if _in_dir:
                    if near_key_level:
                        m15_trigger   = True
                        trigger_basis = (f"{_eng['pattern']} at key level "
                                         f"{key_level_price:.4f}")
                        m15_signal    = (f"{_eng['pattern']} at level "
                                         f"{key_level_price:.4f} — enter on "
                                         f"close above/below engulfing candle")
                    elif not _level_available:
                        # Missing level data is NOT READY, never a looser
                        # trigger (decision_logic_spec D6): the key-level
                        # check is half the trigger, and a failed feed must
                        # not quietly waive it.
                        m15_trigger   = False
                        trigger_basis = (f"{_eng['pattern']} seen, but level "
                                         f"data unavailable — cannot confirm "
                                         f"the entry at a key level; not ready")
                        m15_signal    = (f"{_eng['pattern']} — level data "
                                         f"unavailable, so the key-level "
                                         f"check cannot run; do not enter "
                                         f"on the pattern alone")
                    else:
                        trigger_basis = (f"{_eng['pattern']} detected, "
                                         f"not near a key level "
                                         f"(threshold "
                                         f"{_M15_LEVEL_PROXIMITY_PIPS}p)")
                        m15_signal    = (f"{_eng['pattern']} at "
                                         f"{m15c[-1]:.4f} — not near a key "
                                         f"level, wait for price to reach "
                                         f"structure ({m15_level:.4f})")
                else:
                    _patt = ("bullish engulfing" if direction == "LONG"
                             else "bearish engulfing")
                    trigger_basis = f"No {_patt} in trade direction"
                    m15_signal    = (f"No {_patt} detected — watch M15 "
                                     f"for {_patt} at key level near "
                                     f"{m15_level:.4f}")

        # ── Combined judgment ─────────────────────────────────────────────────
        entry_ready = h1_confirmed and m15_trigger

        if entry_ready:
            entry_note = (f"Entry conditions met — H1 {h1_structure} "
                          f"confirmed, M15 trigger active at {m15_level:.4f}.")
        elif h1_confirmed and not m15_trigger:
            entry_note = (f"H1 confirmed, waiting on M15 — "
                          f"{m15_signal[:60]}")
        elif not h1_confirmed and m15_trigger:
            entry_note = (f"M15 trigger active but H1 structure not aligned "
                          f"({h1_structure}) — do not enter yet.")
        else:
            entry_note = (f"No confirmation on either timeframe — "
                          f"H1: {h1_structure}, M15 trigger: False.")

        precision_brief = _format_entry(
            instrument, direction,
            h1_confirmed, h1_structure, h1_entry_level, h1_adx,
            m15_trigger, m15_signal, m15_level,
            engulfing_detected, near_key_level, key_level_price, trigger_basis,
            entry_ready, entry_note,
        )

        return EntryBrief(
            instrument=instrument,
            direction=direction,
            h1_confirmed=h1_confirmed,
            h1_structure=h1_structure,
            h1_entry_level=h1_entry_level,
            m15_trigger=m15_trigger,
            engulfing_detected=engulfing_detected,
            near_key_level=near_key_level,
            trigger_basis=trigger_basis,
            entry_ready=entry_ready,
            precision_brief=precision_brief,
        )

    except Exception as e:
        precision_brief = _format_error(instrument, direction, str(e))
        return EntryBrief(
            instrument=instrument,
            direction=direction,
            h1_confirmed=False,
            h1_structure="UNKNOWN",
            h1_entry_level=0.0,
            m15_trigger=False,
            engulfing_detected=False,
            near_key_level=False,
            trigger_basis="",
            entry_ready=False,
            precision_brief=precision_brief,
            error=str(e),
        )


def _format_entry(
    instrument:         str,
    direction:          str,
    h1_confirmed:       bool,
    h1_structure:       str,
    h1_entry_level:     float,
    h1_adx:             float,
    m15_trigger:        bool,
    m15_signal:         str,
    m15_level:          float,
    engulfing_detected: bool,
    near_key_level:     bool,
    key_level_price:    Optional[float],
    trigger_basis:      str,
    entry_ready:        bool,
    entry_note:         str,
) -> str:
    width  = 51
    border = "─" * width

    def tick(b: bool) -> str:
        return "✓" if b else "✗"

    def wrap(text: str, indent: int = 17) -> str:
        if len(text) <= width - indent:
            return text
        words = text.split()
        lines_out = []
        current   = ""
        for word in words:
            if len(current) + len(word) + 1 <= width - indent:
                current = f"{current} {word}".strip()
            else:
                if current:
                    lines_out.append(current)
                current = word
        if current:
            lines_out.append(current)
        pad = " " * indent
        return f"\n{pad}".join(lines_out)

    ready_str = "ENTRY READY" if entry_ready else "NOT READY"
    adx_note  = f"{h1_adx:.1f}" if h1_adx > 0 else "n/a"

    lines = [
        border,
        f"  ENTRY CONFIRMATION  {instrument.replace('_','/')}  [{direction}]",
        border,
        f"",
        f"  H1 CONFIRMED  {tick(h1_confirmed)}  "
        f"Structure: {h1_structure}  ADX: {adx_note}",
        f"  H1 LEVEL      {h1_entry_level:.4f}" if h1_entry_level else
        f"  H1 LEVEL      n/a",
        f"",
        f"  M15 TRIGGER   {tick(m15_trigger)}",
        f"  ENGULFING     {tick(engulfing_detected)}",
        (f"  NEAR LEVEL    {tick(near_key_level)}" +
         (f"  {key_level_price:.4f}" if key_level_price else "")),
        f"  M15 SIGNAL    {wrap(m15_signal)}",
    ]
    if trigger_basis:
        lines.append(f"  TRIGGER BASIS {wrap(trigger_basis)}")
    lines += [
        f"",
        f"  STATUS        {ready_str}",
        f"  NOTE          {wrap(entry_note)}",
        f"",
        f"  ⚠  H1/15min thresholds unvalidated —",
        f"     entries logged for Phase 1 review",
        border,
    ]
    return "\n".join(lines)


def _format_error(instrument: str, direction: str, error: str) -> str:
    width  = 51
    border = "─" * width
    return "\n".join([
        border,
        f"  ENTRY CONFIRMATION  {instrument.replace('_','/')}  [{direction}]",
        border,
        f"  ERROR: {error[:45]}",
        f"  Entry confirmation unavailable.",
        border,
    ])
