"""
test_alert_flags.py

Pins the alert-expansion layer (docs/specs/alert_expansion_spec.md):
flip → alert lines (pinned text), no flip → silent, stand-aside days with no
changes stay silent (zero-noise). Emission goes to stderr only — the human
brief on stdout is untouched. Class (c) (shadow fires) is verified as wiring
in the wrapper.

Run: pytest test_alert_flags.py
"""
import io
import os

import decision_brief as db


def _brief(delta, adx_h4=20.0, decision="STAND DOWN"):
    return db.DecisionBrief(
        instrument="GBP_AUD", timestamp="t", price=1.9, atr_pips=90.0,
        decision=decision, reason="r", conviction=0, grade="C", size_pct=0,
        market_state="m", invalidation="i", regime_log="l", stand_down=True,
        override_fired=False, execution_mode="STAND_DOWN", adx_d1=20.0,
        adx_h4=adx_h4, weekly_context="RANGING", error=None,
        session_delta=delta)


# ── Class (a): regime change / filter flip / improved-deteriorated ─────────────

def test_filter_flip_to_allowed_notifies():
    flags = db._machine_flags(_brief({"filter_changed": True, "filter_now": True}))
    assert flags == ["GBP/AUD: conditions improved — the framework now "
                     "allows a trade. Check the brief."]


def test_filter_flip_to_standdown_notifies():
    flags = db._machine_flags(_brief({"filter_changed": True, "filter_now": False}))
    assert flags == ["GBP/AUD: conditions deteriorated — the framework "
                     "has stood down since the last run."]


def test_regime_change_notifies():
    flags = db._machine_flags(_brief({"regime_changed": True}))
    assert flags == ["GBP/AUD: the market regime changed since the last run. "
                     "Check the brief."]


def test_summary_improved_notifies():
    flags = db._machine_flags(_brief({"summary": "CONDITIONS IMPROVED: ..."}))
    assert len(flags) == 1 and "conditions improved" in flags[0]


# ── Class (b): EXIT-IF newly satisfied (v1 stand-down watches) ─────────────────

def test_structure_confirm_exit_watch_fires():
    flags = db._machine_flags(_brief(
        {"structure_changed": True, "structure_prior": "TRANSITIONAL"}))
    assert flags == ["GBP/AUD: exit-watch fired — daily price structure just "
                     "confirmed a direction. Check the brief."]


def test_adx_cross_exit_watch_fires_only_with_h4_holding():
    delta = {"adx_d1_prior": 23.0, "adx_d1_now": 26.0}
    # 4-hour not holding → silent
    assert db._machine_flags(_brief(delta, adx_h4=20.0)) == []
    # 4-hour holding → fires, pinned
    flags = db._machine_flags(_brief(delta, adx_h4=27.0))
    assert flags == ["GBP/AUD: exit-watch fired — daily trend strength "
                     "crossed 25 with the 4-hour holding. Check the brief."]


def test_structure_change_from_confirmed_is_not_an_exit_watch():
    # UPTREND → TRANSITIONAL (structure LOST) is not the watched confirm event
    flags = db._machine_flags(_brief(
        {"structure_changed": True, "structure_prior": "UPTREND"}))
    assert flags == []


# ── Zero-noise rule ────────────────────────────────────────────────────────────

def test_no_delta_is_silent():
    assert db._machine_flags(_brief(None)) == []


def test_stand_aside_day_with_no_changes_is_silent():
    delta = {"summary": "Conditions unchanged.", "filter_changed": False,
             "regime_changed": False, "structure_changed": False,
             "adx_d1_prior": 20.0, "adx_d1_now": 20.5}
    assert db._machine_flags(_brief(delta)) == []


# ── Emission channel: stderr only, ##ALERT## prefixed ─────────────────────────

def test_emit_goes_to_stream_with_prefix():
    buf = io.StringIO()
    db._emit_alerts(["GBP/AUD: test line"], stream=buf)
    assert buf.getvalue() == "##ALERT## GBP/AUD: test line\n"
    db._emit_alerts([], stream=buf)          # empty → writes nothing
    assert buf.getvalue() == "##ALERT## GBP/AUD: test line\n"


# ── Wrapper wiring (class (c) verify + routing present) ────────────────────────

def test_wrapper_routes_alerts_and_still_notifies_shadow():
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "scripts", "scheduled_brief.sh")).read()
    assert "##ALERT##" in src                          # flip routing wired
    assert "SHADOW SIGNALS" in src                     # class (c) still wired
    assert 'grep -qv \'STAND ASIDE\'' in src or "STAND ASIDE" in src
