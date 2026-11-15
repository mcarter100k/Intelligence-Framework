"""
The pre-registered BCS-2 study's own self-test must keep passing
(docs/specs/htf_breakout_study_spec.md §9): weekly and daily levels and when
they become usable, the daily trend, events, fakes and confirmations, the
obstacle check, the stop recipe, the target formula, management (partial,
breakeven, trail, time limit, stop-first ordering), costs, span refusals,
episodes and the verdict rule. A change to the runner or to BCS-1's helpers it
imports fails here.
"""
import os
import sys

from _paths import ROOT

sys.path.insert(0, os.path.join(ROOT, "studies"))
import htf_breakout_study as hbs  # noqa: E402


def test_study_selftest_passes(capsys):
    ok = hbs.selftest()
    out = capsys.readouterr().out
    assert ok, out
    assert "SELFTEST OK" in out and "FAIL " not in out


def test_pinned_constants_match_the_spec():
    assert (hbs.K_D, hbs.K_W, hbs.D_AGE, hbs.W_AGE) == (3, 2, 120, 520)
    assert (hbs.ZONE_ATR, hbs.BUFFER_PIPS, hbs.MIN_STOP_ATR, hbs.MAX_STOP_ATR) == (0.25, 15.0, 0.3, 1.5)
    assert hbs.TARGETS == (1.5, 2.5) and (hbs.BE_R, hbs.TRAIL_START_R, hbs.TRAIL_GAP_R, hbs.PARTIAL) == (1.0, 1.5, 0.5, 0.5)
    assert (hbs.MAX_HOLD, hbs.RETEST_BARS, hbs.USED_SPREAD, hbs.FLAT_SPREADS) == (120, 12, 3.0, (3.0, 5.1))
    assert hbs.CELLS == (("B", 1.5), ("B", 2.5), ("C", 1.5), ("C", 2.5))
    assert abs(hbs.CONF_LOWER - 0.9875) < 1e-12 and hbs.CONF_UPPER == 0.90 and hbs.REFUTE_BAR == 0.15
    assert (hbs.RESAMPLES, hbs.SEED, hbs.MIN_N) == (20000, 7, 20)
