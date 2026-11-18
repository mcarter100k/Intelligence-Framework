# Seven-day replay with LEVEL BREAK under the 0.10 ATR margin (ruling Q1; verbatim output)

Script: studies/ccd1_arrival_lastweek.py with margin=A.BREAK_MARGIN. Live OANDA bars, read-only through scripts/reality_run.py; project unchanged by hash. Prototype rendering.

```
bars: hourly 1000 (Thu 09-17 20:00 PT -> Wed 11-18 06:00 PT), 4-hour 500, daily 520
run at Wed 11-18 07:52 PT; window: hourly bars closing in the last 7 days

ARRIVAL alerts in the window: 5

==============================================================================
ARRIVAL — gold — sent Thu 11-12 06:00 PT (hourly bar Thu 11-12 05:00 PT to Thu 11-12 06:00 PT, close $3,890.28)
  Price has arrived at $3,891.26, a prior week level (low of trading week (2026, 45)).
    It is above the close. Since it formed: 4 earlier visits within $9.03, 0 held (no hourly close through it), last Tue 11-03 04:00 PT.
    Nearest level the other way: $3,870.32 (daily swing), $19.96 = 0.22 ATR from the close
    Next level beyond this one:  $3,982.68 (prior session), $92.40 = 1.02 ATR from the close
    No break base rate has been measured for this kind of level.
  Minimum stop at the 14-day average range ($90.28): same session $27.08; 10-session hold $54.17 to $75.84. A stop at the median adverse move stops about half of the winners by construction; these are floors, not recommendations.
  Next scheduled release: not available: only the current week's calendar is stored, and this hour is before it.
  Clock: inside gold's 4-8 AM PT window (120 minutes left). Gold's 4-8 AM PT hours usually carry most of the day's range. That says movement is likely available, not which way it goes. A trade on this window was tested and REFUTED (R49). Volatility clusters; direction does not.
  Volatility: the 14-day average range is 2.26% of price, above 51% of the last 250 days; high third by R50's cut points.
  This configuration being present is not evidence that it pays. Whether it does is an open question (Track B).
  No direction is recommended.
==============================================================================
ARRIVAL — gold — sent Thu 11-12 07:00 PT (hourly bar Thu 11-12 06:00 PT to Thu 11-12 07:00 PT, close $3,870.03)
  Price has arrived at $3,870.32, a daily swing level (the daily swing of the session that opened Thu 10-29 14:00 PT).
    It is above the close. Since it formed: 1 earlier visits within $9.03, 0 held (no hourly close through it), last Fri 10-30 11:00 PT.
    Nearest level the other way: none among the qualifying levels
    Next level beyond this one:  $3,891.26 (prior week), $21.23 = 0.24 ATR from the close
    A wick beyond a gold daily swing failed 66% of the time and a daily close beyond came back inside 45% of the time, 2021-2026 (R45).
  Minimum stop at the 14-day average range ($90.28): same session $27.08; 10-session hold $54.17 to $75.84. A stop at the median adverse move stops about half of the winners by construction; these are floors, not recommendations.
  Next scheduled release: not available: only the current week's calendar is stored, and this hour is before it.
  Clock: inside gold's 4-8 AM PT window (60 minutes left). Gold's 4-8 AM PT hours usually carry most of the day's range. That says movement is likely available, not which way it goes. A trade on this window was tested and REFUTED (R49). Volatility clusters; direction does not.
  Volatility: the 14-day average range is 2.26% of price, above 51% of the last 250 days; high third by R50's cut points.
  This configuration being present is not evidence that it pays. Whether it does is an open question (Track B).
  No direction is recommended.
==============================================================================
ARRIVAL — gold — sent Fri 11-13 06:00 PT (hourly bar Fri 11-13 05:00 PT to Fri 11-13 06:00 PT, close $3,881.11)
  Price has arrived at $3,870.32, a daily swing level (the daily swing of the session that opened Thu 10-29 14:00 PT).
    It is below the close. Since it formed: 2 earlier visits within $9.67, 1 held (no hourly close through it), last Thu 11-12 06:00 PT.
    Nearest level the other way: $3,891.26 (prior week), $10.15 = 0.10 ATR from the close
    Next level beyond this one:  $3,852.58 (4-hour swing), $28.53 = 0.30 ATR from the close
    A wick beyond a gold daily swing failed 66% of the time and a daily close beyond came back inside 45% of the time, 2021-2026 (R45).
  Minimum stop at the 14-day average range ($96.69): same session $29.01; 10-session hold $58.01 to $81.22. A stop at the median adverse move stops about half of the winners by construction; these are floors, not recommendations.
  Next scheduled release: not available: only the current week's calendar is stored, and this hour is before it.
  Clock: inside gold's 4-8 AM PT window (120 minutes left). Gold's 4-8 AM PT hours usually carry most of the day's range. That says movement is likely available, not which way it goes. A trade on this window was tested and REFUTED (R49). Volatility clusters; direction does not.
  Volatility: the 14-day average range is 2.49% of price, above 66% of the last 250 days; high third by R50's cut points.
  This configuration being present is not evidence that it pays. Whether it does is an open question (Track B).
  No direction is recommended.
==============================================================================
ARRIVAL — gold — sent Sun 11-15 18:00 PT (hourly bar Sun 11-15 17:00 PT to Sun 11-15 18:00 PT, close $3,869.45)
  Price has arrived at $3,852.58, an hourly range edge level (the current hourly range (spec §4)).
    It is below the close. Since it formed: 1 earlier visits within $9.69, 1 held (no hourly close through it), last Thu 11-12 07:00 PT.
    Nearest level the other way: $3,870.32 (daily swing), $0.88 = 0.01 ATR from the close
    Next level beyond this one:  none among the qualifying levels
    No break base rate has been measured for this kind of level.
  Minimum stop at the 14-day average range ($96.94): same session $29.08; 10-session hold $58.16 to $81.43. A stop at the median adverse move stops about half of the winners by construction; these are floors, not recommendations.
  Next scheduled release: Fed Chairman Warsh Speaks at Mon 11-16 09:00 PT, in 15h 00m.
  Clock: after gold's 4-8 AM PT window. Gold's 4-8 AM PT hours usually carry most of the day's range. That says movement is likely available, not which way it goes. A trade on this window was tested and REFUTED (R49). Volatility clusters; direction does not.
  Volatility: the 14-day average range is 2.50% of price, above 66% of the last 250 days; high third by R50's cut points.
  This configuration being present is not evidence that it pays. Whether it does is an open question (Track B).
  No direction is recommended.
==============================================================================
ARRIVAL — gold — sent Tue 11-17 06:00 PT (hourly bar Tue 11-17 05:00 PT to Tue 11-17 06:00 PT, close $3,851.36)
  Price has arrived at $3,832.46, a prior session level (low of the session that opened Sun 11-15 14:00 PT).
    It is below the close. Since it formed: 2 earlier visits within $9.64, 2 held (no hourly close through it), last Mon 11-16 10:00 PT.
    Nearest level the other way: $3,852.58 (prior week), $1.22 = 0.01 ATR from the close
    Next level beyond this one:  none among the qualifying levels
    No break base rate has been measured for this kind of level.
  Price has arrived at $3,832.46, an hourly range edge level (the current hourly range (spec §4)).
    It is below the close. Since it formed: 2 earlier visits within $9.64, 2 held (no hourly close through it), last Mon 11-16 10:00 PT.
    Nearest level the other way: $3,852.58 (prior week), $1.22 = 0.01 ATR from the close
    Next level beyond this one:  none among the qualifying levels
    No break base rate has been measured for this kind of level.
  Minimum stop at the 14-day average range ($96.40): same session $28.92; 10-session hold $57.84 to $80.97. A stop at the median adverse move stops about half of the winners by construction; these are floors, not recommendations.
  Next scheduled release: FOMC Meeting Minutes at Wed 11-18 11:00 PT, in 29h 00m.
  Clock: inside gold's 4-8 AM PT window (120 minutes left). Gold's 4-8 AM PT hours usually carry most of the day's range. That says movement is likely available, not which way it goes. A trade on this window was tested and REFUTED (R49). Volatility clusters; direction does not.
  Volatility: the 14-day average range is 2.50% of price, above 66% of the last 250 days; high third by R50's cut points.
  This configuration being present is not evidence that it pays. Whether it does is an open question (Track B).
  No direction is recommended.

==============================================================================
LEVEL BREAK alerts in the window: 3
==============================================================================
LEVEL BREAK — gold — sent Thu 11-12 07:00 PT (hourly bar Thu 11-12 06:00 PT to Thu 11-12 07:00 PT, close $3,870.03)
  The level you were told about at Thu 11-12 06:00 PT has given way: the hour closed at $3,870.03, $21.23 (0.24 ATR) below $3,891.26.
    Qualified then as: prior week. Qualifies now as: prior week.
    Next level beyond: none among the qualifying levels
    Nearest level the other way (back through $3,891.26): $3,982.68 (prior session), $112.65 = 1.25 ATR from the close
    No break base rate has been measured for this kind of level.
  Minimum stop at the 14-day average range ($90.28): same session $27.08; 10-session hold $54.17 to $75.84. Floors, not recommendations.
  Next scheduled release: not available: only the current week's calendar is stored, and this hour is before it. Clock: inside gold's 4-8 AM PT window (60 minutes left).
  This configuration being present is not evidence that it pays. Whether it does is an open question (Track B).
  No direction is recommended.
==============================================================================
LEVEL BREAK — gold — sent Sun 11-15 22:00 PT (hourly bar Sun 11-15 21:00 PT to Sun 11-15 22:00 PT, close $3,837.22)
  The level you were told about at Fri 11-13 06:00 PT has given way: the hour closed at $3,837.22, $33.11 (0.34 ATR) below $3,870.32.
    Qualified then as: daily swing. Qualifies now as: daily swing.
    Next level beyond: none among the qualifying levels
    Nearest level the other way (back through $3,870.32): $3,923.09 (4-hour swing), $85.88 = 0.89 ATR from the close
    A daily close beyond a gold daily swing came back inside 45% of the time, 2021-2026 (R45).
  The level you were told about at Sun 11-15 18:00 PT has given way: the hour closed at $3,837.22, $15.36 (0.16 ATR) below $3,852.58.
    Qualified then as: hourly range edge. Qualifies now as: hourly range edge, prior week.
    Next level beyond: none among the qualifying levels
    Nearest level the other way (back through $3,852.58): $3,867.67 (prior session), $30.45 = 0.31 ATR from the close
    No break base rate has been measured for this kind of level.
  Minimum stop at the 14-day average range ($96.94): same session $29.08; 10-session hold $58.16 to $81.43. Floors, not recommendations.
  Next scheduled release: Fed Chairman Warsh Speaks at Mon 11-16 09:00 PT, in 11h 00m. Clock: after gold's 4-8 AM PT window.
  This configuration being present is not evidence that it pays. Whether it does is an open question (Track B).
  No direction is recommended.
==============================================================================
LEVEL BREAK — gold — sent Tue 11-17 17:00 PT (hourly bar Tue 11-17 16:00 PT to Tue 11-17 17:00 PT, close $3,814.98)
  The level you were told about at Tue 11-17 06:00 PT has given way: the hour closed at $3,814.98, $17.48 (0.18 ATR) below $3,832.46.
    Qualified then as: hourly range edge, prior session. Qualifies now as: hourly range edge.
    Next level beyond: none among the qualifying levels
    Nearest level the other way (back through $3,832.46): $3,852.58 (prior week), $37.60 = 0.39 ATR from the close
    No break base rate has been measured for this kind of level.
  Minimum stop at the 14-day average range ($96.11): same session $28.83; 10-session hold $57.66 to $80.73. Floors, not recommendations.
  Next scheduled release: FOMC Meeting Minutes at Wed 11-18 11:00 PT, in 18h 00m. Clock: after gold's 4-8 AM PT window.
  This configuration being present is not evidence that it pays. Whether it does is an open question (Track B).
  No direction is recommended.

==============================================================================
TRACE of $3,832.46 (level ids ['H4485', 'PDL518', 'RL3832.46000']), last 7 days:
  Mon 11-16 21:00 PT PDL518: armed (close 3881.34, 0.51 ATR away)
  Mon 11-16 21:00 PT RL3832.46000: armed (close 3881.34, 0.51 ATR away)
  Tue 11-17 05:00 PT PDL518: FIRED
  Tue 11-17 05:00 PT RL3832.46000: FIRED
Presence of the level in each day's set (first and last hour it was listed):
  H4485: listed from Mon 11-16 10:00 PT to Tue 11-17 17:00 PT (30 hours)
  PDL518: listed from Mon 11-16 15:00 PT to Tue 11-17 13:00 PT (23 hours)
  RL3832.46000: listed from Mon 11-16 01:00 PT to Tue 11-17 16:00 PT (38 hours)
```
