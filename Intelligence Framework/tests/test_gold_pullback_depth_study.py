"""
test_gold_pullback_depth_study.py — studies/gold_pullback_depth_study.py
(docs/specs/gold_pullback_depth_study_spec.md §6). Synthetic bars only; no real
gold statistic is computed here.

The planted leg is first_pullback_study's own replica of the owner's GBP/AUD
leg (A 1.8873, B 1.9257, ATR 0.0120): its first pullback dips to 1.9105, past
the 23.6% (1.91664) and 38.2% (1.91103) levels but short of 50% (1.9065).
"""
import csv
import hashlib
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "studies"))
import gold_pullback_depth_study as S  # noqa: E402
import first_pullback_study as FP  # noqa: E402

K = 3.8                                    # reflection constant: p -> K - p turns the rally into a fall


def owner():
    bars, atr, trend = FP._owner_bars()
    return bars, atr, trend


def reflected(bars):
    return {"O": [K - x for x in bars["O"]], "H": [K - x for x in bars["L"]],
            "L": [K - x for x in bars["H"]], "C": [K - x for x in bars["C"]]}


def truncated(bars, n):
    return {k: v[:n] for k, v in bars.items()}


# ── depths ───────────────────────────────────────────────────────────────────

def test_a_rally_leg_reaching_38_but_not_50():
    bars, atr, trend = owner()
    got = {d: S.depth_counts(bars, atr, trend, 1, d) for d in S.DEPTHS + S.SECONDARY}
    for d in S.DEPTHS + S.SECONDARY:
        assert got[d]["qualified"] == 1 and got[d]["cut"] == 0
    assert [(got[d]["reached"], got[d]["expired"]) for d in S.DEPTHS + S.SECONDARY] == \
        [(1, 0), (1, 0), (0, 1), (0, 1), (0, 1), (0, 1)]


def test_the_same_leg_as_a_fall_is_counted_the_same_way():
    bars, atr, trend = owner()
    r = reflected(bars)
    for d in S.DEPTHS + S.SECONDARY:
        up = S.depth_counts(bars, atr, trend, 1, d)
        down = S.depth_counts(r, atr, trend, -1, d)
        assert (down["qualified"], down["reached"], down["expired"]) == \
            (up["qualified"], up["reached"], up["expired"])
    # ...and the reflected series is not a rally leg: nothing qualifies on the long side.
    assert S.depth_counts(r, atr, trend, 1, 0.382)["qualified"] == 0


def test_a_leg_whose_window_runs_past_the_end_is_cut_off_not_expired():
    bars, atr, trend = owner()
    b = truncated(bars, 131)                  # ends on bar 130: qualified at 129, no pullback yet
    for d in (0.382, 0.5):
        c = S.depth_counts(b, atr[:131], trend[:131], 1, d)
        assert (c["qualified"], c["reached"], c["expired"], c["cut"]) == (1, 0, 0, 1)
    out = S.fmt_cell(S.depth_counts(b, atr[:131], trend[:131], 1, 0.5))
    assert "cut off 1" in out and "no legs" in out


def test_qualified_anchor_years_count_every_qualified_leg():
    bars, atr, trend = owner()
    t0 = datetime(2007, 6, 1, tzinfo=timezone.utc)
    bars = dict(bars, opens=[t0 + timedelta(hours=4 * i) for i in range(len(bars["O"]))])
    assert dict(S.qualified_anchor_years(bars, atr, trend, 1)) == {2007: 1}


# ── eras ─────────────────────────────────────────────────────────────────────

def _rows(first_day, sessions, p=1000.0):
    """Daily and H4 rows for consecutive weekday sessions (bars open 22:00 UTC)."""
    d, h4, day = [], [], first_day
    while len(d) < sessions:
        if day.weekday() < 5:
            t = datetime(day.year, day.month, day.day, 22, tzinfo=timezone.utc) - timedelta(days=1)
            d.append((t.isoformat(), p, p + 5, p - 5, p + 1, True))
            for k in range(6):
                h4.append(((t + timedelta(hours=4 * k)).isoformat(), p, p + 2, p - 2, p + 0.5, True))
            p += 1
        day += timedelta(days=1)
    return d, h4


def test_each_era_builds_its_own_context_from_warm_up():
    sd, sh = _rows(datetime(2007, 1, 2).date(), 100)
    ud, uh = _rows(datetime(2022, 1, 3).date(), 100, p=1800.0)
    eras = S.build({"D": {"STUDY": sd, "USED": ud}, "H4": {"STUDY": sh, "USED": uh}})
    for era in ("STUDY", "USED"):
        bars, atr, trend = eras[era]
        assert atr[0] is None and trend[0] is None              # warm-up at each era's start
        assert atr[6 * 15] is not None and trend[6 * 66] is not None
    _, uatr, _ = eras["USED"]
    assert uatr[6 * 15] == pytest.approx(10.0)                  # USED's own true ranges, not STUDY's
    assert eras["USED"][0]["opens"][0].year == 2022


# ── checks and statistics ────────────────────────────────────────────────────

def test_monotonic_check_and_its_loud_failure(monkeypatch):
    assert S.monotonic([(0.236, 9, 10), (0.382, 8, 10), (0.5, 8, 10)])
    assert not S.monotonic([(0.236, 7, 10), (0.382, 8, 10)])
    bars, atr, trend = owner()
    t0 = datetime(2007, 6, 1, tzinfo=timezone.utc)
    bars = dict(bars, opens=[t0 + timedelta(hours=4 * i) for i in range(len(bars["O"]))])
    out = "\n".join(S.report({"STUDY": (bars, atr, trend), "USED": (bars, atr, trend)}))
    assert "- overall: ok" in out and "FAILED" not in out
    real = S.depth_counts

    def rising(b, a, t, side, d):
        c = dict(real(b, a, t, side, d))
        if d == 0.5 and side == 1:
            c["reached"], c["expired"] = 1, 0              # planted: 50% reached by every leg...
        if d == 0.236 and side == 1:
            c["reached"], c["expired"] = 0, 1              # ...but 23.6% by none: a share that rises
        return c
    monkeypatch.setattr(S, "depth_counts", rising)
    out = "\n".join(S.report({"STUDY": (bars, atr, trend), "USED": (bars, atr, trend)}))
    assert "THIS RUN IS NOT USABLE" in out and "- overall: FAILED" in out


def test_intervals_match_published_values():
    lo, hi = S.wilson(81, 263)
    assert (round(lo, 4), round(hi, 4)) == (0.2553, 0.3662)
    d, lo, hi = S.newcombe(56, 70, 48, 80)
    assert (round(d, 4), round(lo, 4), round(hi, 4)) == (0.2, 0.0524, 0.3339)


def test_reading_rules():
    assert S.reading(15, 19) == "INSUFFICIENT"
    assert S.reading(80, 100) == "most reach it"
    assert S.reading(30, 100) == "most don't"
    assert S.reading(52, 100) == "about even"


# ── data loading ─────────────────────────────────────────────────────────────

def _write(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_utc", "o", "h", "l", "c", "span"])
        w.writerows(rows)
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def test_load_refuses_exam_rows_and_other_bytes_and_skips_pre_start(tmp_path):
    p = str(tmp_path / "x.csv")
    sha = _write(p, [["2006-03-19T22:00:00+00:00", 1, 2, 0.5, 1.5, "STUDY"],
                     ["2006-03-20T22:00:00+00:00", 1, 2, 0.5, 1.5, "STUDY"]])
    assert [b[0][:10] for b in S.load(p, sha)["STUDY"]] == ["2006-03-20"]
    with pytest.raises(SystemExit, match="not the pinned"):
        S.load(p, "0" * 64)
    sha = _write(p, [["2016-05-02T21:00:00+00:00", 1, 2, 0.5, 1.5, "USED"]])
    with pytest.raises(SystemExit, match="sealed span"):
        S.load(p, sha)


def test_pinned_hashes_are_the_spec_hashes():
    spec = open(os.path.join(_ROOT, "docs", "specs", "gold_pullback_depth_study_spec.md")).read()
    for name, sha in S.FILES.values():
        assert name in spec and sha in spec
