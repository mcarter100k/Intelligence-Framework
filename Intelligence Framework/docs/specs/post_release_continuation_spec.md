# Spec PRC-1: post-release continuation in gold (pre-registration draft, amended)

**Unit: HRU (half-range unit), not R.** PRC-1 has no stop. Every result is
measured in HRU = P&L ÷ (0.5 × the daily ATR), the ATR being the simple mean
true range of the 14 sessions completed before the event. An HRU normalises
volatility, not risk: no stop stands behind it. **HRU figures are not
comparable to R in any spec with a real stop** (GMW-1, GNC-1, GTP-1, R37–R46):
"+0.44 HRU" here does not mean what "+0.104R" means in GMW-1. (Owner ruling B2,
2026-11-16.)

**This test can return SUPPORTED only for an effect near +0.44 HRU per trade,
roughly ten times anything measured, so in practice it can return REFUTED,
INCONCLUSIVE or INSUFFICIENT.** (Owner rulings B1, A1, A8, 2026-11-16.
INCONCLUSIVE is the named verdict for 20 or more trades that are not refuted;
it confirms nothing. The door stays open if a larger effect turns up on other
data. PRC-1 stays outside the multiple-testing family, α 0.0253 for GMW-1's two
cells; ruling B1.)

**Pending before any run (ruling B3):** the owner decides from §12 whether
PRC-1 runs or is shelved alongside GTP-1.

**The rule as specified here has never been measured on any data** (ruling
A9). With the 1:00 PM PT Fed entry (ruling R4), neither +$34.73 (Fed priced 30
minutes after the release; withdrawn) nor +$14.38 (Fed entered at the 2:00 PM
PT four-hour close) describes it. Neither figure is this rule's expected
result.

**Status:** DRAFT 2026-11-16, written at the owner's request (remediation brief,
Part 6) and amended the same day by the owner's rulings. Not frozen, not run,
nothing computed on 2006–2013 data. **It does not run until the owner signs
off**, because the same-week/weekend split was chosen after looking at 2026
data. Any change after freezing is a new id (PRC-2).

**Free zone:** a study, its tests, and data outside the repo. No protected
module, no ledger, no SEALED EXAM bar.

## Amendments

- 2026-11-16 (ruling R3): the owner's 2026 origin figures are **withdrawn** by
  the owner (§1). The origin is computed from candles only.
- 2026-11-16 (ruling R4): Fed trades enter at the **1:00 PM PT hourly close on
  decision day** and exit at 1:00 PM PT the following session. The earlier
  draft entered at the 2:00 PM PT four-hour close, which fell after the
  1:00 PM PT exit window.
- 2026-11-16 (ruling R5): the 2026 characterisation uses the measured figures
  and records two regimes (§2).
- 2026-11-16 (ruling R6): the family is six named tests (§6); α = 0.0085.
- 2026-11-16 (ruling R7): no SUPPORTED verdict; the sentence above states what
  the test can return. The +0.05R line (GMW-1 only) is not used here; REFUTED
  uses the futility standard.
- 2026-11-16 (round 2, A1): INCONCLUSIVE is a named verdict.
- 2026-11-16 (A2): PRC-1 is not in the multiple-testing family while it has no
  SUPPORTED verdict; REFUTED is deliberately uncorrected. If ruling A8 restores
  SUPPORTED, PRC-1 rejoins the family (three tests; Šidák α 0.0170).
- 2026-11-16 (A4): the Wednesday triple charge is confirmed; Fed financing is
  reported separately, not inside a pooled mean.
- 2026-11-16 (A9): the rule as specified has never been measured (top note).
- 2026-11-16 (A8): §11 records the measured effect in this spec's own unit.
- 2026-11-16 (round 3, B1): A8 decided: the family stays at GMW-1's two cells
  (α 0.0253); the top sentence reworded to name the mechanism.
- 2026-11-16 (B2): the unit is renamed HRU (half-range unit) throughout, with
  a named note at the top: it is not R and not comparable to R.
- 2026-11-16 (B3): §12 records the 90% upper bound of the 2026 effect for the
  owner's run-or-shelve decision.

## What you are deciding (plain English)

- **The question:** after a jobs report or CPI (entry at the first 4-hour
  close) or a Fed decision (entry at 1:00 PM PT that day), does gold keep
  going the way it was heading until 1:00 PM PT the next session? Only trades
  that close the same week count.
- **What it can tell you:** whether the idea loses clearly (REFUTED). It
  cannot tell you it works.
- **Decisions in front of you:** ruling B3, run or shelve (§12: the 90%
  upper bound of the 2026 same-week effect against the +0.44 HRU detection
  floor); the HRU threshold for REFUTED (§6); then, if it runs, sign-off after
  GNC-1's 15-minute data is fetched and checked.

## 1. Origin (a hypothesis source, never evidence)

- **The owner's figures are withdrawn** (ruling R3). They priced Fed entries
  at the price 30 minutes after the release instead of the first 4-hour close
  (2:00 PM PT, three hours later). Checked: repeating that pricing on the 2026
  candles gives same-week 17 trades +$34.73 (t 1.71), all 28 +$20.46 (t 1.37),
  weekend 11 −$1.60, with Fed trades 58.9% of the same-week total, which
  matches the withdrawn figures. The 5:30 AM releases were unaffected, since
  30 minutes after 5:30 is the 6:00 AM four-hour close.
- **From candles only** (`studies/gold_2026_release_reactions.py`, dates in
  `studies/us_events_2026.csv`, OANDA mid candles; entry at the first 4-hour
  close, exit at the next session's 2:00 PM PT close, no costs; the draft's
  definition before ruling R4):

| Group | N | Mean per trade | t |
|---|---|---|---|
| All | 28 | +$8.10 | 0.58 |
| Same-week exits | 17 | +$14.38 | 0.76 |
| Weekend holds | 11 | −$1.60 | −0.08 |

- Nothing from the Gold News Playbook's table is carried forward.
- **The same-week/weekend split was chosen after seeing 2026.** This spec
  tests it on data that did not suggest it.

## 2. External validity: 2026 is two regimes

Measured from OANDA daily candles (`studies/gold_2026_release_reactions.py`
and a session-by-session check):
- gold **rose +25.2%** from the first 2026 open ($4,326.40, Jan 2) to the
  highest close ($5,418.55, Jan 28), and +29.5% to the intraday high
  ($5,602.23, Jan 29);
- it then **fell**: −30.7% from that high to the 2026-11-12 close
  ($3,884.68), leaving the year **−10.2%** from its first open;
- the median daily true range was **2.21%** of price (224 sessions); the C1
  study gives a 2026 median ATR of 2.61% through 2026-09-08 (R47).

So the 28 events that suggested this rule came from a sharp rise and then a
long fall, in the most volatile gold year of either era. A pattern from that
window may not hold elsewhere. (The owner's brief described a rise of roughly
23%; the measured figures above replace it, ruling R5.)

## 3. Data and partition

- **Verdict data:** 2006-03-21 → 2013-12-30 (STUDY) only. **No 2014-01-01 →
  2021-04-25 bar is fetched, loaded or read.** USED (2021–2026) is not used.
- **Events:** `studies/us_events_2005_2013.csv` (NFP, CPI at 8:30 ET) and
  `studies/fomc_statement_times_2006_2013.csv` (scheduled FOMC meetings with a
  sourced, derived, secondary or posted time; unsourced meetings dropped and
  listed).
- **Prices:** the price at the release from GNC-1's M15 data (its check must
  pass first). H4 bars: `research_archive_legs/XAU_USD_H4.csv`
  (`e101117de1af589820a10eb4b5e65b30a4f294e9ee7683ac1baf8a8c02f0011c`). H1 bars
  (the 1:00 PM PT closes): `XAU_USD_H1.csv`
  (`eabec6652e055540b256aa743971a1a5aa5cbb459e94b4887da6f28b8e02a4be`). Daily
  sessions: `XAU_USD_D.csv`
  (`6202a13d86459d2d3453c31ea9ddf40a3aca44243a6d4ff75bf3d0c165d0e3ca`).
- **Same-day releases** (CPI and FOMC on five days): the CPI trade is taken,
  the FOMC skipped and listed.

## 4. The rule

- **Price at the release:** the open of the M15 bar at the release time.
- **NFP and CPI (8:30 AM ET):** entry at the close of the H4 bar holding the
  release, 9:00 AM ET (6:00 AM PT). Direction = that close minus the price at
  the release.
- **FOMC (ruling R4):** entry at **1:00 PM PT on decision day**, the close of
  the H1 bar opening at 12:00 PT. Direction = that close minus the price at
  the release. In 2006–2013 statements came out at 2:15 PM ET (11:15 AM PT),
  12:30 PM ET (9:30 AM PT, the 2011–2012 press-conference meetings) or 2:00 PM
  ET (11:00 AM PT, 2013); press conferences began at 2:15 PM ET (2011–2012) or
  2:30 PM ET (2013). The 1:00 PM PT entry is after each statement; that it is
  after each press conference ends assumes they ran about an hour (INFERRED,
  not checked meeting by meeting).
- **Zero direction:** no trade.
- **Exit:** 1:00 PM PT in the next session (the next weekday daily session in
  the data). NFP and CPI: the close of the M15 bar ending then. FOMC: the
  close of the H1 bar opening at 12:00 PT. Missing bar: skip and count.
- **No stop.** Results in HRU = P&L ÷ (0.5 × daily ATR), ATR from the 14 sessions completed
  before the event's session (a fixed unit so the test has a scale; the owner
  may set another before freezing).
- **Same-week:** the exit falls in the same week as the entry (not a Friday
  release). **Weekend hold:** the exit is after a weekend.

## 5. Costs

- **Spread:** $1.00 round trip (primary placeholder; no release-time spread
  measured). Measured 2026 spread at the 1:00 PM PT window (both the Fed entry
  and every exit): median $0.48, p90 $0.62.
- **Financing:** `studies/gold_rule_costs.held_nights`. Longs pay the US policy
  rate + 2.5% a year, shorts 2.5% (prerequisite P2, shared with GNC-1).
  - A Fed trade (1:00 PM PT to 1:00 PM PT next session) holds exactly one
    17:00 New York roll, **charged as 3 nights when the decision day is a
    Wednesday** (most FOMC decisions), 1 night otherwise. Confirmed by the
    owner (ruling A4): the triple charge is the real cost of holding through
    settlement and is not special-cased.
  - **Fed financing is reported separately** (mean financing in HRU and nights
    for Fed trades, and for NFP/CPI trades), not only inside the pooled mean,
    so the 3× Wednesday charge stays visible (A4).
  - NFP and CPI same-week trades hold one roll: 1 night, or 3 for a Wednesday
    release.
- Gross HRU and each cost stored per trade.

## 6. The test

- **One test:** same-week exits, all three event types pooled. Weekend holds
  reported separately and **never combined** with it.
- **Not in the multiple-testing family** (ruling A2): the family is GMW-1's
  two cells (α 0.0253). REFUTED here is deliberately uncorrected. If ruling A8
  restores a SUPPORTED verdict, PRC-1 rejoins: three tests, Šidák α =
  1 − (1 − 0.05)^(1/3) = 0.0170 (the owner's round-2 note gave 0.0171;
  Bonferroni would be 0.0167). §7's table uses α 0.0085 (the earlier six-test
  figure) and §11 the three-test α.
- **REFUTED** if the one-sided 90% upper bound of the mean (primary costs) is
  below **+0.15 HRU**. (The futility standard's +0.15 was set in stop-based R;
  carried over to HRU by convention, it is not the same bar. Owner to confirm
  or set an HRU threshold before freezing.) **INSUFFICIENT** under 20 trades.
  **INCONCLUSIVE** otherwise (not refuted; confirms nothing).
- **No re-runs.** The full run happens once.
- **Dependence on GNC-1:** both test continuation on the same events, so their
  results are not independent.

## 7. What the test can and cannot see

- **Available N, upper bound** (counted from the event files, not outcomes):
  same-week = 65 non-Friday CPI + 3 non-Friday NFP + 19 FOMC with a time = 87,
  before same-day skips, warm-up and missing bars. Weekend holds: 118.

| Trades | Smallest edge it could confirm (SD 1.2 / 2.0 / 3.0 HRU) | REFUTED if the mean is below (SD 1.2 / 2.0 / 3.0 HRU) |
|---|---|---|
| 87 | +0.415 / +0.692 / +1.038 HRU | −0.015 / −0.125 / −0.262 HRU |

- With no stop, SD is likely at the upper end. A rule with no edge would
  mostly read INCONCLUSIVE; one that clearly loses can read REFUTED.

## 8. Side results (reported; never change a verdict)

1. HRU before costs; the $0.50 spread.
2. Weekend holds, alone.
3. Each event type alone.
4. FOMC entered at the first 4-hour close (2:00 PM PT), as in the first draft.
5. Exit at the 17:00 New York close instead of 1:00 PM PT.
6. Direction by the 30-minute move instead of the entry close.
7. POSTED_TIME FOMC meetings excluded.
8. Counts: events, dropped FOMC meetings, same-day skips, zero moves, missing
   bars, financing nights by weekday.

## 9. Implementation decisions

As GNC-1 §8 where they apply (ATR, next session, missing bars, same-day
releases, FOMC table, financing, counts stage). Named mutations: the FOMC
entry taken at the 2:00 PM PT four-hour close; the FOMC exit at a different
clock time from its entry; NFP/CPI entry at the H4 bar after the release's
bar; direction from a bar's open instead of the price at the release;
weekend holds pooled into the primary; exit at the rollover; one blanket FOMC
time; financing at the exit instant; ATR including the current session.

## 10. Run discipline

1. The owner signs off; frozen in its own commit.
2. GNC-1's M15 fetch and check pass; P2 built.
3. Runner and tests committed; suite green; mutants caught.
4. Counts stage (no R), logged first.
5. One full run through `scripts/reality_run.py --no-env`; output verbatim to
   validation_log and `studies/post_release_continuation_result.md`.

## 11. Ruling A8: the measured effect in this spec's own unit (HRU)

**The question (owner, round 2):** expressed in PRC-1's own unit, is
the observed effect inside what PRC-1 can detect? If so, the "cannot confirm"
sentence is too strong.

**The basis:** PRC-1 has **no stop**. Its unit (HRU) is 0.5 × the daily ATR, the
simple mean true range of the 14 sessions completed before each event (§4). The
round-2 note converted dollars with stops of 0.15 and 0.30 × a median daily
range; that is not this spec's unit, and the conversion used one price level
for all events. Here each trade is divided by its own event's unit (median
unit across the 28 events: $50.29; median ATR $100.59).

**Measured on the 2026 candles** (`studies/gold_2026_release_reactions.py`,
ATR from the same OANDA daily candles; gross, then after a $1.00 spread):

| Definition | Group | N | Mean HRU | After $1 | SD HRU | t | Effect in SDs |
|---|---|---|---|---|---|---|---|
| Fed entry at the 2:00 PM PT four-hour close, exit 2:00 PM PT next session (the candle origin, §1) | same-week | 17 | +0.044 | +0.024 | 1.384 | +0.13 | +0.032 |
| same | weekend | 11 | −0.064 | −0.082 | 1.463 | −0.14 | −0.044 |
| same, exit 1:00 PM PT | same-week | 16 | +0.019 | −0.001 | 1.416 | +0.05 | +0.014 |
| Withdrawn pricing (Fed at 30 minutes), exit 2:00 PM PT; reference only | same-week | 17 | +0.460 | +0.440 | 1.446 | +1.31 | +0.318 |

(Dividing each trade by its own ATR shrinks the large-dollar trades of the
high-volatility weeks, so these t values differ from the dollar t values in
§1.)

**What PRC-1 can confirm at N ≈ 87** (three-test Šidák α 0.0170, 80% power):
an effect of at least **0.318 SD**, which is **about +0.44 HRU** at the measured SD
of about 1.4 HRU. Power if the true effect equalled:
- the candle origin's +0.032 SD: about 3% (no better than a false pass);
- 0.18 SD: about 33%; 0.30 SD: about 75%.

**Reading:**
- The candle-measured effect (+0.044 HRU gross, +0.024 HRU after a $1 spread) is
  about one tenth of what PRC-1 can confirm. Only the withdrawn pricing
  reaches the detection floor.
- PRC-1 *can* return SUPPORTED in principle, for an edge of about +0.44 HRU per
  trade or more. No measured version of this rule shows an effect near that.
  The rule as now specified (1:00 PM PT Fed entry) has never been measured.
- The measured SD (about 1.4 HRU) sits inside the 1.2–3.0 range assumed in §7.
- **Decided (ruling B1):** the family stays at two; the top sentence names the
  mechanism.

## 12. Ruling B3: the 90% upper bound of the 2026 effect (report for the owner's decision)

**The question:** does the 90% one-sided upper bound of the 2026 same-week
effect, in HRU, at the 2:00 PM PT Fed entry, reach the +0.44 HRU detection
floor (§11)? If it does, running PRC-1 is defensible; if not, PRC-1 is shelved
with GTP-1. **The owner decides; this section only reports.**

**Method:** the same per-trade HRU values as §11; `power_check.bootstrap_upper_bound`
(percentile bootstrap, 20,000 resamples, seed 7, the futility rule's method)
and a normal-approximation bound beside it.

| Group (Fed entry at the 2:00 PM PT close) | Exit | Costs | N | Mean | 90% upper (bootstrap) | 90% upper (normal) | Reaches +0.44? |
|---|---|---|---|---|---|---|---|
| **same-week (PRC-1's primary)** | 2:00 PM PT next session | gross | 17 | +0.044 | **+0.468** | +0.474 | yes |
| same-week | 2:00 PM PT | after $1 spread | 17 | +0.024 | **+0.449** | +0.455 | yes |
| same-week | 1:00 PM PT | gross | 16 | +0.019 | +0.462 | +0.473 | yes |
| same-week | 1:00 PM PT | after $1 spread | 16 | −0.001 | +0.443 | +0.454 | yes (by 0.003) |
| all 28 (weekend holds included) | 2:00 PM PT | gross | 28 | +0.002 | +0.334 | +0.338 | no |
| all | 2:00 PM PT | after $1 spread | 28 | −0.018 | +0.316 | +0.319 | no |

**What bears on the decision:**
- The primary group's bound reaches the floor by **+0.03 HRU gross** and
  **+0.01 HRU after a $1 spread**; at the 1:00 PM PT exit after costs, by
  0.003. It is a near-tie, not a clear clearance.
- **N = 17 (16 at the 1:00 PM exit) is below 20**, the framework's minimum
  for reporting a bootstrap bound (`power_check` docstring; M3): at small N on
  skewed data the percentile bootstrap is unreliable. The normal bound gives
  the same reading.
- The floor itself rests on an assumed N of 87 and the measured SD of about
  1.4 HRU; a different SD moves it proportionally.
- Including the 11 weekend holds (all 28) puts the bound at +0.33, below the
  floor; PRC-1's design keeps them apart.
- None of these measure the rule as specified (Fed entry at 1:00 PM PT; top of
  the spec).

Inputs: `events.json` (per-event ATR, OANDA daily candles) and the verbatim
output of `studies/gold_2026_release_reactions.py`; the computation and its
output are in `docs/reports/gold_spec_remediation_2026-11-16.md`, Appendix G.
