"""The shadow cost re-grade's own self-test must keep passing
(studies/shadow_cost_regrade.py): rollover counting (Wednesday x3, entry and
exit instants, winter time), hand-computed spread and financing in R, the
stop-bar exit time, and the positive control that aborts on a ledger R the
bars do not reproduce."""
import os
import sys

from _paths import ROOT

sys.path.insert(0, os.path.join(ROOT, "studies"))
import shadow_cost_regrade as scr  # noqa: E402


def test_study_selftest_passes(capsys):
    ok = scr.selftest()
    out = capsys.readouterr().out
    assert ok, out
    assert "SELFTEST OK" in out and "FAIL " not in out
