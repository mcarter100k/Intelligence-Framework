"""
The pre-registered frozen-candidates study (FCS-1) must keep matching the live
code (docs/specs/frozen_candidates_study_spec.md §12). Its self-test checks that
the replay's context, fires, grades and episodes equal shadow_signals' own
_load_ctx, check_shadow_signals, grade_pending_shadow and graded_episodes on a
synthetic series where every candidate fires, plus hand-computed grades, costs,
the verdict rule and the refusals. A change to shadow_signals, regime_detection
or any study module it imports therefore fails here.
"""
import os
import sys

from _paths import ROOT

sys.path.insert(0, os.path.join(ROOT, "studies"))
import frozen_candidates_study as fcs  # noqa: E402


def test_study_selftest_passes(capsys):
    ok = fcs.selftest()
    out = capsys.readouterr().out
    assert ok, out
    assert "SELFTEST OK" in out and "FAIL " not in out


def test_pinned_constants_match_the_spec():
    assert fcs.CELLS == (("MOMENTUM_JOIN", "GBP_AUD"), ("MOMENTUM_JOIN", "GBP_JPY"),
                         ("THRUST_PULLBACK", "GBP_AUD"), ("THRUST_PULLBACK", "GBP_JPY"),
                         ("EARLY_MOMENTUM_v2", "GBP_JPY"))
    assert (fcs.WINDOW, fcs.HORIZON, fcs.MIN_N, fcs.EXAM_SPLIT_PER_YEAR) == (300, 30, 20, 8)
    assert abs(fcs.CONF_LOWER - 0.99) < 1e-12 and fcs.CONF_UPPER == 0.90 and fcs.REFUTE_BAR == 0.15
    assert (fcs.RESAMPLES, fcs.SEED, fcs.MARKUP, fcs.FLAT_SPREAD) == (20000, 7, 1.0, 3.0)
    assert fcs.DATA_HASHES == fcs.FP.DATA_HASHES and len(fcs.DATA_HASHES) == 4
