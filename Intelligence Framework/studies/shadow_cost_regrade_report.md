# Shadow ledger re-graded with costs (read-only)

Spread 3.0 pips round trip (sensitivity 4.0); financing at OANDA's 2026-11-01 quoted rates (sensitivity: 1 point worse); rollovers at 17:00 New York, Wednesday x3. Raw R is the frozen grader's; adjusted R never replaces it.

Positive control: 28 graded rows; every raw R reproduced from freshly fetched H4 bars to 2 dp (a mismatch would have aborted the run).

## EARLY_MOMENTUM_v2

- Episodes, raw R (frozen grader): N 4; mean -0.400R; median -0.470R  (INSUFFICIENT: N<20)
- Episodes, cost-adjusted R: N 4; mean -0.411R; median -0.513R  (INSUFFICIENT: N<20)
- Episodes, cost-adjusted R at 4.0 pips and rates 1 point worse: N 4; mean -0.442R; median -0.535R  (INSUFFICIENT: N<20)
- All graded fires (20): mean spread cost 0.025R, mean financing +0.004R, mean nights 6.0

| Episode (first fire) | Pair | Side | Risk (pips) | Nights | Raw R | Spread | Financing | Adjusted R |
|---|---|---|---|---|---|---|---|---|
| 2026-09-18T05:00 | GBP_JPY | LONG | 311 | 7 | -0.55 | -0.010 | +0.021 | -0.539 |
| 2026-09-25T17:00 | GBP_JPY | SHORT | 182 | 7 | -0.39 | -0.016 | -0.080 | -0.487 |
| 2026-10-02T17:00 | GBP_JPY | LONG | 144 | 7 | +0.34 | -0.021 | +0.045 | +0.364 |
| 2026-10-19T09:00 | GBP_JPY | LONG | 83 | 5 | -1.00 | -0.036 | +0.056 | -0.980 |

## THRUST_PULLBACK

- Episodes, raw R (frozen grader): N 1; mean -0.330R; median -0.330R  (INSUFFICIENT: N<20)
- Episodes, cost-adjusted R: N 1; mean -0.418R; median -0.418R  (INSUFFICIENT: N<20)
- Episodes, cost-adjusted R at 4.0 pips and rates 1 point worse: N 1; mean -0.443R; median -0.443R  (INSUFFICIENT: N<20)
- All graded fires (1): mean spread cost 0.015R, mean financing -0.073R, mean nights 7.0

| Episode (first fire) | Pair | Side | Risk (pips) | Nights | Raw R | Spread | Financing | Adjusted R |
|---|---|---|---|---|---|---|---|---|
| 2026-09-28T05:00 | GBP_JPY | SHORT | 200 | 7 | -0.33 | -0.015 | -0.073 | -0.418 |

## MOMENTUM_JOIN

- Episodes, raw R (frozen grader): N 2; mean -1.000R; median -1.000R  (INSUFFICIENT: N<20)
- Episodes, cost-adjusted R: N 2; mean -1.038R; median -1.038R  (INSUFFICIENT: N<20)
- Episodes, cost-adjusted R at 4.0 pips and rates 1 point worse: N 2; mean -1.074R; median -1.074R  (INSUFFICIENT: N<20)
- All graded fires (7): mean spread cost 0.049R, mean financing -0.039R, mean nights 3.3

| Episode (first fire) | Pair | Side | Risk (pips) | Nights | Raw R | Spread | Financing | Adjusted R |
|---|---|---|---|---|---|---|---|---|
| 2026-09-28T05:00 | GBP_AUD | LONG | 55 | 1 | -1.00 | -0.054 | -0.018 | -1.072 |
| 2026-10-21T05:00 | GBP_JPY | LONG | 60 | 3 | -1.00 | -0.050 | +0.046 | -1.004 |

