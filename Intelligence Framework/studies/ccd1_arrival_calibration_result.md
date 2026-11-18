# ARRIVAL fire-rate calibration (verbatim output)

Spec §13/§15 (addendum 3f83bcc, before any count). Script: studies/ccd1_arrival_calibration.py. Run through scripts/reality_run.py --no-env; project unchanged by hash. Counts only, no outcome.

```
# ARRIVAL fire-rate calibration (spec §13/§15, addendum 3f83bcc); counts only, no outcome

XAU_USD: hourly bars 31816 (2021-04-26 -> 2026-09-09); levels per bar median 25, max 35
GBP_AUD: hourly bars 33478 (2021-04-26 -> 2026-09-09); levels per bar median 24, max 37
GBP_JPY: hourly bars 33478 (2021-04-26 -> 2026-09-09); levels per bar median 25, max 38
span 2021-04-26 -> 2026-09-09: 280.3 calendar weeks, 281 trading weeks

| Level list | Tolerance (ATR) | Gold / week | GBP/AUD / week | GBP/JPY / week | **Total / week** | Total: median week | Total: 90th-pct week |
|---|---|---|---|---|---|---|---|
| all five | 0.05 | 6.1 | 6.6 | 6.2 | **18.9** | 19 | 26 |
| all five | 0.10 | 7.0 | 7.4 | 7.0 | **21.4** | 21 | 29 |
| all five | 0.15 | 7.9 | 8.4 | 7.9 | **24.2** | 24 | 34 |
| all five | 0.20 | 8.9 | 9.6 | 8.9 | **27.5** | 27 | 38 |
| no 4-hour swings | 0.05 | 4.4 | 5.1 | 4.6 | **14.2** | 14 | 20 |
| no 4-hour swings | 0.10 | 5.0 | 5.7 | 5.3 | **16.0** | 16 | 22 |
| no 4-hour swings | 0.15 | 5.7 | 6.5 | 6.0 | **18.1** | 18 | 25 |
| no 4-hour swings | 0.20 | 6.5 | 7.4 | 6.8 | **20.7** | 20 | 29 |
| no prior session | 0.05 | 5.6 | 6.0 | 5.7 | **17.3** | 17 | 24 |
| no prior session | 0.10 | 6.3 | 6.7 | 6.3 | **19.4** | 19 | 28 |
| no prior session | 0.15 | 7.2 | 7.6 | 7.1 | **21.9** | 22 | 31 |
| no prior session | 0.20 | 8.1 | 8.6 | 8.1 | **24.8** | 24 | 34 |
| daily swings + prior week | 0.05 | 2.1 | 2.3 | 2.3 | **6.8** | 6 | 11 |
| daily swings + prior week | 0.10 | 2.4 | 2.5 | 2.6 | **7.5** | 7 | 12 |
| daily swings + prior week | 0.15 | 2.7 | 2.8 | 2.9 | **8.4** | 8 | 13 |
| daily swings + prior week | 0.20 | 3.0 | 3.2 | 3.2 | **9.4** | 9 | 15 |
```

## Spot-check (gold, daily swings + prior week, tolerance 0.10; fires 100-102 against the raw bars)

```
2022-02-24 19:00:00+00:00 bar H/L 1920.39 1878.095 ATR 22.97 tol 2.297
   level D1 D121 1912.785 | last close >=0.5 ATR away: 2022-02-24 15:00:00+00:00 1928.866
   level D1 D125 1916.615 | last close >=0.5 ATR away: 2022-02-24 15:00:00+00:00 1928.866
   level PWEEK PWH(2022, 7) 1902.545 | last close >=0.5 ATR away: 2022-02-24 18:00:00+00:00 1920.24
2022-02-24 23:00:00+00:00 bar H/L 1913.746 1904.1 ATR 28.233 tol 2.823
   level D1 D121 1912.785 | last close >=0.5 ATR away: 2022-02-24 20:00:00+00:00 1898.186
   level PWEEK PWH(2022, 7) 1902.545 | last close >=0.5 ATR away: 2022-02-24 19:00:00+00:00 1888.19
2022-02-25 01:00:00+00:00 bar H/L 1921.91 1906.38 ATR 28.233 tol 2.823
   level D1 D121 1912.785 | last close >=0.5 ATR away: 2022-02-24 20:00:00+00:00 1898.186
   level D1 D125 1916.615 | last close >=0.5 ATR away: 2022-02-24 20:00:00+00:00 1898.186
```

## HEADS-UP estimate (no 2021-2026 calendar history exists; live calendar.csv, week of 2026-11-16, read-only)

- All three instruments: 7 distinct High-impact times; 2 fall inside 04:00-08:00 PT and go in the morning alert; 5 separate + 5 morning = **10 a week**.
- Gold only (US releases): 3 times; 1 inside the window; 2 separate + 5 morning = **7 a week**.
- One week only: an estimate, not a calibration.
