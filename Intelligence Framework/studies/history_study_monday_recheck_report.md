# Monday re-check after the weekend-candle rule (STUDY span, OANDA)

**Run:** 2026-10-22 01:28 PDT. Rule: docs/specs/study_weekend_candle_spec.md
§6, approved 2026-10-22 after the live-Monday verification. The pass
criterion was declared in §6 and committed in `096be86` (01:26:20 PDT),
before the conversion was built or run.
- **Inputs:** the STUDY candles fetched for the §3 gate (2005-01-01 →
  2013-12-30, embargo applied), kept outside the repo.
- **Scripts:** `history_study_convert.py` (the rule) and
  `history_study_monday_recheck.py` (this check), both in this directory,
  run with `python3 -I` and paths as arguments.
- **Content:** verification numbers only (counts, pass/fail, |D1 − H4| in
  pips). No price level, range or average.

## Verdict: PASS, both pairs

- **Every Monday with six H4 bars passes check 3** before and after the rule:
  468 per pair, 0.0 pips.
- **0 weekend-session candles remain.** Items 1–2 still pass every year.
- **The control works:** a half-built fold makes 162 (GBP_AUD) and 135
  (GBP_JPY) Mondays fail.
- **Short Mondays:** 2006-12-25 and 2007-01-01 have fewer than six H4 bars,
  so they are listed and untested, as declared. The one that received a fold
  (GBP_AUD 2006-12-25) is consistent at 0.0 pips (supplementary). Neither
  pair had a Sunday session on the 2006-12-31 weekend, and GBP_JPY had none
  on 2006-12-24, so those Mondays received no fold.

**Status:** the §3 gate and the Monday re-check both pass on the converted
OANDA STUDY data. The data-side preconditions for Stage 3 are met. The
study itself still needs its own pre-registration (data_map_spec §9
frequency count first).

### GBP_AUD — PASS

- Sunday sessions folded: 420 (D1 candles 420, H4 candles 771). Saturday-session candles dropped: D1 266, H4 480.
- Weekend-session candles left after the rule: **0**. Fold targets that are not Mondays: 0.
- Control (a half-built fold: D1 folded, H4 not): **162 of 468** Mondays fail check 3.

| year | D1 rows before (weekend) → after | H4 rows before (weekend) → after | Mondays passing, before | Mondays passing, after | max \|diff\| after (pips) | short Mondays (listed, untested) | items 1–2 after |
|---|---|---|---|---|---|---|---|
| 2005 | 349 (89) → 260 (0) | 1678 (118) → 1560 (0) | 52/52 | 52/52 | 0.0 | — | D1 260, H4 100.0% |
| 2006 | 341 (81) → 260 (0) | 1667 (108) → 1559 (0) | 51/51 | 51/51 | 0.0 | 2006-12-25 | D1 260, H4 99.62% |
| 2007 | 334 (73) → 261 (0) | 1641 (81) → 1560 (0) | 52/52 | 52/52 | 0.0 | 2007-01-01 | D1 261, H4 99.23% |
| 2008 | 337 (75) → 262 (0) | 1654 (89) → 1565 (0) | 52/52 | 52/52 | 0.0 | — | D1 262, H4 99.24% |
| 2009 | 341 (80) → 261 (0) | 1651 (91) → 1560 (0) | 52/52 | 52/52 | 0.0 | — | D1 261, H4 99.23% |
| 2010 | 353 (92) → 261 (0) | 1693 (132) → 1561 (0) | 52/52 | 52/52 | 0.0 | — | D1 261, H4 99.62% |
| 2011 | 359 (99) → 260 (0) | 2057 (497) → 1560 (0) | 52/52 | 52/52 | 0.0 | — | D1 260, H4 100.0% |
| 2012 | 343 (83) → 260 (0) | 1677 (120) → 1557 (0) | 53/53 | 53/53 | 0.0 | — | D1 260, H4 99.62% |
| 2013 | 272 (14) → 258 (0) | 1563 (15) → 1548 (0) | 52/52 | 52/52 | 0.0 | — | D1 258, H4 100.0% |

Supplementary, not gated — short Mondays that received a fold: 2006-12-25 (5 H4 bars): consistent, diff 0.0/0.0 pips.

### GBP_JPY — PASS

- Sunday sessions folded: 420 (D1 candles 420, H4 candles 710). Saturday-session candles dropped: D1 258, H4 453.
- Weekend-session candles left after the rule: **0**. Fold targets that are not Mondays: 0.
- Control (a half-built fold: D1 folded, H4 not): **135 of 468** Mondays fail check 3.

| year | D1 rows before (weekend) → after | H4 rows before (weekend) → after | Mondays passing, before | Mondays passing, after | max \|diff\| after (pips) | short Mondays (listed, untested) | items 1–2 after |
|---|---|---|---|---|---|---|---|
| 2005 | 350 (90) → 260 (0) | 1669 (109) → 1560 (0) | 52/52 | 52/52 | 0.0 | — | D1 260, H4 100.0% |
| 2006 | 336 (76) → 260 (0) | 1647 (90) → 1557 (0) | 51/51 | 51/51 | 0.0 | 2006-12-25 | D1 260, H4 99.62% |
| 2007 | 331 (70) → 261 (0) | 1641 (82) → 1559 (0) | 52/52 | 52/52 | 0.0 | 2007-01-01 | D1 261, H4 99.23% |
| 2008 | 337 (75) → 262 (0) | 1654 (87) → 1567 (0) | 52/52 | 52/52 | 0.0 | — | D1 262, H4 99.24% |
| 2009 | 339 (78) → 261 (0) | 1644 (85) → 1559 (0) | 52/52 | 52/52 | 0.0 | — | D1 261, H4 99.23% |
| 2010 | 353 (92) → 261 (0) | 1663 (102) → 1561 (0) | 52/52 | 52/52 | 0.0 | — | D1 261, H4 99.62% |
| 2011 | 361 (101) → 260 (0) | 2054 (494) → 1560 (0) | 52/52 | 52/52 | 0.0 | — | D1 260, H4 100.0% |
| 2012 | 342 (82) → 260 (0) | 1656 (99) → 1557 (0) | 53/53 | 53/53 | 0.0 | — | D1 260, H4 99.62% |
| 2013 | 272 (14) → 258 (0) | 1563 (15) → 1548 (0) | 52/52 | 52/52 | 0.0 | — | D1 258, H4 100.0% |

Supplementary, not gated — short Mondays that received a fold: none.

