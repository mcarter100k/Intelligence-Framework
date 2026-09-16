"""
test_trade_signal_wiring.py — evidence_loop_repair_spec.md Part 1 (pinned).

Deliberately the same shape as test_regime_log_wiring.py, because this is
the same defect class: log_signal had NO caller on the live path (its only
caller was shadow/market_brain.py, quarantined 2026-07-29). The ledger sat
at 2 lines from 2026-06-28 while run_outcome_check.py:60 graded it nightly,
and the first live SHORT in framework history — GBP/AUD 2026-09-10 18:04
PDT, rating B, 50% size — was never recorded.

These tests pin the wiring:
  * a LONG decision logs exactly one signal row
  * a SHORT decision logs exactly one signal row, with size and entry context
  * a STAND ASIDE run logs nothing (no signal was issued)
  * a closed-market run logs nothing
  * a logger failure never breaks the brief and is NOT silent (stderr line)
  * the additive schema migration preserves existing rows verbatim
"""
import csv

import pytest

import decision_brief as db


def _mk_regime(**over):
    r = {
        "market_open": True, "stand_down": False, "filter_allowed": True,
        "filter_reason": "", "filter_mode": "NORMAL",
        "regime_d1": "TRENDING_DOWN", "regime_h4": "TRENDING_DOWN",
        "regime": "TRENDING_DOWN", "execution_mode": "NORMAL",
        "confidence": "MEDIUM", "adx": 26.0, "adx_h4": 22.0,
        "atr_vs_avg": 1.0, "structure": "DOWNTREND",
        "weekly_context": "TRENDING_DOWN", "lt_trend": "TRENDING_DOWN",
        "current_price": 1.8879, "atr_pips": 84.3,
    }
    r.update(over)
    return r


def _official(direction="SHORT", conviction=50, grade="B", size_mult=0.5):
    return {"direction": direction, "conviction": conviction,
            "grade": grade, "size_mult": size_mult,
            "reason": "test", "source": "official_filter_path"}


def _neutralize_side_effects(monkeypatch, direction="SHORT"):
    """Everything the brief touches that is not under test."""
    import session_memory as sm
    import regime_classifier_logger as rcl
    import official_decision as od
    import entry_confirmation as ec
    monkeypatch.setattr(sm, "log_session_snapshot", lambda *a, **k: None)
    monkeypatch.setattr(sm, "get_session_delta", lambda inst: {})
    monkeypatch.setattr(rcl, "log_regime", lambda *a, **k: "id")
    monkeypatch.setattr(od, "get_official_decision",
                        lambda regime: _official(direction))

    class _E:
        h1_entry_level = 1.8862
        trigger_basis = "No bearish engulfing in trade direction"
    monkeypatch.setattr(ec, "get_entry_brief", lambda *a, **k: _E())


def _capture(monkeypatch):
    rows = []
    import trade_outcome_logger as tol
    monkeypatch.setattr(
        tol, "log_signal",
        lambda regime, decision, inst, shadow_decision=None,
        size_pct=None, entry_context="":
        rows.append({"instrument": inst, "decision": decision,
                     "regime": regime, "size_pct": size_pct,
                     "entry_context": entry_context}) or "sig-id")
    return rows


# ── the wiring ────────────────────────────────────────────────────────────────

def test_short_decision_logs_exactly_one_signal(monkeypatch):
    rows = _capture(monkeypatch)
    _neutralize_side_effects(monkeypatch, "SHORT")
    monkeypatch.setattr(db, "get_regime", lambda inst: _mk_regime())

    brief = db.get_decision_brief("GBP_AUD")

    assert brief.error is None
    assert brief.decision == "SHORT"
    assert len(rows) == 1, "a directional decision must log exactly one row"
    r = rows[0]
    assert r["instrument"] == "GBP_AUD"
    assert r["decision"]["direction"] == "SHORT"
    assert r["decision"]["grade"] == "B"
    assert r["decision"]["conviction"] == 50
    assert r["size_pct"] == 50, "size must travel with the signal"
    assert "engulfing" in r["entry_context"], "entry context must travel too"


def test_long_decision_logs_exactly_one_signal(monkeypatch):
    rows = _capture(monkeypatch)
    _neutralize_side_effects(monkeypatch, "LONG")
    monkeypatch.setattr(db, "get_regime", lambda inst: _mk_regime())

    brief = db.get_decision_brief("GBP_AUD")

    assert brief.decision == "LONG"
    assert len(rows) == 1
    assert rows[0]["decision"]["direction"] == "LONG"


def test_stand_aside_logs_nothing(monkeypatch):
    """No signal was issued, so no row. A ledger row means a real call."""
    rows = _capture(monkeypatch)
    _neutralize_side_effects(monkeypatch, "NO TRADE")
    monkeypatch.setattr(db, "get_regime",
                        lambda inst: _mk_regime(stand_down=True))

    brief = db.get_decision_brief("GBP_AUD")

    assert brief.decision != "SHORT"
    assert rows == []


def test_closed_market_logs_nothing(monkeypatch):
    """Re-reading a closed market is not a new signal — same rule the
    regime logger and session memory already follow."""
    rows = _capture(monkeypatch)
    _neutralize_side_effects(monkeypatch, "SHORT")
    monkeypatch.setattr(db, "get_regime",
                        lambda inst: _mk_regime(market_open=False))

    db.get_decision_brief("GBP_AUD")

    assert rows == []


def test_logger_failure_is_loud_and_never_fatal(monkeypatch, capsys):
    """A broken logger must not break a brief, and must not be silent —
    the wrapper captures stderr into the day log."""
    import trade_outcome_logger as tol

    def _boom(*a, **k):
        raise RuntimeError("ledger unavailable")

    monkeypatch.setattr(tol, "log_signal", _boom)
    _neutralize_side_effects(monkeypatch, "SHORT")
    monkeypatch.setattr(db, "get_regime", lambda inst: _mk_regime())

    brief = db.get_decision_brief("GBP_AUD")

    assert brief.error is None, "a logger failure must never break the brief"
    assert brief.decision == "SHORT"
    err = capsys.readouterr().err
    assert "trade signal logger failed" in err
    assert "GBP_AUD" in err
    assert "ledger unavailable" in err


# ── the additive schema migration ─────────────────────────────────────────────

def test_migration_preserves_existing_rows_verbatim(tmp_path):
    """Appending a column must never edit a recorded value. Same guarantee
    as setup_check._migrate_journal_header (reviewed 2026-09-09)."""
    import trade_outcome_logger as tol

    old_fields = [f for f in tol._FIELDS
                  if f not in ("size_pct", "entry_context")]
    ledger = tmp_path / "trade_signal_log.csv"
    original = {f: "" for f in old_fields}
    original.update({"signal_id": "2026-06-28T00:00:00Z_GBP_AUD",
                     "instrument": "GBP_AUD", "direction": "SHORT",
                     "grade": "B", "conviction": "50",
                     "price_at_signal": "1.8879"})
    with open(ledger, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=old_fields)
        w.writeheader()
        w.writerow(original)

    tol._migrate_header(str(ledger))

    with open(ledger, newline="") as f:
        rows = list(csv.DictReader(f))
        f.seek(0)
        header = next(csv.reader(f))

    assert header == tol._FIELDS
    assert len(rows) == 1
    for k, v in original.items():
        assert rows[0][k] == v, f"migration altered a recorded value: {k}"
    assert rows[0]["size_pct"] == ""
    assert rows[0]["entry_context"] == ""


def test_migration_is_idempotent(tmp_path):
    import trade_outcome_logger as tol
    ledger = tmp_path / "trade_signal_log.csv"
    with open(ledger, "w", newline="") as f:
        csv.DictWriter(f, fieldnames=tol._FIELDS).writeheader()
    before = ledger.read_text()
    tol._migrate_header(str(ledger))
    assert ledger.read_text() == before


def test_migration_on_missing_file_is_a_no_op(tmp_path):
    import trade_outcome_logger as tol
    tol._migrate_header(str(tmp_path / "nope.csv"))   # must not raise
