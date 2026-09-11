```
==============================================================================
STAGE 2 — source, convert, gate (verification numbers only)
STUDY span in force: 2005-01-01 → 2013-12-31 (spec §2 coverage rule)
==============================================================================

## Feed-overlap check (2023-09-01 → 2026-09-10, Dukascopy-freeserv mid vs OANDA mid)
  [GBP_AUD: 18814 H1 mid bars fetched for overlap]
  GBP_AUD D1: 784 matched bars (0 OANDA-only missing from feed)
      median |diff| pips  O=4.22  H=0.30  L=0.30  C=1.55
      p95    |diff| pips  O=18.15  H=5.70  L=5.20  C=6.20
      disagreement rate (any field > 5 pips): 53.57%
  GBP_AUD H4: 4704 matched bars (0 OANDA-only missing from feed)
      median |diff| pips  O=0.30  H=0.25  L=0.25  C=0.30
      p95    |diff| pips  O=6.90  H=4.00  L=3.40  C=2.70
      disagreement rate (any field > 5 pips): 12.73%
  [GBP_JPY: 18865 H1 mid bars fetched for overlap]
  GBP_JPY D1: 784 matched bars (0 OANDA-only missing from feed)
      median |diff| pips  O=2.90  H=0.20  L=0.20  C=1.65
      p95    |diff| pips  O=12.75  H=4.05  L=3.85  C=5.80
      disagreement rate (any field > 5 pips): 39.67%
  GBP_JPY H4: 4704 matched bars (0 OANDA-only missing from feed)
      median |diff| pips  O=0.25  H=0.15  L=0.15  C=0.20
      p95    |diff| pips  O=5.25  H=2.35  L=1.95  C=2.65
      disagreement rate (any field > 5 pips): 9.16%

  OVERLAP CHECK: FAIL (thresholds: disagreement ≤ 2%, median |close diff| ≤ 1.5 pips)
  Spec §2 failure ladder applies — stopping before any STUDY conversion.

DIAGNOSTIC DECOMPOSITION (same check, thresholds untouched, verdict unchanged)
  GBP_AUD D1: HLC-only disagreement 19.52%   median |C diff| 1.55 pips
  GBP_AUD H4: HLC-only 8.01%; rollover slot-0 all-fields 62.24%; other slots 2.83%
  GBP_JPY D1: HLC-only disagreement 14.67%   median |C diff| 1.65 pips
  GBP_JPY H4: HLC-only 5.23%; rollover slot-0 all-fields 43.75%; other slots 2.24%
  Reading: the 17:00-NY rollover hour dominates the disagreement (H1-derived
  opens cannot reproduce tick-accurate rollover opens), but the failure is NOT
  solely granularity — non-rollover H4 slots still exceed the 2% bar and both
  D1 close medians exceed 1.5 pips.

LADDER STATE (spec section 2):
  - Dukascopy overlap check: FAIL (numbers above).
  - HistData re-run: NOT EXECUTABLE — get.php returns 0 bytes for every
    dataset; the form token is served empty even to a fully-rendered headless
    Chrome DOM. Attempted 2026-09-11, documented in the script header.
  - Both providers failed => history-validation INFEASIBLE as of 2026-09-11
    sourcing conditions. STUDY span was never converted; no STUDY bar was
    opened past coverage probing; no price statistics were computed.
  - Team caveats: datafeed.dukascopy.com (M1/tick transport) was 503/timeout
    all session — if it returns, an M1-based re-attempt would remove the
    rollover-granularity component; that re-attempt is a team decision.
```
