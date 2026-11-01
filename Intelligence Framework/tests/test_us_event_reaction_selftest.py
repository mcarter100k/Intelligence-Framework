"""
The pre-registered US-event study's own self-test must keep passing
(docs/specs/us_event_reaction_spec.md §8). It checks the verdict rule, the
range ratio, control selection, session mapping, round trips, the family
correction, the embargo refusal and the committed event table's shape, so
a change to any module the study imports, or to the table, fails here.
"""
import os
import sys

from _paths import ROOT

sys.path.insert(0, os.path.join(ROOT, "studies"))
import us_event_reaction_test as uer  # noqa: E402


def test_study_selftest_passes(capsys):
    ok = uer.selftest()
    out = capsys.readouterr().out
    assert ok, out
    assert "SELFTEST OK" in out and "FAIL " not in out
