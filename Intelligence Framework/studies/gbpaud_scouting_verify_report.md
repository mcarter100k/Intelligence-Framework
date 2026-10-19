> **Prior-session artifact:** committed 2026-10-18 for citation integrity (foundation/ cites it). Committed exactly as found; not re-verified against current code.

```
==============================================================================
GBP/AUD SCOUTING VERIFICATION — read-only, 2026-09-11
Window 2023-09-01 → 2026-09-10 only. Pre-2023 sealed. Fixed rules, no search.
==============================================================================

PLAIN-ENGLISH SUMMARY
─────────────────────
• Regime tilt, honestly baselined: swing starts track time spent almost
  one-for-one. Ratios (swing share ÷ time share): VOLATILE 1.05, RANGING 0.85, TRENDING_UP 1.13, TRENDING_DOWN 1.17.
  Nothing is far from 1.0 — the earlier 46%-VOLATILE headline was mostly
  a picture of where TIME lives, not where opportunity concentrates.
• Hour artifact: with a continuous zigzag (393 swings) the 14:00 PDT
  share is 15%; excluding week-boundary bars (371 swings) it is
  11%. Compare 27% under the week-local cut — the rollover-hour
  concentration was substantially a week-edge artifact.
• Fixed-rule first-bounce verify (all 8 pre-specified cells reported, spread
  3 pips, stops beyond the LH/HL): avg R ranges -0.21 (at 85%/0.3×ATR) to -0.03 (at 70%/0.1×ATR).
  Every cell is under N=30 — descriptive only, and 21 of the 41 legs sit in
  the in-sample span of the frozen-parameter selection window discussed in
  the provenance study. Nothing here defines or tunes a play.

## 1. Regime baseline (time share vs swing-start share)
Attribution for BOTH columns: prior trading day's as-of-close regime.
  D1 regime      time-share  swing-share   ratio   (bars N=4698, swings N=393)
  VOLATILE           44.3%       46.6%    1.05
  RANGING            35.1%       29.8%    0.85
  TRENDING_UP        10.3%       11.7%    1.13
  TRENDING_DOWN      10.2%       12.0%    1.17

  Top (D1,H4) cells by time share:
  cell                            time-share  swing-share   ratio
       VOLATILE / VOLATILE           18.3%       22.6%    1.24
        RANGING / VOLATILE           13.4%       11.7%    0.87
        RANGING / RANGING            13.4%       11.2%    0.83
       VOLATILE / RANGING            10.1%        8.4%    0.83
       VOLATILE / TRENDING_DOWN       8.6%        9.4%    1.10
       VOLATILE / TRENDING_UP         7.4%        6.1%    0.82
  TRENDING_DOWN / VOLATILE            5.0%        7.9%    1.58
    TRENDING_UP / VOLATILE            4.6%        6.4%    1.38

## 2. Hour census — continuous zigzag (no forced week-edge pivots)
   PDT hour   week-local (prior study)    continuous   excl. boundary bars
  02:00 PDT                      11.5%         15.3%                 16.2%
  06:00 PDT                      18.1%         22.9%                 24.3%
  10:00 PDT                       5.0%          6.9%                  5.9%
  14:00 PDT                      27.2%         14.8%                 11.1%
  18:00 PDT                      17.7%         18.1%                 19.1%
  22:00 PDT                      20.5%         22.1%                 23.5%
  swings:                          419           393                   371
  (boundary-excluded census drops 22 swings starting on a week's
   first or last H4 bar)

## 3. Fixed-rule verification — first-bounce with-trend entries
Entry exactly at 50/60/70/85% progress to the last LH/HL; target = touch of
the reference extreme; stops at LH/HL + 0.1/0.3×ATR(confirmation); spread
3 pips RT inside R; H4 execution, adverse-first same-bar rules (see header);
60-trading-day cap. ALL cells pre-specified and reported — no selection.
   progress      stop   fills wins   win%    avgR  open  ambig   (of 41 legs)
        50%    0.1×ATR      30   14    47%   -0.12     0      0
        50%    0.3×ATR      30   15    50%   -0.12     0      0
        60%    0.1×ATR      26   10    38%   -0.12     0      0  [descriptive only]
        60%    0.3×ATR      26   11    42%   -0.13     0      0  [descriptive only]
        70%    0.1×ATR      24    8    33%   -0.03     0      0  [descriptive only]
        70%    0.3×ATR      24    9    38%   -0.06     0      0  [descriptive only]
        85%    0.1×ATR      19    3    16%   -0.18     0      0  [descriptive only]
        85%    0.3×ATR      19    4    21%   -0.21     0      0  [descriptive only]
  'ambig' = pre-fill bar touched both entry and target: no trade claimed.
  'open' = still open at cap, scored at cap close (included in avgR, not win%).
```
