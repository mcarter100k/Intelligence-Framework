"""Pins the replication wrapper and the comparison script to
docs/specs/session_movement_replication_spec.md: code pins refuse a changed
runner, the rebinding touches only the three inputs, the parser reads the
published 2005-2013 output correctly, and the two-gate verdict, the Šidák α
and the day-trading precondition behave exactly as fixed. Reads the
published report only; no data files, no network."""
import os
import shutil
import sys
from datetime import date

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "studies"))
import session_movement_compare as K  # noqa: E402
import session_movement_replication as W  # noqa: E402

REPORT = os.path.join(ROOT, "studies", "session_movement_report.md")


def test_code_pins_hold_for_the_repo_files():
    W.check_code_pins()


def test_code_pins_refuse_a_changed_runner(tmp_path):
    for name in W.CODE_PINS:
        shutil.copy(os.path.join(ROOT, "studies", name), tmp_path / name)
    with open(tmp_path / "session_movement_study.py", "a") as fh:
        fh.write("\n# changed\n")
    with pytest.raises(SystemExit):
        W.check_code_pins(str(tmp_path))


def test_configure_rebinds_only_the_three_inputs():
    import session_movement_data as D
    import session_movement_study as M
    saved = (dict(M.EXPECTED_HASHES), D.STUDY_FIRST_DAY, D.STUDY_LAST_DAY)
    other = {k: v for k, v in vars(M).items() if k != "EXPECTED_HASHES"}
    try:
        W.configure("modern")
        assert M.EXPECTED_HASHES == W.PERIODS["modern"]["hashes"]
        assert (D.STUDY_FIRST_DAY, D.STUDY_LAST_DAY) == (date(2021, 4, 27), date(2026, 9, 9))
        assert {k: v for k, v in vars(M).items() if k != "EXPECTED_HASHES"} == other
        W.configure("control")
        assert M.EXPECTED_HASHES == saved[0]                  # control inputs == the originals
        assert (D.STUDY_FIRST_DAY, D.STUDY_LAST_DAY) == saved[1:]
    finally:
        M.EXPECTED_HASHES, D.STUDY_FIRST_DAY, D.STUDY_LAST_DAY = saved


def test_parse_reads_the_published_output():
    r = K.parse(K.stdout_from_report(open(REPORT).read()))
    a, j = r["GBP_AUD"], r["GBP_JPY"]
    assert a["q1"][14] == (60.2, 48.3) and a["q1"][21] == (37.8, 29.5)
    assert a["ratio"] == (1.77, 14, 4) and j["ratio"] == (1.92, 14, 21)
    assert a["q3_n"] == 2325 and j["q3_n"] == 2327
    assert a["q3"]["SYDNEY"] == (20.7, 18.0) and a["q3"]["NY_PM"] == (22.7, 25.2)
    assert j["q3"]["LONDON"] == (19.2, 22.5)
    assert a["q3_same"] == 3.6 and j["q3_same"] == 4.7
    assert a["q2"]["LONDON"] == 0.531 and j["q2"]["LONDON"] == 0.571
    assert a["q4"]["hour 18"] == (71.9, 69.0)
    assert a["q5"] == {"H1": 46.2, "H4": 89.5, "D1": 216.5}
    assert j["q5"] == {"H1": 39.8, "H4": 79.7, "D1": 200.6}
    assert len(a["q1"]) == 24 and set(a["q3"]) == set(K.BLOCKS)


def test_sidak_alpha_value():
    assert abs(K.ALPHA_SIDAK - 0.0025613) < 1e-6


def test_two_prop_z_known_value():
    z, p = K.two_prop_z(20.0, 2343, 25.0, 1395)
    assert abs(z - 3.577) < 0.001 and abs(p - 0.000348) < 0.000002   # = sqrt of the 2x2 chi-square
    assert K.two_prop_z(20.0, 1000, 20.0, 1000) == (0.0, 1.0)


@pytest.mark.parametrize("diff,p,verdict", [
    (6.0, 0.0001, "MATERIAL"),
    (-6.0, 0.0001, "MATERIAL"),
    (4.9, 0.0001, "CONSISTENT WITH THE EARLIER PERIOD (statistical gate only)"),
    (6.0, 0.003, "CONSISTENT WITH THE EARLIER PERIOD (practical gate only)"),
    (2.0, 0.2, "CONSISTENT WITH THE EARLIER PERIOD"),
    (5.0, 0.0025, "MATERIAL"),
])
def test_share_verdict_requires_both_gates(diff, p, verdict):
    assert K.share_verdict(diff, p) == verdict


def test_ratio_verdict_is_single_gate():
    assert K.ratio_verdict(0.5) == "MATERIAL — SINGLE-GATE"
    assert K.ratio_verdict(-0.49) == "CONSISTENT WITH THE EARLIER PERIOD — SINGLE-GATE"


def test_precondition_needs_both_parts():
    q3_hi = {"LONDON": (36.0, 10.0), "TOKYO": (10.0, 10.0)}
    q3_lo = {"LONDON": (34.9, 20.0), "TOKYO": (10.0, 10.0)}
    assert K.precondition(2.6, q3_hi) == ("PASS", 36.0)
    assert K.precondition(2.5, q3_hi)[0] == "FAIL"           # ratio must exceed 2.5
    assert K.precondition(3.0, q3_lo)[0] == "FAIL"           # no block reaches 35%
    assert K.precondition(3.0, {"X": (10.0, 35.0)})[0] == "PASS"
