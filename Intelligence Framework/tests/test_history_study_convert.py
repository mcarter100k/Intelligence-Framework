"""
test_history_study_convert.py — the approved weekend-candle rule for the
OANDA STUDY data (docs/specs/study_weekend_candle_spec.md §6).

Saturday-session candles (Fri 17:00 New York onward) are dropped. Sunday-
session candles fold into the next weekday session: Sunday open, combined
high/low, target close, target timestamp. Synthetic candles only.
"""
import importlib.util
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from _paths import ROOT as _ROOT
_spec = importlib.util.spec_from_file_location(
    "history_study_convert", os.path.join(_ROOT, "studies", "history_study_convert.py"))
conv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(conv)

NY = ZoneInfo("America/New_York")


def ny(y, m, d, h):
    return datetime(y, m, d, h, tzinfo=NY).astimezone(timezone.utc)


# Week of 2009-06-08 (summer). Fri 06-05, Sat 06-06, Sun 06-07, Mon 06-08, Tue 06-09.
FRI_D1 = ny(2009, 6, 4, 17)        # session Fri 06-05
SAT_D1 = ny(2009, 6, 5, 17)        # session Sat 06-06 (Friday after-close)
SUN_D1 = ny(2009, 6, 6, 17)        # session Sun 06-07 (Sunday pre-open)
MON_D1 = ny(2009, 6, 7, 17)        # session Mon 06-08
TUE_D1 = ny(2009, 6, 8, 17)        # session Tue 06-09


def mon_h4(day_before=(2009, 6, 7)):
    y, m, d = day_before
    first = ny(y, m, d, 17)
    from datetime import timedelta
    return [first + timedelta(hours=4 * k) for k in range(6)]


def base_week():
    d1 = {FRI_D1: (1.0, 1.5, 0.5, 1.2), MON_D1: (2.0, 2.5, 1.8, 2.2), TUE_D1: (2.2, 2.6, 2.1, 2.3)}
    h4 = {t: (2.0, 2.1, 1.9, 2.05) for t in mon_h4()}
    h4.update({t: (2.2, 2.3, 2.15, 2.25) for t in mon_h4((2009, 6, 8))})
    h4[ny(2009, 6, 5, 13)] = (1.1, 1.2, 1.0, 1.2)        # Friday's last slot
    return d1, h4


def test_session_day_labels_weekend_sessions_in_summer_and_winter():
    assert conv.session_day(SAT_D1).weekday() == 5
    assert conv.session_day(SUN_D1).weekday() == 6
    assert conv.session_day(MON_D1).weekday() == 0
    # winter (EST): Sunday 13:00 NY is still the Sunday session, 17:00 is Monday's
    assert conv.session_day(ny(2009, 1, 11, 13)).weekday() == 6
    assert conv.session_day(ny(2009, 1, 11, 17)).weekday() == 0
    assert conv.session_day(ny(2009, 1, 9, 17)).weekday() == 5


def test_weekday_only_data_passes_through_unchanged():
    d1, h4 = base_week()
    d1o, h4o, log = conv.convert(d1, h4)
    assert d1o == d1 and h4o == h4
    assert log["folds"] == [] and log["saturday_dropped_d1"] == 0


def test_sunday_session_folds_into_monday_open_high_low_close():
    d1, h4 = base_week()
    d1[SUN_D1] = (1.9, 2.7, 1.7, 1.95)            # higher high, lower low than Monday
    sun_h4 = [ny(2009, 6, 7, 9), ny(2009, 6, 7, 13)]
    h4[sun_h4[0]] = (1.9, 2.0, 1.7, 1.95)
    h4[sun_h4[1]] = (1.95, 2.7, 1.9, 1.98)
    d1o, h4o, log = conv.convert(d1, h4)
    assert SUN_D1 not in d1o
    assert d1o[MON_D1] == (1.9, 2.7, 1.7, 2.2)      # Sunday open, combined H/L, Monday close
    first = mon_h4()[0]
    assert all(t not in h4o for t in sun_h4)
    assert h4o[first] == (1.9, 2.7, 1.7, 2.05)      # earliest folded open, own close
    assert h4o[mon_h4()[1]] == h4[mon_h4()[1]]       # later Monday slots untouched
    assert d1o[FRI_D1] == d1[FRI_D1] and d1o[TUE_D1] == d1[TUE_D1]
    assert log["folds"] == [("2009-06-07", "2009-06-08")]
    assert log["sunday_folded_d1"] == 1 and log["sunday_folded_h4"] == 2


def test_monday_extremes_kept_when_sunday_is_inside_them():
    d1, h4 = base_week()
    d1[SUN_D1] = (2.1, 2.2, 1.9, 2.0)
    h4[ny(2009, 6, 7, 13)] = (2.1, 2.2, 1.9, 2.0)
    d1o, _, _ = conv.convert(d1, h4)
    assert d1o[MON_D1] == (2.1, 2.5, 1.8, 2.2)


def test_saturday_session_is_dropped_and_touches_nothing_else():
    d1, h4 = base_week()
    d1[SAT_D1] = (9.0, 9.9, 0.1, 9.5)
    h4[ny(2009, 6, 5, 17)] = (9.0, 9.9, 0.1, 9.5)
    h4[ny(2009, 6, 5, 21)] = (9.0, 9.9, 0.1, 9.5)
    d1o, h4o, log = conv.convert(d1, h4)
    ref_d1, ref_h4 = base_week()
    assert d1o == ref_d1 and h4o == ref_h4
    assert log["saturday_dropped_d1"] == 1 and log["saturday_dropped_h4"] == 2
    assert log["folds"] == []


def test_both_weekend_kinds_saturday_dropped_sunday_folded():
    d1, h4 = base_week()
    d1[SAT_D1] = (9.0, 9.9, 0.1, 9.5)
    d1[SUN_D1] = (1.9, 2.0, 1.85, 1.95)
    h4[ny(2009, 6, 5, 17)] = (9.0, 9.9, 0.1, 9.5)
    h4[ny(2009, 6, 7, 13)] = (1.9, 2.0, 1.85, 1.95)
    d1o, h4o, _ = conv.convert(d1, h4)
    assert d1o[MON_D1] == (1.9, 2.5, 1.8, 2.2)      # Saturday's 9.9 / 0.1 never reach Monday
    assert d1o[FRI_D1] == (1.0, 1.5, 0.5, 1.2)
    assert h4o[mon_h4()[0]] == (1.9, 2.1, 1.85, 2.05)
    assert SAT_D1 not in d1o and SUN_D1 not in d1o


def test_continuous_weekend_quoting_2011_style():
    from datetime import timedelta
    d1, h4 = base_week()
    d1[SAT_D1] = (1.3, 1.4, 1.2, 1.3)
    d1[SUN_D1] = (1.6, 1.7, 1.5, 1.6)
    sat = [ny(2009, 6, 5, 17) + timedelta(hours=4 * k) for k in range(6)]
    sun = [ny(2009, 6, 6, 17) + timedelta(hours=4 * k) for k in range(6)]
    for t in sat:
        h4[t] = (1.3, 1.4, 1.2, 1.3)
    for t in sun:
        h4[t] = (1.6, 1.7, 1.5, 1.6)
    d1o, h4o, log = conv.convert(d1, h4)
    assert log["saturday_dropped_h4"] == 6 and log["sunday_folded_h4"] == 6
    assert not [t for t in h4o if conv.session_day(t).weekday() >= 5]
    assert not [t for t in d1o if conv.session_day(t).weekday() >= 5]
    assert h4o[mon_h4()[0]] == (1.6, 2.1, 1.5, 2.05)
    assert d1o[MON_D1] == (1.6, 2.5, 1.5, 2.2)


def test_holiday_monday_folds_into_tuesday():
    d1, h4 = base_week()
    del d1[MON_D1]
    for t in mon_h4():
        del h4[t]
    d1[SUN_D1] = (1.9, 2.8, 1.7, 1.95)
    h4[ny(2009, 6, 7, 13)] = (1.9, 2.8, 1.7, 1.95)
    d1o, h4o, log = conv.convert(d1, h4)
    assert log["folds"] == [("2009-06-07", "2009-06-09")]
    assert d1o[TUE_D1] == (1.9, 2.8, 1.7, 2.3)
    assert h4o[mon_h4((2009, 6, 8))[0]] == (1.9, 2.8, 1.7, 2.25)


def test_missing_first_monday_slot_folds_into_first_existing_h4():
    d1, h4 = base_week()
    del h4[mon_h4()[0]]
    h4[ny(2009, 6, 7, 13)] = (1.9, 2.8, 1.7, 1.95)
    d1[SUN_D1] = (1.9, 2.8, 1.7, 1.95)
    _, h4o, _ = conv.convert(d1, h4)
    assert h4o[mon_h4()[1]] == (1.9, 2.8, 1.7, 2.05)


def test_no_later_weekday_session_raises():
    d1 = {FRI_D1: (1.0, 1.5, 0.5, 1.2), SUN_D1: (1.9, 2.0, 1.8, 1.9)}
    h4 = {ny(2009, 6, 5, 13): (1.1, 1.2, 1.0, 1.2), ny(2009, 6, 7, 13): (1.9, 2.0, 1.8, 1.9)}
    with pytest.raises(ValueError):
        conv.convert(d1, h4)


def test_folded_monday_stays_internally_consistent():
    d1, h4 = base_week()
    d1[MON_D1] = (2.0, 2.3, 1.85, 2.2)                   # consistent with its six H4
    for i, t in enumerate(mon_h4()):
        h4[t] = (2.0, 2.0 + 0.05 * (i + 1), 1.85 + 0.01 * i, 2.05)
    d1[SUN_D1] = (1.9, 2.6, 1.6, 1.95)
    h4[ny(2009, 6, 7, 9)] = (1.9, 2.6, 1.7, 1.95)
    h4[ny(2009, 6, 7, 13)] = (1.95, 2.0, 1.6, 1.98)
    d1o, h4o, _ = conv.convert(d1, h4)
    mon = [h4o[t] for t in mon_h4()]
    assert d1o[MON_D1][1] == max(b[1] for b in mon)
    assert d1o[MON_D1][2] == min(b[2] for b in mon)


def test_inputs_are_not_modified():
    d1, h4 = base_week()
    d1[SUN_D1] = (1.9, 2.7, 1.7, 1.95)
    h4[ny(2009, 6, 7, 13)] = (1.9, 2.7, 1.7, 1.95)
    before = (dict(d1), dict(h4))
    conv.convert(d1, h4)
    assert (d1, h4) == before
