"""
BCS-3 (docs/specs/m15_entry_study_spec.md): the runner's own self-test must
keep passing, its pinned settings must match the spec, and the M15-vs-H1
consistency check in m15_study_data must be able to fail (a positive control).
"""
import os
import sys
from datetime import datetime, timedelta, timezone

from _paths import ROOT

sys.path.insert(0, os.path.join(ROOT, "studies"))
import m15_entry_study as mes  # noqa: E402
import m15_study_data as md  # noqa: E402

UTC = timezone.utc


def test_study_selftest_passes(capsys):
    ok = mes.selftest()
    out = capsys.readouterr().out
    assert ok, out
    assert "SELFTEST OK" in out and "FAIL " not in out


def test_pinned_constants_match_the_spec():
    assert mes.M15_HASH == "83ef82bb1bf885895c8ef33d998d02bc3569a7d02434d21a80e36531b97925b6"
    assert (mes.WINDOW, mes.H1_HOLD, mes.HTF_HOLD, mes.TIGHT_BUFFER_PIPS) == (48, 96, 480, 15.0)
    assert mes.CELLS == (("H1", None), ("HTF", 1.5), ("HTF", 2.5))
    assert abs(mes.CONF_LOWER - (1 - 0.05 / 3)) < 1e-12 and (mes.CONF_UPPER, mes.REFUTE_BAR) == (0.90, 0.15)
    assert (mes.RESAMPLES, mes.SEED, mes.MIN_N) == (20000, 7, 20)


def _hour(t0, prices):
    return {t0 + timedelta(minutes=15 * i): p for i, p in enumerate(prices)}


def test_consistency_check_matches_and_can_fail():
    t0 = datetime(2008, 1, 8, 10, tzinfo=UTC)
    m15 = _hour(t0, [(1.0, 1.002, 0.999, 1.001), (1.001, 1.003, 1.0, 1.002),
                     (1.002, 1.0025, 0.998, 1.0), (1.0, 1.001, 0.9995, 1.0005)])
    agg = md.aggregate(m15)
    assert agg[t0] == (1.0, 1.003, 0.998, 1.0005, 4)
    good = md.compare(agg, {t0: (1.0, 1.003, 0.998, 1.0005)})
    assert good["all four within tol"] == 1 and good["hours over tol"] == []
    bad = md.compare(agg, {t0: (1.0, 1.003, 0.998, 1.0007)})       # close off by 2 pips
    assert bad["all four within tol"] == 0 and bad["hours over tol"] == [t0]
    missing = md.compare(agg, {t0 + timedelta(hours=1): (1.0, 1.0, 1.0, 1.0)})
    assert missing["archive hours with no M15"] == 1 and missing["M15 hours not in archive"] == 1


def test_m15_keep_refuses_the_sealed_block_and_weekends():
    import pytest
    with pytest.raises(Exception):
        md.keep(datetime(2013, 12, 30, 22, 0, tzinfo=UTC))
    assert md.keep(datetime(2013, 12, 30, 21, 15, tzinfo=UTC))
    assert not md.keep(datetime(2008, 1, 5, 12, tzinfo=UTC))          # a Saturday session
