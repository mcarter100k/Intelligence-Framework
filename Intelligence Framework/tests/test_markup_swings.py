"""
test_markup_swings.py — studies/markup_swings.py, the weekly markup's swing
prices (foundation/chart_reading_method.md §2; docs/gold_plan.md Phase A1).

No network: requests.get and the credential helpers are replaced with a fake
OANDA that serves synthetic candles whose ATR is known exactly (every candle
30 units high-to-low, never gapping more than 15, so every true range is 30).
Protections pinned here:
  U1 each instrument prints sizes in its own unit: pips for FX, dollars for gold
  U2 a metal with no unit entry is refused, never printed in pips
  U3 prices print at the instrument's precision
  S1 a swing is reported only once k candles have closed on each side
  S2 swings are labelled against the previous swing of the same kind
  A1 ATR is Wilder's: a simple mean of the first n true ranges, then smoothed
"""
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "studies"))
import markup_swings as MS  # noqa: E402

T0 = datetime(2026, 1, 5, tzinfo=timezone.utc)


def _bar(i, mid, half, complete=True):
    return (T0 + timedelta(hours=i), mid, mid + half, mid - half, mid, complete)


# ── U1-U3: units and precision ───────────────────────────────────────────────

def test_unit_table():
    assert MS.unit("XAU_USD") == (1.0, "dollars", 3)
    assert MS.unit("GBP_AUD") == (0.0001, "pips", 5)
    assert MS.unit("GBP_JPY") == (0.01, "pips", 3)


@pytest.mark.parametrize("pair", ["XAG_USD", "XAU_GBP", "XPT_USD"])
def test_metal_without_a_unit_is_refused(pair):
    with pytest.raises(SystemExit, match="no unit set"):
        MS.unit(pair)


def _zigzag(base, step, n=320):
    """Mid prices rising 5 candles, falling 5, so swings form; each step is
    at most half the 30-unit range, which keeps every true range at 30."""
    mids, m = [], base
    for i in range(n):
        m += step if (i // 5) % 2 == 0 else -step
        mids.append(m)
    return mids


class _Resp:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


def _fake_oanda(monkeypatch, base, step, half, live_bid, live_ask, decimals):
    fmt = f"{{:.{decimals}f}}".format

    def get(url, headers=None, timeout=None, params=None):
        if url.endswith("/pricing"):
            return _Resp({"prices": [{"bids": [{"price": fmt(live_bid)}], "asks": [{"price": fmt(live_ask)}],
                                      "time": "2026-11-13T21:59:00.000000000Z", "tradeable": False}]})
        mids = _zigzag(base, step, params["count"])
        candles = [{"time": (T0 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%S.000000000Z"),
                    "complete": True,
                    "mid": {"o": fmt(m), "h": fmt(m + half), "l": fmt(m - half), "c": fmt(m)}}
                   for i, m in enumerate(mids)]
        return _Resp({"candles": candles})

    monkeypatch.setattr(MS.requests, "get", get)
    monkeypatch.setattr(MS, "_account_id", lambda: "ACCT")
    monkeypatch.setattr(MS, "_headers", lambda: {})
    monkeypatch.setattr(MS, "_base_url", lambda: "https://fake.invalid")


def _atr_lines(out):
    return re.findall(r"^## \S+ \(k=\d\) ATR14 (.+?); last", out, re.M)


def test_gold_prints_dollars_not_pips(monkeypatch, capsys):
    _fake_oanda(monkeypatch, base=4000.0, step=10.0, half=15.0,
                live_bid=3884.45, live_ask=3884.92, decimals=3)
    MS.main("XAU_USD")
    out = capsys.readouterr().out
    assert _atr_lines(out) == ["30.0 dollars"] * len(MS.FRAMES)
    assert "pips" not in out
    assert "XAU_USD live mid 3884.685 at" in out
    swings = re.findall(r"swing (?:high|low ) (\S+) ", out)
    assert swings, "the synthetic zigzag must produce swings"
    assert all(re.fullmatch(r"\d+\.\d{3}", s) for s in swings)


def test_gbp_aud_still_prints_pips(monkeypatch, capsys):
    _fake_oanda(monkeypatch, base=1.9400, step=0.0010, half=0.0015,
                live_bid=1.94290, live_ask=1.94304, decimals=5)
    MS.main("GBP_AUD")
    out = capsys.readouterr().out
    assert _atr_lines(out) == ["30.0 pips"] * len(MS.FRAMES)
    assert "GBP_AUD live mid 1.94297 at" in out
    swings = re.findall(r"swing (?:high|low ) (\S+) ", out)
    assert swings and all(re.fullmatch(r"\d\.\d{5}", s) for s in swings)


def test_gbp_jpy_prints_pips_at_three_decimals(monkeypatch, capsys):
    _fake_oanda(monkeypatch, base=213.00, step=0.10, half=0.15,
                live_bid=213.075, live_ask=213.085, decimals=3)
    MS.main("GBP_JPY")
    out = capsys.readouterr().out
    assert _atr_lines(out) == ["30.0 pips"] * len(MS.FRAMES)
    assert "GBP_JPY live mid 213.080 at" in out
    swings = re.findall(r"swing (?:high|low ) (\S+) ", out)
    assert swings and all(re.fullmatch(r"\d{3}\.\d{3}", s) for s in swings)


# ── S1-S2: swings ────────────────────────────────────────────────────────────

def test_swing_needs_k_closed_candles_each_side():
    mids = [10, 11, 12, 15, 12, 11, 10]          # peak at index 3
    bars = [_bar(i, m, 0.5) for i, m in enumerate(mids)]
    assert [(k, p) for _, k, p in MS.swings(bars, 3)] == [("H", 15.5)]
    # One candle short on the right: not yet confirmed.
    assert [k for _, k, _ in MS.swings(bars[:-1], 3) if k == "H"] == []
    # The last candle still forming does not count toward confirmation.
    forming = bars[:-1] + [_bar(6, 10, 0.5, complete=False)]
    assert [k for _, k, _ in MS.swings(forming, 3) if k == "H"] == []


def test_swing_labels_compare_like_with_like():
    sw = [(T0, "H", 5.0), (T0, "L", 1.0), (T0, "H", 6.0), (T0, "L", 0.5),
          (T0, "H", 5.5), (T0, "L", 0.8)]
    assert [tag for *_, tag in MS.label(sw)] == ["  ", "  ", "HH", "LL", "LH", "HL"]


# ── A1: ATR ──────────────────────────────────────────────────────────────────

def test_atr_is_wilder_smoothed():
    # Ranges 1..16 with no gaps (open = close = mid): true range = range.
    bars = [_bar(i, 100.0, (i + 1) / 2) for i in range(17)]
    trs = [i + 1 for i in range(1, 17)]           # bars 1..16 (bar 0 has no previous close)
    a = sum(trs[:14]) / 14
    for tr in trs[14:]:
        a = (a * 13 + tr) / 14
    assert MS.atr(bars) == pytest.approx(a)
    assert MS.atr(bars) != pytest.approx(sum(trs[-14:]) / 14)   # not a plain recent mean
