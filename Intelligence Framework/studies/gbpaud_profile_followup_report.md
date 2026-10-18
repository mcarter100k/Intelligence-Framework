> **Prior-session artifact:** committed 2026-10-18 for citation integrity (foundation/ cites it). Committed exactly as found; not re-verified against current code.

```
==============================================================================
GBP/AUD PROFILE — READ-ONLY FOLLOW-UP, 2026-09-11
==============================================================================
## 1. Provenance of THRUST_PULLBACK's frozen parameters
Selection: studies/structure_engine_study.py v2 grid sweep —
  N ∈ {6,8,12,18} × X ∈ {1.5,2.0,2.5,3.0} × thrust ∈ {0.5,0.75,1.0,1.25}×ATR,
  3 detector variants; RANGE_ONLY N=18 X=3.0 thrust=1.0 chosen (validation_log
  2026-07-29 pivot entry). PB_ZONE=0.25 and PB_WINDOW=10 were FIXED constants
  of the sweep (never searched), carried into the frozen spec as
  TP_PULLBACK_ATR / TP_PULLBACK_BARS.
Run date: 2026-07-29 (commit 5def001 “v2 study run”); data = 4900 H4 bars +
  1300 D1 bars ending at the last completed session, 2026-07-28.
  → selection window ≈ 2023-06-02 → 2026-07-28 (4900 H4 bars, computed from the cached series)

PLAINLY: the profile window 2023-09-01 → 2026-09-10 overlaps the parameter-
selection window for everything from 2023-09-01 through 2026-07-28.
Only 2026-07-29 → 2026-09-10 (~31 trading days) is out-of-sample with respect
to parameter selection. Of the 22 walk-forward episodes in the profile study,
21 fall inside the selection window (IN-SAMPLE) and 1 (2026-09-02 LONG, −1.0R)
is out-of-sample. The profile's play-test numbers therefore measure how the
chosen cell behaved on largely the SAME data that chose it — a ceiling, not an
estimate of forward edge. The live shadow ledger (N from the 2026-09-10 fix)
remains the only honest forward test.

## 2. Break split — overshoot beyond confirmed swing extremes,
failed (closed back inside ≤3 days) vs held. ATR basis: D1 ATR(14) of the
day before the breach.
  POOLED 2023-09→2026-09  (N=69; failed 49 / held 20 — 71% failed)
    failed ≤3d                   N=49                     pips p50/p75/p90   73/ 144/ 195   ×ATR 0.65/1.10/1.48
    held                         N=20 [descriptive only]  pips p50/p75/p90  209/ 269/ 308   ×ATR 1.81/2.12/2.56
    all                          N=69                     pips p50/p75/p90  111/ 199/ 268   ×ATR 0.88/1.44/2.26
  SepY1 2023-09→2024-08  (N=26 [descriptive only]; failed 20 / held 6 — 77% failed)
    failed ≤3d                   N=20 [descriptive only]  pips p50/p75/p90   70/ 118/ 182   ×ATR 0.59/1.10/1.58
    held                         N=6 [descriptive only]   pips p50/p75/p90  171/ 211/ 240   ×ATR 1.39/1.79/2.00
    all                          N=26 [descriptive only]  pips p50/p75/p90   99/ 149/ 228   ×ATR 0.79/1.37/2.00
  SepY2 2024-09→2025-08  (N=23 [descriptive only]; failed 16 / held 7 — 70% failed)
    failed ≤3d                   N=16 [descriptive only]  pips p50/p75/p90  106/ 166/ 197   ×ATR 0.82/1.11/1.43
    held                         N=7 [descriptive only]   pips p50/p75/p90  273/ 343/ 433   ×ATR 2.46/2.88/3.63
    all                          N=23 [descriptive only]  pips p50/p75/p90  163/ 225/ 370   ×ATR 1.10/1.65/3.12
  SepY3 2025-09→2026-09-10  (N=20 [descriptive only]; failed 13 / held 7 — 65% failed)
    failed ≤3d                   N=13 [descriptive only]  pips p50/p75/p90   72/ 110/ 154   ×ATR 0.65/0.97/1.43
    held                         N=7 [descriptive only]   pips p50/p75/p90  199/ 235/ 267   ×ATR 1.84/1.97/2.13
    all                          N=20 [descriptive only]  pips p50/p75/p90  105/ 167/ 218   ×ATR 0.86/1.54/1.96

## 3. Doctrine assumption — does the first counter-trend bounce breach the
last confirmed LH (downtrend) / HL (uptrend) before a new with-trend extreme?
Race from the confirmation day (label-flip day s): breach of the LH/HL level
vs a new extreme beyond the move's reference extreme (extreme between the
LH/HL pivot bar and day s). Cap 60 trading days. Bounce depth = adverse
excursion from the reference extreme until resolution, ÷ ATR(day s).
  Legs examined: 41 (N=41); skipped 0 (no confirmed LH/HL), 0 (level from engine fallback, no real pivot bar)
    new_extreme_first   24  (59%)
    breach_first        16  (39%)
    same_day_both        0  (0%)
    unresolved           1  (2%)
  Of resolved races (N=40): bounce breached the LH/HL BEFORE a new with-trend extreme in 40% of legs.
  Bounce depth ×ATR (all examined, N=41): p50 1.7 / p75 2.3 / p90 3.5
    UPTREND    N=18 [descriptive only]  breach_first 7, new_extreme_first 11, other 0; depth ×ATR p50 1.9 / p75 2.6 / p90 3.5
    DOWNTREND  N=23 [descriptive only]  breach_first 9, new_extreme_first 13, other 1; depth ×ATR p50 1.6 / p75 2.1 / p90 3.3

## 4. Trend legs — with-trend pips per Sep-year; concentration; MFE vs flip
With-trend net = signed net over the label run. MFE = best extreme during the
run vs the confirmation base (prev close before the run's first day).
  SepY1 2023-09→2024-08  (N=16 [descriptive only])
    with-trend net: total -861 pips, mean -54, median -51
    top-2 legs contribute +255 pips (total of all others: -1117) — share undefined as % when total ≤ 0; stated in pips
    confirmation→MFE: total +2055 pips (median +115) vs confirmation→flip total -861
    → give-back from best point to label flip: 2916 pips (142% of MFE)
  SepY2 2024-09→2025-08  (N=15 [descriptive only])
    with-trend net: total -995 pips, mean -66, median -35
    top-2 legs contribute +364 pips (total of all others: -1359) — share undefined as % when total ≤ 0; stated in pips
    confirmation→MFE: total +3241 pips (median +137) vs confirmation→flip total -995
    → give-back from best point to label flip: 4236 pips (131% of MFE)
  SepY3 2025-09→2026-09-10  (N=10 [descriptive only])
    with-trend net: total +577 pips, mean +58, median -52
    top-2 legs contribute +1198 pips (total of all others: -620) — share undefined as % when total ≤ 0; stated in pips
    confirmation→MFE: total +2799 pips (median +143) vs confirmation→flip total +577
    → give-back from best point to label flip: 2222 pips (79% of MFE)
  POOLED (N=41): with-trend net total -1279 pips; MFE total +8095 pips; give-back 9374 pips (116% of MFE)

## 5. Release reactions at day 1 / day 3 / day 5
retention_k = (close(d+k) − close(d−1)) / (close(d0) − close(d−1));
EXT ≥ 1.0, HELD 0.5–1.0, RT < 0.5.
  event         N   day1 EXT/HELD/RT      day3 EXT/HELD/RT      day5 EXT/HELD/RT
  RBA          25    40/ 24/ 36%           44/  4/ 52%           52/  4/ 44%  [descriptive only]
  BoE          24    38/ 21/ 42%           38/ 21/ 42%           46/  8/ 46%  [descriptive only]
  AU_CPI_q     12    50/ 33/ 17%           50/ 42/  8%           42/  0/ 58%  [descriptive only]
  UK_CPI       36    47/ 22/ 31%           47/  8/ 44%           47/ 11/ 42%
  US_CPI       35    51/ 23/ 26%           40/ 11/ 49%           46/  0/ 54%
  NFP          35    40/ 14/ 46%           34/ 17/ 49%           34/ 11/ 54%
  US_ISM_mfg   37    32/ 14/ 54%           30/ 24/ 46%           46/  8/ 46%

  Surprise-sign split: NOT EXECUTABLE from this repo. calendar.csv holds only
  the current day's rows; there is no historical actual-vs-consensus source,
  and 3 years × 7 series of consensus figures cannot be verifiably
  reconstructed here. If a consensus export (e.g. investing.com /
  ForexFactory CSV) is provided, the split runs on this same code path.

## 6. OANDA GBP_AUD history depth (probe only — NOT analyzed)
  D: earliest candle 2004-05-31
  H4: earliest candle 2004-06-01
  Pre-2023-09 years remain UNTOUCHED by this and the prior study (only the
  warm-up tails back to 2022-06 D1 / 2023-05 H4 were fetched, used solely to
  seed trailing windows). They stay reserved as out-of-sample data for any
  future frozen spec.
```
