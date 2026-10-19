"""
test_invalid_accuracy_hidden.py — the brief never shows the regime-accuracy
percentage while its measure is known to be invalid
(docs/specs/accuracy_line_suppression_spec.md; audit 2026-09-29 item 2, I18).

The live brief read "49 outcomes logged, 0% accuracy (developing)": wrong 49
of 49 to a reader, when the measure itself is broken.
"""
import re

import pytest

import decision_brief as db


def _acc(n, accuracy, flagged=False, actionable=False):
    return lambda instrument=None: {"VOLATILE": {
        "n": n, "accuracy": accuracy, "correct": round(n * accuracy),
        "flagged": flagged, "actionable": actionable}}


@pytest.mark.parametrize("n,acc,flagged,actionable", [
    (49, 0.0, False, False),          # today's line
    (75, 0.31, True, False),          # used to add "FLAG, watch closely"
    (180, 0.20, True, True),          # used to say "validated sample — REVISE thresholds"
])
def test_no_percentage_tier_or_advice_from_the_invalid_measure(monkeypatch, n, acc, flagged, actionable):
    monkeypatch.setattr(db, "get_regime_accuracy", _acc(n, acc, flagged, actionable))
    out = db._build_regime_log("VOLATILE", "GBP_AUD")
    assert f"{n} outcomes logged" in out
    assert not re.search(r"\d+%", out), out
    for word in ("developing", "flag threshold", "validated sample", "REVISE", "FLAG"):
        assert word not in out, out
    assert "accuracy not shown" in out and "known to be wrong" in out


def test_the_rendered_data_basis_line_carries_no_percentage(monkeypatch):
    monkeypatch.setattr(db, "get_regime_accuracy", _acc(49, 0.0))
    line = db._plain(db._build_regime_log("VOLATILE", "GBP_AUD"))
    brief = db.DecisionBrief(
        instrument="GBP_AUD", timestamp="t", price=1.9, atr_pips=100.0,
        decision="STAND DOWN", reason="r", conviction=0, grade="C", size_pct=0,
        market_state="m", invalidation="i", regime_log=line, stand_down=True,
        override_fired=False, execution_mode="X", adx_d1=19.0, adx_h4=17.0,
        weekly_context="W", error=None).format()
    basis = brief.split("DATA BASIS", 1)[1].split("═", 1)[0]
    assert "49 outcomes logged" in re.sub(r"\s+", " ", basis)
    assert "%" not in basis


def test_under_20_wording_is_unchanged(monkeypatch):
    monkeypatch.setattr(db, "get_regime_accuracy", _acc(3, 0.0))
    assert db._build_regime_log("VOLATILE", "GBP_AUD").endswith(
        "3 outcomes logged (early data — accuracy not yet meaningful)")
