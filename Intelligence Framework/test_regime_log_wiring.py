"""
test_regime_log_wiring.py — regime_log_restore spec item 1 (pinned).

The six-week regime_classification_log.csv outage happened because log_regime
had NO caller on the live path (its only caller was the shadow stack,
quarantined 2026-07-29). These tests pin the wiring:

  * a live open-market brief run logs the classification exactly once
  * a closed-market run logs nothing (no fresh bar => no new prediction)
  * a logger failure never breaks the brief and is NOT silent (stderr line)
"""
import decision_brief as db


def _mk_regime(**over):
    r = {
        "market_open": True, "stand_down": True, "filter_allowed": False,
        "filter_reason": "test stand-down", "filter_mode": "STAND_DOWN",
        "regime_d1": "VOLATILE", "regime_h4": "VOLATILE",
        "regime": "VOLATILE", "execution_mode": "STAND_DOWN",
        "confidence": "NONE", "adx": 20.0, "adx_h4": 15.0,
        "atr_vs_avg": 1.0, "structure": "TRANSITIONAL",
        "weekly_context": "RANGING", "lt_trend": "RANGING",
        "current_price": 1.9, "atr_pips": 80.0,
    }
    r.update(over)
    return r


def _neutralize_side_effects(monkeypatch):
    import session_memory as sm
    monkeypatch.setattr(sm, "log_session_snapshot", lambda *a, **k: None)
    monkeypatch.setattr(sm, "get_session_delta", lambda inst: {})


def test_live_open_market_brief_logs_classification_once(monkeypatch):
    calls = []
    import regime_classifier_logger as rcl
    monkeypatch.setattr(rcl, "log_regime",
                        lambda reg, inst: calls.append((reg, inst)) or "id")
    _neutralize_side_effects(monkeypatch)
    monkeypatch.setattr(db, "get_regime", lambda inst: _mk_regime())

    brief = db.get_decision_brief("GBP_AUD")

    assert brief.error is None
    assert len(calls) == 1, "live brief must log the classification exactly once"
    assert calls[0][1] == "GBP_AUD"
    assert calls[0][0]["regime_d1"] == "VOLATILE"


def test_closed_market_run_logs_nothing(monkeypatch):
    calls = []
    import regime_classifier_logger as rcl
    monkeypatch.setattr(rcl, "log_regime",
                        lambda reg, inst: calls.append(inst) or "id")
    _neutralize_side_effects(monkeypatch)
    monkeypatch.setattr(db, "get_regime",
                        lambda inst: _mk_regime(market_open=False))

    brief = db.get_decision_brief("GBP_AUD")

    # A crashed brief also logs nothing. Without this line the test
    # passes on a crash (2026-09-29 audit, T5).
    assert brief.error is None, brief.error
    assert calls == [], "closed market re-reads old bars — not a new prediction"


def test_logger_failure_is_nonfatal_and_not_silent(monkeypatch, capsys):
    import regime_classifier_logger as rcl

    def _boom(reg, inst):
        raise OSError("disk full")

    monkeypatch.setattr(rcl, "log_regime", _boom)
    _neutralize_side_effects(monkeypatch)
    monkeypatch.setattr(db, "get_regime", lambda inst: _mk_regime())

    brief = db.get_decision_brief("GBP_AUD")

    assert brief is not None and brief.decision  # brief still renders
    err = capsys.readouterr().err
    assert "regime classification logger failed" in err
    assert "GBP_AUD" in err
