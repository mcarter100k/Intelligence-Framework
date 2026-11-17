# Spec GMW-1: gold's 4–7 AM PT window (pre-registration draft, amended)

**Status:** DRAFT, amended 2026-11-16 after independent review and the owner's
remediation brief. Not frozen and not run. Nothing in it has been computed on
2006–2013 data. **It does not run until the owner signs off.** It freezes at
a later commit; any change after freezing is a new id (GMW-2) with a fresh
run.

**Free zone:** a study, its tests, and data outside the repo. No protected
module, no ledger, no SEALED EXAM bar.

## Amendments

- 2026-11-16: §1 rewritten. The claim "by 7 AM the day's high is already in
  on 67% of days" is removed as a reason. Under a driftless random walk with
  17 of gold's 23 trading hours elapsed, P = (2/π)·asin(√(17/23)) = 65.87%;
  shaped to gold's own hourly volatility the chance baseline is 66.2%
  (`docs/reports/timing_claims_sweep.md`). The observed 67.0% is +0.6 standard
  errors from chance and carries no information. The "4–7 AM is most of the
  day" wording is corrected to what the session study measured.
- 2026-11-16: §3.4 exit moved from 2:00 PM PT (17:00 New York, the daily
  rollover) to **1:00 PM PT**, the close of the H1 bar opening at 12:00 PT.
  The old wording "flat before 5 PM New York" was false: the old exit was the
  rollover itself. Measured spreads (OANDA bid/ask, Sep 14 – Nov 13, 2026):
  the 5-minute candle closing 1:00 PM PT median $0.48 (p90 $0.62) against
  $0.46 (p90 $0.60) mid-session; the candle closing 2:00 PM PT median $0.66
  (p90 $1.54). 1:00 PM PT is not materially wider than mid-session.
- 2026-11-16: §3 B1 and B2 now use **the same stop distance** (§3.3), so both
  cells trade exactly the same days. Before, B2's stop sat just beyond the
  extreme the close was usually near, and the minimum-risk skip removed most
  B2 days that closed near their extreme.
- 2026-11-16: §3.4 the risk cap stays for the headline result; an uncapped
  result is now a required side result, with the share of trades and of total
  R the cap removes.
- 2026-11-16: §3.4 two stop floors are run: 0.15 and 0.30 daily ATR. **Binding:
  if a cell passes at 0.15 and fails at 0.30, the 0.30 result is the verdict**,
  because 0.30 (`MIN_STOP_ATR_MULTIPLE`, `setup_check.py:58`) is the only
  version the existing tools can trade.
- 2026-11-16: §3.5 a stop bar that opens beyond the stop fills at its open (the
  first traded price beyond the stop), not at the stop.
- 2026-11-16: §4 the per-test threshold became the Šidák-corrected one-sided
  α for the whole family, replacing the within-spec Bonferroni (first set at
  0.0073 for seven tests, then 0.0085 for six (R6), now 0.0253 for two (A2)).
- 2026-11-16: §4 the two verdict thresholds are replaced by **one tradeable-edge
  line at +0.05R**, used for both SUPPORTED and REFUTED, so the two can never
  both be true (§4.2).
- 2026-11-16: §4.3 exam rule recorded: **if more than one test in the family
  passes, GMW-1 is the one that goes to the sealed exam.**
- 2026-11-16: §7 the news-day side check is removed. It measured nearly the
  same question as GNC-1 on the same events before GNC-1 runs.
- 2026-11-16: §6 power restated at SD 1.2, 2.0 and 3.0R at the Šidák α. The
  owner asked for power from the empirical SD of R on the STUDY sample; that
  SD exists only by running the rule, which the brief forbids and which would
  break pre-registration. Not computed (see the remediation report).
- 2026-11-16: §8 every detail left to implementation is now decided in the
  spec (within-bar order, pooling, ATR, missing bars, mutations).
- 2026-11-16 (owner ruling R6): the family is the six tests that can run and
  produce a pass; GTP-1 is shelved and not counted. Per-test
  α = 1 − (1 − 0.05)^(1/6) = 0.0085 (was 0.0073 for seven). Superseded by A2
  below.
- 2026-11-16 (owner ruling R7): the +0.05R line applies to GMW-1 only.
- 2026-11-16 (owner ruling A2, round 2): the family is **GMW-1's two cells
  only**. GNC-1 and PRC-1 have no SUPPORTED verdict, so they cannot produce a
  false pass and do not belong in the family the correction protects.
  α = 1 − (1 − 0.05)^(1/2) = **0.0253** (was 0.0085 for six). Boundaries and
  power recomputed. REFUTED verdicts are deliberately uncorrected (§4.1).
- 2026-11-16: §2 costs labelled: $0.50 is a placeholder, not shown to be
  conservative for 2006–2013 (no spread from that era has been measured); the
  0.012% secondary is optimistic for that era.
- 2026-11-16 (round 3, for signature): two gaps found when preparing this
  document for the owner's signature, each closed by a marked **[PROPOSED]**
  passage the owner can accept or strike: §3.4 the verdict is computed under
  floor B only (the two-floor rule named only the pass-at-A, fail-at-B case
  and left the reverse open, a second look); §4.3 the exam rule is restated
  for a two-cell family (it said "GMW-1 goes" without naming a cell). §6's
  "about +0.25R" at SD 3.0 corrected to +0.19–0.22R (it dated from α 0.0073).
- 2026-11-16: §1 a confound is named: 7:00 AM PT is 10:00 New York, when US
  10:00 releases (ISM, consumer sentiment) land and, in most weeks, the London
  afternoon gold fix (15:00 London; reviewer-stated, NOT CHECKED here). A
  secondary entry at 8:00 AM PT is added.

## What you are deciding (plain English)

- **The question:** gold does a lot of its moving between 4 and 7 AM Pacific.
  At 7 AM, does that morning move tend to keep going until 1 PM, or to give
  some back? B1 bets it keeps going; B2 bets it reverses.
- **What a result lets you do:**
  - **SUPPORTED:** the rule earns one look at the sealed 2014–2021 data, and
    nothing more. Even then it needs a venue, real costs and a forward paper
    log before money (gold plan Phases E, G).
  - **REFUTED:** the idea is retired. You stop thinking about trading the
    morning move this way.
  - **INCONCLUSIVE:** the data can't tell. Nothing changes.
- **How long to confirm it forward:** one trade a day, so 20 paper trades take
  about a month.
- **Decisions in front of you:** whether to run with placeholder costs, and
  whether to run before the gold plan's Phase E (venue costs) and team ruling
  T1 (the sealed exam). A STUDY run never touches the sealed exam.

## 1. The idea, and why it might work

**What the gold session study measured (2021–2026, `studies/gold_session_report.md`):**
- the busiest hours are 12:00–15:00 UTC (4–7 AM PST, 5–8 AM PDT), peaking at
  13:00 UTC; the busiest hour moves 2.84 times the quietest;
- the London/New York block (12:00–16:00 UTC, 4–8 AM PST) covers a median 67%
  of the day's range.

**Against chance (`docs/reports/timing_claims_sweep.md`):**
- the busy hours are real: 12:00–15:00 UTC averages $13.45 an hour against
  $7.78 for the other hours;
- the block's 67% share is above what gold's own volatility shape gives by
  chance (58.9%), by 10.6 standard errors;
- "the day's high is set by 7 AM PST" (67.0%) equals chance (66.2%);
- "the day's low is set by 7 AM PST" (73.1%) is above chance (65.9%), by 6.0
  standard errors.

**The two readings, both tested, neither chosen in advance:**
- **continuation (B1):** a strong morning shows where the day's money is
  going, so the move carries on. Untested on gold.
- **fade (B2):** the morning move overshoots and gives some back. Untested on
  gold. Its earlier support (the 67% high statistic) is UNINFORMATIVE: it
  equals chance.

**Why this is a fair test:** the session facts come from 2021–2026; the
verdict comes from 2006–2013, which the session study never touched.

**Prior work:** no gold rule has been tested. On the GBP pairs, breakout rules
(R43, R44, R46) and fades of levels (R14) failed.

**The confound named in advance:** 7:00 AM PT (10:00 New York) is when US
10:00 releases land, and in most weeks the London afternoon gold fix. A
result driven by that minute may not be tradeable at that print. The 8:00 AM
PT entry (§7) shows whether the result depends on it.

## 2. Data and costs

- **Prices:** `~/intel_study_archives/research_archive_legs/XAU_USD_H1.csv`
  (sha256 `eabec6652e055540b256aa743971a1a5aa5cbb459e94b4887da6f28b8e02a4be`)
  and `XAU_USD_D.csv` (`6202a13d86459d2d3453c31ea9ddf40a3aca44243a6d4ff75bf3d0c165d0e3ca`).
  The runner refuses other bytes.
- **The verdict comes from STUDY only:** 2006-03-21 → 2013-12-30.
- **USED (2021-04-26 → 2026-09-09):** the same frozen rule as a learning check,
  reported separately. This is also the span the idea came from.
- **Never read:** 2014-01-01 → 2021-04-25. FORWARD rows exist in the files and
  are skipped by their span label; rows dated in the sealed span are refused.
- **Hours:** every bar's open is converted to Pacific time with the zone rules
  (America/Los_Angeles), bar by bar. The session study used fixed UTC hours
  labelled as winter time; this spec follows the Pacific clock by choice.
- **Spread (placeholders, all labelled):**
  - primary **$0.50** round trip. The measured 2026 quote is $0.46–0.48 at
    these hours; whether $0.50 is conservative for 2006–2013 is NOT CHECKED;
  - stress **$1.00**;
  - secondary **0.012% of the entry price**, optimistic for 2006–2013 (about
    $0.07–0.23 at that era's prices).
- **Financing:** `studies/gold_rule_costs.held_nights`. Every trade closes
  before 5 PM New York, so it should charge 0 nights; the runner asserts it.
- **Stored per trade:** gross R and each cost component, so a venue's real
  costs can be applied later as a declared re-costing, not a new test.

## 3. The rule

### 3.1 The window

- **Window bars:** the three H1 bars opening at 04:00, 05:00 and 06:00 PT.
- **Window move:** the 06:00 bar's close minus the 04:00 bar's open. A move of
  exactly 0 is no trade (counted).
- **Window high and low:** the highest high and lowest low of the three bars.
- **Daily ATR (authoritative):** the simple mean true range of the 14 daily
  sessions completed **before** the day's session, found by bisecting session
  days (`history_study_convert.session_day`) as
  `first_pullback_study.bar_context` does. The day's own session is never
  included, even though gold's daily candle is stamped at its open.

### 3.2 Direction and entry

- **B1 (continuation):** the window move's direction. **B2 (fade):** the
  opposite.
- **Entry:** 7:00 AM PT, at the 06:00 bar's close, for both cells.

### 3.3 Stop (identical distance in both cells)

- **Stop distance d** = (window high − window low) + 0.05 × ATR, measured from
  the entry: a long's stop is entry − d, a short's is entry + d.
- Both cells therefore trade the same days with the same risk.

### 3.4 Floors, cap, exit

- **Floor (verdict) [PROPOSED 2026-11-16 for signature]:** skip and count if
  d < 0.30 ATR (floor B, `MIN_STOP_ATR_MULTIPLE`). **Every verdict is computed
  under floor B only.** Floor A (d ≥ 0.15 ATR) is run as a side result and
  never changes a verdict. (This replaces the rule "a cell that passes under
  floor A and fails under floor B takes floor B's result", which left the
  reverse case open. If struck, the owner names the verdict for a cell that
  fails under A and passes under B.)
- **Cap (headline):** skip and count if d > 1.0 ATR. **Required side result:**
  no cap, with the share of trades and of total R the cap removes.
- **Exit:** 1:00 PM PT, at the close of the H1 bar opening at 12:00 PT. If that
  bar is missing, the trade is skipped and counted (not exited elsewhere).
- **Stopped:** −1R, checked on every bar from the 07:00 bar to the 12:00 bar.

### 3.5 Within-bar order and gaps

- Within one H1 bar the order of high and low is unknown. If a bar touches the
  stop, the trade is stopped on that bar (conservative), whatever else the bar
  did.
- A bar that **opens beyond the stop** fills at its open: R = (open − entry) ÷ d
  for a long, which can be below −1R. This replaces "always −1R".

### 3.6 Grouping

- Each cell pools its longs and shorts into one test. Longs and shorts are
  reported separately as side results with no verdict.
- One trade a day, closed the same day: each day is its own episode.
- Missing window bars (holidays, gaps) skip the day; missing bars inside the
  holding window are counted and listed.

## 4. Verdicts

### 4.1 The family and the threshold

**The family (two tests, owner ruling A2, 2026-11-16):**
1. GMW-1 B1 (continuation)
2. GMW-1 B2 (fade)

The family is every test that can return SUPPORTED, because only those can
produce a false pass. GNC-1 and PRC-1 cannot return SUPPORTED and are not in
it; GTP-1 is shelved. If any of them gains a SUPPORTED verdict (or GTP-1 is
unshelved), it joins the family and every threshold recomputes. **Per-test
one-sided α = 1 − (1 − 0.05)^(1/2) = 0.0253** (exactly 0.025321; z = 1.955).

**REFUTED verdicts are deliberately uncorrected** for the number of tests: a
false refute shelves an idea rather than trading one, and a shelved spec stays
recoverable.

### 4.2 One line for pass and fail

- **m = +0.05R per trade** after primary costs.
- **SUPPORTED** if the one-sided 97.47% lower bound of the mean is above m,
  **and** the mean without the best 1% of trades (rounded up) is above 0.
- **REFUTED** if the one-sided 90% upper bound (the futility standard) is
  below m.
- **INCONCLUSIVE** otherwise. **INSUFFICIENT** under 20 trades.
- Because the 97.47% lower bound is always below the 90% upper bound, a result
  can never be both SUPPORTED and REFUTED.
- Bounds: percentile bootstrap, 20,000 resamples, seed 7, plus a block
  bootstrap by calendar month as a cross-check (side result).

Decision boundaries on the mean, by N and SD (normal approximation):

| N | SD | SUPPORTED if mean above | REFUTED if mean below |
|---|---|---|---|
| 1,500 | 1.2R | +0.111R | +0.010R |
| 1,500 | 2.0R | +0.151R | −0.016R |
| 1,500 | 3.0R | +0.201R | −0.049R |
| 1,900 | 1.2R | +0.104R | +0.015R |
| 1,900 | 2.0R | +0.140R | −0.009R |
| 1,900 | 3.0R | +0.185R | −0.038R |

### 4.3 Exam rule

**[PROPOSED 2026-11-16 for signature]** If exactly one cell is SUPPORTED,
that cell goes to the sealed exam. If both B1 and B2 are SUPPORTED (opposite
bets on the same days with the same stop distance both paying after costs),
that is treated as a defect in the test, not an edge: neither goes to the exam
and the run is reviewed. The sealed exam still needs team ruling T1 and real
venue costs.

## 5. Expected trades

About 2,020 STUDY sessions (C1 counted 2,024 daily bars from 2006-03-20), minus
missing windows, zero moves, floor and cap skips. Not counted before freezing.

## 6. Power (at the Šidák α = 0.0253)

| Trades | SD 1.2R: smallest edge / power at +0.15R | SD 2.0R | SD 3.0R |
|---|---|---|---|
| 1,500 | +0.087R / >99% | +0.144R / 83% | +0.217R / 49% |
| 1,900 | +0.077R / >99% | +0.128R / 91% | +0.192R / 59% |

N needed for +0.15R at 80% power: 501 (SD 1.2), 1,390 (SD 2.0), 3,128 (SD 3.0).
With d floored at 0.15 ATR, single trades can reach +5R or more, so SD 2–3 is
the realistic range. At SD 3.0 this test can confirm only edges of about
+0.19R (N 1,900) to +0.22R (N 1,500).

## 7. Side results (reported; never change a verdict)

1. R before costs; the $1.00 stress spread; the 0.012% spread.
2. The uncapped result, with the share of trades and of total R the cap
   removes.
3. Floor A (d ≥ 0.15 ATR) results beside the floor-B verdict.
4. Entry at 8:00 AM PT instead of 7:00 (the fix/release confound).
5. Exits at 10:00 AM and 12:00 PM PT.
6. Only days whose window move is at least 0.5 ATR, and only days below it.
7. The owner's management (`foundation/risk_and_execution.md`): stop to
   breakeven and close 50% at +1R, trail 0.5R behind price from +1.5R, still
   flat by 1:00 PM PT.
8. Longs and shorts separately; by year; by the 6-month trend's sign.
9. Counts: days, missing windows, zero moves, floor and cap skips, stops,
   gap fills, timed exits.
10. Per-trade cost in R, and the share of trades whose cost exceeds 0.2R.

## 8. Implementation decisions recorded here

| Detail | Decision |
|---|---|
| Within-bar order | a touched stop counts first (§3.5) |
| Gap through the stop | fill at the bar's open (§3.5) |
| Pooling | per cell, longs and shorts pooled; sides as side results (§3.6) |
| Floor | verdict under floor B (d ≥ 0.30 ATR); floor A a side result (§3.4, proposed) |
| Both cells SUPPORTED | treated as a test defect; neither to the exam (§4.3, proposed) |
| ATR | simple 14-session mean of completed sessions, by session-day bisect (§3.1) |
| Missing window bar | skip the day, count it |
| Missing exit bar | skip the trade, count it |
| Missing bar inside the hold | count and list; the stop is checked on the bars present |
| Financing | `gold_rule_costs.held_nights`; asserted 0 |
| FORWARD rows | skipped by span label; sealed-span dates refused |
| Counts stage | prints counts only, and cannot trigger an edit to this spec |

**Named mutation set (each must be caught by the tests before freezing):**
1. window found in UTC instead of Pacific time;
2. exit at the 13:00 PT bar (the rollover) instead of the 12:00 PT bar;
3. B2's stop distance different from B1's;
4. ATR including the day's own session;
5. a gap through the stop filled at the stop;
6. the verdict computed under floor A instead of floor B;
7. the verdict using a bound other than the two-test Šidák bound (97.47%);
8. SUPPORTED and REFUTED allowed together (two thresholds);
9. FORWARD or sealed-span rows read;
10. a missing exit bar exited at an earlier bar.

## 9. Tests before the run

`tests/test_gold_morning_window.py`, on synthetic H1 bars: the window in
Pacific time across a daylight-saving change; a missing window bar; B1 and B2
on a planted up morning with identical d; a stop on the entry hour; a gap
through the stop; the 1:00 PM exit; floors and cap; the verdict under floor B only;
the ATR excluding the current session (a huge-range current session leaves
ATR unchanged); `held_nights` = 0; the verdict boundaries with m = +0.05R and
the Šidák bound (α 0.0253); exam-span and wrong-hash refusals; plus every named mutant.

## 10. Run discipline

1. The owner signs off; the spec is frozen in its own commit.
2. The runner and tests are committed; the suite is green; the named mutants
   are all caught.
3. **Counts stage:** days, skips and trades per cell, no R. Logged first.
4. **Full run, once,** through `scripts/reality_run.py --no-env`. Output goes
   verbatim to validation_log and `studies/gold_morning_window_result.md`, with
   a finding number, whatever it says.
