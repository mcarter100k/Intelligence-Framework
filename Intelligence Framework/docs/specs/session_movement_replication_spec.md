# Spec addendum: session movement study, replication on the USED span (2021-04-27 → 2026-09-09)

**Status:** FROZEN 2026-11-05, owner/team approved (option (a)), before any
statistic on this span is computed.
- This addendum is committed before the wrapper and the comparison script
  exist, and before the control run and the modern run.
- It adds a second period to `session_movement_study_spec.md` (85e5c19).
  It changes nothing in that spec's question list, definitions or reading
  rules.

**Free zone:** `studies/`, tests and data outside the repo. No protected
module is edited, no ledger is written, and the SEALED EXAM is not touched.

---

## 1. What this is

A replication. The five frozen questions Q1–Q5 are computed on the USED
span with the same code, the same fixed UTC blocks and the same
definitions. The two periods are then reported side by side, per pair, and
never pooled.
- No motivation or expected direction is stated, by the team's
  instruction. The pre-committed thresholds in §5 and §6 are the only
  arbiters.
- Whether to day trade remains out of scope.

## 2. Data

`~/intel_study_archives/modern_data/`: OANDA mid D, H4 and H1, fetched
2026-11-06T05:36Z through the guarded modern fetch (research archive build,
validation_log 2026-11-05).
- It starts at the first USED candle, 2021-04-26 21:00 UTC, so the ATR
  series do not jump across 2014–2021.
- It has 0 weekend-session candles, so the approved weekend rule is a no-op
  here and Q1 excludes no fold bars.

| File | sha256 |
|---|---|
| GBP_AUD_D.csv | `3f17cd0e7d2b7ab3492d22044876dc4703423fbd60a5d77edfc202abf0530100` |
| GBP_AUD_H4.csv | `623f0f5e09e2f8d39e2637eb1d307751a72be155d6214aa1fddf9deadcd77042` |
| GBP_AUD_H1.csv | `7c8f899f31e4f1f4d92e6c932d202ff8d3375bd5c69eb8d684b8b3f5c3509fed` |
| GBP_JPY_D.csv | `3635903a1d7d573f1489d61fd1f8eada21d1e3429feccb8a83e717700fdbc3d6` |
| GBP_JPY_H4.csv | `3d5131f99184ef1642b5aa075e3a8dea9cadcfb918e59cd42d6c9d7af6bfcf47` |
| GBP_JPY_H1.csv | `f0d2437c79778e9fbe003282a7d4f3ec5301b14b54f179f26a1c9640597e1cd3` |

**Window:** study days (21:00 → 21:00 UTC, Mon–Fri) and New York session
days (for Q5), from 2021-04-27 to 2026-09-09.
- The files extend past the window: the 2026-09-10 boundary session and the
  FORWARD span to 2026-11-05.
- Those bars are outside the window and enter no figure. An ATR value at a
  bar depends only on earlier bars, so later bars cannot change in-window
  values.

## 3. Method: the unmodified runner, driven by a wrapper, proven by a control

The runner cannot run on this span as written: its data hashes and day
window are constants. The approved method:

1. **The wrapper.** `studies/session_movement_replication.py` imports the
   runner and rebinds only three inputs, then calls the runner's own
   `run()`:
   - `session_movement_study.EXPECTED_HASHES`;
   - `session_movement_data.STUDY_FIRST_DAY`;
   - `session_movement_data.STUDY_LAST_DAY`.
2. **Code pins, checked by the wrapper before any computation.** It
   refuses to run if any of these differ (they are the values at the
   original run, 2f7c68b):
   - `session_movement_study.py` `2302ab4203419186ca3341906bad017aed4b81e5a653c5ae78dd60883724935d`
   - `session_movement_data.py` `3f2d43145eca863ace4ad30a2b7af542747f1ad2bf105bb91bc613c61b655ff1`
   - `history_study_convert.py` `584ff76da113d3ab8d8eae277f95b6596981badfb8923634063b87de044ea553`
3. **The control, which runs first and gates everything after it.** The
   wrapper is run through the same rebinding path with the 2005–2013
   inputs: the original six hashes, 2005-01-03 and 2013-12-30.
   - Its stdout must equal the published run's stdout, byte for byte,
     except the two timestamp lines that can never match:
     - `run start (UTC): …`
     - `first computation start (UTC): …`
   - Those two lines are removed from both sides before comparing. Every
     other byte must be identical.
   - **If the control fails, stop.** No modern run happens.
4. **The modern run.** The wrapper runs once with the §2 hashes and window.
5. **The comparison.** `studies/session_movement_compare.py` reads both
   stdouts (the published one from `session_movement_report.md` §7 and the
   modern one). It computes only what §4–§6 name.

All runs go through `scripts/reality_run.py --no-env`, with no network.

## 4. Side-by-side reporting (all-days tables, per pair)

| Question | Shown for both periods |
|---|---|
| Q1 | mean and median per UTC hour, plus the busiest-to-quietest ratio of the hourly means |
| Q2 | median share per block |
| Q3 | % of days with the high, and with the low, per block, plus % with both in one block |
| Q4 | % of days with the high, and with the low, in place by hour 6, 12 and 18 |
| Q5 | mean ATR in pips at H1, H4 and D1 (numbers only, no rule proposal) |

- **Weekday breakdown:** the modern run's weekday tables appear in its
  verbatim output. They are not compared and not tested; that would add
  about 200 comparisons.
- **Absolute pip figures** differ with each era's volatility. Only shares,
  percentages and ratios are compared (§5).

## 5. Materiality: a difference counts only if BOTH gates pass

**Q3 shares.** There are 5 blocks × (high, low) × 2 pairs = **20
comparisons.**
- **Statistical gate:** a two-sided two-proportion z-test (pooled), at the
  Šidák-adjusted α = 1 − 0.95^(1/20) = **0.0026** per comparison
  (`power_check.sidak_alpha(0.05, 20)`). At a naive 0.05 each, the
  family-wise false-alarm rate would be 64%.
  - Inputs: each period's printed percentage (one decimal) and N days.
  - The rounding is at most 0.05 points, against a standard error of about
    1.4 points for the difference.
- **Practical gate:** |difference| ≥ **5 percentage points**.
- **Rationale for the practical gate:**
  - The standard error on a 20% proportion is about 1.1 points at ~1,395
    sessions, and 0.8 points at ~2,343.
  - The 95% band on the difference is therefore about ±2.6 points, so
    anything under ~3 points is noise.
  - Five points is the conservative line.
- **Each comparison reports:** both values, the difference, z, two-sided p,
  pass/fail at the per-comparison 0.05 and at the Šidák 0.0026, and the
  verdict.

**Q1 busiest-to-quietest ratio (2 comparisons).**
- **Practical gate:** |difference| ≥ **0.5**.
- **No significance test can be computed.** The runner prints hourly means,
  medians and N, but no spread, so the statistical gate cannot be computed
  from the frozen outputs.
- **The ratio is judged on the practical gate alone,** and the report labels
  it SINGLE-GATE.

**Verdict words, exactly:**
- **MATERIAL:** both gates pass.
- **CONSISTENT WITH THE EARLIER PERIOD:** anything else.
- **No other wording.** Not "slightly higher", not "a mild shift". A
  difference that passes one gate only is CONSISTENT, with the one gate it
  passed noted.

## 6. Day-trading precondition (modern data, per pair, fixed now)

**PASS** only if, on the USED span, BOTH of these hold:
- the busiest hour's mean range is **more than 2.5 ×** the quietest's (Q1
  all-days); AND
- at least one block holds **≥ 35%** of daily highs, or of daily lows (Q3
  all-days).

Otherwise **FAIL**.
- The report shows PASS or FAIL per pair, with the two figures, and nothing
  more.
- No recommendation is made.

## 7. Carried limits

- **The verification caveat** (`session_movement_report.md` §6) applies to
  both periods. Hourly figures are consistent with verified 4-hour data,
  not verified bar by bar. Q1 is built mostly from unverified values; Q3
  and Q4 are proven only to the 4-hour block.
- **USED is learning only,** never proof. These are descriptive figures,
  with no VALIDATED label.
- **DST smear** and the **study-day / framework-day difference** are as
  in the original spec.
- **Anything else the two periods show** that §4–§6 do not capture is
  recorded as a HYPOTHESIS and not computed.

## 8. Corrections to the request, recorded (team, 2026-11-05)

These are not inherited:
- **The motivation sentence is struck.** It said the earlier study
  concluded the pairs are poorly suited to day trading. The study drew no
  such conclusion; its gate read CONCENTRATED.
- **The "~104 / ~136" daily ATR figures for "now"** were quoted from
  conversation, not the repo. Q5 measures the USED-span means.
- **The Šidák adjustment is reused, but not `power_check`'s statistic.**
  That tool's statistic is a one-sided test of mean R; the test here is
  named in §5.
