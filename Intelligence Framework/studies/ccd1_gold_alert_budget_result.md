# Gold ALERT budget, ruling M3 (verbatim output)

Script: studies/ccd1_gold_alert_budget.py. Run through scripts/reality_run.py --no-env; project unchanged by hash. Counts only, no outcome.

```
# Gold ALERT budget (ruling M3): 2021-04-26 -> 2026-09-09, 281 trading weeks, tolerance 0.1

BREAK detections (CCD-1 as signed): 47 = 0.17 a week

| Level list | ARRIVAL / week | ARRIVAL + BREAK / week (measured) | median week | 90th-pct week | busiest week | + 2 release warnings (estimate) = total / week | 90th-pct week + 2 |
|---|---|---|---|---|---|---|---|
| all five | 7.0 | 7.1 | 7 | 11 | 19 | 9.1 | 13 |
| no 4-hour swings | 5.0 | 5.2 | 5 | 8 | 14 | 7.2 | 10 |
| no prior session | 6.3 | 6.5 | 6 | 10 | 18 | 8.5 | 12 |
| daily swings + prior week | 2.4 | 2.5 | 2 | 5 | 9 | 4.5 | 7 |

Share of weeks above 10 (measured ARRIVAL + BREAK, + the release estimate):
- all five: 74 of 281 weeks (26%)
- no 4-hour swings: 17 of 281 weeks (6%)
- no prior session: 57 of 281 weeks (20%)
- daily swings + prior week: 2 of 281 weeks (1%)
```
