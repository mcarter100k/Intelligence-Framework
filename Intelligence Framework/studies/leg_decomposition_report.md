# Currency-leg decomposition and pair correlation: report (2026-11-05)

**Spec:** `docs/specs/leg_decomposition_study_spec.md`, frozen at 671033a.
**Runner:** `studies/leg_decomposition_study.py`, af4b95e, run once.
**Data:** `studies/leg_data_report.md` (Phase 1).

**What it is, and is not:**
- Descriptive and risk only.
- **No trading rule is proposed, and `risk_config` is not changed.** The
  team rules.
- USED is learning only, never proof.

## Ordering

| Event | Pacific | UTC |
|---|---|---|
| **Spec committed, 671033a** (runner absent: `ls` → "No such file") | **2026-11-05 23:33:58 PST** | 2026-11-06 07:33:58 |
| Runner committed, af4b95e | 23:36:12 PST | 07:36:12 |
| **First computation** (runner's own stamp) | **23:36:13 PST** | 07:36:13 |

The run went through `reality_run.py --no-env`: exit 0, stderr 0 bytes,
project unchanged by hash.

## Plain English: how much of each pair is the GBP leg, and is holding both one bet or two?

**The GBP leg (GBP/USD) explains little of GBP/AUD and only part of
GBP/JPY.**

| Share of daily moves explained | 2005–2013 | 2021–2026 |
|---|---|---|
| GBP/AUD by GBP/USD | 1% | 2% |
| GBP/JPY by GBP/USD | 39% | 16% |
| GBP/AUD by AUD/USD (its other leg) | 58% | 35% |
| GBP/JPY by USD/JPY (its other leg) | 52% | 39% |

- **Each pair is driven more by its other leg** than by the GBP leg.
- **Why GBP/AUD's figure is so low:**
  - GBP/USD and AUD/USD move together (correlation +0.57 and +0.71), both
    being priced in dollars.
  - The dollar cancels out of GBP/AUD.
  - The reported R² follows exactly from the legs' own variances and
    correlation (0.009 and 0.023, checked separately).

**One bet or two? It depends on the era, and that is the main finding.**
- **2005–2013:** week to week the two pairs were unrelated. The correlation
  was −0.01 overall and −0.10 in the most volatile fifth of weeks.
  - By the rule fixed before the run, counting them as one position was
    **OVER-CONSERVATIVE**.
- **2021–2026:** they move somewhat together, +0.20 overall and +0.33 in
  volatile weeks.
  - The rule gives **BETWEEN**: holding both is about **1.5 independent
    positions**, not 1 and not 2.
  - The uncertainty is wide. The 95% interval for the volatile-week figure
    runs from +0.07 to +0.54.
- **The two eras disagree.** The spec calls that a stability finding, and it
  matters more than any average. In neither era is "one position"
  justified (that needs at least 0.7).
- **The rule today:** it limits position count, not size, and it is not
  wired, so it currently costs nothing.

**The requester's expected result was NOT met.**
- **"A high shared-leg share":** NOT MET. The R² is 0.01–0.39, not ≥ 0.5.
- **"A cross-to-cross correlation in the middle" (0.3–0.7):** NOT MET. It is
  −0.01 and +0.20.
- **"Residual correlation close to zero":** NOT MET. It is −0.22 and +0.12,
  read as the remaining link, which includes the US dollar.
- **Forward period:** too short for the weekly figures (8 weeks).

**Leading-indicator idea (Phase 3): mostly killed, with one unexpected
exception.**
- **GBP/JPY:** yesterday's leg moves do not predict today's move in any
  period.
- **GBP/AUD:** shows a small but statistically detectable next-day
  relationship in both long periods. It explains about 1% of daily moves,
  with p < 0.0001 in 2005–2013 and p = 0.0068 in 2021–2026, against a Šidák
  α of 0.0085.
- **As the spec requires,** it is **recorded as a hypothesis only and not
  built on.** It is tiny, it is measured on mid prices at the daily close,
  and it may be a closing-quote effect.

**Gold (descriptive).** Weekly gold moves are mildly negatively related to
GBP/AUD (−0.14, then −0.23) and unrelated to GBP/JPY.

## Hypotheses recorded, NOT computed (each needs its own pre-registered run)

1. **The GBP/AUD next-day relationship.** Is it GBP/AUD's own one-day
   autocorrelation, or mean reversion in AUD/USD at the 17:00 New York close
   (a quote-timing effect)? Does anything survive costs?
2. **Why the pairs were unrelated in 2005–2013.** AUD and JPY are opposite
   risk currencies: risk-off lifts GBP/AUD and lowers GBP/JPY, offsetting
   the shared GBP. Test with a risk proxy.
3. **The correlation change between eras** (−0.01 → +0.20). Is it a level
   shift or drift? Sub-period stability.
4. **The residual-correlation sign flip** (−0.22 → +0.12): how the dollar
   and risk effects combine in each era.
5. **The GBP/AUD–gold link,** through AUD as a commodity currency.

## Limits

- **Values are checked for consistency, not correctness.** Daily closes
  agree with 4-hour and hourly closes. No second source exists.
- **The identity holds to quote noise, not exactly:**
  - median 0.07–0.47 bp;
  - correlation ≥ 0.9994;
  - 9 of 7,550 pair-days above 10 bp, the largest 87.8 bp (2005–2013,
    GBP/AUD).
- **Weekly correlations rest on N = 469 (STUDY) and 281 (USED) weeks.**
  - The stress cells hold 94 and 56 weeks.
  - FORWARD cells are INSUFFICIENT, and their ±1.000 values are artefacts
    of N = 2.
- **2005–2013 is the financial-crisis era.** USED is learning only.
- **The risk verdict is descriptive input.** The rule is not wired;
  `risk_config` is unchanged.

---

## Full output of the single run (verbatim)

```
run start (UTC): 2026-11-06T07:36:13+00:00
manifest cross: OK
manifest legs: OK
first computation start (UTC): 2026-11-06T07:36:13+00:00

## 1. Identity check (positive control; §4)

| period | pair | N days | corr(actual, reconstructed) | median \|res\| bp | p99 bp | max bp | days > 10 bp | corr with legs shifted 1 date | result |
|---|---|---|---|---|---|---|---|---|---|
| STUDY | GBP_AUD | 2342 | 0.999429 | 0.069 | 0.63 | 87.81 | 2 | -0.0729 | PASS |
| STUDY | GBP_JPY | 2342 | 0.999875 | 0.467 | 5.39 | 21.89 | 2 | +0.0358 | PASS |
| USED | GBP_AUD | 1394 | 0.999601 | 0.370 | 5.76 | 11.49 | 1 | -0.0321 | PASS |
| USED | GBP_JPY | 1394 | 0.999771 | 0.344 | 5.36 | 12.12 | 4 | +0.0342 | PASS |
| FORWARD | GBP_AUD | 39 | 0.999959 | 0.284 | 0.80 | 0.81 | 0 | -0.1511 | PASS |
| FORWARD | GBP_JPY | 39 | 0.999920 | 0.317 | 1.10 | 1.15 | 0 | -0.1507 | PASS |

D1 bars not in the aligned set, per period: STUDY {'GBP_AUD': 0, 'GBP_JPY': 0, 'GBP_USD': 0, 'AUD_USD': 0, 'USD_JPY': 0}; USED {'GBP_AUD': 0, 'GBP_JPY': 0, 'GBP_USD': 0, 'AUD_USD': 0, 'USD_JPY': 0}; FORWARD {'GBP_AUD': 0, 'GBP_JPY': 0, 'GBP_USD': 0, 'AUD_USD': 0, 'USD_JPY': 0}

## 2. Q1 and Q2: share of each cross explained by one leg (daily R²)

| period | pair | N days | Q1 R² on GBP/USD | Q2 R² on own leg (own leg) |
|---|---|---|---|---|
| STUDY | GBP_AUD | 2342 | 0.009 | 0.584 (AUD_USD) |
| STUDY | GBP_JPY | 2342 | 0.386 | 0.521 (USD_JPY) |
| USED | GBP_AUD | 1394 | 0.023 | 0.347 (AUD_USD) |
| USED | GBP_JPY | 1394 | 0.164 | 0.393 (USD_JPY) |
| FORWARD | GBP_AUD | 39 | 0.149 | 0.468 (AUD_USD) |
| FORWARD | GBP_JPY | 39 | 0.198 | 0.340 (USD_JPY) |

## 3. Q3, Q4, Q5: how the two crosses move together

Q4 is the remaining link after the GBP/USD component is removed, **which includes the US dollar** (§5).

| period | Q3 weekly corr, all weeks | Q4 daily residual corr | Q5 weekly corr, stress weeks | Q5 weekly residual corr, stress weeks | weeks excluded (< 3 days) |
|---|---|---|---|---|---|
| STUDY | -0.009 [-0.100, +0.082] (N 469) | -0.224 [-0.262, -0.185] (N 2342) | -0.095 [-0.292, +0.110] (N 94) | -0.269 [-0.448, -0.071] (N 94) | 1 |
| USED | +0.199 [+0.084, +0.309] (N 281) | +0.124 [+0.071, +0.175] (N 1394) | +0.325 [+0.068, +0.542] (N 56) | +0.239 [-0.026, +0.472] (N 56) | 0 |
| FORWARD | +0.198 [-0.589, +0.792] (N 8 INSUFFICIENT) | +0.035 [-0.284, +0.346] (N 39) | +1.000 [+nan, +nan] (N 2 INSUFFICIENT) | +nan [+nan, +nan] (N 2 INSUFFICIENT) | 0 |

## 4. Risk verdict (§8; ρ = Q5 weekly cross-to-cross correlation in stress weeks)

| period | ρ | stress weeks | verdict |
|---|---|---|---|
| STUDY | -0.095 | 94 | OVER-CONSERVATIVE (costs a position slot for no reason) |
| USED | +0.325 | 56 | BETWEEN — effective independent positions 2/(1+ρ) = 1.51; ruling is the team's |
| FORWARD | +1.000 | 2 | INSUFFICIENT (no verdict) |

Stability across periods with a verdict: DIFFERS — a stability finding (§8) (STUDY OVER-CONSERVATIVE, USED BETWEEN)

## 5. Phase 3: do yesterday's leg returns predict today's cross return? (§6)

Šidák α for 6 cells: 0.0085

| period | pair | N | b(GBP/USD t−1) | b(own leg t−1) | F | p | predictive R² | verdict |
|---|---|---|---|---|---|---|---|---|
| STUDY | GBP_AUD | 2341 | +0.0177 | +0.0801 | 13.164 | 0.0000 | 0.0111 | LEAD DETECTED — RECORDED AS A HYPOTHESIS ONLY |
| STUDY | GBP_JPY | 2341 | +0.0341 | +0.0371 | 1.504 | 0.2225 | 0.0013 | NO LEAD DETECTED |
| USED | GBP_AUD | 1393 | +0.0250 | +0.0442 | 5.016 | 0.0068 | 0.0072 | LEAD DETECTED — RECORDED AS A HYPOTHESIS ONLY |
| USED | GBP_JPY | 1393 | +0.0213 | +0.0413 | 0.994 | 0.3704 | 0.0014 | NO LEAD DETECTED |
| FORWARD | GBP_AUD | 38 | -0.2203 | +0.1253 | 0.494 | 0.6146 | 0.0274 | NO LEAD DETECTED |
| FORWARD | GBP_JPY | 38 | -0.2011 | -0.1237 | 0.483 | 0.6213 | 0.0268 | NO LEAD DETECTED |

## 6. G1: gold (weekly correlation with each cross; descriptive, §7)

| period | corr(GBP/AUD, XAU/USD) | corr(GBP/JPY, XAU/USD) |
|---|---|---|
| STUDY | -0.136 [-0.230, -0.039] (N 406) | +0.057 [-0.041, +0.153] (N 406) |
| USED | -0.225 [-0.333, -0.110] (N 281) | -0.010 [-0.127, +0.107] (N 281) |
| FORWARD | +0.488 [-0.331, +0.887] (N 8 INSUFFICIENT) | +0.408 [-0.416, +0.864] (N 8 INSUFFICIENT) |

## 7. The requester's expected result (§9)

| period | Q1 R² ≥ 0.5 both pairs | 0.3 < Q3 < 0.7 | \|Q4\| ≤ 0.1 |
|---|---|---|---|
| STUDY | NOT MET | NOT MET | NOT MET |
| USED | NOT MET | NOT MET | NOT MET |
| FORWARD | NOT MET | n/a (INSUFFICIENT) | MET |
```
