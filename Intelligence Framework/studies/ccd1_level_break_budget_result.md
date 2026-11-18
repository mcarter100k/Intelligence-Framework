# LEVEL BREAK budget, ruling P2 (verbatim output)

Script: studies/ccd1_level_break_budget.py. Gold archives (pinned hashes), through scripts/reality_run.py --no-env; project unchanged by hash. Counts only, no outcome. The options sections were added in two later runs; the earlier sections were confirmed identical across all three runs (diff).

```
# LEVEL BREAK budget (ruling P2): gold 2021-04-26 -> 2026-09-09, 281 trading weeks; list 'no 4-hour swings', tolerance 0.1

- ARRIVAL alerts: 1411 bars with an arrival; 1160 sent as ARRIVAL (the rest arrived and closed through in the same hour, sent as one LEVEL BREAK) = 4.13 a week
- watched prices: 1623; closed through while still qualifying: 1084 (67%); the rest stopped qualifying first
- LEVEL BREAK alerts: 931 bars = 3.31 a week; 370 in the arrival's own hour; hours from arrival to break: median 1, 90th pct 8
- CCD-1 BREAK: 47 = 0.17 a week
- refactor check: every arrival bar = 5.0 a week (the M3 run printed 5.0 for this list)

| Alerts | Average a week | Median week | 90th-pct week | Busiest week | Weeks over 11 |
|---|---|---|---|---|---|
| ARRIVAL + CCD-1 BREAK (measured; before P1) | 5.2 | 5 | 8 | 14 | 2 (1%) |
| ARRIVAL + CCD-1 BREAK + LEVEL BREAK (measured) | 7.6 | 7 | 12 | 18 | 36 (13%) |
| before P1, + 3 release warnings (estimate) | 8.2 | 8 | 11 | 17 | 17 (6%) |
| **with LEVEL BREAK, + 3 release warnings (estimate)** | 10.6 | 10 | 15 | 21 | 110 (39%) |

## Options for the owner (ruling P2: reported, not applied)

| Option | LEVEL BREAK a week | Total a week (with 3 releases) | 90th-pct week | Weeks over 11 |
|---|---|---|---|---|
| spec as written (any close through) | 3.31 | 10.6 | 15 | 110 (39%) |
| close at least 0.05 ATR beyond | 2.93 | 10.5 | 15 | 107 (38%) |
| close at least 0.10 ATR beyond (the arrival tolerance) | 2.59 | 10.3 | 15 | 97 (35%) |
| close at least 0.20 ATR beyond | 2.12 | 10.1 | 14 | 91 (32%) |
| 2 or more hours after the arrival | 2.97 | 11.2 | 16 | 134 (48%) |
| 0.10 ATR beyond and 2+ hours after | 2.42 | 10.6 | 15 | 113 (40%) |

## Each ARRIVAL level list with LEVEL BREAK as written (ruling P2: reported, not applied)

| ARRIVAL list | ARRIVAL sent a week | LEVEL BREAK a week | Total a week (with 3 releases) | 90th-pct week | Weeks over 11 |
|---|---|---|---|---|---|
| all five | 5.95 | 4.66 | 13.8 | 20 | 194 (69%) |
| no 4-hour swings | 4.13 | 3.31 | 10.6 | 15 | 110 (39%) |
| no prior session | 5.41 | 4.32 | 12.9 | 19 | 171 (61%) |
| daily swings + prior week | 1.90 | 1.68 | 6.7 | 10 | 18 (6%) |
```
