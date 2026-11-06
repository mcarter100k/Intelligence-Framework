# Spec: session movement study (descriptive, GBP/AUD and GBP/JPY, STUDY partition)

**Status:** FROZEN 2026-11-05, before any movement statistic is computed.
This file is committed before the runner that computes Q1–Q5 exists. The
runner implements exactly what is written here, runs once, and its output
goes into `studies/session_movement_report.md` and validation_log verbatim,
whatever it says.

**Free zone:** `studies/`, tests and data outside the repo. No protected
module is edited, no ledger is written, and no live-path behavior changes.

---

## 1. Purpose and limits

- **What it measures:** WHEN these two pairs move during the day: whether
  movement is concentrated in particular hours, and by how much.
- **What it cannot say:** whether day trading these pairs makes money. It
  has no entry, no exit, no direction, no costs and no strategy. The report
  must not drift into that claim. Whether to day trade is the team's call.
- **Why it comes first:** concentration of movement in particular hours is
  the precondition for day trading being viable at all. If movement is
  spread evenly through the day, there is nothing session-specific to trade.
- **No null hypothesis:** a descriptive study has none. Its discipline is
  this frozen question list (§4). Exactly these statistics are computed,
  and no others. Anything else that looks interesting is recorded as a
  hypothesis (§8) for a future pre-registered run, never computed in this one.

## 2. Data (all verified in Phase 1, commit 0a38135)

| Series | Source | Span (bar opens) | sha256 |
|---|---|---|---|
| GBP_AUD H1 | OANDA mid, guarded STUDY fetch, `~/intel_study_archives/session_movement_data/` | 2005-01-02 → 2013-12-30 | `9f9303621542ec5e66546132d24be79525054e8d69b483a461954ec2df82f4c3` |
| GBP_JPY H1 | same | 2005-01-02 → 2013-12-30 | `e00361f23f416b3479d49f08901beb02a943ae3cb759b23e93a3c533c53399cf` |
| GBP_AUD H4 | held STUDY data, `~/intel_study_archives/us_event_reaction_data/` | 2005-01-02 → 2013-12-30 | `a59db9940e8d7a1c4ff02441112390c5d7b7544e764d980943877dee51b0ff77` |
| GBP_AUD D1 | same | same | `661a9d49c09ed9fbaa7a26a1e3ae60a4fc07860d19ea3ec89342398a9db7d939` |
| GBP_JPY H4 | same | same | `f06892d1ebf958cc1a52bebf399e6ce10bef8e73e5e2c5b6a7f5634644053764` |
| GBP_JPY D1 | same | same | `ca1602404c5c501dffc0ee8ec5eeb4bee4a2197fe2fc76d3bbf69be2c8fa000a` |

- **Validation (Phase 1):** raw H1 aggregated into the framework's H4 slots
  matches every held H4 bar exactly on open, high, low and close: 15,281 of
  15,281 (GBP/AUD) and 15,191 of 15,191 (GBP/JPY). A positive control caught
  20 of 20 planted 1-pip defects per pair.
- **Partition:** STUDY only. The SEALED EXAM and its embargo are not sourced,
  counted, opened or touched. The fetch refuses the block before sending
  and after receipt; 0 stored candles fall inside it.
- **Weekend rule (approved, `study_weekend_candle_spec.md` §6), applied
  unchanged:** `history_study_convert.convert(held D1, H1)` for H1, and
  `convert(held D1, held H4)` for H4 and D1.
  - Saturday-session candles are dropped.
  - Sunday-session candles fold into the next trading session's first bar.
- The runner verifies all six sha256 values before computing anything, and
  stops on any mismatch.

## 3. Definitions (fixed now)

**Study day.** Day D runs from D−1 21:00 UTC to D 21:00 UTC, and is labelled
by the UTC date at its end. Only Monday–Friday days from 2005-01-03 to
2013-12-30 are used.
- This differs from the framework's 17:00-New-York day by one hour in
  northern winter, when 17:00 New York is 22:00 UTC.
- It is chosen so that the five blocks below tile the day exactly.
- In winter, the Friday 21:00–22:00 UTC hour falls in a Saturday study day
  and is not used. That is 169 bars per pair (counted in Phase 1).

**Session blocks.** These are fixed in UTC, do not overlap, and tile the
day. The Pacific equivalents shift by one hour with US daylight saving.

| Block | UTC | Pacific (PST, winter) | Pacific (PDT, summer) | Hours |
|---|---|---|---|---|
| SYDNEY (Sydney / early Asia) | 21:00–00:00 | 13:00–16:00 | 14:00–17:00 | 3 |
| TOKYO | 00:00–07:00 | 16:00–23:00 | 17:00–00:00 | 7 |
| LONDON | 07:00–12:00 | 23:00–04:00 | 00:00–05:00 | 5 |
| LDN_NY (London / New York overlap) | 12:00–16:00 | 04:00–08:00 | 05:00–09:00 | 4 |
| NY_PM (New York afternoon) | 16:00–21:00 | 08:00–13:00 | 09:00–14:00 | 5 |

- An H1 bar belongs to the block containing its open time.
- The existing `levels_context.py` session windows overlap (Asian 00–09,
  London 07–16 UTC). They are not used here, and are not changed.

**Hour index.** A bar's hour index is the number of hours from its study
day's start to its open, from 0 (the 21:00 UTC bar) to 23 (the 20:00 UTC bar).

**Complete study day.** Every H1 slot the market is scheduled open in that
study day has a bar. The weekly window is Sun 17:00 → Fri 17:00 New York.
That means 24 bars, except winter Mondays, which have 23 because the market
opens at 22:00 UTC. Phase 1 counted 2,325 complete days (GBP/AUD) and 2,327
(GBP/JPY). Every incomplete day is a Christmas or New Year holiday.

**Units.** Ranges are in pips: 0.0001 for GBP/AUD, 0.01 for GBP/JPY. Prices
are OANDA mid.

**Ties.** When two bars share the day's high (or low), the EARLIEST bar is
taken as where it formed.

**Fold bars.** The approved rule folds Sunday-session quotes into Monday's
first H1 bar. 420 target sessions are affected per pair. Such a bar's range
contains hours of pre-open quoting that modern data does not have.
- Q1 excludes these bars, because Q1 is about each hour's own movement.
  The count excluded is reported.
- Q2–Q4 use the converted series as approved, unchanged. Q5 does the same,
  because ATR runs on the framework's own bar series.

## 4. THE FROZEN QUESTION LIST: compute these five and nothing else

Every answer is reported **per pair, separately (never pooled)**, and then
**by day of week** (Monday … Friday) as well as over all days. Any
difference between the pairs is described, not tested.

**Q1. Hourly range profile.**
- Population: converted H1 bars in Mon–Fri STUDY study days, complete or
  not, excluding fold bars.
- For each UTC hour 0–23: N bars, mean (high − low), median (high − low),
  in pips.
- Rows are labelled with UTC and both Pacific equivalents.
- By weekday: the same table for each weekday.

**Q2. Share of daily range by block.**
- Population: complete study days.
- Day range R = highest high − lowest low over the day's bars. Days with
  R = 0 are excluded and counted.
- For each block: share = (block's highest high − block's lowest low) ÷ R.
- Reported per block: N days, mean, p10, p25, median, p75, p90. Percentiles
  use the inclusive method.
- The shares do not sum to 1, because each block's range is measured on its
  own. The report says so.
- In winter, the Monday SYDNEY block holds 2 bars instead of 3. The report
  says so.

**Q3. Where the daily high and low form.**
- Population: complete study days.
- The high bar is the earliest bar whose high equals the day's high. The
  low bar is the same for the low.
- Reported: the percentage of days whose high bar lies in each block, and
  the same for the low (each sums to 100%), plus the percentage of days with
  both in the same block. N days is shown.

**Q4. How early the extremes are set.**
- Population: complete study days.
- For H = 6, 12 and 18: the percentage of days whose high bar's hour index
  is below H, and separately the same for the low bar.
- "High in place by hour 6" means no bar from hour index 6 onward exceeded
  it.
- Hour 6 = 03:00 UTC, hour 12 = 09:00 UTC, hour 18 = 15:00 UTC. The Pacific
  equivalents are shown.

**Q5. ATR by holding timeframe.**
- Indicator: ATR(14), Wilder, exactly the formula of
  `regime_detection.compute_atr_series`. A test pins the runner's copy to
  that function.
- Series: the converted H1, H4 and D1 series, each run chronologically over
  its whole stored span. The value at index j belongs to bar index 14 + j.
- Reported: the mean ATR in pips, and N values, over bars whose New York
  session day (`history_study_convert.session_day`) is a Mon–Fri trading
  day from 2005-01-03 to 2013-12-30. By weekday uses that same session day.
- **No interpretation, no ratio, no rule proposal.** Q5 is an input to a
  separate team question about whether the minimum-stop floor should scale
  with holding period.

**N and honesty.**
- The unit for Q2–Q4 is the study day. Days do not overlap by construction.
- Q1's unit is the hour bar.
- Any cell with N < 20 is flagged INSUFFICIENT. None is expected, because
  each weekday has about 465 complete days.
- These are descriptive figures. No VALIDATED label applies to them.

## 5. Boundary-step reading rule (DST), fixed now

London and New York shift by an hour twice a year; Tokyo and Sydney do not.
Fixed UTC blocks therefore smear by one hour across the boundaries that a
London or New York event sits on:
- 07:00 UTC: the London open is 08:00 UTC in winter and 07:00 UTC in summer.
- 12:00 UTC: the New York open.
- 16:00 UTC: the London close.
- 21:00 UTC: the New York close.

00:00 UTC (Tokyo) is not exposed.

**Rule:** take Q1's all-days mean range table. For each block boundary b,
compute step = mean(hour b) ÷ mean(hour b − 1). This is arithmetic on two
Q1 figures, not a new statistic.
- A step ≥ 1.5 or ≤ 0.667 is reported as a SHARP STEP AT A BOUNDARY.
- If the boundary is DST-exposed, the report says that the Q2/Q3 figures
  for the two adjacent blocks carry the one-hour smear. It recommends a
  DST-aware re-run before those figures are relied on, instead of reporting
  them as clean.

## 6. Reading rule for Phase 3, fixed now

The Phase 3 question (`asian_range_london_direction_spec.md`) is moot if
movement is evenly spread through the day.

**"Evenly spread"** means, for BOTH pairs, the largest hourly mean in Q1's
all-days table is less than 1.5 times the smallest.
- If either pair reaches 1.5 or more, movement is concentrated and the
  question is not moot.
- Whether to run it is still the team's decision.

## 7. Limits stated up front

- **Era (data_map_spec §5):** 2005–2013 spans the financial crisis and
  zero-rate years. The figures describe that era; whether today's hours
  look the same is not shown by this study.
- A prior GBP/AUD hour-of-day profile exists on 2023-09 → 2026-09 data
  (`foundation/research_findings.md`, "Hour-of-day (PDT)"). That is the USED
  span: learning only, and not combined with this.
- **DST smear:** see §5.
- **The study day is not the framework's day** in winter (§3).
- **Mid prices; no spread.** Descriptive only, so costs do not enter.
- **Old-convention weekend quoting** is handled by the approved rule. Monday
  figures carry the fold. The weekday breakdown keeps Monday visible on its
  own.

## 8. Not computed (explicitly)

The following are not computed:
- direction, returns, or open-to-close moves of any block;
- per-year splits;
- volatility-regime splits;
- event-day splits;
- session-to-session prediction of any kind (that is Phase 3, spec only);
- pooled-pair figures;
- any statistic not in §4.

Ideas that come up while reading the results are written as **HYPOTHESES**
in the report, each with what a pre-registered test would need. None is
computed.

## 9. Run procedure

- The runner is `studies/session_movement_study.py`, written after this
  commit. Its helpers are pinned by `tests/test_session_movement_study.py`.
- It runs ONCE, through `scripts/reality_run.py --no-env --code <worktree>
  script …`, from the live project, with no network.
- It prints a UTC start timestamp as its first line, verifies the six data
  hashes, and then computes.
- Its stdout is the report body.
- The commit timestamp of this spec and the runner's first-computation
  timestamp are both recorded in the report and the validation_log entry,
  to show the ordering.
