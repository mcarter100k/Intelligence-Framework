"""
test_gold_breakout_study.py — studies/gold_breakout_study.py
(docs/specs/gold_breakout_study_spec.md §6). Synthetic bars only; no real
gold statistic is computed here.

Every scenario starts with 20 slowly rising bars (true range 2, no swings),
then a swing high at 105 (day 21), confirmed at the close of day 24, so it is
the level from day 25. The downside is the same bars mirrored (p -> 200 - p).
"""
import csv
import hashlib
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "studies"))
import gold_breakout_study as S  # noqa: E402
import markup_swings as MS  # noqa: E402


def bars_from(hlc, start=0):
    return [(f"T{start + i:04d}", c, h, l, c, True) for i, (h, l, c) in enumerate(hlc)]


def base(n=20):
    return [(100 + 0.01 * i, 98 + 0.01 * i, 99 + 0.01 * i) for i in range(n)]


PEAK = [(103, 100, 102), (105, 102, 104), (104, 101, 102), (103, 100, 101), (102.5, 99.5, 100.5)]
HELD = [(104, 100.5, 101), (106, 103, 105.5), (106.5, 105.2, 106), (107.5, 106, 107),
        (108.5, 107, 108), (109, 107.5, 108.5)]
WICK_FAIL = [(104, 100.5, 101), (106, 103, 104.5), (105.8, 103, 104), (104.5, 102, 103),
             (104, 101.5, 102.5), (103.5, 101, 102), (103, 100.8, 101.5)]
CLOSE_FAIL = [(104, 100.5, 101), (106, 103, 105.5), (105.5, 103, 104), (104.5, 102, 103),
              (104, 101.5, 102.5), (103.5, 101, 102)]
# A lower swing high at 104.5 (day 27, confirmed day 30) replaces 105 as the level.
LATEST = [(104, 100.5, 101), (104.2, 101, 102), (104.5, 102, 103.5), (104, 101.5, 102),
          (103.5, 101, 101.5), (103, 100.8, 101), (104.8, 102, 104.7), (105, 103, 104.6),
          (104.9, 103.5, 104.7), (105, 104, 104.8)]


def scenario(tail, n_base=20):
    return bars_from(base(n_base) + PEAK + tail)


def mirror(bars):
    return [(t, 200 - o, 200 - l, 200 - h, 200 - c, ok) for t, o, h, l, c, ok in bars]


def ups(evs, d):
    return [e for e in evs if e["def"] == d and e["side"] == "up"]


def downs(evs, d):
    return [e for e in evs if e["def"] == d and e["side"] == "down"]


# ── events ───────────────────────────────────────────────────────────────────

def test_the_swing_is_the_level_from_the_fourth_day():
    sw = MS.swings(scenario(HELD), 3)
    assert ("T0021", "H", 105) in sw


def test_a_held_break_up_and_mirrored_down():
    b = scenario(HELD)
    atr = S.atr_series(b)
    evs = S.events(b)
    w, c = ups(evs, "W"), ups(evs, "C")
    assert [(e["day"], e["level"], e["status"]) for e in w] == [("T0026", 105, "held")]
    assert [(e["day"], e["level"], e["status"]) for e in c] == [("T0026", 105, "held")]
    assert c[0]["distance_atr"] == pytest.approx(0.5 / atr[25])        # ATR of day d - 1
    assert w[0]["overshoot_atr"] == pytest.approx(4.0 / atr[25])       # 109 - 105 over d..d+4
    m = S.events(mirror(b))
    assert [(e["day"], e["level"], e["status"]) for e in downs(m, "W")] == [("T0026", 95, "held")]
    assert [(e["day"], e["level"], e["status"]) for e in downs(m, "C")] == [("T0026", 95, "held")]


def test_a_wick_that_closes_back_inside_fails_and_is_no_close_break():
    for b, pick in ((scenario(WICK_FAIL), ups), (mirror(scenario(WICK_FAIL)), downs)):
        evs = S.events(b)
        assert [(e["day"], e["status"]) for e in pick(evs, "W")] == [("T0026", "failed")]
        assert pick(evs, "C") == []


def test_a_close_beyond_then_back_inside_fails_both():
    for b, pick in ((scenario(CLOSE_FAIL), ups), (mirror(scenario(CLOSE_FAIL)), downs)):
        evs = S.events(b)
        assert [(e["day"], e["status"]) for e in pick(evs, "W")] == [("T0026", "failed")]
        assert [(e["day"], e["status"]) for e in pick(evs, "C")] == [("T0026", "failed")]


def test_close_failure_window_is_the_next_three_days():
    # Held for C only if days d+1..d+3 stay beyond; a close back inside on d+4 does not count.
    tail = [(104, 100.5, 101), (106, 103, 105.5), (106, 105.1, 105.6), (106, 105.1, 105.7),
            (106, 105.1, 105.8), (105.5, 103, 104)]
    assert [e["status"] for e in ups(S.events(scenario(tail)), "C")] == ["held"]
    # ...while a close back inside on d+3 does.
    tail2 = tail[:4] + [(106, 103, 104.9), (105.5, 103, 104)]
    assert [e["status"] for e in ups(S.events(scenario(tail2)), "C")] == ["failed"]


def test_wick_failure_window_includes_the_break_day_and_stops_at_d_plus_2():
    # Closes beyond on d, d+1, d+2, back inside on d+3: W held.
    tail = [(104, 100.5, 101), (106, 103, 105.5), (106, 105.1, 105.6), (106, 105.1, 105.7),
            (105.5, 103, 104), (105, 103, 104)]
    assert [e["status"] for e in ups(S.events(scenario(tail)), "W")] == ["held"]


def test_each_level_fires_once():
    # WICK_FAIL pokes above 105 on day 26 and again on day 27: one W event.
    evs = S.events(scenario(WICK_FAIL))
    assert len([e for e in ups(evs, "W") if e["level"] == 105]) == 1


def test_the_latest_confirmed_swing_is_the_level():
    evs = S.events(scenario(LATEST))
    assert [(e["day"], e["level"]) for e in ups(evs, "W")] == [("T0031", 104.5)]
    assert [(e["day"], e["level"], e["status"]) for e in ups(evs, "C")] == [("T0031", 104.5, "held")]


def test_ungraded_and_warm_up_are_counted_apart():
    evs = S.events(scenario(HELD)[:28])           # no day d+2 (28) for the day-26 break
    assert [e["status"] for e in ups(evs, "W")] == ["ungraded"]
    assert [e["status"] for e in ups(evs, "C")] == ["ungraded"]
    short = scenario(HELD, n_base=5)              # ATR not defined until bar 14
    assert {e["status"] for e in ups(S.events(short), "W")} == {"warm-up"}
    t = S.tally(S.events(short))
    assert t["n"] == 0 and t["warmup"] >= 1


# ── data loading ─────────────────────────────────────────────────────────────

def _write(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_utc", "o", "h", "l", "c", "span"])
        w.writerows(rows)
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def test_load_splits_eras_and_drops_forward_and_pre_start(tmp_path):
    p = str(tmp_path / "x.csv")
    sha = _write(p, [["2006-03-19T22:00:00+00:00", 1, 2, 0.5, 1.5, "STUDY"],
                     ["2006-03-20T22:00:00+00:00", 1, 2, 0.5, 1.5, "STUDY"],
                     ["2021-04-26T21:00:00+00:00", 3, 4, 2.5, 3.5, "USED"],
                     ["2026-09-10T21:00:00+00:00", 5, 6, 4.5, 5.5, "FORWARD"]])
    got = S.load(p, sha, start=S.GOLD_START)
    assert [b[0][:10] for b in got["STUDY"]] == ["2006-03-20"]
    assert [b[0][:10] for b in got["USED"]] == ["2021-04-26"]
    assert set(got) == {"STUDY", "USED"}


def test_load_refuses_an_exam_row(tmp_path):
    p = str(tmp_path / "x.csv")
    sha = _write(p, [["2013-12-29T22:00:00+00:00", 1, 2, 0.5, 1.5, "STUDY"],
                     ["2016-05-02T21:00:00+00:00", 1, 2, 0.5, 1.5, "USED"]])
    with pytest.raises(SystemExit, match="sealed span"):
        S.load(p, sha)


def test_load_refuses_other_bytes(tmp_path):
    p = str(tmp_path / "x.csv")
    _write(p, [["2006-03-20T22:00:00+00:00", 1, 2, 0.5, 1.5, "STUDY"]])
    with pytest.raises(SystemExit, match="not the pinned"):
        S.load(p, "0" * 64)


def test_pinned_hashes_are_the_spec_hashes():
    spec = open(os.path.join(_ROOT, "docs", "specs", "gold_breakout_study_spec.md")).read()
    for rel, sha, _ in S.FILES.values():
        assert rel in spec and sha in spec


# ── statistics ───────────────────────────────────────────────────────────────

def test_wilson_matches_published_values():
    lo, hi = S.wilson(81, 263)                     # Newcombe 1998 (single proportion)
    assert (round(lo, 4), round(hi, 4)) == (0.2553, 0.3662)
    lo, hi = S.wilson(0, 10)
    assert lo == 0.0 and round(hi, 4) == 0.2775


def test_newcombe_matches_published_values():
    d, lo, hi = S.newcombe(56, 70, 48, 80)         # Newcombe 1998 (difference), method 10
    assert (round(d, 4), round(lo, 4), round(hi, 4)) == (0.2, 0.0524, 0.3339)


def test_reading_rules():
    assert S.reading(15, 19) == "INSUFFICIENT"
    assert S.reading(70, 100) == "most breaks fail"
    assert S.reading(30, 100) == "most breaks hold"
    assert S.reading(52, 100) == "about even"


def test_atr_series_ends_at_the_markup_atr():
    b = scenario(HELD)
    assert S.atr_series(b)[-1] == pytest.approx(MS.atr(b))
    assert S.atr_series(b)[13] is None and S.atr_series(b)[14] is not None


def test_report_runs_and_flags_small_cells():
    data = {"XAU_USD": {"STUDY": scenario(HELD), "USED": scenario(CLOSE_FAIL)},
            "GBP_AUD": {"STUDY": scenario(WICK_FAIL), "USED": scenario(LATEST)}}
    out = "\n".join(S.report(data))
    assert "INSUFFICIENT" in out and "Definition W" in out and "Definition C" in out
    assert "gold minus GBP/AUD" in out and "gold up minus gold down" in out
