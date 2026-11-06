"""Pins studies/journal_scoring.py: the grade function equals the framework's
standard rule, price-at-check recovery inverts setup_check's stop_pips, and a
row without a stop is never scored. Synthetic data only; no ledger touched."""
import os
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "studies"))
import journal_scoring as J  # noqa: E402

UTC = timezone.utc


def test_grade_matches_standard_rule():
    # SHORT, entry 1.8800, stop 1.8810 (10 pips): stop touched -> -1R
    assert J.grade("SHORT", 1.8800, 1.8810, [1.8805, 1.8811], [1.8790, 1.8780], 1.8770) == (-1.0, True)
    # SHORT, stop never touched, exit 30 pips lower -> +3R
    assert J.grade("SHORT", 1.8800, 1.8810, [1.8805, 1.8809], [1.8790, 1.8760], 1.8770) == (3.0, False)
    # LONG mirror
    assert J.grade("LONG", 210.00, 209.50, [210.4, 211.0], [209.6, 209.9], 210.75) == (1.5, False)
    assert J.grade("LONG", 210.00, 209.50, [210.4, 211.0], [209.5, 209.9], 210.75) == (-1.0, True)


def test_price_at_check_inverts_stop_pips():
    price, stop, pip = 1.87620, 1.87692, 0.0001
    pips = round(abs(price - stop) / pip, 1)                 # what setup_check writes
    assert abs(J.price_at_check("SHORT", stop, pips, pip) - price) < 0.05 * pip + 1e-12
    assert abs(J.price_at_check("LONG", 212.0, 50.0, 0.01) - 212.5) < 1e-9


def _bars(start, n, step_h, price=1.88):
    return {start + timedelta(hours=step_h * k): (price, price + 0.001, price - 0.001, price) for k in range(n)}


def test_row_without_stop_is_not_scored():
    h4 = _bars(datetime(2026, 9, 1, 1, tzinfo=UTC), 40, 4)
    h1 = _bars(datetime(2026, 9, 1, 1, tzinfo=UTC), 160, 1)
    row = {"instrument": "GBP_AUD", "direction": "LONG", "timestamp": "2026-09-01T03:30:00Z",
           "target": "1.9", "stop_price": "", "stop_pips": ""}
    r = J.score_row(row, h4, h1)
    assert r["status"].startswith("UNGRADEABLE") and "grades" not in r


def test_row_with_stop_uses_next_30_bars():
    h4 = _bars(datetime(2026, 9, 1, 1, tzinfo=UTC), 40, 4)
    h1 = _bars(datetime(2026, 9, 1, 1, tzinfo=UTC), 160, 1)
    row = {"instrument": "GBP_AUD", "direction": "SHORT", "timestamp": "2026-09-01T03:30:00Z",
           "target": "", "stop_price": "1.8820", "stop_pips": "20.0"}
    r = J.score_row(row, h4, h1)
    assert r["h4_bar"] == datetime(2026, 9, 1, 1, tzinfo=UTC)
    assert r["exit_bar"] == datetime(2026, 9, 1, 1, tzinfo=UTC) + timedelta(hours=4 * 30)
    assert set(r["grades"]) == {"E2", "E3"}                    # the measured-from price is never graded
    assert r["grades"]["E2"] == (0.0, False)                   # flat path: exit = entry
    assert abs(r["measured_from"] - 1.8800) < 1e-9


def test_short_stop_touched_exactly_counts_as_hit():
    assert J.grade("SHORT", 1.8800, 1.8810, [1.8805, 1.8810], [1.8790, 1.8780], 1.8770) == (-1.0, True)
