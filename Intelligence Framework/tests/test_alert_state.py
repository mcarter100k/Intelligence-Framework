"""
test_alert_state.py — scripts/alert_state.py (docs/specs/alert_importance_spec.md
N4, N5). Rule 12: each case asks whether the owner should be told.

The state file is redirected into tmp_path, so nothing in the project changes.
"""
import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import alert_state as A  # noqa: E402


@pytest.fixture
def state_file(tmp_path, monkeypatch):
    p = tmp_path / "logs" / "alert_state.json"
    monkeypatch.setattr(A, "STATE_FILE", str(p))
    return p


# ── N5: decisions notify on a change ─────────────────────────────────────────

def test_parse_dstate():
    assert A.parse_dstate("GBP_AUD=LONG/open;GBP_JPY=STAND ASIDE/closed") == [
        ("GBP_AUD", "LONG", True), ("GBP_JPY", "STAND ASIDE", False)]
    assert A.parse_dstate("") == []


@pytest.mark.parametrize("prior, now, expected", [
    (None, "LONG", ["GBP/AUD LONG"]),                         # new, no record
    ("STAND ASIDE", "SHORT", ["GBP/AUD SHORT"]),              # new
    ("LONG", "LONG", []),                                     # unchanged: silent
    ("LONG", "SHORT", ["GBP/AUD SHORT (was LONG)"]),          # reversal
    ("SHORT", "STAND ASIDE", ["GBP/AUD back to stand aside — the SHORT idea is withdrawn"]),
    ("STAND ASIDE", "STAND ASIDE", []),
    (None, "STAND ASIDE", []),                                # recorded silently
])
def test_open_market_changes(prior, now, expected):
    rec = {} if prior is None else {"GBP_AUD": prior}
    msgs, new = A.decision_changes(f"GBP_AUD={now}/open", rec)
    assert msgs == expected
    assert new == {"GBP_AUD": now}


def test_closed_and_error_neither_notify_nor_record():
    for dstate in ("GBP_AUD=SHORT/closed", "GBP_AUD=ERROR/open", "GBP_AUD=?/open"):
        msgs, new = A.decision_changes(dstate, {"GBP_AUD": "LONG"})
        assert msgs == [] and new == {"GBP_AUD": "LONG"}, dstate


def test_a_closed_weekend_does_not_reset_the_record():
    # LONG Friday, closed all weekend (still printing LONG), LONG Monday: silent.
    rec = A.decision_changes("GBP_AUD=LONG/open", {})[1]
    for _ in range(4):
        rec = A.decision_changes("GBP_AUD=LONG/closed", rec)[1]
    assert A.decision_changes("GBP_AUD=LONG/open", rec)[0] == []


def test_both_pairs_named_in_order():
    msgs, _ = A.decision_changes("GBP_AUD=LONG/open;GBP_JPY=SHORT/open", {})
    assert " · ".join(msgs) == "GBP/AUD LONG · GBP/JPY SHORT"


def test_the_input_record_is_not_mutated():
    rec = {"GBP_AUD": "LONG"}
    A.decision_changes("GBP_AUD=SHORT/open", rec)
    assert rec == {"GBP_AUD": "LONG"}


def test_cli_decisions_persists_between_runs(state_file, capsys):
    assert A.main(["x", "decisions", "GBP_AUD=LONG/open"]) == 0
    assert capsys.readouterr().out.strip() == "GBP/AUD LONG"
    assert A.main(["x", "decisions", "GBP_AUD=LONG/open"]) == 0
    assert capsys.readouterr().out == ""                       # second run silent
    assert json.loads(state_file.read_text())["decisions"] == {"GBP_AUD": "LONG"}
    assert A.main(["x", "decisions", "GBP_AUD=STAND ASIDE/open"]) == 0
    assert "withdrawn" in capsys.readouterr().out


def test_cli_fails_loudly_on_a_corrupt_state(state_file, capsys):
    state_file.parent.mkdir(parents=True)
    state_file.write_text("{not json")
    assert A.main(["x", "decisions", "GBP_AUD=LONG/open"]) == 3
    out = capsys.readouterr()
    assert out.out == "" and "alert_state failed" in out.err


# ── N4: review gates ─────────────────────────────────────────────────────────

def test_a_gate_is_announced_once():
    msgs, ann = A.gate_announcements({"MOMENTUM_JOIN": 20}, True, {})
    assert msgs == ["MOMENTUM_JOIN reached 20 graded episodes: the futility "
                    "checkpoint is due (docs/specs/futility_rule_spec.md)"]
    assert A.gate_announcements({"MOMENTUM_JOIN": 21}, True, ann)[0] == []


def test_below_the_first_gate_says_nothing():
    assert A.gate_announcements({"EARLY_MOMENTUM_v2": 19}, True, {}) == ([], {})


def test_a_gate_reached_while_closed_waits_for_the_open():
    msgs, ann = A.gate_announcements({"MOMENTUM_JOIN": 20}, False, {})
    assert msgs == [] and ann == {}
    msgs, ann = A.gate_announcements({"MOMENTUM_JOIN": 20}, True, ann)
    assert len(msgs) == 1 and ann == {"MOMENTUM_JOIN": 20}


def test_the_next_gates():
    _, ann = A.gate_announcements({"THRUST_PULLBACK": 20}, True, {})
    msgs, ann = A.gate_announcements({"THRUST_PULLBACK": 30}, True, ann)
    assert msgs == ["THRUST_PULLBACK reached 30 graded episodes: the review flag is due"]
    msgs, ann = A.gate_announcements({"THRUST_PULLBACK": 64}, True, ann)
    assert msgs == ["THRUST_PULLBACK reached 60 graded episodes: the decision review is due"]


def test_cli_gates_uses_the_live_inputs(state_file, monkeypatch, capsys):
    monkeypatch.setattr(A, "_live_inputs", lambda: ({"MOMENTUM_JOIN": 20}, True))
    assert A.main(["x", "gates"]) == 0
    assert "MOMENTUM_JOIN reached 20" in capsys.readouterr().out
    assert A.main(["x", "gates"]) == 0
    assert capsys.readouterr().out == ""


def test_live_inputs_read_the_real_sources():
    """The market test is the brief's own closed-banner function, and the
    counts are graded independent episodes."""
    import inspect
    src = inspect.getsource(A._live_inputs)
    assert "from regime_detection import _market_status" in src
    assert 'get_shadow_tally(c)["episodes"]' in src
