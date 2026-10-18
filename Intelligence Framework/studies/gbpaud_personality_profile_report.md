> **Prior-session artifact:** committed 2026-10-18 for citation integrity (foundation/ cites it). Committed exactly as found; not re-verified against current code.

```
==============================================================================
GBP/AUD 3-YEAR PERSONALITY PROFILE — read-only study, 2026-09-11
Window: 2023-09-01 → 2026-09-10 (trading days, NY-close convention; clock times reported in PDT)
==============================================================================

## 0. Precondition
PRECONDITION PASS — compute_atr_series returns len(C)-14 values; atr[-1] maps to the LAST bar; by-index reads use atr[b - (len(C)-len(atr))] (off=14), matching _atr_at in shadow_signals.py. No lookahead contamination.

## 1. Data
- D1: 784 trading days in window (full fetch 1110 bars from 2022-05-31 for the 220-bar warm-up)
- Missing weekdays vs Mon–Fri calendar: 6 — 2023-12-25, 2024-01-01, 2024-12-25, 2025-01-01, 2025-12-25, 2026-01-01
- H4: 4704 bars in window (fetch 5239 from 2023-04-30; expected ≈6/trading day → 6.00/day)
- H4 days with <5 bars: 0
- H1: 18816 bars in window (24.0/day; 24 expected on full days)

## 2. Day map (live-parity per-day classification)
- Classified 784 trading days with trailing 220-bar D1 / 120-bar H4 windows (get_regime derivation, as-of-day-close).
- D1 structure episodes: 82 (18 up, 23 down, 41 transitional)

==============================================================================
## 3a. Sep–Sep year segments

### SepY1 2023-09→2024-08  (2023-09-01 → 2024-08-30, N=259 trading days)
- Net change: -140 pips  (close 1.9544 → 1.9404)
- High 2.0040 / Low 1.8589  (range 1452 pips)
- Median D1 ATR(14): 120 pips (p25 103 / p75 135)
- Regime cells (D1,H4), % of days (N=259):
          RANGING / VOLATILE       16.6%  (n=43)
          RANGING / RANGING        15.4%  (n=40)
         VOLATILE / VOLATILE       15.1%  (n=39)
         VOLATILE / RANGING         9.3%  (n=24)
         VOLATILE / TRENDING_UP     8.1%  (n=21)
         VOLATILE / TRENDING_DOWN   6.6%  (n=17)
          RANGING / TRENDING_DOWN   6.6%  (n=17)
      TRENDING_UP / VOLATILE        4.6%  (n=12)
          RANGING / TRENDING_UP     3.9%  (n=10)
    TRENDING_DOWN / VOLATILE        2.7%  (n=7)
    TRENDING_DOWN / RANGING         2.7%  (n=7)
      TRENDING_UP / TRENDING_UP     2.7%  (n=7)
      TRENDING_UP / RANGING         2.7%  (n=7)
    TRENDING_DOWN / TRENDING_UP     2.3%  (n=6)
    TRENDING_DOWN / TRENDING_DOWN   0.4%  (n=1)
      TRENDING_UP / TRENDING_DOWN   0.4%  (n=1)
- % days D1 regime RANGING: 42.5%   % days D1 structure TRANSITIONAL: 48.6%
- Confirmed D1 trend legs starting in segment (N=16  [descriptive only]): 7 up / 9 down
    length days: median 7 (min 1, max 22)   with-trend net pips: median -51 (min -341, max +136)
- Overshoot beyond prior confirmed swing extreme (N=26  [descriptive only] events): median 99 pips (p25 56 / p75 158, max 278); closed back inside ≤3 days: 77%
- Share of daily range by PDT hour (avg % of summed H1 ranges; top 5): 07:00 6.2%, 05:00 6.1%, 06:00 5.8%, 00:00 5.5%, 18:00 5.3%
    full 24h profile: 00h=5.5 01h=4.9 02h=4.4 03h=4.1 04h=4.1 05h=6.1 06h=5.8 07h=6.2 08h=4.6 09h=3.5 10h=3.2 11h=2.9 12h=2.5 13h=2.1 14h=3.8 15h=2.8 16h=3.3 17h=4.6 18h=5.3 19h=4.3 20h=3.6 21h=3.3 22h=3.8 23h=5.3

### SepY2 2024-09→2025-08  (2024-09-02 → 2025-08-29, N=258 trading days)
- Net change: +1245 pips  (close 1.9404 → 2.0649)
- High 2.1647 / Low 1.9125  (range 2522 pips)
- Median D1 ATR(14): 134 pips (p25 123 / p75 146)
- Regime cells (D1,H4), % of days (N=258):
         VOLATILE / VOLATILE       17.8%  (n=46)
          RANGING / VOLATILE       13.2%  (n=34)
          RANGING / RANGING        10.9%  (n=28)
         VOLATILE / RANGING        10.1%  (n=26)
         VOLATILE / TRENDING_DOWN   9.7%  (n=25)
      TRENDING_UP / VOLATILE        7.8%  (n=20)
         VOLATILE / TRENDING_UP     7.8%  (n=20)
          RANGING / TRENDING_UP     6.6%  (n=17)
      TRENDING_UP / TRENDING_UP     4.3%  (n=11)
          RANGING / TRENDING_DOWN   3.5%  (n=9)
      TRENDING_UP / RANGING         3.1%  (n=8)
    TRENDING_DOWN / TRENDING_UP     1.6%  (n=4)
    TRENDING_DOWN / RANGING         1.6%  (n=4)
    TRENDING_DOWN / VOLATILE        1.2%  (n=3)
      TRENDING_UP / TRENDING_DOWN   0.8%  (n=2)
    TRENDING_DOWN / TRENDING_DOWN   0.4%  (n=1)
- % days D1 regime RANGING: 34.1%   % days D1 structure TRANSITIONAL: 36.0%
- Confirmed D1 trend legs starting in segment (N=15  [descriptive only]): 8 up / 7 down
    length days: median 9 (min 3, max 30)   with-trend net pips: median -35 (min -423, max +197)
- Overshoot beyond prior confirmed swing extreme (N=23  [descriptive only] events): median 163 pips (p25 65 / p75 246, max 850); closed back inside ≤3 days: 70%
- Share of daily range by PDT hour (avg % of summed H1 ranges; top 5): 07:00 6.3%, 05:00 5.4%, 06:00 5.4%, 00:00 5.3%, 23:00 5.2%
    full 24h profile: 00h=5.3 01h=4.8 02h=4.2 03h=4.1 04h=4.3 05h=5.4 06h=5.4 07h=6.3 08h=4.6 09h=3.5 10h=3.2 11h=2.8 12h=2.6 13h=2.6 14h=3.7 15h=3.4 16h=3.4 17h=4.6 18h=4.9 19h=4.3 20h=3.7 21h=3.6 22h=3.9 23h=5.2

### SepY3 2025-09→2026-09-10  (2025-09-01 → 2026-09-10, N=267 trading days)
- Net change: -1769 pips  (close 2.0649 → 1.8879)
- High 2.0851 / Low 1.8540  (range 2312 pips)
- Median D1 ATR(14): 110 pips (p25 103 / p75 137)
- Regime cells (D1,H4), % of days (N=267):
         VOLATILE / VOLATILE       21.7%  (n=58)
          RANGING / RANGING        13.9%  (n=37)
    TRENDING_DOWN / VOLATILE       11.2%  (n=30)
         VOLATILE / RANGING        10.9%  (n=29)
          RANGING / VOLATILE       10.5%  (n=28)
         VOLATILE / TRENDING_DOWN   9.4%  (n=25)
         VOLATILE / TRENDING_UP     6.4%  (n=17)
    TRENDING_DOWN / TRENDING_UP     3.0%  (n=8)
          RANGING / TRENDING_UP     2.6%  (n=7)
      TRENDING_UP / TRENDING_UP     2.6%  (n=7)
    TRENDING_DOWN / RANGING         2.2%  (n=6)
          RANGING / TRENDING_DOWN   1.9%  (n=5)
    TRENDING_DOWN / TRENDING_DOWN   1.5%  (n=4)
      TRENDING_UP / VOLATILE        1.5%  (n=4)
      TRENDING_UP / TRENDING_DOWN   0.4%  (n=1)
      TRENDING_UP / RANGING         0.4%  (n=1)
- % days D1 regime RANGING: 28.8%   % days D1 structure TRANSITIONAL: 38.2%
- Confirmed D1 trend legs starting in segment (N=10  [descriptive only]): 3 up / 7 down
    length days: median 10 (min 1, max 57)   with-trend net pips: median -52 (min -232, max +873)
- Overshoot beyond prior confirmed swing extreme (N=20  [descriptive only] events): median 105 pips (p25 61 / p75 189, max 282); closed back inside ≤3 days: 65%
- Share of daily range by PDT hour (avg % of summed H1 ranges; top 5): 07:00 6.7%, 06:00 5.9%, 05:00 5.2%, 00:00 5.1%, 08:00 5.0%
    full 24h profile: 00h=5.1 01h=4.9 02h=4.1 03h=4.0 04h=4.3 05h=5.2 06h=5.9 07h=6.7 08h=5.0 09h=3.7 10h=3.3 11h=2.8 12h=2.7 13h=2.7 14h=4.5 15h=3.4 16h=3.3 17h=4.4 18h=4.7 19h=4.0 20h=3.4 21h=3.4 22h=3.6 23h=4.8

==============================================================================
## 3b. Calendar-year segments

### Cal2023 (Sep–Dec, partial)  (2023-09-01 → 2023-12-29, N=85 trading days)
- Net change: -852 pips  (close 1.9544 → 1.8692)
- High 1.9749 / Low 1.8589  (range 1160 pips)
- Median D1 ATR(14): 136 pips (p25 131 / p75 140)
- Regime cells (D1,H4), % of days (N=85):
         VOLATILE / VOLATILE       21.2%  (n=18)
          RANGING / VOLATILE       20.0%  (n=17)
          RANGING / RANGING        20.0%  (n=17)
         VOLATILE / TRENDING_DOWN  14.1%  (n=12)
         VOLATILE / RANGING         5.9%  (n=5)
         VOLATILE / TRENDING_UP     4.7%  (n=4)
    TRENDING_DOWN / RANGING         4.7%  (n=4)
          RANGING / TRENDING_UP     4.7%  (n=4)
          RANGING / TRENDING_DOWN   3.5%  (n=3)
    TRENDING_DOWN / VOLATILE        1.2%  (n=1)
- % days D1 regime RANGING: 48.2%   % days D1 structure TRANSITIONAL: 69.4%
- Confirmed D1 trend legs starting in segment (N=6  [descriptive only]): 3 up / 3 down
    length days: median 4 (min 1, max 9)   with-trend net pips: median -51 (min -175, max +105)
- Overshoot beyond prior confirmed swing extreme (N=9  [descriptive only] events): median 111 pips (p25 53 / p75 191, max 267); closed back inside ≤3 days: 67%
- Share of daily range by PDT hour (avg % of summed H1 ranges; top 5): 07:00 6.3%, 05:00 5.8%, 00:00 5.8%, 06:00 5.6%, 23:00 5.3%
    full 24h profile: 00h=5.8 01h=4.9 02h=4.6 03h=4.3 04h=4.1 05h=5.8 06h=5.6 07h=6.3 08h=4.5 09h=3.5 10h=3.3 11h=3.0 12h=2.5 13h=2.1 14h=4.1 15h=2.9 16h=3.3 17h=4.7 18h=4.9 19h=4.3 20h=3.4 21h=3.2 22h=3.8 23h=5.3

### Cal2024  (2024-01-02 → 2024-12-31, N=260 trading days)
- Net change: +1530 pips  (close 1.8692 → 2.0222)
- High 2.0301 / Low 1.8605  (range 1696 pips)
- Median D1 ATR(14): 115 pips (p25 103 / p75 128)
- Regime cells (D1,H4), % of days (N=260):
         VOLATILE / RANGING        13.8%  (n=36)
         VOLATILE / VOLATILE       12.7%  (n=33)
          RANGING / VOLATILE       11.5%  (n=30)
          RANGING / RANGING        11.5%  (n=30)
         VOLATILE / TRENDING_UP     8.5%  (n=22)
      TRENDING_UP / VOLATILE        8.1%  (n=21)
         VOLATILE / TRENDING_DOWN   6.2%  (n=16)
      TRENDING_UP / TRENDING_UP     5.4%  (n=14)
          RANGING / TRENDING_DOWN   5.4%  (n=14)
          RANGING / TRENDING_UP     5.0%  (n=13)
      TRENDING_UP / RANGING         3.8%  (n=10)
    TRENDING_DOWN / TRENDING_UP     3.5%  (n=9)
    TRENDING_DOWN / VOLATILE        2.7%  (n=7)
    TRENDING_DOWN / RANGING         1.2%  (n=3)
    TRENDING_DOWN / TRENDING_DOWN   0.4%  (n=1)
      TRENDING_UP / TRENDING_DOWN   0.4%  (n=1)
- % days D1 regime RANGING: 33.5%   % days D1 structure TRANSITIONAL: 31.9%
- Confirmed D1 trend legs starting in segment (N=15  [descriptive only]): 7 up / 8 down
    length days: median 11 (min 3, max 24)   with-trend net pips: median -29 (min -341, max +167)
- Overshoot beyond prior confirmed swing extreme (N=26  [descriptive only] events): median 138 pips (p25 68 / p75 203, max 388); closed back inside ≤3 days: 73%
- Share of daily range by PDT hour (avg % of summed H1 ranges; top 5): 07:00 6.3%, 05:00 6.1%, 06:00 5.7%, 23:00 5.4%, 00:00 5.3%
    full 24h profile: 00h=5.3 01h=4.9 02h=4.3 03h=4.0 04h=4.2 05h=6.1 06h=5.7 07h=6.3 08h=4.7 09h=3.4 10h=3.2 11h=2.8 12h=2.5 13h=2.2 14h=3.6 15h=2.9 16h=3.4 17h=4.6 18h=5.2 19h=4.4 20h=3.8 21h=3.4 22h=3.9 23h=5.4

### Cal2025  (2025-01-02 → 2025-12-31, N=259 trading days)
- Net change: -31 pips  (close 2.0222 → 2.0191)
- High 2.1647 / Low 1.9593  (range 2054 pips)
- Median D1 ATR(14): 136 pips (p25 124 / p75 147)
- Regime cells (D1,H4), % of days (N=259):
         VOLATILE / VOLATILE       22.8%  (n=59)
          RANGING / VOLATILE       17.8%  (n=46)
          RANGING / RANGING        12.4%  (n=32)
         VOLATILE / TRENDING_DOWN   9.7%  (n=25)
         VOLATILE / RANGING         8.5%  (n=22)
         VOLATILE / TRENDING_UP     8.1%  (n=21)
          RANGING / TRENDING_UP     5.0%  (n=13)
      TRENDING_UP / VOLATILE        4.2%  (n=11)
          RANGING / TRENDING_DOWN   4.2%  (n=11)
      TRENDING_UP / RANGING         1.9%  (n=5)
      TRENDING_UP / TRENDING_UP     1.5%  (n=4)
    TRENDING_DOWN / RANGING         1.5%  (n=4)
    TRENDING_DOWN / VOLATILE        0.8%  (n=2)
      TRENDING_UP / TRENDING_DOWN   0.8%  (n=2)
    TRENDING_DOWN / TRENDING_DOWN   0.4%  (n=1)
    TRENDING_DOWN / TRENDING_UP     0.4%  (n=1)
- % days D1 regime RANGING: 39.4%   % days D1 structure TRANSITIONAL: 42.5%
- Confirmed D1 trend legs starting in segment (N=15  [descriptive only]): 6 up / 9 down
    length days: median 9 (min 3, max 30)   with-trend net pips: median -89 (min -423, max +197)
- Overshoot beyond prior confirmed swing extreme (N=23  [descriptive only] events): median 73 pips (p25 34 / p75 201, max 850); closed back inside ≤3 days: 78%
- Share of daily range by PDT hour (avg % of summed H1 ranges; top 5): 07:00 6.4%, 06:00 5.7%, 00:00 5.4%, 05:00 5.2%, 23:00 5.0%
    full 24h profile: 00h=5.4 01h=4.9 02h=4.1 03h=4.1 04h=4.4 05h=5.2 06h=5.7 07h=6.4 08h=4.8 09h=3.6 10h=3.3 11h=2.8 12h=2.6 13h=2.7 14h=3.9 15h=3.4 16h=3.4 17h=4.5 18h=4.9 19h=4.1 20h=3.5 21h=3.6 22h=3.7 23h=5.0

### Cal2026 (→Sep 10, partial)  (2026-01-02 → 2026-09-10, N=180 trading days)
- Net change: -1311 pips  (close 2.0191 → 1.8879)
- High 2.0202 / Low 1.8540  (range 1663 pips)
- Median D1 ATR(14): 107 pips (p25 100 / p75 133)
- Regime cells (D1,H4), % of days (N=180):
         VOLATILE / VOLATILE       18.3%  (n=33)
    TRENDING_DOWN / VOLATILE       16.7%  (n=30)
          RANGING / RANGING        14.4%  (n=26)
         VOLATILE / RANGING         8.9%  (n=16)
         VOLATILE / TRENDING_DOWN   7.8%  (n=14)
          RANGING / VOLATILE        6.7%  (n=12)
         VOLATILE / TRENDING_UP     6.1%  (n=11)
    TRENDING_DOWN / TRENDING_UP     4.4%  (n=8)
      TRENDING_UP / TRENDING_UP     3.9%  (n=7)
    TRENDING_DOWN / RANGING         3.3%  (n=6)
    TRENDING_DOWN / TRENDING_DOWN   2.2%  (n=4)
      TRENDING_UP / VOLATILE        2.2%  (n=4)
          RANGING / TRENDING_UP     2.2%  (n=4)
          RANGING / TRENDING_DOWN   1.7%  (n=3)
      TRENDING_UP / TRENDING_DOWN   0.6%  (n=1)
      TRENDING_UP / RANGING         0.6%  (n=1)
- % days D1 regime RANGING: 25.0%   % days D1 structure TRANSITIONAL: 38.3%
- Confirmed D1 trend legs starting in segment (N=5  [descriptive only]): 2 up / 3 down
    length days: median 20 (min 1, max 57)   with-trend net pips: median +130 (min -144, max +873)
- Overshoot beyond prior confirmed swing extreme (N=12  [descriptive only] events): median 110 pips (p25 80 / p75 189, max 282); closed back inside ≤3 days: 58%
- Share of daily range by PDT hour (avg % of summed H1 ranges; top 5): 07:00 6.6%, 06:00 5.8%, 05:00 5.2%, 18:00 4.9%, 08:00 4.9%
    full 24h profile: 00h=4.9 01h=4.9 02h=4.1 03h=4.0 04h=4.2 05h=5.2 06h=5.8 07h=6.6 08h=4.9 09h=3.8 10h=3.3 11h=2.9 12h=2.8 13h=2.7 14h=4.8 15h=3.4 16h=3.2 17h=4.5 18h=4.9 19h=3.9 20h=3.5 21h=3.3 22h=3.7 23h=4.6

==============================================================================
## 3c. D1 structure episodes (grouped by label; every episode ≥5 days listed)

### UPTREND episodes (N=18  [descriptive only])
- length days: median 10 (min 1, max 30)   net pips: median -41
    2023-11-23 → 2023-12-01    7d  net    -54 pips  hi 1.9199 lo 1.9020
    2024-02-06 → 2024-02-22   13d  net    -29 pips  hi 1.9530 lo 1.9193
    2024-03-12 → 2024-03-21    8d  net   -109 pips  hi 1.9508 lo 1.9256
    2024-05-29 → 2024-06-27   22d  net   -177 pips  hi 1.9353 lo 1.8944
    2024-07-30 → 2024-08-19   15d  net   -341 pips  hi 2.0040 lo 1.9293
    2024-09-03 → 2024-09-25   17d  net   +167 pips  hi 1.9702 lo 1.9351
    2024-10-21 → 2024-11-08   15d  net   +166 pips  hi 1.9885 lo 1.9360
    2024-12-19 → 2024-12-31    8d  net     +0 pips  hi 2.0301 lo 2.0005
    2025-02-06 → 2025-02-17    8d  net    -35 pips  hi 1.9950 lo 1.9640
    2025-03-14 → 2025-04-24   30d  net   +197 pips  hi 2.1647 lo 2.0326
    2025-05-30 → 2025-06-13   11d  net    -21 pips  hi 2.1018 lo 2.0671
    2025-08-25 → 2025-09-16   17d  net   -423 pips  hi 2.0849 lo 2.0342
    2025-11-28 → 2025-12-11   10d  net   -175 pips  hi 2.0280 lo 1.9998
    2026-06-16 → 2026-07-13   20d  net   +324 pips  hi 1.9362 lo 1.8802

### DOWNTREND episodes (N=23  [descriptive only])
- length days: median 6 (min 1, max 57)   net pips: median +75
    2023-10-04 → 2023-10-12    7d  net   +119 pips  hi 1.9309 lo 1.9048
    2023-11-06 → 2023-11-16    9d  net   +175 pips  hi 1.9317 lo 1.8976
    2024-03-27 → 2024-04-23   20d  net   -136 pips  hi 1.9482 lo 1.9110
    2024-05-06 → 2024-05-20   11d  net    +75 pips  hi 1.9060 lo 1.8908
    2024-07-03 → 2024-07-09    5d  net    -59 pips  hi 1.9054 lo 1.8945
    2024-08-23 → 2024-08-30    6d  net   -120 pips  hi 1.9538 lo 1.9322
    2024-10-08 → 2024-10-15    6d  net   +141 pips  hi 1.9520 lo 1.9340
    2024-11-12 → 2024-12-13   24d  net   +262 pips  hi 2.0108 lo 1.9229
    2025-06-18 → 2025-06-30    9d  net   +134 pips  hi 2.1037 lo 2.0598
    2025-07-18 → 2025-08-11   17d  net    -60 pips  hi 2.0724 lo 2.0424
    2025-10-03 → 2025-10-21   13d  net   +232 pips  hi 2.0851 lo 2.0244
    2025-11-12 → 2025-11-24    9d  net   +126 pips  hi 2.0366 lo 1.9959
    2025-12-23 → 2025-12-31    6d  net    -30 pips  hi 2.0245 lo 2.0065
    2026-01-12 → 2026-03-31   57d  net   -873 pips  hi 2.0145 lo 1.8695
    2026-04-22 → 2026-06-02   30d  net   -130 pips  hi 1.8957 lo 1.8540

### TRANSITIONAL episodes (N=41)
- length days: median 5 (min 1, max 42)   net pips: median -10
    2023-09-08 → 2023-10-03   18d  net   -397 pips  hi 1.9594 lo 1.8858
    2023-10-13 → 2023-10-26   10d  net    -99 pips  hi 1.9342 lo 1.9019
    2023-10-30 → 2023-11-03    5d  net   -128 pips  hi 1.9206 lo 1.8900
    2023-12-08 → 2024-01-29   35d  net   +153 pips  hi 1.9420 lo 1.8589
    2024-02-23 → 2024-03-01    6d  net    +81 pips  hi 1.9507 lo 1.9259
    2024-04-24 → 2024-05-03    8d  net   -210 pips  hi 1.9311 lo 1.8952
    2024-05-21 → 2024-05-28    6d  net   +136 pips  hi 1.9250 lo 1.9031
    2024-07-10 → 2024-07-29   14d  net   +670 pips  hi 1.9762 lo 1.8960
    2024-09-26 → 2024-10-07    8d  net   -164 pips  hi 1.9532 lo 1.9125
    2025-01-02 → 2025-01-22   15d  net   -590 pips  hi 2.0234 lo 1.9593
    2025-01-29 → 2025-02-05    6d  net     -6 pips  hi 2.0151 lo 1.9875
    2025-02-18 → 2025-03-13   18d  net   +751 pips  hi 2.0629 lo 1.9746
    2025-05-02 → 2025-05-12    7d  net   -121 pips  hi 2.0817 lo 2.0482
    2025-05-16 → 2025-05-29   10d  net   +174 pips  hi 2.1036 lo 2.0673
    2025-07-11 → 2025-07-17    5d  net    +73 pips  hi 2.0746 lo 2.0443
    2025-08-12 → 2025-08-22    9d  net   +213 pips  hi 2.1006 lo 2.0590
    2025-10-22 → 2025-11-11   15d  net   -459 pips  hi 2.0630 lo 1.9988
    2025-12-12 → 2025-12-22    7d  net   +134 pips  hi 2.0291 lo 2.0042
    2026-01-02 → 2026-01-09    6d  net   -147 pips  hi 2.0202 lo 1.9967
    2026-04-01 → 2026-04-10    8d  net   -115 pips  hi 1.9261 lo 1.8918
    2026-06-03 → 2026-06-15    9d  net   +216 pips  hi 1.9124 lo 1.8750
    2026-07-14 → 2026-09-09   42d  net   -526 pips  hi 1.9355 lo 1.8732

==============================================================================

## Release reactions (day-0 close-to-close vs day-3 retention)
Classes: EXTENDED (retention ≥ 1.0), HELD (0.5–1.0), ROUND_TRIP (< 0.5,
includes full reversals). Date sources: verified / known / rule — see script.
(median D1 range over full window: 114 pips)
- RBA        N=25  [descriptive only]   |move0| med   89 pips, day-0 range med  157 pips  →  EXT  44%  HELD   4%  RT  52%
      SepY1 2023-09→2024-08        N=9  [descriptive only]  EXT  4 HELD  0 RT  5
      SepY2 2024-09→2025-08        N=8  [descriptive only]  EXT  4 HELD  1 RT  3
      SepY3 2025-09→2026-09-10     N=8  [descriptive only]  EXT  3 HELD  0 RT  5
- BoE        N=24  [descriptive only]   |move0| med   70 pips, day-0 range med  169 pips  →  EXT  38%  HELD  21%  RT  42%
      SepY1 2023-09→2024-08        N=8  [descriptive only]  EXT  1 HELD  1 RT  6
      SepY2 2024-09→2025-08        N=8  [descriptive only]  EXT  4 HELD  3 RT  1
      SepY3 2025-09→2026-09-10     N=8  [descriptive only]  EXT  4 HELD  1 RT  3
- AU_CPI_q   N=12  [descriptive only]   |move0| med   86 pips, day-0 range med  173 pips  →  EXT  50%  HELD  42%  RT   8%
      SepY1 2023-09→2024-08        N=4  [descriptive only]  EXT  3 HELD  0 RT  1
      SepY2 2024-09→2025-08        N=4  [descriptive only]  EXT  3 HELD  1 RT  0
      SepY3 2025-09→2026-09-10     N=4  [descriptive only]  EXT  0 HELD  4 RT  0
- UK_CPI     N=36                       |move0| med   55 pips, day-0 range med  124 pips  →  EXT  47%  HELD   8%  RT  44%
      SepY1 2023-09→2024-08        N=12  [descriptive only] EXT  9 HELD  1 RT  2
      SepY2 2024-09→2025-08        N=12  [descriptive only] EXT  4 HELD  1 RT  7
      SepY3 2025-09→2026-09-10     N=12  [descriptive only] EXT  4 HELD  1 RT  7
- US_CPI     N=35                       |move0| med   63 pips, day-0 range med  118 pips  →  EXT  40%  HELD  11%  RT  49%
      SepY1 2023-09→2024-08        N=12  [descriptive only] EXT  4 HELD  1 RT  7
      SepY2 2024-09→2025-08        N=12  [descriptive only] EXT  6 HELD  2 RT  4
      SepY3 2025-09→2026-09-10     N=11  [descriptive only] EXT  4 HELD  1 RT  6
- NFP        N=36                       |move0| med   36 pips, day-0 range med  123 pips  →  EXT  33%  HELD  19%  RT  47%
      SepY1 2023-09→2024-08        N=12  [descriptive only] EXT  5 HELD  1 RT  6
      SepY2 2024-09→2025-08        N=12  [descriptive only] EXT  4 HELD  2 RT  6
      SepY3 2025-09→2026-09-10     N=12  [descriptive only] EXT  3 HELD  4 RT  5
- US_ISM_mfg N=37                       |move0| med   45 pips, day-0 range med  126 pips  →  EXT  30%  HELD  24%  RT  46%
      SepY1 2023-09→2024-08        N=12  [descriptive only] EXT  4 HELD  2 RT  6
      SepY2 2024-09→2025-08        N=12  [descriptive only] EXT  2 HELD  4 RT  6
      SepY3 2025-09→2026-09-10     N=13  [descriptive only] EXT  5 HELD  3 RT  5

==============================================================================

## Frozen play walk-forward — THRUST_PULLBACK (spec frozen 2026-07-29)
Executed byte-identical to shadow_signals.py (TP_BOX_N=18, TP_BOX_X=3.0,
TP_BODY_ATR=1.0, TP_PULLBACK_ATR=0.25, TP_PULLBACK_BARS=10, HORIZON=30 H4
bars, stop = far box edge, r=-1.0 on stop touch else net/risk at horizon).
Walk-forward at every closed H4 bar over a trailing 300-bar window (live
_load_ctx shape). Episodes are non-overlapping: after a fire, further
fires inside its 30-bar horizon are the same opportunity, not counted.
Raw bar-level fires: 29.  Episodes: 22 (0 still inside horizon, ungraded).
  ALL (graded)                   N=22  [descriptive only]   win  36%  avgR -0.10  medR -0.40  maxDD 6.8R  stops hit 9 (noise-stops 1)
  SepY1 2023-09→2024-08          N=7  [descriptive only]    win  57%  avgR +0.35  medR +0.51  maxDD 1.5R  stops hit 1 (noise-stops 1)
  SepY2 2024-09→2025-08          N=7  [descriptive only]    win  14%  avgR -0.64  medR -1.00  maxDD 5.3R  stops hit 5 (noise-stops 0)
  SepY3 2025-09→2026-09-10       N=8  [descriptive only]    win  38%  avgR -0.01  medR -0.40  maxDD 3.0R  stops hit 3 (noise-stops 0)
  — by direction —
  LONG                           N=13  [descriptive only]   win  23%  avgR -0.33  medR -1.00  maxDD 7.0R  stops hit 7 (noise-stops 1)
  SHORT                          N=9  [descriptive only]    win  56%  avgR +0.25  medR +0.46  maxDD 1.9R  stops hit 2 (noise-stops 0)
  — by regime cell at fire (D1,H4 as of prior day close) —
  VOLATILE/VOLATILE              N=6  [descriptive only]    win  33%  avgR -0.27  medR -0.42  maxDD 2.4R  stops hit 2 (noise-stops 0)
  VOLATILE/RANGING               N=3  [descriptive only]    win  33%  avgR +0.06  medR -0.53  maxDD 1.5R  stops hit 1 (noise-stops 0)
  VOLATILE/TRENDING_DOWN         N=2  [descriptive only]    win  50%  avgR -0.09  medR -0.09  maxDD 1.0R  stops hit 1 (noise-stops 0)
  TRENDING_UP/VOLATILE           N=2  [descriptive only]    win   0%  avgR -1.00  medR -1.00  maxDD 2.0R  stops hit 2 (noise-stops 1)
  TRENDING_UP/TRENDING_UP        N=2  [descriptive only]    win   0%  avgR -1.00  medR -1.00  maxDD 2.0R  stops hit 2 (noise-stops 0)
  RANGING/TRENDING_UP            N=1  [descriptive only]    win 100%  avgR +0.51  medR +0.51  maxDD 0.0R  stops hit 0 (noise-stops 0)
  VOLATILE/TRENDING_UP           N=1  [descriptive only]    win 100%  avgR +1.75  medR +1.75  maxDD 0.0R  stops hit 0 (noise-stops 0)
  TRENDING_DOWN/TRENDING_UP      N=1  [descriptive only]    win   0%  avgR -0.09  medR -0.09  maxDD 0.1R  stops hit 0 (noise-stops 0)
  TRENDING_UP/RANGING            N=1  [descriptive only]    win 100%  avgR +0.98  medR +0.98  maxDD 0.0R  stops hit 0 (noise-stops 0)
  TRENDING_DOWN/RANGING          N=1  [descriptive only]    win   0%  avgR -1.00  medR -1.00  maxDD 1.0R  stops hit 1 (noise-stops 0)
  RANGING/RANGING                N=1  [descriptive only]    win   0%  avgR -0.20  medR -0.20  maxDD 0.2R  stops hit 0 (noise-stops 0)
  TRENDING_DOWN/VOLATILE         N=1  [descriptive only]    win 100%  avgR +1.55  medR +1.55  maxDD 0.0R  stops hit 0 (noise-stops 0)
  — loss species (graded losers) —
    bled_out: 9
    never_onside: 4
    stopped_then_reversed: 1

  Episode list (graded):
    2023-09-21 09:00Z SHORT entry 1.9164 stop 1.9288 r +0.83      mfe   205 mae    18 cell VOLATILE/TRENDING_DOWN 
    2023-11-16 18:00Z SHORT entry 1.9183 stop 1.9317 r +0.51      mfe   167 mae    36 cell RANGING/TRENDING_UP 
    2024-01-12 14:00Z LONG  entry 1.9053 stop 1.8940 r +1.75      mfe   367 mae    26 cell VOLATILE/TRENDING_UP 
    2024-02-02 10:00Z LONG  entry 1.9367 stop 1.9183 r -0.09      mfe    88 mae   114 cell TRENDING_DOWN/TRENDING_UP bled_out
    2024-02-23 06:00Z LONG  entry 1.9312 stop 1.9193 r +0.98      mfe   195 mae    20 cell TRENDING_UP/RANGING 
    2024-06-10 21:00Z LONG  entry 1.9279 stop 1.9151 r -0.53      mfe    51 mae   122 cell VOLATILE/RANGING bled_out
    2024-08-01 01:00Z LONG  entry 1.9683 stop 1.9571 r -1.00 STOP mfe   357 mae   352 cell TRENDING_UP/VOLATILE stopped_then_reversed
    2024-09-03 09:00Z LONG  entry 1.9486 stop 1.9322 r +0.77      mfe   215 mae    12 cell VOLATILE/VOLATILE 
    2024-09-19 01:00Z SHORT entry 1.9449 stop 1.9606 r -0.26      mfe    51 mae   125 cell VOLATILE/VOLATILE bled_out
    2024-11-14 18:00Z LONG  entry 1.9624 stop 1.9487 r -1.00 STOP mfe    14 mae   299 cell VOLATILE/RANGING never_onside
    2024-12-30 06:00Z LONG  entry 2.0208 stop 2.0039 r -1.00 STOP mfe    46 mae   308 cell TRENDING_UP/TRENDING_UP bled_out
    2025-02-03 10:00Z LONG  entry 2.0072 stop 1.9889 r -1.00 STOP mfe    28 mae   351 cell VOLATILE/TRENDING_DOWN never_onside
    2025-03-26 01:00Z SHORT entry 2.0497 stop 2.0651 r -1.00 STOP mfe   106 mae   280 cell TRENDING_UP/VOLATILE bled_out
    2025-04-30 09:00Z LONG  entry 2.0953 stop 2.0710 r -1.00 STOP mfe    11 mae   471 cell TRENDING_DOWN/RANGING never_onside
    2025-10-01 05:00Z SHORT entry 2.0360 stop 2.0492 r -0.59      mfe    33 mae    86 cell VOLATILE/VOLATILE bled_out
    2025-12-16 06:00Z LONG  entry 2.0214 stop 2.0040 r -0.20      mfe    77 mae    94 cell RANGING/RANGING bled_out
    2026-01-19 02:00Z SHORT entry 2.0005 stop 2.0145 r +1.71      mfe   326 mae    41 cell VOLATILE/RANGING 
    2026-01-30 10:00Z SHORT entry 1.9660 stop 1.9809 r +1.55      mfe   246 mae   118 cell TRENDING_DOWN/VOLATILE 
    2026-04-08 13:00Z SHORT entry 1.9014 stop 1.9172 r +0.46      mfe    79 mae   140 cell VOLATILE/VOLATILE 
    2026-06-17 21:00Z SHORT entry 1.8947 stop 1.9054 r -1.00 STOP mfe   146 mae   193 cell VOLATILE/VOLATILE bled_out
    2026-07-09 13:00Z LONG  entry 1.9319 stop 1.9222 r -1.00 STOP mfe    36 mae   158 cell TRENDING_UP/TRENDING_UP bled_out
    2026-09-02 05:00Z LONG  entry 1.8942 stop 1.8857 r -1.00 STOP mfe    12 mae   210 cell VOLATILE/VOLATILE never_onside

==============================================================================
Caveats (honesty section)
- Day-level regime cells are as-of-day-close descriptions; play-test cell
  attribution uses the PRIOR day's D1 regime + prior-close H4 regime (no peek).
- UK_CPI and US_ISM_mfg dates are rule-derived (Wednesday 14th–20th / first
  business day); RBA/BoE 2023-25 and AU quarterly CPI are known published
  schedules; US CPI/NFP and all 2026 CB dates verified from the institutions
  on 2026-09-11. AU monthly CPI indicator is EXCLUDED (dates not verifiable
  here in bulk; quarterly print is the dominant mover).
- Walk-forward evaluates the frozen check at every closed H4 bar; the live
  harness samples it at brief cadence, so live would catch a subset of these
  episodes. Spec parameters and grading are byte-identical to the shadow path.
- OANDA mid prices; no spread/slippage. Shadow-ledger convention retained.
```
