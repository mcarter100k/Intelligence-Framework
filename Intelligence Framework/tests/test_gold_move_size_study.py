"""
test_gold_move_size_study.py — studies/gold_move_size_study.py
(docs/specs/gold_move_size_study_spec.md §6). Synthetic bars only; no real
gold statistic is computed here.
"""
import csv
import hashlib
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "studies"))
import gold_move_size_study as S  # noqa: E402
import markup_swings as MS  # noqa: E402


def bars_from(ohlc, year="2007"):
    return [(f"{year}-01-{1 + i // 24:02d}T{i % 24:02d}:00", o, h, l, c, True)
            for i, (o, h, l, c) in enumerate(ohlc)]


def drift(n, p=100.0, step=0.5, rng=2.0):
    return [(p + step * i, p + step * i + rng / 2, p + step * i - rng / 2, p + step * i + step / 2)
            for i in range(n)]


# ── measures ─────────────────────────────────────────────────────────────────

def test_true_range_pct_uses_the_previous_close_and_gaps():
    b = bars_from([(100, 101, 99, 100),        # first bar: no true range
                   (100, 102, 99.5, 101),      # inside: TR = 102 - 99.5 = 2.5 on prev close 100
                   (104, 105, 104, 104.5),     # gap up: TR = 105 - 101 = 4 on 101
                   (98, 99, 97, 98.5)])        # gap down: TR = 104.5 - 97 = 7.5 on 104.5
    m = S.measures(b)
    assert m[0]["tr"] is None and m[0]["tr_pct"] is None
    assert m[1]["tr"] == pytest.approx(2.5) and m[1]["tr_pct"] == pytest.approx(2.5)
    assert m[2]["tr"] == pytest.approx(4.0) and m[2]["tr_pct"] == pytest.approx(400 / 101)
    assert m[3]["tr"] == pytest.approx(7.5) and m[3]["tr_pct"] == pytest.approx(750 / 104.5)


def test_atr_pct_on_the_last_bar_is_the_markup_atr_over_the_close():
    b = bars_from(drift(40))
    m = S.measures(b)
    assert m[-1]["atr_pct"] == pytest.approx(100 * MS.atr(b) / b[-1][4])


def test_atr_warm_up_is_excluded():
    m = S.measures(bars_from(drift(20)))
    assert all(x["atr_pct"] is None for x in m[:14])
    assert all(x["atr_pct"] is not None for x in m[14:])


def test_eras_never_share_a_close():
    data = {f: {"STUDY": bars_from(drift(30)), "USED": bars_from(drift(30, p=1000.0), year="2022")}
            for f in S.FRAMES}
    out = "\n".join(S.report(data))
    # Each era's first bar is excluded from the true range: 29 of 30 bars, not 30.
    assert out.count("true range on 29 (first bar excluded)") == 6
    # A true range spanning the jump from ~115 to 1000 would be ~770%; none appears.
    m = S.measures(data["D"]["USED"])
    assert m[0]["tr_pct"] is None and max(x["tr_pct"] for x in m[1:]) < 1


def test_percentiles_on_a_known_list():
    v = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
    assert (S.pctl(v, 10), S.pctl(v, 50), S.pctl(v, 90)) == (2, 6, 10)
    assert S.pctl([1, 2], 50) == pytest.approx(1.5)


def test_ratios_and_overlap_reading_on_hand_values():
    data = {"D": {"STUDY": bars_from(drift(30, rng=4.0)), "USED": bars_from(drift(30, rng=4.0), year="2022")},
            "H4": {"STUDY": bars_from(drift(30, rng=2.0)), "USED": bars_from(drift(30, rng=2.0), year="2022")},
            "H1": {"STUDY": bars_from(drift(30, rng=1.0)), "USED": bars_from(drift(30, rng=1.0), year="2022")}}
    out = "\n".join(S.report(data))
    # Same shapes, so the bars' true ranges are about 4, 2 and 1 on similar closes: H4/D ~0.5, H1/D ~0.25.
    line = next(x for x in out.splitlines() if x.startswith("- STUDY: H4 / D"))
    h4d, h1d = (float(p.split()[-1]) for p in line.split(";"))
    assert h4d == pytest.approx(0.5, abs=0.02) and h1d == pytest.approx(0.25, abs=0.02)
    assert S.overlap_reading((1.0, 2.0), (1.5, 3.0)) == "overlapping"
    assert S.overlap_reading((1.0, 2.0), (2.0, 3.0)) == "overlapping"
    assert S.overlap_reading((1.0, 2.0), (2.1, 3.0)) == "the eras differ"
    assert S.overlap_reading((2.1, 3.0), (1.0, 2.0)) == "the eras differ"


def test_calendar_year_grouping_and_small_years():
    b = bars_from(drift(10), year="2007") + bars_from(drift(25, p=110.0), year="2008")
    years = S.by_year(S.measures(b))
    assert list(years) == ["2007", "2008"]
    assert len(years["2007"]) == 9 and len(years["2008"]) == 25     # the era's first bar has no TR
    data = {f: {"STUDY": b, "USED": bars_from(drift(30), year="2022")} for f in S.FRAMES}
    out = "\n".join(S.report(data))
    y07 = next(x for x in out.splitlines() if x.startswith("- STUDY 2007"))
    y08 = next(x for x in out.splitlines() if x.startswith("- STUDY 2008"))
    assert "INSUFFICIENT" in y07 and "INSUFFICIENT" not in y08


# ── data loading ─────────────────────────────────────────────────────────────

def _write(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_utc", "o", "h", "l", "c", "span"])
        w.writerows(rows)
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def test_load_splits_eras_and_skips_forward_and_pre_start(tmp_path):
    p = str(tmp_path / "x.csv")
    sha = _write(p, [["2006-03-19T22:00:00+00:00", 1, 2, 0.5, 1.5, "STUDY"],
                     ["2006-03-20T22:00:00+00:00", 1, 2, 0.5, 1.5, "STUDY"],
                     ["2021-04-26T21:00:00+00:00", 3, 4, 2.5, 3.5, "USED"],
                     ["2026-09-10T21:00:00+00:00", 5, 6, 4.5, 5.5, "FORWARD"]])
    got = S.load(p, sha)
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
    spec = open(os.path.join(_ROOT, "docs", "specs", "gold_move_size_study_spec.md")).read()
    for name, sha in S.FILES.values():
        assert name in spec and sha in spec


def test_report_runs():
    data = {f: {"STUDY": bars_from(drift(30)), "USED": bars_from(drift(30), year="2022")} for f in S.FRAMES}
    out = "\n".join(S.report(data))
    for head in ("## D", "## H4", "## H1", "USED compared with STUDY", "By calendar year"):
        assert head in out
