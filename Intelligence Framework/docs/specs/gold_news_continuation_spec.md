# Spec GNC-1: does gold's first 30 minutes after big US news carry on? (pre-registration draft, amended)

**This test can return REFUTED, INCONCLUSIVE or INSUFFICIENT. It cannot
confirm an edge at a tradeable size.** (Owner rulings R7 and A1, 2026-11-16.
Its smallest detectable edges are +0.40R to +1.01R at 92 events. INCONCLUSIVE
is the named verdict for 20 or more trades that are not refuted; it confirms
nothing. The Fed cell is INSUFFICIENT before the run (A7).)

**Status:** DRAFT, amended 2026-11-16 after independent review and the owner's
remediation brief. Not frozen and not run. Nothing in it has been computed on
2006–2013 data. **It does not run until the owner signs off.** It freezes at
a later commit; any change after freezing is a new id (GNC-2) with a fresh
run.

**Free zone:** a study, its tests, and data outside the repo. No protected
module, no ledger, no SEALED EXAM bar.

## Amendments

- 2026-11-16: §1 the 2026 counts are now reproduced in the repo from our own
  candles: `studies/gold_2026_release_reactions.py` with its sourced date table
  `studies/us_events_2026.csv` (output in the remediation report). The
  reproduction gives the same counts: 8 of 10 jobs reports, 6 of 11 CPI, 6 of
  7 Fed decisions, 20 of 28 in all.
- 2026-11-16: §1 a chance level is printed beside those counts. If the first
  30 minutes simply don't continue, the 30-minute direction still matches the
  next close about 59–65% of the time, because the first move is part of the
  total (reviewer's arithmetic). At 0.62, 20 or more of 28 happens with
  probability 0.20, so the 2026 pattern is consistent with no continuation.
- 2026-11-16: §2 FOMC statement times now come from a per-meeting data table,
  `studies/fomc_statement_times_2006_2013.csv`, one source per row. 19 of the
  63 scheduled meetings in the window have a sourced, derived or posted time;
  **44 have none and are dropped and listed**. The C-FOMC cell will therefore
  have at most 19 events and is expected to be INSUFFICIENT.
- 2026-11-16: §3.2 the exit moved from the next session's close (17:00 New
  York, the rollover) to **1:00 PM PT of the next session**.
- 2026-11-16: §3.3 financing uses `studies/gold_rule_costs.held_nights`: a
  position closed before the 17:00 roll is not charged for it. Under the old
  shared helper a Tuesday CPI trade exited Wednesday at 17:00 would have been
  charged 4 nights (Tuesday 1 + Wednesday 3); now 1.
- 2026-11-16: §3.2 a stop bar that opens beyond the stop, including after a
  weekend, fills at its open, not at the stop.
- 2026-11-16: §3.2 two stop floors (0.15 and 0.30 ATR) are run; **binding: a
  cell that passes at 0.15 and fails at 0.30 takes the 0.30 result.**
- 2026-11-16: §3.2 the 1.0 ATR cap stays for the headline result; the uncapped
  result is a required side result, with the share of trades and of total R
  the cap removes.
- 2026-11-16: §5 the family-wide Šidák threshold and a +0.05R line were first
  applied here (α 0.0073, seven tests). **Superseded the same day by owner
  rulings R6 and R7:** the family is six named tests (α 0.0085), the +0.05R
  line is for GMW-1 only, and this spec has no SUPPORTED verdict. REFUTED uses
  the futility standard (90% upper bound below +0.15R).
- 2026-11-16: §5 exam rule: **if more than one test in the family passes,
  GMW-1 goes to the sealed exam, not GNC-1.**
- 2026-11-16: §2 the 15-minute data check now has a pass criterion and can
  fail (§2.3).
- 2026-11-16: §8 every implementation detail is decided in the spec.
- 2026-11-16 (owner ruling A1, round 2): INCONCLUSIVE is a named verdict for
  20 or more trades that neither refute nor support.
- 2026-11-16 (owner ruling A2): GNC-1 is **not in the multiple-testing
  family** (it cannot return SUPPORTED, so it cannot produce a false pass).
  REFUTED is deliberately uncorrected: a false refute shelves an idea rather
  than trading one, and shelved specs stay recoverable.
- 2026-11-16 (owner ruling A7): the 44 missing Fed statement times are not
  pursued. **C-FOMC is declared INSUFFICIENT before the run**: 19 scheduled
  meetings have a sourced, derived, secondary or posted time, below the
  20-trade minimum, and 44 have none (a sourcing gap, not a market result).
  The run covers C-NFP and C-CPI.
- 2026-11-16: §5 a drift control is added: "always long on the same event
  days", same entry, exit and costs.

## What you are deciding (plain English)

- **The question:** when a jobs report, CPI or Fed decision lands, does gold's
  direction in the first 30 minutes keep going until the next afternoon?
- **What this test can tell you:** with fewer than 100 events per type, only a
  very large edge could show up (about +0.4R or more). It can rule the idea
  out; it can't confirm a modest edge. The Fed cell is likely too small to
  read at all.
- **REFUTED** retires the idea. **INCONCLUSIVE** (not refuted) changes
  nothing and confirms nothing. **INSUFFICIENT** means too few events. There
  is no SUPPORTED verdict (ruling R7).
- **Forward confirmation:** about 12 jobs reports a year, so 20 paper trades
  take about 2 years for that cell alone.
- **Decision in front of you:** sign-off to run C-NFP and C-CPI (the Fed
  cell is INSUFFICIENT by ruling A7).

## 1. The idea, and where it came from

**When a jobs report, CPI or Fed decision lands, take the direction gold moved
in the first 30 minutes, and hold until 1:00 PM PT the next session.**

- **Where it came from (M6):** the 2026 releases, measured on OANDA 5-minute
  candles, now reproduced by `studies/gold_2026_release_reactions.py`. The
  30-minute direction held to the next session's close 8 of 10 times after
  jobs reports, 6 of 11 after CPI and 6 of 7 after Fed decisions. These 28
  events are **learning data, never evidence**, and the pattern is consistent
  with chance (amendments above).
- **The jobs report is the hypothesis (C-NFP).** CPI and Fed decisions are
  their own cells so the best-looking one isn't chosen after the fact.
- **A reason it might hold, untested:** a big surprise changes expected rates
  for days. **A reason it might not:** about half of release moves on the GBP
  pairs gave themselves back within 3 days (R25).

## 2. Data

### 2.1 Events

- `studies/us_events_2005_2013.csv`, scheduled rows on or after the 2006-03-21
  session: **93 NFP, 93 CPI, 63 FOMC** (counted from the file). Every NFP and
  CPI row is 8:30 AM ET.
- **FOMC times:** `studies/fomc_statement_times_2006_2013.csv`. Rows with status
  SOURCED, DERIVED, SOURCED_SECONDARY or POSTED_TIME are used (19 scheduled
  meetings); POSTED_TIME rows (four 2012 meetings at a scheduled 12:30 PM, Fed
  pages showing posting times of 12:20–12:35) are also reported separately.
  UNSOURCED rows (44 scheduled) are dropped and listed.
- **Same-day releases:** CPI and FOMC share five days (2008-09-16,
  2008-12-16, 2009-03-18, 2009-12-16, 2013-10-30). The CPI trade is taken; the
  FOMC event that day is skipped and listed.

### 2.2 Prices

- XAU_USD **M15** mid candles for the STUDY span, fetched once by a gold
  version of `studies/m15_study_data.py` through the embargo-guarded
  `history_study_gate_s3.fetch`, into `~/intel_study_archives/m15_study/`, with
  sha256 recorded before any statistic.
- The daily ATR comes from `research_archive_legs/XAU_USD_D.csv`
  (`6202a13d86459d2d3453c31ea9ddf40a3aca44243a6d4ff75bf3d0c165d0e3ca`).
- The verdict comes from STUDY only (2006-03-21 → 2013-12-30). The sealed span
  is refused by the fetch and the runner. No USED check in this spec.

### 2.3 The 15-minute data check (must pass before any statistic)

- Each hour of the archive's gold H1 (sha256
  `eabec6652e055540b256aa743971a1a5aa5cbb459e94b4887da6f28b8e02a4be`) is rebuilt
  from its four M15 bars: open of the first, high and low across the four,
  close of the last.
- **Tolerance:** $0.05 on each of open, high, low and close. OANDA prints gold
  to 3 decimals; GBP/AUD's 0.5-pip tolerance in `m15_study_data.compare` does
  not apply to gold and is not used.
- **Pass:** at least 99% of comparable hours within tolerance, and every
  mismatch listed with its explanation (weekend fold, partial hour, missing
  bar). **Below 99%, the study stops** and nothing is computed.
- A test plants a mismatch and the check must report it.

## 3. The rule

### 3.1 The first 30 minutes

- **Release time T:** 8:30 AM ET (NFP, CPI) or the table's FOMC time,
  converted to UTC with the New York zone rules.
- **Price at the release:** the open of the M15 bar opening at T.
- **The window:** the M15 bars opening at T and T + 15 min. If either is
  missing, the event is skipped and listed.
- **Direction:** the second bar's close minus the price at the release. Up =
  long. Exactly zero = no trade (counted).

### 3.2 Entry, stop, exit

- **Entry:** T + 30 min, at the second bar's close.
- **Daily ATR (authoritative):** the simple mean true range of the 14 daily
  sessions completed before the event's session, by session-day bisect; the
  event's own session is never included. Events before 15 completed sessions
  exist (the first NFP of the span) are skipped and counted.
- **Stop:** beyond the window's opposite extreme: a long's stop is the window
  low − 0.05 × ATR.
- **Floors (both run):** skip and count if risk < 0.15 ATR (floor A) or
  < 0.30 ATR (floor B). **Binding:** pass at A and fail at B means the B
  result is the verdict.
- **Cap (headline):** skip and count if risk > 1.0 ATR. **Required side
  result:** no cap, with the share of trades and of total R removed.
- **Exit:** 1:00 PM PT in the **next session**, the next weekday daily session
  present in the data (session key `history_study_convert.session_day`): the
  close of the M15 bar ending at 1:00 PM PT. A Friday release exits Monday. If
  that bar is missing, the trade is skipped and counted.
- **Stopped:** −1R, checked on every M15 bar after the entry bar. A bar that
  opens beyond the stop (a weekend or daily-break gap included) fills at its
  open, which can be worse than −1R.
- Within one M15 bar, a touched stop counts first.

### 3.3 Costs

- **Spread:** $1.00 round trip (primary placeholder: no venue's spread at
  release time has been measured; the 2026 quote at the 1:00 PM PT exit was a
  median $0.48). Secondary $0.50.
- **Financing:** `studies/gold_rule_costs.held_nights`. Longs pay the US policy
  rate + 2.5% a year, shorts pay 2.5% (prerequisite P2: the policy-rate history
  from the archive's FRED files `fred_DFEDTAR.csv` / `fred_DFEDTARU.csv`, hashed,
  before the runner is written). A secondary counts Friday 3 times instead of
  Wednesday (venue convention unverified).
- **Stored per trade:** gross R and each cost component.

## 4. Episodes

Each event is its own episode; trades end by 1:00 PM PT the next session, and
same-day pairs are resolved by §2.1.

## 5. Cells and verdicts

- **Cells:** C-NFP (the hypothesis) and C-CPI are run. **C-FOMC is
  INSUFFICIENT by declaration** (ruling A7: 19 meetings with a time, 44
  without; not computed). NFP and CPI pooled is reported with no verdict.
- **Not in the multiple-testing family** (ruling A2): the family is GMW-1's
  two cells (α 0.0253), the tests that can return SUPPORTED. REFUTED here is
  deliberately uncorrected. §6 shows the smallest edge this test could have
  confirmed at α 0.0085 (the earlier six-test figure), only to show why it has
  no SUPPORTED verdict; at a looser α the conclusion is the same.
- **REFUTED** if the one-sided 90% upper bound of the mean (primary costs) is
  below +0.15R (the futility standard). **INSUFFICIENT** under 20 trades.
  **INCONCLUSIVE** otherwise (not refuted; confirms nothing).
- **Baselines (reported):** a coin-flip direction on the same events (it comes
  out at about minus costs); "always long" on the same events (the drift
  control); the same rule at the same clock time on non-event days of the same
  weekday within ±28 days (note: those days still carry other 8:30 releases
  such as weekly jobless claims).
- **Exam:** this spec cannot send a rule to the sealed exam (no SUPPORTED
  verdict); GMW-1 has the exam if it passes.

## 6. What the test can and cannot see (at the Šidák α = 0.0085)

| Trades | Smallest edge it could confirm (SD 1.2 / 2.0 / 3.0R) | REFUTED if the mean is below (SD 1.2 / 2.0 / 3.0R) |
|---|---|---|
| 19 (C-FOMC, sourced) | +0.889 / +1.481 / +2.222R | −0.203 / −0.438 / −0.732R |
| 60 | +0.500 / +0.833 / +1.250R | −0.049 / −0.181 / −0.346R |
| 92 (C-NFP, C-CPI) | +0.404 / +0.673 / +1.010R | −0.010 / −0.117 / −0.251R |

N needed to confirm +0.15R: 667 / 1,853 / 4,168. **No cell can confirm a
realistic edge**, which is why there is no SUPPORTED verdict. REFUTED
thresholds use the normal approximation 0.15 − 1.2816 × SD ÷ √N.

## 7. Side results (reported; never change a verdict)

1. R before costs; the $0.50 spread; Friday-triple financing.
2. The uncapped result; floor A beside floor B.
3. Exit at the same session's 1:00 PM PT instead of the next.
4. Only events whose 30-minute move is at least 0.25 ATR, and those below.
5. Longs and shorts; by year; before and after mid-2008.
6. The 30-minute direction held to the exit, as a count, printed beside the
   chance level (§1).
7. The owner's management: breakeven and 50% off at +1R, trail 0.5R from
   +1.5R.
8. POSTED_TIME FOMC meetings excluded.
9. Counts: events, dropped FOMC meetings, same-day skips, missing windows,
   zero moves, floor and cap skips, stops, gap fills.

## 8. Implementation decisions recorded here

| Detail | Decision |
|---|---|
| Within-bar order | a touched stop counts first |
| Gap through the stop | fill at the bar's open |
| Pooling | one cell per event type; sides as side results |
| ATR | 14 completed sessions by session-day bisect; current session excluded |
| "Next session" | next weekday daily session present in the data |
| Missing window or exit bar | skip and count |
| Holiday on the exit day | the next session present in the data |
| Same-day releases | the earlier release is traded; the later skipped (§2.1) |
| FOMC times | the data table only; no constant in code |
| 15-minute check | $0.05 tolerance, 99% pass rate, otherwise stop (§2.3) |
| Financing | `gold_rule_costs.held_nights` |
| Counts stage | counts only; cannot trigger an edit to this spec |

**Named mutation set:**
1. one blanket FOMC time instead of the table;
2. exit at the rollover (17:00 New York) instead of 1:00 PM PT;
3. financing counted at the exit instant;
4. a weekend gap through the stop filled at the stop;
5. ATR including the current session;
6. direction measured from the T bar's close instead of the price at T;
7. the 15-minute check passing with a planted mismatch;
8. a missing exit bar exited elsewhere;
9. same-day FOMC traded alongside CPI;
10. a SUPPORTED verdict produced at all (this spec has none).

## 9. Run discipline

1. The owner signs off; the spec is frozen in its own commit.
2. P2 (policy rates) is built and hashed; the M15 data is fetched, hashed and
   passes §2.3, with the check's output logged.
3. The runner and tests are committed; the suite is green; every named mutant
   is caught.
4. **Counts stage:** events, skips and trades per cell, no R. Logged first.
5. **Full run, once,** through `scripts/reality_run.py --no-env`. Output goes
   verbatim to validation_log and `studies/gold_news_continuation_result.md`,
   with a finding number, whatever it says.
