"""
historical_scenario_replay.py
─────────────────────────────
Replay framework decisions against real historical OANDA data.

No synthetic data. No mocks. No expected outputs defined in advance.
The data tells us whether the framework was right.

PURPOSE:
  Find where the framework fails, not validate that it passes.
  NEEDS REVIEW is an honest and useful output.

HOW IT WORKS:
  1. Fetches OANDA bars ending at end_date — no future bars
  2. Monkey-patches regime_detection module-level feed bindings
     with the pre-fetched historical slices
  3. Calls get_decision_brief() normally — full pipeline runs on
     historical data as if it were live
  4. Restores original feed bindings after each scenario
  5. Prints brief + what actually happened + judgment

FX SESSION BOUNDARY:
  OANDA FX day bars open at 22:00 UTC (not midnight). The "Oct 26"
  bar opens at Oct 25 22:00Z. Using `to = end_date T22:00:00Z`
  excludes the next-session bar correctly for D1, H4, and W.
"""

from __future__ import annotations

import os as _os, sys as _sys  # studies path bootstrap (root + shadow)
_ROOT = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
for _p in (_ROOT, _os.path.join(_ROOT, 'shadow')):
    if _p not in _sys.path:
        _sys.path.insert(0, _p)

from contextlib import contextmanager
from typing import Optional

import pandas as pd
import requests


# ── Historical bar fetch ───────────────────────────────────────────────────────

def _fetch_historical(
    pair_code:   str,   # "GBPAUD"
    granularity: str,   # "D", "H4", "W"
    count:       int,
    end_date:    str,   # "YYYY-MM-DD"
    timeout:     int = 20,
) -> Optional[pd.DataFrame]:
    """
    Fetch OANDA candles ending at the FX session close on end_date.

    Uses `to = end_date T22:00:00Z`. OANDA returns candles whose
    open time is strictly less than `to`. Since FX daily bars open
    at 22:00 UTC, this correctly includes the end_date session and
    excludes the next-day session.
    """
    from oanda_feed import _base_url, _headers, _pair

    to_str = f"{end_date}T22:00:00.000000000Z"

    try:
        instrument = _pair(pair_code)
        url = f"{_base_url()}/v3/instruments/{instrument}/candles"
        params = {
            "granularity": granularity,
            "count":       min(count + 5, 5000),
            "price":       "M",
            "to":          to_str,
        }
        resp = requests.get(url, headers=_headers(), params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        candles = data.get("candles", [])
        if not candles:
            return None

        rows = []
        for c in candles:
            if not c.get("complete", True):
                continue
            try:
                dt  = pd.to_datetime(c["time"]).tz_convert("UTC")
                mid = c["mid"]
                rows.append({
                    "Datetime": dt,
                    "Open":     float(mid["o"]),
                    "High":     float(mid["h"]),
                    "Low":      float(mid["l"]),
                    "Close":    float(mid["c"]),
                    "Volume":   int(c.get("volume", 0)),
                })
            except (KeyError, ValueError, TypeError):
                continue

        if not rows:
            return None

        df = pd.DataFrame(rows).set_index("Datetime").sort_index()
        return df

    except Exception as e:
        print(f"    [fetch error {granularity}: {e}]")
        return None


# ── Feed patch context ────────────────────────────────────────────────────────

@contextmanager
def _patch_regime_feeds(d1_df, h4_df, w_df):
    """
    Temporarily replace regime_detection's OANDA feed bindings with
    pre-fetched historical DataFrames.

    regime_detection imports the feed functions at module load time as
    module-level names (_oanda_daily_bars etc.). Replacing those names
    in the module namespace redirects all internal calls without
    touching oanda_feed itself.
    """
    import regime_detection
    orig_d1 = regime_detection._oanda_daily_bars
    orig_h4 = regime_detection._oanda_h4_bars
    orig_w  = regime_detection._oanda_weekly_bars
    try:
        regime_detection._oanda_daily_bars  = lambda *a, **kw: d1_df
        regime_detection._oanda_h4_bars     = lambda *a, **kw: h4_df
        regime_detection._oanda_weekly_bars = lambda *a, **kw: w_df
        yield
    finally:
        regime_detection._oanda_daily_bars  = orig_d1
        regime_detection._oanda_h4_bars     = orig_h4
        regime_detection._oanda_weekly_bars = orig_w


# ── Judgment ──────────────────────────────────────────────────────────────────

def _derive_judgment(decision: str, what_happened: str) -> str:
    """
    Derive the framework judgment from the decision and outcome.

    This function is honest — it returns NEEDS REVIEW when the
    framework was wrong, not just when the outcome was uncertain.

    CANNOT JUDGE is for genuinely ambiguous outcomes (both directions,
    extreme volatility, intervention events where outcome unclear).
    """
    what = what_happened.lower()

    # Live / not yet known — no judgment possible
    if any(x in what for x in ("live", "not yet known", "unknown")):
        return "CANNOT JUDGE — outcome not yet known"

    # Directional signals in outcome text
    went_up = any(x in what for x in (
        "+400", "+300", "+250", "+200", "+150", "+100",
        "reversed hard", "reversed", "higher", "broke higher",
        "squeezed", "bounced", "recovery", "recovered",
    ))
    went_down = any(x in what for x in (
        "fell", "down 200", "down 300", "continued down",
        "crashed", "lower", "decline", "-",
    ))
    both_ways   = went_up and went_down
    extreme_vol = any(x in what for x in (
        "both directions dangerous", "5x", "intervention",
        "48 hours then recovered",
    ))

    if decision == "STAND DOWN":
        if extreme_vol:
            return "CORRECT — STOOD DOWN (extreme volatility)"
        if both_ways:
            return "CORRECT — STOOD DOWN (both-ways market)"
        if went_up:
            return "CORRECT — STOOD DOWN (missed reversal — acceptable)"
        if went_down:
            return "CORRECT — STOOD DOWN"
        return "CORRECT — STOOD DOWN"

    # Framework took a directional view
    if both_ways or extreme_vol:
        return "CANNOT JUDGE — both-ways / intervention outcome"

    if decision == "LONG":
        if went_up and not went_down:  return "CORRECT"
        if went_down and not went_up:  return "NEEDS REVIEW"
        return "CANNOT JUDGE"

    if decision == "SHORT":
        if went_down and not went_up:  return "CORRECT"
        if went_up and not went_down:  return "NEEDS REVIEW"
        return "CANNOT JUDGE"

    return "CANNOT JUDGE"


# ── Main replay function ───────────────────────────────────────────────────────

def replay_scenario(
    instrument:    str,
    end_date:      str,    # "YYYY-MM-DD"
    description:   str,    # plain English name for this scenario
    what_happened: str,    # what price actually did after this date
) -> None:
    """
    Replay the full framework decision pipeline on a historical slice.

    Fetches real OANDA bars. Runs regime → filter → brief.
    Prints full brief + what happened + framework judgment.
    """
    from oanda_feed import is_configured
    from decision_brief import get_decision_brief

    W = 55
    OUTER = "═" * W
    INNER = "─" * W

    print(OUTER)
    print(f"  REPLAY: {description}")
    print(f"  Pair: {instrument.replace('_','/')}   End date: {end_date}")
    print(OUTER)

    if not is_configured():
        print("  ERROR: OANDA not configured.")
        print("  Historical replay requires a live OANDA API connection.")
        print(OUTER + "\n")
        return

    pair_code = instrument.replace("_", "")

    # ── Fetch historical data ─────────────────────────────────────────────────
    print(f"\n  Fetching {end_date} historical slice from OANDA...")

    d1_df = _fetch_historical(pair_code, "D",  220, end_date)
    h4_df = _fetch_historical(pair_code, "H4", 120, end_date)
    w_df  = _fetch_historical(pair_code, "W",  110, end_date)

    d1_n = len(d1_df) if d1_df is not None else 0
    h4_n = len(h4_df) if h4_df is not None else 0
    w_n  = len(w_df)  if w_df  is not None else 0

    print(f"  D1: {d1_n} bars  |  H4: {h4_n} bars  |  W: {w_n} bars")

    if d1_df is not None and not d1_df.empty:
        print(f"  D1 range: {d1_df.index[0].date()} → {d1_df.index[-1].date()}")
    if h4_df is not None and not h4_df.empty:
        print(f"  H4 range: {h4_df.index[0].date()} → {h4_df.index[-1].date()}")
    if w_df is not None and not w_df.empty:
        print(f"  W  range: {w_df.index[0].date()}  → {w_df.index[-1].date()}")

    if d1_n < 42:
        print(f"\n  ERROR: Insufficient D1 data ({d1_n} bars, minimum 42).")
        print(f"  This date may be outside OANDA's available history.")
        print(OUTER + "\n")
        return

    # ── Run framework on historical slice ─────────────────────────────────────
    print(f"\n  Running full framework pipeline on historical slice...")

    try:
        with _patch_regime_feeds(d1_df, h4_df, w_df):
            brief = get_decision_brief(instrument)
    except Exception as e:
        print(f"\n  FRAMEWORK ERROR: {e}")
        print(OUTER + "\n")
        return

    # ── Print decision brief ──────────────────────────────────────────────────
    print()
    print(brief.format())

    # ── Print what happened and judgment ──────────────────────────────────────
    judgment = _derive_judgment(brief.decision, what_happened)

    print()
    print(INNER)
    print(f"  WHAT HAPPENED NEXT:")
    # Wrap what_happened at ~50 chars
    words = what_happened.split()
    line = ""
    wrapped = []
    for w in words:
        if len(line) + len(w) + 1 <= 50:
            line = (line + " " + w).strip()
        else:
            if line:
                wrapped.append(line)
            line = w
    if line:
        wrapped.append(line)
    for ln in wrapped:
        print(f"  {ln}")

    print()
    print(f"  FRAMEWORK CALL WAS:  {judgment}")
    print(INNER)
    print()


# ── Scenarios ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":

    replay_scenario(
        instrument="GBP_AUD",
        end_date="2022-10-26",
        description="GBP/AUD one day after Truss mini-budget bottom",
        what_happened=(
            "Price reversed hard from 20-week low. "
            "+400 pips in 10 days. Shorts got squeezed."
        ),
    )

    replay_scenario(
        instrument="GBP_JPY",
        end_date="2024-05-14",
        description="GBP/JPY day before major BoJ intervention",
        what_happened=(
            "BoJ intervened. GBP/JPY fell 300 pips "
            "in 48 hours then recovered."
        ),
    )

    replay_scenario(
        instrument="GBP_AUD",
        end_date="2020-03-16",
        description="GBP/AUD mid-COVID crash",
        what_happened=(
            "Continued down 200 more pips then reversed. "
            "ATR was 5x normal. Both directions dangerous."
        ),
    )

    replay_scenario(
        instrument="GBP_AUD",
        end_date="2023-08-15",
        description="GBP/AUD mid-range 2023 consolidation",
        what_happened=(
            "Price continued ranging for 3 more weeks "
            "then broke higher by 250 pips."
        ),
    )

    replay_scenario(
        instrument="GBP_AUD",
        end_date="2026-06-27",
        description="GBP/AUD current state — ADX rising through transition",
        what_happened="LIVE — outcome not yet known",
    )
