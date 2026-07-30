"""
test_notify_decision_source.py

Locks in Phase 1.2: notify surfaces the OFFICIAL decision (report["decision"])
as the single source of truth for grade/direction/allowed — it does not
re-grade. A STAND_DOWN can never surface as a tradeable alert, and the
surfaced grade/direction always equal report["decision"].

Run: pytest test_notify_decision_source.py
"""
import pytest

import notify
from risk_config import GRADE_CONFIG


def _report(decision, *, setup=None, bias="NEUTRAL", price=1.9000):
    """Minimal report shaped like build_market_report output."""
    return {
        "decision": decision,
        "setup": setup or {"quality": "LOW", "wait_for": "", "event_risk": False},
        "primary_state": "TEST STATE",
        "overall_bias": bias,
        "conviction_score": decision.get("conviction", 0),
        "layers": {
            "session": {"session_label": "TestSession"},
            "liquidity": {"current_price": price},
        },
    }


@pytest.fixture
def patch_report(monkeypatch):
    """Patch market_brain.build_market_report to return a controlled report."""
    def _install(report):
        monkeypatch.setattr("market_brain.build_market_report", lambda *a, **k: report)
    return _install


def test_stand_down_never_surfaces_as_tradeable(patch_report):
    patch_report(_report({
        "direction": "NO TRADE", "grade": "C", "conviction": 0,
        "size_mult": 0.0, "reason": "Filter STAND_DOWN", "source": "official_filter_path",
    }, bias="BULLISH"))  # aggregate bias BULLISH must NOT leak into the alert
    r = notify._run_framework()
    assert r["allowed"] is False
    assert r["grade"] == "C"
    assert r["direction"] == "NO TRADE"
    assert r["risk_pct"] == 0.0

    _, _, message = notify._build_notification_text(r, "S")
    assert "NO TRADE" in message
    assert "BULLISH" not in message  # the old "BULLISH | NO TRADE" bug


def test_tradeable_decision_is_surfaced_verbatim(patch_report):
    patch_report(_report({
        "direction": "LONG", "grade": "A", "conviction": 75,
        "size_mult": 1.0, "reason": "CONTINUATION", "source": "official_filter_path",
    }, bias="BULLISH"))
    r = notify._run_framework()
    assert r["allowed"] is True
    assert r["grade"] == "A"
    assert r["direction"] == "LONG"
    # risk = standard risk for grade A scaled by size_mult (1.0)
    assert r["risk_pct"] == pytest.approx(GRADE_CONFIG["A"]["risk_pct"])


def test_reduced_size_override_scales_risk(patch_report):
    patch_report(_report({
        "direction": "SHORT", "grade": "B", "conviction": 45,
        "size_mult": 0.35, "reason": "COUNTER_TREND_OVERRIDE", "source": "official_filter_path",
    }))
    r = notify._run_framework()
    assert r["allowed"] is True
    # risk = standard B risk scaled by the 0.35 override multiplier, shown to 2dp
    assert r["risk_pct"] == pytest.approx(round(GRADE_CONFIG["B"]["risk_pct"] * 0.35, 2))


def test_event_risk_forces_no_trade_even_at_grade_a(patch_report):
    patch_report(_report({
        "direction": "LONG", "grade": "A", "conviction": 75,
        "size_mult": 1.0, "reason": "CONTINUATION", "source": "official_filter_path",
    }, setup={"quality": "HIGH", "wait_for": "", "event_risk": True}))
    r = notify._run_framework()
    assert r["allowed"] is False
    assert r["direction"] == "NO TRADE"
    assert r["risk_pct"] == 0.0
