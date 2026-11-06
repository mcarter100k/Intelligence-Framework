"""Pins the breadth-universe selection to the 2026-11-06 ruling: GBP_AUD and
GBP_JPY first, crosses before USD pairs, lowest spread within each group, no
currency in more than three pairs, at most ten pairs, examined pairs excluded.
Synthetic spreads only; no network."""
import os
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "studies"))
import universe_spread_probe as U  # noqa: E402


def test_included_first_then_crosses_by_spread():
    spreads = {"GBP_AUD": 2.0, "GBP_JPY": 1.5, "EUR_GBP": 0.8, "EUR_JPY": 1.0,
               "EUR_USD": 0.1, "AUD_NZD": 1.2}
    chosen, _ = U.select(spreads, cap=5)
    assert chosen == ["GBP_AUD", "GBP_JPY", "EUR_GBP", "EUR_JPY", "AUD_NZD"]   # EUR_USD (cheapest) waits


def test_majors_only_after_crosses_run_out():
    spreads = {"GBP_AUD": 2.0, "GBP_JPY": 1.5, "EUR_USD": 0.1, "EUR_CHF": 1.0}
    chosen, _ = U.select(spreads, cap=4)
    assert chosen == ["GBP_AUD", "GBP_JPY", "EUR_CHF", "EUR_USD"]


def test_no_currency_in_more_than_three_pairs():
    spreads = {"GBP_AUD": 9, "GBP_JPY": 9, "EUR_GBP": 0.5, "GBP_CHF": 0.6, "GBP_CAD": 0.7,
               "EUR_JPY": 1.0, "AUD_JPY": 1.1, "CAD_JPY": 1.2, "CHF_JPY": 1.3}
    chosen, skipped = U.select(spreads, cap=10)
    counts = Counter(c for p in chosen for c in p.split("_"))
    assert max(counts.values()) <= 3
    assert "GBP_CHF" not in chosen and "more than 3" in skipped["GBP_CHF"]
    assert "CAD_JPY" not in chosen                                            # JPY full after AUD_JPY


def test_excluded_and_cap():
    spreads = {"GBP_AUD": 2, "GBP_JPY": 2, "GBP_USD": 0.1, "EUR_CHF": 1, "NZD_CHF": 2, "EUR_NZD": 3}
    chosen, skipped = U.select(spreads, cap=4)
    assert "GBP_USD" not in chosen and skipped["GBP_USD"].startswith("excluded")
    assert len(chosen) == 4 and skipped["EUR_NZD"] == "cap reached"


def test_is_cross():
    assert U.is_cross("EUR_GBP") and not U.is_cross("USD_JPY") and not U.is_cross("EUR_USD")
