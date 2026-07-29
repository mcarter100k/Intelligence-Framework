"""
test_session_dst.py

Locks Phase 4 DST fix: the forex week boundary is 5pm New York = 21:00 UTC in
summer (EDT) but 22:00 UTC in winter (EST). The old hardcoded 21:00 made winter
Sunday 21:00-22:00 UTC read as 'open' an hour before real liquidity, and Friday
21:00-22:00 UTC read as 'closed' while still open.

Run: pytest test_session_dst.py
"""
from datetime import datetime

import pytest

import session_context as sc

# 2026-01-04 is a Sunday, 2026-01-02 is a Friday (used with a mocked offset, so
# the actual season is irrelevant — the offset controls EST vs EDT).
_SUNDAY = lambda h: datetime(2026, 1, 4, h)
_FRIDAY = lambda h: datetime(2026, 1, 2, h)


@pytest.fixture
def est(monkeypatch):
    # US standard time (winter): Pacific = PST = -8 → NY close 22:00 UTC
    monkeypatch.setattr("utils.pacific_offset", lambda: (-8, "PST"))


@pytest.fixture
def edt(monkeypatch):
    # US daylight time (summer): Pacific = PDT = -7 → NY close 21:00 UTC
    monkeypatch.setattr("utils.pacific_offset", lambda: (-7, "PDT"))


def test_dates_are_expected_weekdays():
    assert _SUNDAY(0).weekday() == 6
    assert _FRIDAY(0).weekday() == 4


# ── Winter (EST): boundary is 22:00 UTC ────────────────────────────────────────

def test_est_sunday_21utc_is_still_closed(est):
    # THE BUG: old code said open at 21:00. Correct: closed until 22:00.
    is_closed, _, _ = sc._market_status(_SUNDAY(21))
    assert is_closed is True


def test_est_sunday_22utc_is_open(est):
    is_closed, _, _ = sc._market_status(_SUNDAY(22))
    assert is_closed is False


def test_est_friday_21utc_is_still_open(est):
    # Friday 21:00-22:00 UTC in winter: market still open (closes 22:00).
    is_closed, _, _ = sc._market_status(_FRIDAY(21))
    assert is_closed is False


def test_est_friday_22utc_is_closed(est):
    is_closed, _, _ = sc._market_status(_FRIDAY(22))
    assert is_closed is True


# ── Summer (EDT): boundary is 21:00 UTC ────────────────────────────────────────

def test_edt_sunday_21utc_is_open(edt):
    is_closed, _, _ = sc._market_status(_SUNDAY(21))
    assert is_closed is False


def test_edt_sunday_20utc_is_closed(edt):
    is_closed, _, _ = sc._market_status(_SUNDAY(20))
    assert is_closed is True
