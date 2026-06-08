"""
tests/unit/phase2/test_notify.py

Unit + behavioral tests for notify.py pure functions.

Plain English: these tests verify the logic that decides when to fire a
               notification and what the trade card says. No Mac alerts
               are sent, no framework is run — pure function tests only.
"""

import pytest
from notify import _grade_meets_threshold, _build_notification_text, build_trade_card
from tests.fixtures.market_scenarios import SCENARIO_A

GRADE_ORDER = ["A+", "A", "B+", "B", "C"]


# ── _grade_meets_threshold() ──────────────────────────────────────────────────

class TestGradeThreshold:

    def test_A_plus_meets_all_thresholds(self):
        """A+ is the highest grade — it meets every threshold."""
        for threshold in ["A+", "A", "B+", "B"]:
            assert _grade_meets_threshold("A+", threshold) is True, (
                f"A+ should meet threshold {threshold}"
            )

    def test_B_only_meets_B_threshold(self):
        """B grade meets B threshold but not A or A+."""
        assert _grade_meets_threshold("B", "B")  is True
        assert _grade_meets_threshold("B", "B+") is False
        assert _grade_meets_threshold("B", "A")  is False
        assert _grade_meets_threshold("B", "A+") is False

    def test_C_meets_nothing(self):
        """C is NO TRADE — should never meet any threshold."""
        for threshold in ["A+", "A", "B+", "B"]:
            assert _grade_meets_threshold("C", threshold) is False

    def test_invalid_grade_returns_false(self):
        assert _grade_meets_threshold("Z", "B+") is False
        assert _grade_meets_threshold("A+", "Z") is False

    def test_grade_order_is_strict(self):
        """Each grade only meets its own level and below, not above."""
        for i, grade in enumerate(["A+", "A", "B+", "B"]):
            for j, threshold in enumerate(["A+", "A", "B+", "B"]):
                expected = i <= j   # grade index <= threshold index = meets
                assert _grade_meets_threshold(grade, threshold) == expected, (
                    f"grade={grade} vs threshold={threshold}: "
                    f"expected {expected}"
                )


# ── _build_notification_text() ────────────────────────────────────────────────

class TestBuildNotificationText:

    def _result(self, grade="A", bias="BEARISH", price=2.0300,
                risk_pct=1.0, proximity_pips=None, primary="ESTABLISHED_DOWNTREND"):
        return {
            "grade": grade, "bias": bias, "price": price,
            "risk_pct": risk_pct, "proximity_pips": proximity_pips,
            "primary": primary, "session": "London Session",
        }

    def test_returns_three_tuple(self):
        title, subtitle, message = _build_notification_text(
            self._result(), "Pre-London"
        )
        assert isinstance(title, str)
        assert isinstance(subtitle, str)
        assert isinstance(message, str)

    def test_title_contains_grade(self):
        title, _, _ = _build_notification_text(self._result(grade="A+"), "Pre-London")
        assert "A+" in title

    def test_message_contains_price(self):
        _, _, message = _build_notification_text(self._result(price=2.0350), "Pre-London")
        assert "2.0350" in message

    def test_proximity_appears_in_message_when_provided(self):
        _, _, message = _build_notification_text(
            self._result(proximity_pips=15), "Pre-London"
        )
        assert "15" in message

    def test_no_trade_message_when_risk_zero(self):
        _, _, message = _build_notification_text(
            self._result(grade="C", risk_pct=0), "Pre-London"
        )
        assert "NO TRADE" in message or "0%" in message


# ── build_trade_card() ────────────────────────────────────────────────────────

class TestBuildTradeCard:

    def _result(self, grade="A", bias="BEARISH", price=2.0300,
                risk_pct=1.0, allowed=True, proximity_pips=None,
                alignment=75, quality="HIGH", wait_for=""):
        return {
            "grade": grade, "bias": bias, "price": price,
            "risk_pct": risk_pct, "allowed": allowed,
            "proximity_pips": proximity_pips, "alignment": alignment,
            "quality": quality, "wait_for": wait_for,
            "session": "London Session",
        }

    def test_returns_string(self):
        card = build_trade_card(self._result())
        assert isinstance(card, str)

    def test_card_contains_grade(self):
        card = build_trade_card(self._result(grade="A+"))
        assert "A+" in card

    def test_card_contains_direction_plain_english(self):
        """BEARISH must say 'sell' or 'FALLS' in plain English."""
        card = build_trade_card(self._result(bias="BEARISH"))
        assert "sell" in card.lower() or "FALLS" in card or "SHORT" in card

    def test_bullish_card_says_buy(self):
        """BULLISH must say 'buy' or 'RISES'."""
        card = build_trade_card(self._result(bias="BULLISH"))
        assert "buy" in card.lower() or "RISES" in card or "LONG" in card

    def test_card_contains_risk_pct(self):
        """Risk % must be visible so trader knows position size."""
        card = build_trade_card(self._result(risk_pct=1.5))
        assert "1.5" in card

    def test_no_trade_card_mentions_grade(self):
        """Grade C card must clearly say no trade."""
        card = build_trade_card(self._result(grade="C", risk_pct=0.0, allowed=False))
        assert "NO TRADE" in card or "stand aside" in card.lower()

    def test_proximity_shown_when_provided(self):
        card = build_trade_card(self._result(proximity_pips=22))
        assert "22" in card

    def test_card_is_multiline(self):
        """A trade card must have multiple lines — it's not a one-liner."""
        card = build_trade_card(self._result())
        assert card.count("\n") >= 5

    def test_session_label_appears_in_card(self):
        card = build_trade_card(self._result(), session_label="Pre-London")
        assert "Pre-London" in card


# ── Behavioral: Scenario A — A+ SHORT notification ───────────────────────────

class TestScenarioA:
    """
    Scenario A — A+ SHORT during London open. All signals aligned.
    Expected: notification fires at the lowest threshold (B+), grade A+.

    Plain English: this is the best possible setup. London session,
                   confirmed sweep, value zone, downtrend regime.
                   The alert must fire and the trade card must show
                   1.5% risk with SHORT direction clearly explained.
    """

    def _result(self):
        return {
            "grade":          SCENARIO_A["expected_grade"],
            "risk_pct":       SCENARIO_A["expected_risk_pct"],
            "bias":           "BEARISH",
            "price":          SCENARIO_A["liquidity"]["current_price"],
            "alignment":      SCENARIO_A["expected_conviction_min"],
            "quality":        "HIGH",
            "allowed":        True,
            "session":        SCENARIO_A["session_data"]["session_label"],
            "proximity_pips": None,
            "wait_for":       "",
            "primary":        "ESTABLISHED_DOWNTREND",
        }

    def test_grade_meets_default_threshold(self):
        """A+ meets the default B+ threshold — notification should fire."""
        assert _grade_meets_threshold(
            SCENARIO_A["expected_grade"], "B+"
        ) is True

    def test_grade_meets_A_threshold(self):
        """A+ also meets the stricter A threshold."""
        assert _grade_meets_threshold(SCENARIO_A["expected_grade"], "A") is True

    def test_trade_card_shows_correct_risk(self):
        """1.5% risk for A+ must appear on the card."""
        card = build_trade_card(self._result(), session_label="London")
        assert str(SCENARIO_A["expected_risk_pct"]) in card

    def test_trade_card_explains_short_direction(self):
        """BEARISH bias must be explained in plain English on the card."""
        card = build_trade_card(self._result(), session_label="London")
        assert "sell" in card.lower() or "FALLS" in card or "SHORT" in card

    def test_trade_card_shows_A_plus_grade(self):
        card = build_trade_card(self._result(), session_label="London")
        assert "A+" in card

    def test_notification_text_contains_grade(self):
        title, subtitle, message = _build_notification_text(
            self._result(), "London"
        )
        assert "A+" in title

    def test_C_grade_does_not_meet_threshold(self):
        """Even on a great run, grade C must not fire (sanity check)."""
        assert _grade_meets_threshold("C", "B+") is False
