# STUDY conversion gate (data_map_spec §3) on OANDA data

**Run:** 2026-10-22 01:09 PDT, under the owner ruling of 2026-10-22
(data_map_spec §11.1). The run rules were declared in data_map_spec §11.4
and committed in `340aef0` (2026-10-22 01:08:35 PDT) **before any price was
fetched**. Script: `history_study_gate_s3.py` (this directory, `python3 -I`,
paths as arguments). Fetched candles stayed outside the repo.

**Verification numbers only.** This report holds counts, pass/fail, and
|D1 − H4| differences in pips. It contains no price level, range or average.

**Scope:**
- **Span:** STUDY trading days 2005-01-01 → 2013-12-30. The §11.2 embargo
  removes 2013-12-31.
- **Sealed block:** every request was checked before sending against the
  embargo-plus-sealed block, [2013-12-30T22:00Z, 2021-04-26T21:00Z), with a
  one-day margin, and every returned candle was checked after receipt.
  **0 of 36,522 stored candles fall inside it.**
- **Candles are as OANDA serves them; no weekend-candle rule is applied.**
  That rule is PROPOSED in docs/specs/study_weekend_candle_spec.md and not
  approved.

## Verdict

| §3 item | GBP_AUD | GBP_JPY |
|---|---|---|
| 1. weekday D1 count in [252, 262], every year | PASS (258–262) | PASS (258–262) |
| 2. ≥ 99% of sessions with all 6 H4 bars, every year | PASS (99.23–100%) | PASS (99.23–100%) |
| 3. D1 high/low == max/min of its 6 H4 (0.5 pip), fixed sample 50/yr | PASS (450/450, max diff 0.0 pips) | PASS (450/450, max diff 0.0 pips) |
| 4. known-date existence + range sign check | PASS | PASS |

**The §3 gate PASSES on OANDA's STUDY-span weekday grid, both pairs.**
Two conditions still hold:
- **Mondays are re-checked under the approved weekend rule.** Monday sessions
  change under any fold, so item 3 is re-run on Mondays once a rule is
  approved and built. Tuesday–Friday sessions are untouched by any option.
  Every weekend session is internally consistent with its own H4 bars,
  which suggests a fold built on both timeframes will stay consistent; that
  is INFERRED until it is run.
- **No study builds on this data until the weekend rule is approved,
  built and the Monday re-run passes.**

The short sessions behind item 2 are the Christmas and New Year sessions
listed in studies/history_depth_report.md.

### GBP_AUD

D1: 3029 candles, first 2005-01-01 14:00 PST, last 2013-12-29 14:00 PST. H4: 15281 candles, first 2005-01-02 10:00 PST, last 2013-12-30 10:00 PST. Raw counts include weekend-session candles; the items below use the weekday grid.

| year | item 1: weekday D1 (band 252–262) | item 2: H4 sessions with all 6 bars | item 3: sampled days passing (of eligible) |
|---|---|---|---|
| 2005 | 260 ✓ | 260/260 = 100.0% ✓ | 50/50 (of 260) |
| 2006 | 260 ✓ | 259/260 = 99.62% ✓ | 50/50 (of 259) |
| 2007 | 261 ✓ | 259/261 = 99.23% ✓ | 50/50 (of 259) |
| 2008 | 262 ✓ | 260/262 = 99.24% ✓ | 50/50 (of 260) |
| 2009 | 261 ✓ | 259/261 = 99.23% ✓ | 50/50 (of 259) |
| 2010 | 261 ✓ | 260/261 = 99.62% ✓ | 50/50 (of 260) |
| 2011 | 260 ✓ | 260/260 = 100.0% ✓ | 50/50 (of 260) |
| 2012 | 260 ✓ | 259/260 = 99.62% ✓ | 50/50 (of 259) |
| 2013 | 258 ✓ | 258/258 = 100.0% ✓ | 50/50 (of 258) |

- Item 3 sample: **450/450 pass**; largest |difference| 0.0 pips; days with any nonzero difference: 0.
- Supplementary (not gated): every eligible weekday 2334/2334; every weekend session against its own H4 686/686 (weekend sessions with H4 but no D1: 0; D1 but no H4: 0).

### GBP_JPY

D1: 3021 candles, first 2005-01-01 14:00 PST, last 2013-12-29 14:00 PST. H4: 15191 candles, first 2005-01-02 10:00 PST, last 2013-12-30 10:00 PST. Raw counts include weekend-session candles; the items below use the weekday grid.

| year | item 1: weekday D1 (band 252–262) | item 2: H4 sessions with all 6 bars | item 3: sampled days passing (of eligible) |
|---|---|---|---|
| 2005 | 260 ✓ | 260/260 = 100.0% ✓ | 50/50 (of 260) |
| 2006 | 260 ✓ | 259/260 = 99.62% ✓ | 50/50 (of 259) |
| 2007 | 261 ✓ | 259/261 = 99.23% ✓ | 50/50 (of 259) |
| 2008 | 262 ✓ | 260/262 = 99.24% ✓ | 50/50 (of 260) |
| 2009 | 261 ✓ | 259/261 = 99.23% ✓ | 50/50 (of 259) |
| 2010 | 261 ✓ | 260/261 = 99.62% ✓ | 50/50 (of 260) |
| 2011 | 260 ✓ | 260/260 = 100.0% ✓ | 50/50 (of 260) |
| 2012 | 260 ✓ | 259/260 = 99.62% ✓ | 50/50 (of 259) |
| 2013 | 258 ✓ | 258/258 = 100.0% ✓ | 50/50 (of 258) |

- Item 3 sample: **450/450 pass**; largest |difference| 0.0 pips; days with any nonzero difference: 0.
- Supplementary (not gated): every eligible weekday 2334/2334; every weekend session against its own H4 678/678 (weekend sessions with H4 but no D1: 0; D1 but no H4: 0).

### Item 4 — known-date spot checks

| trading day | pair | D1 exists | range above its 20-day Tue–Fri median |
|---|---|---|---|
| 2008-10-24 | GBP_AUD | ✓ | ✓ |
| 2008-10-24 | GBP_JPY | ✓ | ✓ |
| 2010-05-06 | GBP_AUD | ✓ | ✓ |
| 2010-05-06 | GBP_JPY | ✓ | ✓ |
| 2011-03-17 | GBP_AUD | ✓ | not computed (as declared) |
| 2011-03-17 | GBP_JPY | ✓ | ✓ |
| 2013-04-04 | GBP_AUD | ✓ | not computed (as declared) |
| 2013-04-04 | GBP_JPY | ✓ | ✓ |

Item 4: **PASS**.

### Controls (each check shown able to fail)

- `item3_plant_0.6pip_fails`: True
- `item3_plant_0.4pip_passes`: True
- `item3_gate_flips_on_one_planted_day`: True
- `item4_known_missing_2012-12-25_absent`: True
- `item4_range_just_below_baseline_fails`: True
- `item4_range_just_above_baseline_passes`: True

OANDA requests: 424.
