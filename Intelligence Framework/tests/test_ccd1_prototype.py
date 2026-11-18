"""Positive control and near misses for studies/ccd1_prototype.py (the CCD-1
definition, spec bcc444a). A synthetic chart built to meet every condition
must be detected; each near miss must fail on the condition it breaks."""
import os, sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "studies"))
import ccd1_prototype as P

T0 = datetime(2026, 1, 5, 0, 0, tzinfo=timezone.utc)


def path(points, step=5):
    """Linear legs between turning points, `step` bars per leg."""
    out = [points[0]]
    for a, b in zip(points, points[1:]):
        out += [a + (b - a) * k / step for k in range(1, step + 1)]
    return out


def bars(closes, start, hours, wick=0.05):
    t = [start + timedelta(hours=hours * i) for i in range(len(closes))]
    prev = [closes[0]] + closes[:-1]
    # the close side gets the full wick and the open side half, so the bar
    # after a turn never ties the turn's high or low (the structure rule
    # counts ties, and two equal swings read as neither higher nor lower)
    H = [c + wick if c >= p else p + wick / 2 for p, c in zip(prev, closes)]
    L = [c - wick if c <= p else p - wick / 2 for p, c in zip(prev, closes)]
    return {"t": t, "H": H, "L": L, "C": list(closes)}


def daily(atr=10.0, n=40):
    t = [T0 - timedelta(days=n - i) for i in range(n)]
    return {"t": t, "H": [200 + atr / 2] * n, "L": [200 - atr / 2] * n, "C": [200.0] * n}


def h4_down(n=160):
    pts = [200 - 3 * k + (6 if k % 2 else 0) for k in range(n // 5 + 2)]
    c = path(pts)[:n]
    return bars(c, T0 - timedelta(hours=4 * n), 4)


def h1_chart(range_highs=(100.0, 99.6, 99.3), range_lows=(95.2, 95.0, 94.9), brk=94.0):
    """A falling leg into a range that steps down (lows alternate with highs,
    starting with a low), then a straight fall from the last high whose final
    bar is the first close below the range."""
    lead = path([200, 190, 193, 180, 183, 170, 173, 160, 163, 150, 153, 140, 143,
                 130, 133, 120, 123, 113], step=6)
    zig = []
    for lo, hi in zip(range_lows, range_highs):
        zig += [lo, hi]
    rng = path([lead[-1]] + zig + [brk], step=5)[1:]
    closes = lead + rng
    return bars(closes, T0, 1)


def run(h1, h4=None, d1=None):
    return P.detect(h1, len(h1["C"]) - 1, h4 or h4_down(), d1 or daily())


def test_positive_control_is_detected():
    r = run(h1_chart())
    assert r["why"] is None, r["why"]
    assert r["side"] == "DOWN"
    assert abs(r["range"]["low"] - (94.9 - 0.05)) < 1e-9
    assert len(r["tested_touches"]) >= 3


def test_no_close_beyond_is_not_a_detection():
    assert run(h1_chart(brk=96.0))["why"] == "no close beyond"


def test_two_touches_fail_the_touch_count():
    # the zone is 0.10 ATR = 1.0 below the range high (100.05): highs 100 and
    # 99.6 reach it, 98.6 does not (it would at a 0.20-ATR zone). Highs still
    # step down, so the trend holds and only the touch count fails.
    r = run(h1_chart(range_highs=(100.0, 99.6, 98.6)))
    assert r["why"] == "tested boundary touched 2 times (< 3)", r["why"]


def test_wide_range_is_not_a_range():
    # width 100 - 80 = 20 = 2.0 ATR > 1.2
    r = run(h1_chart(range_lows=(82.0, 81.0, 80.0), brk=79.0))
    assert r["why"] == "no range"


def test_uptrend_4h_blocks_a_downside_break():
    up = h4_down()
    up = {"t": up["t"], "H": [400 - x for x in up["L"]], "L": [400 - x for x in up["H"]], "C": [400 - x for x in up["C"]]}
    r = run(h1_chart(), h4=up)
    assert r["why"] and r["why"].startswith("trend not aligned"), r["why"]


def test_stop_arithmetic():
    r = run(h1_chart())
    s = P.stops(r)
    a = r["atr"]
    edge = r["range"]["high"] + 0.05 * a
    assert abs(s["same_session"][0] - max(0.30 * a, edge - r["close"])) < 1e-9
    assert abs(s["same_session"][1] - (r["close"] + s["same_session"][0])) < 1e-9
    assert [round(x[0], 9) for x in s["ten_session"]] == [round(0.60 * a, 9), round(0.84 * a, 9)]
