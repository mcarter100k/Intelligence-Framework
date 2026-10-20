# History data — OANDA depth check (Phase 1) and HistData re-probe (Phase 3)

**Run:** 2026-10-20 00:00 → 00:20 PDT, under the 2026-10-20 team
ruling ("OANDA depth check first, Dukascopy attempt 2 only if needed";
validation_log 2026-10-20). Spec: docs/specs/data_map_spec.md (f5eea4f,
67578e5).

**Verification numbers only.** No price level, average, range, volatility or
pattern count appears here. OANDA candles outside the reduced-gate window
were reduced to timestamps on receipt. The reduced gate reports
differences between two copies of the same bars, in pips, and nothing else.

**SEALED EXAM (2014-01-01 → 2021-04-25): not counted, not stored.** Every
request window was checked against the seal before sending, and every
returned timestamp after receipt. One boundary incident is recorded below.

Scripts (this directory, run with `python3 -I`, paths as arguments):
`history_depth_oanda_probe.py`, `history_depth_bar_grid.py`,
`history_depth_reduced_gate.py`, `history_depth_histdata_probe.py`.
Downloads and timestamp files stayed outside the repo.

---

## Premise conflicts found before running (rule 5)

1. **Task 2 asked for bar counts over 2014-01-01 → 2021-12-31.** All of it
   up to 2021-04-25 is the SEALED EXAM, and the ruling's own boundary says
   the exam is "not counted, at any point, in any phase." **Not done.**
   Counted instead, and labelled as a substitution: the STUDY span
   2005–2013 (the span the Phase 1 verdict asks about) and the unsealed
   remainder of the requested range, 2021-04-27 → 2021-12-31.
2. **"OANDA's own 2014–2021 data" (audit 2026-09-29, §5 item 2) is the
   SEALED EXAM itself.** Using it for history is not a change of data
   source. It means opening the exam under spec §7: one frozen candidate
   spec, hashes, the marker file, one run. Recorded for the team, not acted on.

## Boundary incident (sealed edge)

The first request for the 2021 remainder used `from=2021-04-26T00:00Z`.
OANDA returns the candle **containing** `from`, so it also returned the
candle opening **2021-04-25 14:00 PDT** (Sunday 17:00 New York). That
candle's label date is in the sealed span, but its session is Monday
2021-04-26, which is in the USED span. The post-receipt guard aborted the
run. Nothing from that request was written to disk. The candle's
timestamp was printed; no price was printed or stored. The guard now keeps
a one-day margin, so the remainder starts at the 2021-04-27 session and the
Monday 2021-04-26 session was given up. **The spec does not say which side
of the seal that Sunday-open candle is on; that is for the team to rule.**

---

## Phase 1 — OANDA depth

### 1. Earliest candle served (this live account, mid prices, default 17:00-NY alignment)

| pair | D1 | H4 | H1 |
|---|---|---|---|
| GBP_AUD | 2004-05-31 14:00 PDT | 2004-06-01 10:00 PDT | 2004-05-31 13:00 PDT |
| GBP_JPY | 2002-05-07 14:00 PDT | 2002-05-08 10:00 PDT | 2002-05-07 13:00 PDT |

Found by paging forward from 2000-01-01; every earlier window returned zero
candles. A second request for the window ending at the first candle also
returned zero. Both pairs therefore cover the STUDY start (2005-01-01).

### 2. Coverage, STUDY span 2005–2013 (substituted for 2014–2021; see above)

- **As served, the D1 series fails the §3 count band.** It carries 273–361
  candles a year against [252, 262], because of 14–101 weekend-session
  candles a year. Those are candles whose 17:00-NY session falls on a
  Saturday or Sunday; 2011 is the heaviest year, with about 495 weekend H4
  candles and about 1,070 weekend H1 candles per pair.
- **The weekday grid underneath is intact.** Aligned weekday D1 candles
  number **259–262 a year** (inside [252, 262]). Weekday sessions carrying
  all **6 H4 bars: 99.23–100%** (§3 needs ≥ 99%). No candle on any weekday
  is off the expected start time (0 misaligned, all years, both pairs,
  all three granularities).
- **Every gap and every short session is a Christmas or New Year
  holiday**: Dec 24–26 and Dec 31–Jan 2. Full list below.
- **Census reconciliation (INFERRED).** The spec's census line "H4 ~4.8–5.7
  bars/day with 70–95 short days/yr" reproduces as H4 rows ÷ D1 rows *with
  weekend candles included*: 4.71–5.75 here. Its "330–360 raw D1 rows/yr"
  matches the 331–361 measured for 2005–2012. So the census measured the
  weekend extras, not missing weekday bars. The census method was not
  recorded, so this explanation rests on the arithmetic match alone.

USED remainder 2021-04-27 → 2021-12-31 (modern convention): 179 D1 / 1,074
H4 / 4,291 H1 per pair; 0 weekend, 0 misaligned, 100% full H4 sessions.
One H1 gap: 2021-11-21 14:00–15:00 PST, the two hours of the Sunday open.

### 3. API constraints for a later bulk pull (all observed this run)

- **5,000 candles per request, hard.** `count=5001` → HTTP 400 "Maximum value
  for 'count' exceeded". A `from`/`to` window implying more than 5,000
  candles (about 6,200 H1) gets the same 400, so windows must be sized; a
  month of H1 (≤ 744) works.
- `to` in the future → HTTP 400 "Time is in the future".
- **`from` returns the candle containing that instant**, not the first one
  starting after it. Any pull that runs up to the seal must keep a margin
  of at least one candle.
- 30 back-to-back requests: all HTTP 200 in 3.63 s. That is too fast for
  any retry (each retry waits at least 2 s), so none was throttled. The bulk
  runs (about 1,200 requests in all) completed, but the client retries
  429/5xx silently, so throttling during them was not measured. OANDA's
  published rate limits were not checked.
- Depth for this live account is shown above. Whether another account tier
  (for example practice) serves different depth was not checked.

### 4. Reduced gate — OANDA's historical API vs the framework's own stored bars

The September cache (`studies/data_cache/`, OANDA pulls of 2026-09-10/11),
re-fetched today with the same request, matched on every timestamp and
every field. So did the last completed D1 close the live path recorded in
`regime_classification_log.csv` (`price_basis=d1_close`), matched to the
last OANDA D1 candle closed at the log's timestamp:

- **Cache: 30,810 bars compared, 30,810 identical on O/H/L/C; difference
  0.0 pips at the median, p95 and max**; 0 timestamps on one side only.
  Window: 2022-05-31 → 2026-09-10 (GBP_AUD D1 from 2022-05-31, H4 from
  2023-04-30, H1 from 2023-08-24; GBP_JPY D1/H4 from 2023-08-24).
- **Live ledger: 76 of 76 recorded closes identical (38 per pair), max
  difference 0.0 pips.** Logged 2026-09-30 02:30 PDT → 2026-10-19 19:49 PDT.
- **Positive control:** a copy with one H4 close moved +1 pip and one ledger
  close moved +2 pips reported exactly those two (4,734/4,735 identical,
  max 1.0; 37/38 identical, max 2.0), and nothing else.
- **Limit:** this shows OANDA's history for 2022–2026 is stable and equals
  what the live path recorded. It cannot show that OANDA's 2005–2013 bars
  today equal what OANDA served then, because no copy from then exists.
  Live-recorded coverage is D1 closes only; H4 was never stored by the live path.

### 5. Verdict

**Can OANDA alone cover the STUDY span at D1 and H4? Not as served: NO.**
The weekend-session candles put raw D1 counts outside the §3 band.
**After one mechanical step that sets the weekend-session candles aside,
the counts say YES for both pairs and all nine years.** D1 is 259–262 a
year and H4 sessions are 99.23–100% complete; the only gaps are holidays.
Since the source is the same broker, there is no feed to reconcile:
the reduced gate matched exactly where both copies exist.

Not yet shown, so this is not a gate pass:
- §3 item 3 (D1 high/low == max/min of that day's H4, 50 days/pair/year)
  and item 4 (the four known-date spot checks) need prices and were not run.
- **The treatment of the weekend-session candles** (drop them, or fold
  them into the Monday session) is a conversion rule. It changes Monday
  bars, and the team has not set it.

---

## Phase 2 — Dukascopy attempt 2 of 2: NOT RUN

The ruling runs Phase 2 "only if Phase 1 comes up short." Phase 1 came back
neither as the ruling's YES nor as clearly short. It found a same-broker
path, which is the outcome the ruling's ordering exists to prefer
("it may end the whole problem"). Attempt 2 is the last Dukascopy attempt
and cannot be taken back. Spending it while that path is open is the
team's decision, not an inference from an ambiguous trigger. No Phase 2
spec was committed. Nothing was requested from Dukascopy this run.

## Phase 3 — HistData re-probe: endpoint FUNCTIONAL

Probed 2026-10-20 00:09 PDT. Pages and form tokens were read, and one
study-year archive per pair was downloaded into its own empty directory
outside the repo. The archives were not extracted to disk and will not be
used.

| pair | years offered | STUDY years offered | archive tried | token | get.php | archive content |
|---|---|---|---|---|---|---|
| GBPJPY | 2002–2026 | 2005–2013 (all) | 2005 | 32 chars | HTTP 200, 2,780,596 bytes, valid zip | `DAT_ASCII_GBPJPY_M1_2005.csv`, 351,750 rows, first `20050103 014800`, last `20051229 165700` (HistData clock) |
| GBPAUD | 2007–2026 | 2007–2013 only | 2007 | 32 chars | HTTP 200, 556,345 bytes, valid zip | `DAT_ASCII_GBPAUD_M1_2007.csv`, 68,842 rows, first `20070930 170000`, last `20071231 164000` |

The GBPAUD 2005 year page (a year not offered) served an empty token. That
is the 2026-09-11 symptom, now seen only on a year that doesn't exist.
**HistData does not cover GBP/AUD before 2007-09-30.** About 2¾ years of
the STUDY span are missing for that pair.

---

### Per-year bar counts on the modern 17:00-NY grid (timestamps only)

`rows` = every candle OANDA serves. `weekday` = candles on the Mon–Fri session grid at the expected start times. `weekend` = candles whose session falls on a Saturday or Sunday (the old-convention extras). `misaligned` = weekday candles off the expected start times. `full days` = weekday sessions carrying every expected bar, as a share of weekday sessions with any bar.

**GBP_AUD D — STUDY 2005–2013:** 3030 rows, first 2005-01-01 14:00 PST, last 2013-12-30 14:00 PST

| year | rows | weekday | weekend | misaligned | weekday sessions | with bars | full days % | short days |
|---|---|---|---|---|---|---|---|---|
| 2005 | 349 | 260 | 89 | 0 | 260 | 260 | 100.0 | 0 |
| 2006 | 341 | 260 | 81 | 0 | 260 | 260 | 100.0 | 0 |
| 2007 | 334 | 261 | 73 | 0 | 261 | 261 | 100.0 | 0 |
| 2008 | 337 | 262 | 75 | 0 | 262 | 262 | 100.0 | 0 |
| 2009 | 341 | 261 | 80 | 0 | 261 | 261 | 100.0 | 0 |
| 2010 | 353 | 261 | 92 | 0 | 261 | 261 | 100.0 | 0 |
| 2011 | 359 | 260 | 99 | 0 | 260 | 260 | 100.0 | 0 |
| 2012 | 343 | 260 | 83 | 0 | 261 | 260 | 100.0 | 0 |
| 2013 | 273 | 259 | 14 | 0 | 261 | 259 | 100.0 | 0 |

**GBP_AUD H4 — STUDY 2005–2013:** 15287 rows, first 2005-01-02 10:00 PST, last 2013-12-31 10:00 PST

| year | rows | weekday | weekend | misaligned | weekday sessions | with bars | full days % | short days |
|---|---|---|---|---|---|---|---|---|
| 2005 | 1678 | 1560 | 118 | 0 | 260 | 260 | 100.0 | 0 |
| 2006 | 1667 | 1559 | 108 | 0 | 260 | 260 | 99.62 | 1 |
| 2007 | 1641 | 1560 | 81 | 0 | 261 | 261 | 99.23 | 2 |
| 2008 | 1654 | 1565 | 89 | 0 | 262 | 262 | 99.24 | 2 |
| 2009 | 1651 | 1560 | 91 | 0 | 261 | 261 | 99.23 | 2 |
| 2010 | 1693 | 1561 | 132 | 0 | 261 | 261 | 99.62 | 1 |
| 2011 | 2057 | 1560 | 497 | 0 | 260 | 260 | 100.0 | 0 |
| 2012 | 1677 | 1557 | 120 | 0 | 261 | 260 | 99.62 | 1 |
| 2013 | 1569 | 1554 | 15 | 0 | 261 | 259 | 100.0 | 0 |

**GBP_AUD H1 — STUDY 2005–2013:** 58750 rows, first 2005-01-02 10:00 PST, last 2013-12-31 10:00 PST

| year | rows | weekday | weekend | misaligned | weekday sessions | with bars | full days % | short days |
|---|---|---|---|---|---|---|---|---|
| 2005 | 6479 | 6239 | 240 | 0 | 260 | 260 | 99.62 | 1 |
| 2006 | 6458 | 6232 | 226 | 0 | 260 | 260 | 99.62 | 1 |
| 2007 | 6403 | 6231 | 172 | 0 | 261 | 261 | 99.23 | 2 |
| 2008 | 6456 | 6256 | 200 | 0 | 262 | 262 | 99.24 | 2 |
| 2009 | 6436 | 6233 | 203 | 0 | 261 | 261 | 99.23 | 2 |
| 2010 | 6509 | 6241 | 268 | 0 | 261 | 261 | 99.62 | 1 |
| 2011 | 7317 | 6240 | 1077 | 0 | 260 | 260 | 100.0 | 0 |
| 2012 | 6463 | 6219 | 244 | 0 | 261 | 260 | 98.85 | 3 |
| 2013 | 6229 | 6207 | 22 | 0 | 261 | 259 | 98.84 | 3 |

**GBP_JPY D — STUDY 2005–2013:** 3022 rows, first 2005-01-01 14:00 PST, last 2013-12-30 14:00 PST

| year | rows | weekday | weekend | misaligned | weekday sessions | with bars | full days % | short days |
|---|---|---|---|---|---|---|---|---|
| 2005 | 350 | 260 | 90 | 0 | 260 | 260 | 100.0 | 0 |
| 2006 | 336 | 260 | 76 | 0 | 260 | 260 | 100.0 | 0 |
| 2007 | 331 | 261 | 70 | 0 | 261 | 261 | 100.0 | 0 |
| 2008 | 337 | 262 | 75 | 0 | 262 | 262 | 100.0 | 0 |
| 2009 | 339 | 261 | 78 | 0 | 261 | 261 | 100.0 | 0 |
| 2010 | 353 | 261 | 92 | 0 | 261 | 261 | 100.0 | 0 |
| 2011 | 361 | 260 | 101 | 0 | 260 | 260 | 100.0 | 0 |
| 2012 | 342 | 260 | 82 | 0 | 261 | 260 | 100.0 | 0 |
| 2013 | 273 | 259 | 14 | 0 | 261 | 259 | 100.0 | 0 |

**GBP_JPY H4 — STUDY 2005–2013:** 15197 rows, first 2005-01-02 10:00 PST, last 2013-12-31 10:00 PST

| year | rows | weekday | weekend | misaligned | weekday sessions | with bars | full days % | short days |
|---|---|---|---|---|---|---|---|---|
| 2005 | 1669 | 1560 | 109 | 0 | 260 | 260 | 100.0 | 0 |
| 2006 | 1647 | 1557 | 90 | 0 | 260 | 260 | 99.62 | 1 |
| 2007 | 1641 | 1559 | 82 | 0 | 261 | 261 | 99.23 | 2 |
| 2008 | 1654 | 1567 | 87 | 0 | 262 | 262 | 99.24 | 2 |
| 2009 | 1644 | 1559 | 85 | 0 | 261 | 261 | 99.23 | 2 |
| 2010 | 1663 | 1561 | 102 | 0 | 261 | 261 | 99.62 | 1 |
| 2011 | 2054 | 1560 | 494 | 0 | 260 | 260 | 100.0 | 0 |
| 2012 | 1656 | 1557 | 99 | 0 | 261 | 260 | 99.62 | 1 |
| 2013 | 1569 | 1554 | 15 | 0 | 261 | 259 | 100.0 | 0 |

**GBP_JPY H1 — STUDY 2005–2013:** 58615 rows, first 2005-01-02 10:00 PST, last 2013-12-31 10:00 PST

| year | rows | weekday | weekend | misaligned | weekday sessions | with bars | full days % | short days |
|---|---|---|---|---|---|---|---|---|
| 2005 | 6474 | 6240 | 234 | 0 | 260 | 260 | 100.0 | 0 |
| 2006 | 6427 | 6227 | 200 | 0 | 260 | 260 | 99.62 | 1 |
| 2007 | 6404 | 6230 | 174 | 0 | 261 | 261 | 99.23 | 2 |
| 2008 | 6457 | 6259 | 198 | 0 | 262 | 262 | 99.24 | 2 |
| 2009 | 6423 | 6231 | 192 | 0 | 261 | 261 | 99.23 | 2 |
| 2010 | 6469 | 6241 | 228 | 0 | 261 | 261 | 99.62 | 1 |
| 2011 | 7305 | 6240 | 1065 | 0 | 260 | 260 | 100.0 | 0 |
| 2012 | 6427 | 6219 | 208 | 0 | 261 | 260 | 98.85 | 3 |
| 2013 | 6229 | 6207 | 22 | 0 | 261 | 259 | 98.84 | 3 |

**GBP_AUD D — USED remainder 2021-04-27 → 2021-12-31:** 179 rows, first 2021-04-26 14:00 PDT, last 2021-12-30 14:00 PST

| year | rows | weekday | weekend | misaligned | weekday sessions | with bars | full days % | short days |
|---|---|---|---|---|---|---|---|---|
| 2021 | 179 | 179 | 0 | 0 | 179 | 179 | 100.0 | 0 |

**GBP_AUD H4 — USED remainder 2021-04-27 → 2021-12-31:** 1074 rows, first 2021-04-26 14:00 PDT, last 2021-12-31 10:00 PST

| year | rows | weekday | weekend | misaligned | weekday sessions | with bars | full days % | short days |
|---|---|---|---|---|---|---|---|---|
| 2021 | 1074 | 1074 | 0 | 0 | 179 | 179 | 100.0 | 0 |

**GBP_AUD H1 — USED remainder 2021-04-27 → 2021-12-31:** 4291 rows, first 2021-04-26 17:00 PDT, last 2021-12-31 13:00 PST

| year | rows | weekday | weekend | misaligned | weekday sessions | with bars | full days % | short days |
|---|---|---|---|---|---|---|---|---|
| 2021 | 4291 | 4291 | 0 | 0 | 179 | 179 | 98.88 | 2 |

**GBP_JPY D — USED remainder 2021-04-27 → 2021-12-31:** 179 rows, first 2021-04-26 14:00 PDT, last 2021-12-30 14:00 PST

| year | rows | weekday | weekend | misaligned | weekday sessions | with bars | full days % | short days |
|---|---|---|---|---|---|---|---|---|
| 2021 | 179 | 179 | 0 | 0 | 179 | 179 | 100.0 | 0 |

**GBP_JPY H4 — USED remainder 2021-04-27 → 2021-12-31:** 1074 rows, first 2021-04-26 14:00 PDT, last 2021-12-31 10:00 PST

| year | rows | weekday | weekend | misaligned | weekday sessions | with bars | full days % | short days |
|---|---|---|---|---|---|---|---|---|
| 2021 | 1074 | 1074 | 0 | 0 | 179 | 179 | 100.0 | 0 |

**GBP_JPY H1 — USED remainder 2021-04-27 → 2021-12-31:** 4291 rows, first 2021-04-26 17:00 PDT, last 2021-12-31 13:00 PST

| year | rows | weekday | weekend | misaligned | weekday sessions | with bars | full days % | short days |
|---|---|---|---|---|---|---|---|---|
| 2021 | 4291 | 4291 | 0 | 0 | 179 | 179 | 98.88 | 2 |

### Every gap (missing expected weekday slots), Pacific time

**STUDY_2005_2013 GBP_AUD D** — 3 gap(s)
- 2012-12-24 14:00 PST — 1 slot(s), 24 h
- 2012-12-31 14:00 PST — 1 slot(s), 24 h
- 2013-12-24 14:00 PST — 1 slot(s), 24 h

**STUDY_2005_2013 GBP_AUD H4** — 13 gap(s); short sessions: 2006-12-25, 2007-01-01, 2007-12-25, 2008-01-01, 2008-12-25, 2009-01-01, 2009-12-25, 2010-01-01, 2012-12-26
- 2006-12-25 02:00 PST — 1 slot(s), 4 h
- 2006-12-31 14:00 PST → 2006-12-31 22:00 PST — 3 slot(s), 12 h
- 2007-01-01 06:00 PST — 1 slot(s), 4 h
- 2007-12-25 02:00 PST → 2007-12-25 06:00 PST — 2 slot(s), 8 h
- 2007-12-31 18:00 PST → 2008-01-01 06:00 PST — 4 slot(s), 16 h
- 2008-12-25 02:00 PST → 2008-12-25 10:00 PST — 3 slot(s), 12 h
- 2008-12-31 18:00 PST → 2009-01-01 06:00 PST — 4 slot(s), 16 h
- 2009-12-25 02:00 PST — 1 slot(s), 4 h
- 2009-12-25 10:00 PST — 1 slot(s), 4 h
- 2009-12-31 18:00 PST → 2010-01-01 10:00 PST — 5 slot(s), 20 h
- 2012-12-24 14:00 PST → 2012-12-25 22:00 PST — 9 slot(s), 36 h
- 2012-12-31 14:00 PST → 2013-01-01 10:00 PST — 6 slot(s), 24 h
- 2013-12-24 14:00 PST → 2013-12-25 10:00 PST — 6 slot(s), 24 h

**STUDY_2005_2013 GBP_AUD H1** — 18 gap(s); short sessions: 2005-12-26, 2006-12-25, 2007-01-01, 2007-12-25, 2008-01-01, 2008-12-25, 2009-01-01, 2009-12-25, 2010-01-01, 2012-12-24, 2012-12-26, 2012-12-31, 2013-01-02, 2013-12-24, 2013-12-31
- 2005-12-26 10:00 PST — 1 slot(s), 1 h
- 2006-12-25 01:00 PST → 2006-12-25 05:00 PST — 5 slot(s), 5 h
- 2006-12-25 10:00 PST → 2006-12-25 11:00 PST — 2 slot(s), 2 h
- 2006-12-25 13:00 PST — 1 slot(s), 1 h
- 2006-12-31 14:00 PST → 2007-01-01 01:00 PST — 12 slot(s), 12 h
- 2007-01-01 03:00 PST → 2007-01-01 10:00 PST — 8 slot(s), 8 h
- 2007-01-01 12:00 PST — 1 slot(s), 1 h
- 2007-12-25 01:00 PST → 2007-12-25 11:00 PST — 11 slot(s), 11 h
- 2007-12-25 13:00 PST — 1 slot(s), 1 h
- 2007-12-31 15:00 PST → 2008-01-01 09:00 PST — 19 slot(s), 19 h
- 2008-12-25 01:00 PST → 2008-12-25 13:00 PST — 13 slot(s), 13 h
- 2008-12-31 15:00 PST → 2009-01-01 09:00 PST — 19 slot(s), 19 h
- 2009-12-25 01:00 PST → 2009-12-25 06:00 PST — 6 slot(s), 6 h
- 2009-12-25 08:00 PST → 2009-12-25 13:00 PST — 6 slot(s), 6 h
- 2009-12-31 15:00 PST → 2010-01-01 13:00 PST — 23 slot(s), 23 h
- 2012-12-24 11:00 PST → 2012-12-26 04:00 PST — 42 slot(s), 42 h
- 2012-12-31 11:00 PST → 2013-01-01 16:00 PST — 30 slot(s), 30 h
- 2013-12-24 11:00 PST → 2013-12-25 13:00 PST — 27 slot(s), 27 h

**STUDY_2005_2013 GBP_JPY D** — 3 gap(s)
- 2012-12-24 14:00 PST — 1 slot(s), 24 h
- 2012-12-31 14:00 PST — 1 slot(s), 24 h
- 2013-12-24 14:00 PST — 1 slot(s), 24 h

**STUDY_2005_2013 GBP_JPY H4** — 11 gap(s); short sessions: 2006-12-25, 2007-01-01, 2007-12-25, 2008-01-01, 2008-12-25, 2009-01-01, 2009-12-25, 2010-01-01, 2012-12-26
- 2006-12-25 02:00 PST → 2006-12-25 10:00 PST — 3 slot(s), 12 h
- 2006-12-31 14:00 PST → 2007-01-01 06:00 PST — 5 slot(s), 20 h
- 2007-12-25 02:00 PST → 2007-12-25 06:00 PST — 2 slot(s), 8 h
- 2007-12-31 22:00 PST → 2008-01-01 02:00 PST — 2 slot(s), 8 h
- 2008-12-25 02:00 PST → 2008-12-25 10:00 PST — 3 slot(s), 12 h
- 2008-12-31 18:00 PST → 2009-01-01 06:00 PST — 4 slot(s), 16 h
- 2009-12-25 02:00 PST → 2009-12-25 10:00 PST — 3 slot(s), 12 h
- 2009-12-31 18:00 PST → 2010-01-01 10:00 PST — 5 slot(s), 20 h
- 2012-12-24 14:00 PST → 2012-12-25 22:00 PST — 9 slot(s), 36 h
- 2012-12-31 14:00 PST → 2013-01-01 10:00 PST — 6 slot(s), 24 h
- 2013-12-24 14:00 PST → 2013-12-25 10:00 PST — 6 slot(s), 24 h

**STUDY_2005_2013 GBP_JPY H1** — 13 gap(s); short sessions: 2006-12-25, 2007-01-01, 2007-12-25, 2008-01-01, 2008-12-25, 2009-01-01, 2009-12-25, 2010-01-01, 2012-12-24, 2012-12-26, 2012-12-31, 2013-01-02, 2013-12-24, 2013-12-31
- 2006-12-25 01:00 PST → 2006-12-25 13:00 PST — 13 slot(s), 13 h
- 2006-12-31 14:00 PST → 2007-01-01 12:00 PST — 23 slot(s), 23 h
- 2007-12-25 01:00 PST → 2007-12-25 11:00 PST — 11 slot(s), 11 h
- 2007-12-31 15:00 PST → 2007-12-31 16:00 PST — 2 slot(s), 2 h
- 2007-12-31 18:00 PST → 2007-12-31 20:00 PST — 3 slot(s), 3 h
- 2007-12-31 22:00 PST → 2008-01-01 08:00 PST — 11 slot(s), 11 h
- 2008-12-25 01:00 PST → 2008-12-25 13:00 PST — 13 slot(s), 13 h
- 2008-12-31 15:00 PST → 2009-01-01 10:00 PST — 20 slot(s), 20 h
- 2009-12-25 01:00 PST → 2009-12-25 13:00 PST — 13 slot(s), 13 h
- 2009-12-31 15:00 PST → 2010-01-01 13:00 PST — 23 slot(s), 23 h
- 2012-12-24 11:00 PST → 2012-12-26 04:00 PST — 42 slot(s), 42 h
- 2012-12-31 11:00 PST → 2013-01-01 16:00 PST — 30 slot(s), 30 h
- 2013-12-24 11:00 PST → 2013-12-25 13:00 PST — 27 slot(s), 27 h

**USED_2021_remainder GBP_AUD D** — 0 gap(s)

**USED_2021_remainder GBP_AUD H4** — 0 gap(s)

**USED_2021_remainder GBP_AUD H1** — 1 gap(s); short sessions: 2021-04-27, 2021-11-22
- 2021-11-21 14:00 PST → 2021-11-21 15:00 PST — 2 slot(s), 2 h

**USED_2021_remainder GBP_JPY D** — 0 gap(s)

**USED_2021_remainder GBP_JPY H4** — 0 gap(s)

**USED_2021_remainder GBP_JPY H1** — 1 gap(s); short sessions: 2021-04-27, 2021-11-22
- 2021-11-21 14:00 PST → 2021-11-21 15:00 PST — 2 slot(s), 2 h

### Reduced gate detail

| pair | TF | stored rows | compared | identical (all 4 fields) | stored-only | API-only | max abs diff O/H/L/C (pips) |
|---|---|---|---|---|---|---|---|
| GBP_AUD | D | 1110 | 1110 | 1110 | 0 | 0 | 0.0 / 0.0 / 0.0 / 0.0 |
| GBP_AUD | H4 | 5239 | 5239 | 5239 | 0 | 0 | 0.0 / 0.0 / 0.0 / 0.0 |
| GBP_AUD | H1 | 18937 | 18937 | 18937 | 0 | 0 | 0.0 / 0.0 / 0.0 / 0.0 |
| GBP_JPY | D | 789 | 789 | 789 | 0 | 0 | 0.0 / 0.0 / 0.0 / 0.0 |
| GBP_JPY | H4 | 4735 | 4735 | 4735 | 0 | 0 | 0.0 / 0.0 / 0.0 / 0.0 |

- Live ledger `regime_classification_log.csv`, GBP_AUD: 38 rows with `price_basis=d1_close`, 38 compared, 38 identical, max abs diff 0.0 pips, unmatched 0.
- Live ledger `regime_classification_log.csv`, GBP_JPY: 38 rows with `price_basis=d1_close`, 38 compared, 38 identical, max abs diff 0.0 pips, unmatched 0.
