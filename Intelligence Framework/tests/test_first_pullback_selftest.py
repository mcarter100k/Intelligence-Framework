"""
The pre-registered first-pullback study's own self-test must keep passing
(docs/specs/first_pullback_study_spec.md §11). It checks the leg detector,
the fill, the stop and horizon, the short-side mirror, costs, the context's
use of completed sessions only, episode collapse, the verdict rule with its
Bonferroni correction, the embargo refusal and the data-hash refusal, so a
change to the runner or to any module it imports (history_study_convert,
shadow_cost_regrade.rollover_nights, foundation/tools episodes and
power_check) fails here.
"""
import os
import sys

from _paths import ROOT

sys.path.insert(0, os.path.join(ROOT, "studies"))
import first_pullback_study as fps  # noqa: E402


def test_study_selftest_passes(capsys):
    ok = fps.selftest()
    out = capsys.readouterr().out
    assert ok, out
    assert "SELFTEST OK" in out and "FAIL " not in out


def test_pinned_constants_match_the_spec():
    # The spec freezes these; a silent edit to the runner must fail here as well.
    assert fps.LEVELS == (0.382, 0.5)
    assert (fps.RANGE_BARS, fps.MIN_IMPULSE_ATR, fps.ATR_SESSIONS, fps.TREND_SESSIONS) == (120, 2.0, 14, 65)
    assert (fps.LEG_WINDOW, fps.STOP_BUFFER_ATR, fps.HORIZON) == (60, 0.1, 30)
    assert (fps.MARKUP, fps.FLAT_SPREAD, fps.CELLS, fps.REFUTE_BAR) == (1.0, 3.0, 4, 0.15)
    assert abs(fps.CONF_LOWER - 0.9875) < 1e-12 and fps.CONF_UPPER == 0.90
    assert (fps.RESAMPLES, fps.SEED, fps.MIN_N) == (20000, 7, 20)
