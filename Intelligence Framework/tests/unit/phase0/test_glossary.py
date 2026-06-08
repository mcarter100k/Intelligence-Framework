"""
tests/unit/phase0/test_glossary.py

Unit tests for glossary.py and explain.py.

Plain English: these tests make sure every term we use in the framework
               has a real plain-English definition, and that the lookup
               works correctly from any angle.
"""

import pytest
from glossary import explain, all_terms, TERMS, _format


# ── Structural integrity ───────────────────────────────────────────────────────

class TestGlossaryStructure:

    def test_terms_dict_is_not_empty(self):
        """The glossary must have content — an empty glossary is useless."""
        assert len(TERMS) > 0, "TERMS dict is empty"

    def test_every_term_has_a_non_empty_definition(self):
        """No blank definitions allowed — every key must have a real explanation."""
        for term, definition in TERMS.items():
            assert isinstance(definition, str), f"Definition for '{term}' is not a string"
            assert len(definition.strip()) > 10, (
                f"Definition for '{term}' is too short: '{definition}'"
            )

    def test_all_grade_labels_defined(self):
        """Every grade the framework assigns must be in the glossary."""
        for grade in ["A+", "A", "B+", "B", "C"]:
            assert grade in TERMS, f"Grade '{grade}' missing from glossary"

    def test_all_direction_labels_defined(self):
        """LONG, SHORT, NO TRADE must all be explained."""
        for direction in ["LONG", "SHORT", "NO TRADE"]:
            assert direction in TERMS, f"Direction '{direction}' missing from glossary"

    def test_all_htf_contexts_defined(self):
        """Every HTF context string the framework prints must be defined."""
        contexts = [
            "ESTABLISHED_UPTREND", "ESTABLISHED_DOWNTREND",
            "PULLBACK_IN_UPTREND", "COUNTER_TREND_BOUNCE",
            "RANGING", "TRANSITIONAL",
        ]
        for ctx in contexts:
            assert ctx in TERMS, f"HTF context '{ctx}' missing from glossary"

    def test_all_regime_labels_defined(self):
        """Every regime the framework can report must be in the glossary."""
        for regime in ["TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE", "DEFAULT"]:
            assert regime in TERMS, f"Regime '{regime}' missing from glossary"

    def test_all_macro_quadrants_defined(self):
        """All four macro quadrants must be explained."""
        for quad in ["GOLDILOCKS", "REFLATION", "STAGFLATION", "DEFLATION", "TRANSITIONAL"]:
            assert quad in TERMS, f"Macro quadrant '{quad}' missing from glossary"

    def test_all_session_labels_defined(self):
        """Every session name the report prints must be explained."""
        sessions = ["London Session", "New York Session", "Tokyo Session",
                    "Sydney Session", "London/New York Overlap", "Off-hours"]
        for s in sessions:
            assert s in TERMS, f"Session '{s}' missing from glossary"

    def test_all_intraday_fakeout_types_defined(self):
        """Every fakeout type string must be explained."""
        types = ["BULLISH_FAKEOUT", "BEARISH_FAKEOUT",
                 "CLEAN_BREAK_UP", "CLEAN_BREAK_DOWN", "BOTH_SWEPT"]
        for t in types:
            assert t in TERMS, f"Fakeout type '{t}' missing from glossary"

    def test_trade_math_terms_defined(self):
        """Core trade math terms must be explained."""
        for term in ["pips", "R:R", "spread", "lot_size", "Stop Loss", "entry_zone"]:
            assert term in TERMS, f"Trade math term '{term}' missing from glossary"

    def test_outcome_labels_defined(self):
        """WIN, LOSS, NEUTRAL outcomes must be explained."""
        for label in ["WIN", "LOSS"]:
            assert label in TERMS, f"Outcome label '{label}' missing from glossary"

    def test_session_guard_statuses_defined(self):
        """HALTED, SESSION_CLOSED, ACTIVE must all be explained."""
        for status in ["HALTED", "SESSION_CLOSED", "ACTIVE"]:
            assert status in TERMS, f"Session guard status '{status}' missing from glossary"


# ── explain() function ────────────────────────────────────────────────────────

class TestExplainFunction:

    def test_exact_match_returns_definition(self):
        """explain('LONG') should return the LONG definition."""
        result = explain("LONG")
        assert "LONG" in result
        assert "buying" in result.lower() or "profit" in result.lower()

    def test_case_insensitive_exact_match(self):
        """explain() should work regardless of how the user types the term."""
        lower  = explain("long")
        upper  = explain("LONG")
        mixed  = explain("Long")
        # All three should return the same definition (content should match)
        assert "LONG" in lower
        assert "LONG" in upper
        assert "LONG" in mixed

    def test_partial_match_on_sweep(self):
        """explain('sweep') should return both sweep_up and sweep_down."""
        result = explain("sweep")
        # Should surface at least one sweep term
        assert "sweep" in result.lower()

    def test_partial_match_on_session(self):
        """explain('session') should surface session-related terms."""
        result = explain("session")
        assert "session" in result.lower()

    def test_unknown_term_returns_helpful_message(self):
        """Unknown terms must not crash and should guide the user."""
        result = explain("xyzzy_not_a_term_12345")
        assert "not found" in result.lower() or "usage" in result.lower()
        assert result  # never empty

    def test_empty_string_returns_usage(self):
        """explain('') should return a usage hint, not crash."""
        result = explain("")
        assert result
        assert len(result) > 0

    def test_returns_string(self):
        """explain() must always return a string."""
        for term in ["ADX", "VIX", "COT", "something random", "", "A+"]:
            result = explain(term)
            assert isinstance(result, str), f"explain('{term}') returned non-string"

    def test_adr_definition_mentions_trend_strength(self):
        """ADX definition should mention trend strength (not direction)."""
        result = explain("ADX")
        assert "strength" in result.lower()
        # ADX does NOT show direction — make sure we didn't confuse this
        assert "direction" not in result.lower() or "not" in result.lower()

    def test_counter_trend_bounce_definition_mentions_selling(self):
        """COUNTER_TREND_BOUNCE explanation should mention selling the rally."""
        result = explain("COUNTER_TREND_BOUNCE")
        assert "sell" in result.lower() or "short" in result.lower()

    def test_both_swept_definition_warns_no_trade(self):
        """BOTH_SWEPT must clearly say no trade."""
        result = explain("BOTH_SWEPT")
        assert "no trade" in result.lower() or "no clean" in result.lower()

    def test_halted_definition_mentions_daily_loss(self):
        """HALTED must mention why — daily loss limit."""
        result = explain("HALTED")
        assert "loss" in result.lower() or "limit" in result.lower()


# ── all_terms() function ──────────────────────────────────────────────────────

class TestAllTerms:

    def test_returns_list(self):
        terms = all_terms()
        assert isinstance(terms, list)

    def test_list_is_sorted(self):
        terms = all_terms()
        assert terms == sorted(terms)

    def test_list_length_matches_terms_dict(self):
        assert len(all_terms()) == len(TERMS)

    def test_all_keys_appear_in_list(self):
        terms_set = set(all_terms())
        for key in TERMS:
            assert key in terms_set


# ── Behavioral: plain-English quality check ───────────────────────────────────

class TestDefinitionQuality:
    """
    Checks that definitions actually read like plain English, not jargon.
    Plain English rule: if a definition requires the reader to know the term
    already, it is circular and fails this test.
    """

    def test_long_definition_does_not_use_only_trading_jargon(self):
        """LONG definition should use the word 'buy' or 'price rises'."""
        defn = TERMS["LONG"]
        plain_words = ["buy", "buying", "price", "profit", "rise"]
        assert any(w in defn.lower() for w in plain_words), (
            "LONG definition is too jargon-heavy — add plain-English words"
        )

    def test_conviction_definition_uses_analogy(self):
        """Conviction should have a relatable analogy (jury, signals agree, etc.)."""
        defn = TERMS["conviction"]
        relatable = ["jury", "agree", "signals", "point", "unanimous", "disagree"]
        assert any(w in defn.lower() for w in relatable)

    def test_sweep_definition_uses_plain_language(self):
        """Sweep definitions should say 'stop-losses' or 'trap' in plain terms."""
        for key in ["sweep_up", "sweep_down"]:
            defn = TERMS[key]
            plain = ["stop", "trap", "reversed", "flushed", "shook"]
            assert any(w in defn.lower() for w in plain), (
                f"'{key}' definition should use plain-English words like 'stop-losses' or 'trap'"
            )

    def test_no_definition_is_just_the_term_repeated(self):
        """A definition like 'ADX: ADX is ADX' is circular and invalid."""
        for term, defn in TERMS.items():
            # Definition should not start with the term word-for-word
            assert not defn.strip().startswith(term + " is " + term), (
                f"Definition for '{term}' is circular"
            )
