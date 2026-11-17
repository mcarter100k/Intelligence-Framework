"""gold_rule_costs.py — financing nights for the gold rule specs
(docs/specs/gold_morning_window_spec.md, gold_news_continuation_spec.md,
post_release_continuation_spec.md).

A position is charged for a 17:00 New York rollover only if it is open at that
instant and stays open after it. An exit at exactly 17:00 is not charged for
the night it did not hold. Wednesday's rollover counts 3 nights.

The older shared helper, shadow_cost_regrade.rollover_nights, charges an exit
landing exactly on 17:00 as held. Its behaviour is pinned by committed
self-tests and by pre-registered specs (first_pullback_study_spec §5.4), so it
is left unchanged; held_nights is the gold specs' rule.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")


def held_nights(entry_time, exit_time):
    """Nights of financing for a position open from entry_time to exit_time
    (aware datetimes). Each weekday 17:00 New York rollover strictly after the
    entry and strictly before the exit counts 1; Wednesday's counts 3."""
    if exit_time <= entry_time:
        return 0
    nights = 0
    t0, t1 = entry_time.astimezone(NY), exit_time.astimezone(NY)
    day = t0.date()
    while True:
        roll = datetime(day.year, day.month, day.day, 17, 0, tzinfo=NY)
        if roll >= t1:
            break
        if roll > t0 and roll.weekday() < 5:
            nights += 3 if roll.weekday() == 2 else 1
        day += timedelta(days=1)
    return nights
