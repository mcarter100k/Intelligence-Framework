# Spec: currency-leg decomposition and pair correlation (descriptive and risk; FROZEN before any statistic)

**Status:** FROZEN 2026-11-05, before any study statistic is computed.
- Phase 1 (data and validation) is complete: `studies/leg_data_report.md`,
  validation_log 2026-11-05.
- This file is committed before the runner exists. The runner implements
  exactly what is written here, runs once, and its output goes into the
  report and validation_log verbatim, whatever it says.
- **The three design points held after Phase 1** were resolved by the
  owner's instruction "Commit the spec and run" (2026-11-05), which adopts
  the recommendations put to them: §6 (Phase 3 form), §7 (gold) and §4 Q4
  (reading).

**Free zone:** `studies/`, tests and the research archives outside the repo.
- No protected module is edited. In particular, **`risk_config` is not
  changed.**
- No ledger is written.
- No trading rule, filter or entry condition is proposed.
- The SEALED EXAM is not fetched, counted, opened or touched. M40 governs.

---

## 1. Purpose and the rule it informs

The rule: `risk_config.py:56` `shared_leg_counts_as_one` and
`session_guard.count_leg_grouped_positions`.
- **What it does:** GBP/AUD and GBP/JPY share GBP, so holding both counts
  as ONE position against `MAX_TRADES_PER_SESSION` (2).
- **What it costs:** a position slot, not position size.
- **Status:** it is **not wired** to the live path today. This study
  measures whether "one position" is the right count before the rule is
  ever wired.

## 2. Data (Phase 1, validated)

| Archive | Contents | manifest sha256 |
|---|---|---|
| `~/intel_study_archives/research_archive/` | GBP_AUD, GBP_JPY (D, H4, H1) | `4af4983e5f986dbd86fed8420f0b87db19c8b4fdca62b26ab24037aeed893f87` |
| `~/intel_study_archives/research_archive_legs/` | GBP_USD, AUD_USD, USD_JPY, XAU_USD (D, H4, H1) | `e66eaf44d51b691adf4802aafd8980f56dc90d10035ac22848484f9c680edcc1` |

- **Integrity:** the runner checks both manifest hashes. Every file is read
  through `research_archive.load`, which checks each file's hash against its
  manifest and refuses SEALED.
- **Daily closes only** (the D files). The study uses closes, not highs or
  lows. That means it rests on the values the archive check does verify:
  each daily close equals its last 4-hour close, which equals its last
  hourly close.
- **Periods:** STUDY, USED and FORWARD, each computed separately and never
  pooled. No return spans a period boundary.

## 3. Definitions (fixed now)

- **Aligned dates.** Within a period, the D1 bar times present for every
  instrument in the set:
  - the main set: GBP_AUD, GBP_JPY, GBP_USD, AUD_USD, USD_JPY;
  - the gold set (§7): GBP_AUD, GBP_JPY, XAU_USD.
- **Daily log return:** r = ln(close_t / close_{t−1}) between consecutive
  aligned dates.
- **Weekly log return:** the sum of the daily log returns whose date falls
  in one ISO week of the session day. Weeks with fewer than 3 daily returns
  are excluded and counted.
- **Weekly realised volatility (Q5):** for each cross, √(sum of squared
  daily returns in the week). The week's stress measure is the mean of the
  two crosses' values.
  - **Stress weeks:** the top quintile, at or above the 80th percentile
    (inclusive method) of that measure within the period.
- **OLS** with an intercept. R² is the usual 1 − SSR/SST.
- **Correlation:** Pearson, with a 95% interval by Fisher z.
- **N floor:** any cell with N < 20 is reported as INSUFFICIENT and carries
  no verdict. FORWARD weekly cells hold about 8 weeks, and its stress cells
  about 2.

## 4. The positive control, which runs first: the identity check

In log returns the crosses decompose exactly:
- r(GBP/AUD) = r(GBP/USD) − r(AUD/USD)
- r(GBP/JPY) = r(GBP/USD) + r(USD/JPY)

**Exact equality is not expected.** OANDA quotes each cross independently,
and mid prices carry rounding and quote-timing noise at the daily close.
The check must separate that noise from a data or alignment error.
- **PASS, per pair and per period, requires both:**
  - the correlation between actual and reconstructed daily cross returns is
    ≥ 0.999; and
  - the median |actual − reconstructed| is ≤ 1 basis point (log return
    × 10⁴).
- **Also reported:** the 99th percentile, the maximum, and the count of days
  with |residual| > 10 bp.
- **Control of the control:** the same correlation is computed with the leg
  returns shifted by one aligned date. It must fall far below 0.999, showing
  the check detects misalignment.
- **If any period or pair FAILS, the runner stops.** No question is
  computed.

## 5. THE FROZEN QUESTION LIST: compute these and nothing else

Everything is per pair and per period.

**Q1. Shared-leg share (daily).** R² of cross on GBP/USD.

**Q2. Own-leg share (daily).** R² of GBP/AUD on AUD/USD, and of GBP/JPY on
USD/JPY.

**Q3. Cross-to-cross correlation (weekly, all weeks).**
corr(GBP/AUD, GBP/JPY), with N and a 95% interval.

**Q4. Residual correlation (daily).** The correlation of the two crosses'
Q1 residuals (each cross with its GBP/USD component removed by OLS).
- **Reading, fixed now:** decomposing in US-dollar terms leaves the dollar
  inside both residuals, because −AUD/USD and USD/JPY both carry USD.
- **The figure is reported as "the remaining link, which includes the US
  dollar".** A non-zero value is not read as "something else" without
  that qualification.

**Q5. Stress split (weekly, stress weeks only).**
- Q3 on stress weeks.
- Q4 on stress weeks: the residuals of weekly OLS of each cross on weekly
  GBP/USD, fitted within the stress weeks.
- Reported beside Q3 (all weeks), so the stress effect on the cross-to-cross
  number is visible. There is no all-weeks weekly residual figure; that
  asymmetry is stated, not filled.

## 6. Phase 3: does a lagged leg lead the cross? (daily, one lag)

**The form, adopted on the owner's instruction.** "Beyond the
contemporaneous relationship" is vacuous: by the §4 identity, same-day legs
determine the cross. The test therefore uses lagged legs alone.

- **Model:** r_cross(t) = a + b₁·r_GBPUSD(t−1) + b₂·r_ownleg(t−1).
  - The own leg is AUD/USD for GBP/AUD, and USD/JPY for GBP/JPY.
  - t−1 is the previous aligned date in the same period.
- **Test:** a joint F-test that b₁ = b₂ = 0, with 2 and N−3 degrees of
  freedom (exact tail for 2 numerator degrees of freedom).
- **Cells:** 2 pairs × 3 periods = 6. The Šidák α is 1 − 0.95^(1/6) =
  **0.0085** per cell.
- **Reported:** b₁, b₂, the F statistic, p, and the predictive R².
- **Verdict per cell:**
  - p ≥ 0.0085: **NO LEAD DETECTED**.
  - p < 0.0085: **LEAD DETECTED, RECORDED AS A HYPOTHESIS ONLY**. Not
    built on. It needs its own pre-registered run.
- **Expected answer:** no.

## 7. Gold (secondary, adopted on the owner's instruction)

- **Start:** XAU_USD from the 2006-03-21 session, so the one conversion
  defect at gold's first session (2006-03-20, Phase 1) is excluded.
- **G1.** Weekly corr(GBP/AUD, XAU/USD) and corr(GBP/JPY, XAU/USD), per
  period, with N and a 95% interval, on the gold set's aligned dates.
- **Descriptive only.** No verdict, and nothing else computed with gold.

## 8. Risk verdict, fixed now

ρ is the Q5 weekly cross-to-cross correlation in the stress weeks, per
period.

| ρ | Verdict |
|---|---|
| ρ ≥ 0.7 | "Count as one position" is **JUSTIFIED** |
| ρ ≤ 0.3 | The pairs are substantially independent; the rule is **OVER-CONSERVATIVE** and costs a position slot for no reason |
| between | Report the **effective independent position count, 2 ÷ (1 + ρ)**; the ruling is the team's |

- A period with N < 20 stress weeks gets no verdict.
- **If the periods' verdicts differ, that is reported as a stability
  finding.** It matters more than any average, and no pooled verdict is
  formed.

## 9. Expected result (the requester's, recorded before running)

"A high shared-leg share, a cross-to-cross correlation somewhere in the
middle, and residual correlation close to zero."

**Read, fixed now, so that a marginal number cannot be claimed later:**

| Phrase | Meaning |
|---|---|
| "high shared-leg share" | Q1 R² ≥ 0.5 for both pairs |
| "in the middle" | Q3 strictly between 0.3 and 0.7 |
| "close to zero" | \|Q4\| ≤ 0.1 |

Each is reported as MET or NOT MET per period.

## 10. Not computed

The following are not computed:
- any trading rule or filter;
- any change to `risk_config`;
- hourly or 4-hour statistics;
- other lags or horizons;
- per-year splits;
- pooled periods;
- anything not named in §4–§9.

Interesting results outside the list are recorded as HYPOTHESES.

## 11. Run procedure

- The runner is `studies/leg_decomposition_study.py`, written after this
  commit. Tests: `tests/test_leg_decomposition_study.py`.
- It runs ONCE through `scripts/reality_run.py --no-env --code <worktree>
  script …`, with no network.
- It prints a UTC start timestamp, checks the two manifest hashes, then
  prints "first computation start (UTC)" before the identity check.
- Its stdout is the report body.
