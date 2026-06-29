"""
entry_confirmation.py
─────────────────────
Intraday entry confirmation layer. Only runs when the regime brief
shows LONG or SHORT. Fetches H1 and M15 bars and checks whether
the higher-timeframe setup is showing on the lower timeframes.

THRESHOLDS (all unvalidated — logged for Phase 1 review):
  H1 ADX trending threshold : 25 (matching D1 validated value)
  H1 ATR spike threshold    : 1.5x (conservative)
  M15                       : structure confirmation only,
                              no ADX regime classification

NOTE: "H1/15min thresholds unvalidated — entries logged for Phase 1 review"
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class EntryBrief:
    instrument:    str
    direction:     str   # LONG / SHORT (inherited from regime brief)

    # H1 fields
    h1_confirmed:    bool   # H4 setup showing on H1
    h1_structure:    str    # UPTREND / DOWNTREND / TRANSITIONAL
    h1_entry_level:  float  # nearest H1 support (long) or resistance (short)
    h1_adx:          float  # H1 ADX — unvalidated, logged only

    # M15 fields
    m15_trigger:  bool   # 15min entry trigger active
    m15_signal:   str    # plain English: what to look for
    m15_level:    float  # specific price level to enter at

    # Combined
    entry_ready:  bool   # h1_confirmed AND m15_trigger
    entry_note:   str    # one sentence on entry status

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
            _detect_structure, _compute_adx, compute_atr_series, PAIRS,
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
            if hasattr(raw_h1.columns, "levels"):
                raw_h1.columns = raw_h1.columns.get_level_values(0)
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
        m15_trigger = False
        m15_signal  = ""
        m15_level   = 0.0

        if raw_m15 is not None and not raw_m15.empty:
            if hasattr(raw_m15.columns, "levels"):
                raw_m15.columns = raw_m15.columns.get_level_values(0)
            m15h = [float(v) for v in raw_m15["High"].dropna().values]
            m15l = [float(v) for v in raw_m15["Low"].dropna().values]
            m15c = [float(v) for v in raw_m15["Close"].dropna().values]
            nm   = min(len(m15h), len(m15l), len(m15c))
            m15h, m15l, m15c = m15h[:nm], m15l[:nm], m15c[:nm]

            if nm >= 3:
                m15_struct = _detect_structure(m15h, m15l, m15c)
                m15_str    = m15_struct["structure"]

                if direction == "LONG":
                    m15_level = m15l[-1]    # current 15min low
                    if m15_str == "UPTREND":
                        m15_trigger = True
                        m15_signal  = (f"M15 uptrend confirmed — "
                                       f"enter on pullback to {m15_level:.4f} "
                                       f"or break of prior M15 high")
                    else:
                        m15_signal  = (f"M15 structure not aligned ({m15_str}) — "
                                       f"wait for M15 higher low at "
                                       f"~{m15_level:.4f} before entering")
                elif direction == "SHORT":
                    m15_level = m15h[-1]    # current 15min high
                    if m15_str == "DOWNTREND":
                        m15_trigger = True
                        m15_signal  = (f"M15 downtrend confirmed — "
                                       f"enter on bounce to {m15_level:.4f} "
                                       f"or break of prior M15 low")
                    else:
                        m15_signal  = (f"M15 structure not aligned ({m15_str}) — "
                                       f"wait for M15 lower high at "
                                       f"~{m15_level:.4f} before entering")

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
            entry_ready, entry_note,
        )

        return EntryBrief(
            instrument=instrument,
            direction=direction,
            h1_confirmed=h1_confirmed,
            h1_structure=h1_structure,
            h1_entry_level=h1_entry_level,
            h1_adx=h1_adx,
            m15_trigger=m15_trigger,
            m15_signal=m15_signal,
            m15_level=m15_level,
            entry_ready=entry_ready,
            entry_note=entry_note,
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
            h1_adx=0.0,
            m15_trigger=False,
            m15_signal="",
            m15_level=0.0,
            entry_ready=False,
            entry_note=f"Entry confirmation error: {str(e)[:60]}",
            precision_brief=precision_brief,
            error=str(e),
        )


def _format_entry(
    instrument:      str,
    direction:       str,
    h1_confirmed:    bool,
    h1_structure:    str,
    h1_entry_level:  float,
    h1_adx:          float,
    m15_trigger:     bool,
    m15_signal:      str,
    m15_level:       float,
    entry_ready:     bool,
    entry_note:      str,
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
        f"  M15 SIGNAL    {wrap(m15_signal)}",
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
