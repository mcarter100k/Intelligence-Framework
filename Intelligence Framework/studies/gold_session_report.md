# Gold (XAU/USD) session movement study: when gold moves (2021–2026)

**Spec:** `docs/specs/gold_session_study_spec.md`, frozen at 1409a75 (11:37:17 PM
PST, 2026-11-10), before the wrapper existed.
- Wrapper c313a6f; first computation 11:37:54 PM PST.
- Run once through `reality_run.py --no-env`: exit 0, stderr empty, project
  unchanged by hash.

**What it is:** descriptive only; USED-span data, learning only. **Gold is not
tradeable on the OANDA account.** This is for practice markups.

**Units:** gold figures are **US dollars**. The runner's output says "pips";
for gold, read "dollars".

## When gold moves (Pacific time, winter / PST)

Average high-to-low move in an hour, 2021–2026:

| Pacific (PST) | What's happening | Average move per hour |
|---|---|---|
| **4:00 – 7:00 AM** | New York opens into London's afternoon; US news at 5:30 AM | **$11.7 – $14.4**, by far the busiest |
| ↳ **5:00 AM** | The single busiest hour | **$14.4** |
| **5:00 PM** | Asian session opens | $10.9, a clear second bump |
| 10:00 PM – 1:00 AM | London opens | $8.2 – $8.3, only modest for gold |
| **1:00 PM** and **8:00 PM** | The quietest hours | **$5.1 – $5.2** |

What this adds up to:
- **The busiest hour moves 2.8 times the quietest,** more concentrated than
  GBP/AUD (2.4).
- **One window carries most of gold's day.** The London/New York overlap
  (4–8 AM PST) covers a median **67% of the day's whole range**, against 54%
  for GBP/AUD.
- **Where the extremes form:** the day's high forms in that window on 32% of
  days, and the low on 30%.
- **By 7:00 AM PST,** the day's high is already set on **67%** of days and the
  low on **73%**.
- **London matters much less for gold than for GBP/AUD.** Gold's London-open
  hours are only a little busier than its Tokyo hours.

**Dollar amounts mix eras.** Gold traded from about $1,800 to over $4,000
between 2021 and 2026, so the dollar figures are averages across very
different price levels. Today's typical day is about $75 (the 2026-11-10
probe), against a 2021–2026 average of $45. **Read the shape, not the
dollars.**

## Reading rules
- **No sharp step at any block boundary.** The rule's threshold is a step of
  at least 1.5.
- **The 12:00 UTC step (4 AM PST, the New York open) is 1.48,** just under
  the threshold. That boundary moves an hour with daylight saving, so the
  rise is probably sharper than fixed UTC blocks show.
- **Ignore the runner's "Phase 3 gate" line.** It is generic; the Phase 3
  question is about GBP/AUD and doesn't apply to gold.

## Hypotheses (not computed)
1. The 5:00 PM PST bump may be the Shanghai gold market's morning open
   (9 AM Beijing).
2. The New York-open rise may be sharper on a daylight-saving-aware clock.

## Limits
- **Hourly values are consistent, not verified.** They agree with gold's
  4-hour bars, but no second source has checked them.
- **One era (2021–2026).**
- **Not tradeable on this account.**

---

## Full output (verbatim)

```
run start (UTC): 2026-11-11T07:37:54+00:00
hash XAU_USD_H1.csv: OK
hash XAU_USD_H4.csv: OK
hash XAU_USD_D.csv: OK
first computation start (UTC): 2026-11-11T07:37:54+00:00


## XAU_USD

Study days with bars 1391; complete 1325; fold bars excluded from Q1 0

### Q1. Hourly range profile

**Q1 XAU_USD, all weekdays** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 336 | 5.1 | 2.3 |
| 22:00 | 14:00 PST / 15:00 PDT | 947 | 6.0 | 2.5 |
| 23:00 | 15:00 PST / 16:00 PDT | 1387 | 6.5 | 2.7 |
| 00:00 | 16:00 PST / 17:00 PDT | 1388 | 8.0 | 3.8 |
| 01:00 | 17:00 PST / 18:00 PDT | 1388 | 10.9 | 5.7 |
| 02:00 | 18:00 PST / 19:00 PDT | 1388 | 8.0 | 4.3 |
| 03:00 | 19:00 PST / 20:00 PDT | 1388 | 6.3 | 3.6 |
| 04:00 | 20:00 PST / 21:00 PDT | 1388 | 5.2 | 3.1 |
| 05:00 | 21:00 PST / 22:00 PDT | 1388 | 7.9 | 4.2 |
| 06:00 | 22:00 PST / 23:00 PDT | 1388 | 8.2 | 5.1 |
| 07:00 | 23:00 PST / 00:00 PDT | 1388 | 8.3 | 5.8 |
| 08:00 | 00:00 PST / 01:00 PDT | 1388 | 8.3 | 5.6 |
| 09:00 | 01:00 PST / 02:00 PDT | 1388 | 7.5 | 4.9 |
| 10:00 | 02:00 PST / 03:00 PDT | 1388 | 7.2 | 4.8 |
| 11:00 | 03:00 PST / 04:00 PDT | 1388 | 7.9 | 5.0 |
| 12:00 | 04:00 PST / 05:00 PDT | 1388 | 11.7 | 8.2 |
| 13:00 | 05:00 PST / 06:00 PDT | 1388 | 14.4 | 10.6 |
| 14:00 | 06:00 PST / 07:00 PDT | 1388 | 14.2 | 10.3 |
| 15:00 | 07:00 PST / 08:00 PDT | 1388 | 11.9 | 7.6 |
| 16:00 | 08:00 PST / 09:00 PDT | 1388 | 9.1 | 5.8 |
| 17:00 | 09:00 PST / 10:00 PDT | 1382 | 7.8 | 5.0 |
| 18:00 | 10:00 PST / 11:00 PDT | 1381 | 7.6 | 4.3 |
| 19:00 | 11:00 PST / 12:00 PDT | 1359 | 7.1 | 4.0 |
| 20:00 | 12:00 PST / 13:00 PDT | 1344 | 5.8 | 3.2 |

**Q1 XAU_USD, Mon** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 0 | – | – |
| 22:00 | 14:00 PST / 15:00 PDT | 190 | 9.9 | 5.1 |
| 23:00 | 15:00 PST / 16:00 PDT | 275 | 9.7 | 3.7 |
| 00:00 | 16:00 PST / 17:00 PDT | 276 | 10.5 | 4.6 |
| 01:00 | 17:00 PST / 18:00 PDT | 276 | 12.9 | 6.8 |
| 02:00 | 18:00 PST / 19:00 PDT | 276 | 8.6 | 4.9 |
| 03:00 | 19:00 PST / 20:00 PDT | 276 | 6.6 | 3.8 |
| 04:00 | 20:00 PST / 21:00 PDT | 276 | 5.5 | 3.2 |
| 05:00 | 21:00 PST / 22:00 PDT | 276 | 8.7 | 4.5 |
| 06:00 | 22:00 PST / 23:00 PDT | 276 | 8.7 | 5.5 |
| 07:00 | 23:00 PST / 00:00 PDT | 276 | 9.3 | 6.0 |
| 08:00 | 00:00 PST / 01:00 PDT | 276 | 8.1 | 5.7 |
| 09:00 | 01:00 PST / 02:00 PDT | 276 | 7.8 | 5.3 |
| 10:00 | 02:00 PST / 03:00 PDT | 276 | 7.2 | 4.8 |
| 11:00 | 03:00 PST / 04:00 PDT | 276 | 8.5 | 5.1 |
| 12:00 | 04:00 PST / 05:00 PDT | 276 | 10.3 | 7.0 |
| 13:00 | 05:00 PST / 06:00 PDT | 276 | 12.8 | 9.0 |
| 14:00 | 06:00 PST / 07:00 PDT | 276 | 13.0 | 8.8 |
| 15:00 | 07:00 PST / 08:00 PDT | 276 | 10.1 | 6.3 |
| 16:00 | 08:00 PST / 09:00 PDT | 276 | 8.1 | 5.2 |
| 17:00 | 09:00 PST / 10:00 PDT | 273 | 7.0 | 4.6 |
| 18:00 | 10:00 PST / 11:00 PDT | 273 | 6.4 | 3.8 |
| 19:00 | 11:00 PST / 12:00 PDT | 260 | 6.5 | 3.8 |
| 20:00 | 12:00 PST / 13:00 PDT | 250 | 4.9 | 2.8 |

**Q1 XAU_USD, Tue** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 76 | 5.2 | 2.4 |
| 22:00 | 14:00 PST / 15:00 PDT | 191 | 4.5 | 2.2 |
| 23:00 | 15:00 PST / 16:00 PDT | 281 | 5.5 | 2.6 |
| 00:00 | 16:00 PST / 17:00 PDT | 281 | 7.6 | 3.5 |
| 01:00 | 17:00 PST / 18:00 PDT | 281 | 10.8 | 5.9 |
| 02:00 | 18:00 PST / 19:00 PDT | 281 | 7.7 | 4.2 |
| 03:00 | 19:00 PST / 20:00 PDT | 281 | 6.1 | 3.7 |
| 04:00 | 20:00 PST / 21:00 PDT | 281 | 5.1 | 3.0 |
| 05:00 | 21:00 PST / 22:00 PDT | 281 | 8.1 | 4.4 |
| 06:00 | 22:00 PST / 23:00 PDT | 281 | 8.3 | 4.9 |
| 07:00 | 23:00 PST / 00:00 PDT | 281 | 8.1 | 5.8 |
| 08:00 | 00:00 PST / 01:00 PDT | 281 | 8.9 | 6.2 |
| 09:00 | 01:00 PST / 02:00 PDT | 281 | 7.4 | 4.9 |
| 10:00 | 02:00 PST / 03:00 PDT | 281 | 6.8 | 4.4 |
| 11:00 | 03:00 PST / 04:00 PDT | 281 | 8.1 | 5.2 |
| 12:00 | 04:00 PST / 05:00 PDT | 281 | 11.0 | 7.8 |
| 13:00 | 05:00 PST / 06:00 PDT | 281 | 14.0 | 11.0 |
| 14:00 | 06:00 PST / 07:00 PDT | 281 | 14.9 | 10.6 |
| 15:00 | 07:00 PST / 08:00 PDT | 281 | 12.3 | 8.5 |
| 16:00 | 08:00 PST / 09:00 PDT | 281 | 8.7 | 5.9 |
| 17:00 | 09:00 PST / 10:00 PDT | 281 | 7.5 | 5.0 |
| 18:00 | 10:00 PST / 11:00 PDT | 281 | 7.0 | 4.1 |
| 19:00 | 11:00 PST / 12:00 PDT | 279 | 6.5 | 3.8 |
| 20:00 | 12:00 PST / 13:00 PDT | 279 | 5.5 | 2.8 |

**Q1 XAU_USD, Wed** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 89 | 4.3 | 2.0 |
| 22:00 | 14:00 PST / 15:00 PDT | 191 | 5.2 | 2.0 |
| 23:00 | 15:00 PST / 16:00 PDT | 279 | 5.7 | 2.5 |
| 00:00 | 16:00 PST / 17:00 PDT | 279 | 7.3 | 3.5 |
| 01:00 | 17:00 PST / 18:00 PDT | 279 | 9.8 | 5.1 |
| 02:00 | 18:00 PST / 19:00 PDT | 279 | 7.7 | 3.9 |
| 03:00 | 19:00 PST / 20:00 PDT | 279 | 6.0 | 3.4 |
| 04:00 | 20:00 PST / 21:00 PDT | 279 | 5.1 | 3.2 |
| 05:00 | 21:00 PST / 22:00 PDT | 279 | 7.3 | 4.0 |
| 06:00 | 22:00 PST / 23:00 PDT | 279 | 7.7 | 5.1 |
| 07:00 | 23:00 PST / 00:00 PDT | 279 | 7.8 | 5.9 |
| 08:00 | 00:00 PST / 01:00 PDT | 279 | 8.0 | 5.3 |
| 09:00 | 01:00 PST / 02:00 PDT | 279 | 7.4 | 4.6 |
| 10:00 | 02:00 PST / 03:00 PDT | 279 | 7.3 | 5.0 |
| 11:00 | 03:00 PST / 04:00 PDT | 279 | 7.6 | 4.7 |
| 12:00 | 04:00 PST / 05:00 PDT | 279 | 11.7 | 7.7 |
| 13:00 | 05:00 PST / 06:00 PDT | 279 | 14.3 | 10.3 |
| 14:00 | 06:00 PST / 07:00 PDT | 279 | 13.7 | 9.8 |
| 15:00 | 07:00 PST / 08:00 PDT | 279 | 11.5 | 8.0 |
| 16:00 | 08:00 PST / 09:00 PDT | 279 | 8.6 | 5.6 |
| 17:00 | 09:00 PST / 10:00 PDT | 279 | 7.6 | 4.9 |
| 18:00 | 10:00 PST / 11:00 PDT | 279 | 10.2 | 5.3 |
| 19:00 | 11:00 PST / 12:00 PDT | 277 | 9.1 | 4.9 |
| 20:00 | 12:00 PST / 13:00 PDT | 277 | 6.7 | 3.7 |

**Q1 XAU_USD, Thu** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 87 | 5.6 | 2.7 |
| 22:00 | 14:00 PST / 15:00 PDT | 190 | 5.8 | 2.4 |
| 23:00 | 15:00 PST / 16:00 PDT | 278 | 6.3 | 2.7 |
| 00:00 | 16:00 PST / 17:00 PDT | 278 | 7.4 | 3.6 |
| 01:00 | 17:00 PST / 18:00 PDT | 278 | 10.6 | 5.7 |
| 02:00 | 18:00 PST / 19:00 PDT | 278 | 8.1 | 4.3 |
| 03:00 | 19:00 PST / 20:00 PDT | 278 | 6.3 | 3.4 |
| 04:00 | 20:00 PST / 21:00 PDT | 278 | 5.2 | 3.1 |
| 05:00 | 21:00 PST / 22:00 PDT | 278 | 7.9 | 4.1 |
| 06:00 | 22:00 PST / 23:00 PDT | 278 | 8.4 | 5.2 |
| 07:00 | 23:00 PST / 00:00 PDT | 278 | 8.2 | 5.7 |
| 08:00 | 00:00 PST / 01:00 PDT | 278 | 8.4 | 5.7 |
| 09:00 | 01:00 PST / 02:00 PDT | 278 | 7.2 | 4.9 |
| 10:00 | 02:00 PST / 03:00 PDT | 278 | 7.6 | 5.0 |
| 11:00 | 03:00 PST / 04:00 PDT | 278 | 7.6 | 5.0 |
| 12:00 | 04:00 PST / 05:00 PDT | 278 | 12.8 | 9.3 |
| 13:00 | 05:00 PST / 06:00 PDT | 278 | 15.2 | 11.3 |
| 14:00 | 06:00 PST / 07:00 PDT | 278 | 14.3 | 10.7 |
| 15:00 | 07:00 PST / 08:00 PDT | 278 | 12.8 | 8.0 |
| 16:00 | 08:00 PST / 09:00 PDT | 278 | 10.3 | 6.0 |
| 17:00 | 09:00 PST / 10:00 PDT | 278 | 8.4 | 5.1 |
| 18:00 | 10:00 PST / 11:00 PDT | 277 | 6.8 | 4.2 |
| 19:00 | 11:00 PST / 12:00 PDT | 275 | 6.8 | 3.9 |
| 20:00 | 12:00 PST / 13:00 PDT | 272 | 5.8 | 3.0 |

**Q1 XAU_USD, Fri** (pips per hour bar)

| UTC hour | Pacific | N | mean | median |
|---|---|---|---|---|
| 21:00 | 13:00 PST / 14:00 PDT | 84 | 5.3 | 2.2 |
| 22:00 | 14:00 PST / 15:00 PDT | 185 | 4.7 | 2.0 |
| 23:00 | 15:00 PST / 16:00 PDT | 274 | 5.5 | 2.5 |
| 00:00 | 16:00 PST / 17:00 PDT | 274 | 7.1 | 3.6 |
| 01:00 | 17:00 PST / 18:00 PDT | 274 | 10.4 | 5.3 |
| 02:00 | 18:00 PST / 19:00 PDT | 274 | 8.0 | 4.3 |
| 03:00 | 19:00 PST / 20:00 PDT | 274 | 6.4 | 3.6 |
| 04:00 | 20:00 PST / 21:00 PDT | 274 | 5.0 | 2.9 |
| 05:00 | 21:00 PST / 22:00 PDT | 274 | 7.3 | 4.0 |
| 06:00 | 22:00 PST / 23:00 PDT | 274 | 7.9 | 5.0 |
| 07:00 | 23:00 PST / 00:00 PDT | 274 | 8.0 | 5.7 |
| 08:00 | 00:00 PST / 01:00 PDT | 274 | 8.3 | 5.3 |
| 09:00 | 01:00 PST / 02:00 PDT | 274 | 7.5 | 5.0 |
| 10:00 | 02:00 PST / 03:00 PDT | 274 | 7.2 | 4.6 |
| 11:00 | 03:00 PST / 04:00 PDT | 274 | 7.8 | 5.1 |
| 12:00 | 04:00 PST / 05:00 PDT | 274 | 12.9 | 9.0 |
| 13:00 | 05:00 PST / 06:00 PDT | 274 | 15.7 | 11.9 |
| 14:00 | 06:00 PST / 07:00 PDT | 274 | 15.3 | 11.3 |
| 15:00 | 07:00 PST / 08:00 PDT | 274 | 12.7 | 8.1 |
| 16:00 | 08:00 PST / 09:00 PDT | 274 | 9.9 | 6.2 |
| 17:00 | 09:00 PST / 10:00 PDT | 271 | 8.3 | 5.2 |
| 18:00 | 10:00 PST / 11:00 PDT | 271 | 7.8 | 4.5 |
| 19:00 | 11:00 PST / 12:00 PDT | 268 | 6.4 | 4.1 |
| 20:00 | 12:00 PST / 13:00 PDT | 266 | 5.9 | 3.6 |

### Q2. Share of daily range by block

Days with zero range excluded: 0. Winter Mondays' SYDNEY block holds 2 bars, not 3.

**Q2 XAU_USD, all weekdays**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 1325 | 0.174 | 0.064 | 0.092 | 0.138 | 0.216 | 0.333 |
| TOKYO | 1325 | 0.467 | 0.230 | 0.319 | 0.443 | 0.594 | 0.734 |
| LONDON | 1325 | 0.430 | 0.210 | 0.294 | 0.396 | 0.542 | 0.697 |
| LDN_NY | 1325 | 0.669 | 0.401 | 0.522 | 0.669 | 0.821 | 0.955 |
| NY_PM | 1325 | 0.394 | 0.198 | 0.258 | 0.359 | 0.486 | 0.630 |

**Q2 XAU_USD, Mon**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 249 | 0.260 | 0.112 | 0.147 | 0.217 | 0.334 | 0.462 |
| TOKYO | 249 | 0.541 | 0.313 | 0.402 | 0.530 | 0.655 | 0.791 |
| LONDON | 249 | 0.455 | 0.237 | 0.313 | 0.430 | 0.567 | 0.701 |
| LDN_NY | 249 | 0.616 | 0.381 | 0.473 | 0.598 | 0.753 | 0.903 |
| NY_PM | 249 | 0.363 | 0.186 | 0.253 | 0.336 | 0.474 | 0.583 |

**Q2 XAU_USD, Tue**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 265 | 0.155 | 0.063 | 0.086 | 0.127 | 0.191 | 0.281 |
| TOKYO | 265 | 0.474 | 0.244 | 0.332 | 0.445 | 0.596 | 0.726 |
| LONDON | 265 | 0.444 | 0.219 | 0.317 | 0.424 | 0.564 | 0.711 |
| LDN_NY | 265 | 0.689 | 0.438 | 0.535 | 0.689 | 0.837 | 0.974 |
| NY_PM | 265 | 0.368 | 0.195 | 0.249 | 0.341 | 0.449 | 0.576 |

**Q2 XAU_USD, Wed**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 277 | 0.146 | 0.057 | 0.083 | 0.117 | 0.174 | 0.262 |
| TOKYO | 277 | 0.444 | 0.205 | 0.310 | 0.414 | 0.555 | 0.710 |
| LONDON | 277 | 0.422 | 0.212 | 0.298 | 0.379 | 0.518 | 0.693 |
| LDN_NY | 277 | 0.646 | 0.367 | 0.510 | 0.635 | 0.794 | 0.961 |
| NY_PM | 277 | 0.478 | 0.227 | 0.310 | 0.440 | 0.610 | 0.814 |

**Q2 XAU_USD, Thu**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 270 | 0.171 | 0.071 | 0.096 | 0.146 | 0.212 | 0.332 |
| TOKYO | 270 | 0.449 | 0.223 | 0.309 | 0.414 | 0.556 | 0.717 |
| LONDON | 270 | 0.429 | 0.207 | 0.291 | 0.400 | 0.539 | 0.698 |
| LDN_NY | 270 | 0.695 | 0.420 | 0.554 | 0.699 | 0.844 | 0.976 |
| NY_PM | 270 | 0.376 | 0.188 | 0.246 | 0.345 | 0.474 | 0.577 |

**Q2 XAU_USD, Fri**: block range ÷ day range (shares do not sum to 1)

| block | N days | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| SYDNEY | 264 | 0.143 | 0.057 | 0.080 | 0.112 | 0.180 | 0.253 |
| TOKYO | 264 | 0.430 | 0.209 | 0.262 | 0.396 | 0.563 | 0.700 |
| LONDON | 264 | 0.400 | 0.181 | 0.265 | 0.368 | 0.522 | 0.652 |
| LDN_NY | 264 | 0.698 | 0.430 | 0.578 | 0.704 | 0.836 | 0.956 |
| NY_PM | 264 | 0.378 | 0.201 | 0.257 | 0.357 | 0.454 | 0.595 |

### Q3. Where the daily high and low form

**Q3 XAU_USD, all weekdays** (N days 1325)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 9.4% | 12.4% |
| TOKYO | 21.1% | 23.5% |
| LONDON | 12.5% | 12.8% |
| LDN_NY | 32.0% | 30.3% |
| NY_PM | 25.1% | 20.9% |

High and low in the same block: 9.5% of days

**Q3 XAU_USD, Mon** (N days 249)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 14.9% | 18.5% |
| TOKYO | 24.1% | 23.7% |
| LONDON | 14.9% | 12.9% |
| LDN_NY | 24.9% | 28.1% |
| NY_PM | 21.3% | 16.9% |

High and low in the same block: 4.8% of days

**Q3 XAU_USD, Tue** (N days 265)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 8.3% | 9.4% |
| TOKYO | 22.6% | 24.5% |
| LONDON | 10.6% | 14.3% |
| LDN_NY | 34.7% | 32.1% |
| NY_PM | 23.8% | 19.6% |

High and low in the same block: 10.2% of days

**Q3 XAU_USD, Wed** (N days 277)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 5.4% | 10.1% |
| TOKYO | 18.4% | 20.6% |
| LONDON | 11.2% | 14.8% |
| LDN_NY | 33.6% | 27.4% |
| NY_PM | 31.4% | 27.1% |

High and low in the same block: 14.8% of days

**Q3 XAU_USD, Thu** (N days 270)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 10.4% | 11.5% |
| TOKYO | 22.6% | 24.4% |
| LONDON | 13.3% | 10.0% |
| LDN_NY | 30.7% | 36.3% |
| NY_PM | 23.0% | 17.8% |

High and low in the same block: 8.9% of days

**Q3 XAU_USD, Fri** (N days 264)

| block | % of days the HIGH formed here | % of days the LOW formed here |
|---|---|---|
| SYDNEY | 8.3% | 12.9% |
| TOKYO | 17.8% | 24.6% |
| LONDON | 12.5% | 12.1% |
| LDN_NY | 35.6% | 27.7% |
| NY_PM | 25.8% | 22.7% |

High and low in the same block: 8.3% of days

### Q4. How early the extremes are set

**Q4 XAU_USD, all weekdays** (N days 1325)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 23.4% | 27.7% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 36.0% | 42.7% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 67.0% | 73.1% |

**Q4 XAU_USD, Mon** (N days 249)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 31.3% | 32.9% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 45.0% | 50.2% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 73.1% | 77.1% |

**Q4 XAU_USD, Tue** (N days 265)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 22.3% | 27.9% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 35.8% | 43.0% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 69.8% | 73.2% |

**Q4 XAU_USD, Wed** (N days 277)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 17.0% | 24.2% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 29.6% | 37.9% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 60.6% | 67.1% |

**Q4 XAU_USD, Thu** (N days 270)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 27.8% | 24.4% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 38.5% | 40.4% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 68.9% | 75.6% |

**Q4 XAU_USD, Fri** (N days 264)

| already in place by | UTC | Pacific | % days HIGH set | % days LOW set |
|---|---|---|---|---|
| hour 6 | 03:00 | 19:00 PST / 20:00 PDT | 19.3% | 29.5% |
| hour 12 | 09:00 | 01:00 PST / 02:00 PDT | 31.8% | 42.8% |
| hour 18 | 15:00 | 07:00 PST / 08:00 PDT | 63.3% | 73.1% |

### Q5. Mean ATR(14) by timeframe (pips; numbers only)

| timeframe | all weekdays (N) | Mon | Tue | Wed | Thu | Fri |
|---|---|---|---|---|---|---|
| H1 | 8.6 (31802) | 9.1 (6289) | 8.3 (6444) | 8.2 (6412) | 8.6 (6380) | 8.5 (6277) |
| H4 | 17.4 (8307) | 18.1 (1653) | 17.3 (1680) | 17.2 (1668) | 17.2 (1665) | 17.2 (1641) |
| D1 | 45.4 (1374) | 45.8 (274) | 45.4 (278) | 45.5 (276) | 45.1 (275) | 45.3 (271) |


## Reading rules fixed in the spec (§5, §6)

| pair | boundary (UTC) | step = mean(hour b) ÷ mean(hour b−1) | sharp (≥1.5 or ≤0.667)? | DST-exposed? |
|---|---|---|---|---|
| XAU_USD | 21:00 | 0.87 | no | yes |
| XAU_USD | 00:00 | 1.22 | no | no |
| XAU_USD | 07:00 | 1.01 | no | yes |
| XAU_USD | 12:00 | 1.48 | no | yes |
| XAU_USD | 16:00 | 0.77 | no | yes |

XAU_USD: largest hourly mean 14.4 at 13:00 UTC; smallest 5.1 at 21:00 UTC; ratio 2.84

Phase 3 gate (§6): CONCENTRATED — Phase 3 question not moot (team decides)
```
