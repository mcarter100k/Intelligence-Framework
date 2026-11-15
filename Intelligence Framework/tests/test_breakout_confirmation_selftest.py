"""
The pre-registered breakout-confirmation study's own self-test must keep
passing (docs/specs/breakout_confirmation_study_spec.md §11). It checks the
swing rule, events, fakes and confirmations (including a replica of the
2026-11-13 four-fakes-then-a-break sequence), the retest limit, grading,
the short-side mirror, costs, completed-session ATR, episode collapse, the
verdict rule with its Bonferroni correction, and the embargo and data-hash
refusals, so a change to the runner or to any module it imports
(history_study_convert, shadow_cost_regrade.rollover_nights, foundation/tools
episodes and power_check) fails here.
"""
import os
import sys

from _paths import ROOT

sys.path.insert(0, os.path.join(ROOT, "studies"))
import breakout_confirmation_study as bcs  # noqa: E402


def test_study_selftest_passes(capsys):
    ok = bcs.selftest()
    out = capsys.readouterr().out
    assert ok, out
    assert "SELFTEST OK" in out and "FAIL " not in out


def test_pinned_constants_match_the_spec():
    # The spec freezes these; a silent edit to the runner must fail here as well.
    assert (bcs.PAIR, bcs.PIP, bcs.K, bcs.STOP_ATR, bcs.ATR_SESSIONS) == ("GBP_AUD", 0.0001, 5, 0.25, 14)
    assert (bcs.HORIZON, bcs.RETEST_BARS, bcs.MARKUP, bcs.FLAT_SPREADS) == (24, 12, 1.0, (3.0, 5.1))
    assert bcs.ERA_SPREAD == {range(2005, 2010): 10.0, range(2010, 2014): 7.0}
    assert bcs.CELLS == ("A", "B", "C") and abs(bcs.CONF_LOWER - (1 - 0.05 / 3)) < 1e-12
    assert (bcs.CONF_UPPER, bcs.REFUTE_BAR, bcs.RESAMPLES, bcs.SEED, bcs.MIN_N) == (0.90, 0.15, 20000, 7, 20)
    assert bcs.DATA_HASHES == {
        "GBP_AUD_H1.csv": "f170a0403ac306de24f3b5ca4910a6b66fec009da5de335e9f4f1a1ff8b36768",
        "GBP_AUD_D.csv": "24e4bbe9065a1c463464a174162fab38be6b5f583aef71e7e2306554680bf7f6",
    }
