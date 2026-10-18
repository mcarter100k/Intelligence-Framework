# Decision-channel measurement — pre-registration (2026-10-17)

**Status: FROZEN at commit.** This file is committed before any market data
is pulled for the study (M5, M11). Any change to a definition below after
that commit starts a new spec id (`decision_channel_measurement_v2`) and is
recorded in `validation_log.md`; it never edits this file in place.

**Scope.** The official DECISION channel (LONG / SHORT / STAND ASIDE) is the
one the owner reads and acts on, and it has never been graded. This spec
defines three measurements of it. **Only Measurement A is built now.** B and
C are defined here so they cannot later be defined against known results.
No protected module is edited by this work. Study code and output live in
`studies/`; nothing writes to a real ledger (rule 10).

**What was seen before this file was written (disclosed, M11).** The author
read the format of the day logs (run headers, the three decision wordings,
error pages) and one run in full: `logs/brief_2026-10-16.log` at 18:12 PDT
(GBP/AUD LONG at a printed price of 1.9189, market closed). The owner's
framing of week 2026-10-11 (a ~285-pip GBP/AUD week, LONG issued after the
close) was given with the task. No H4 bars, no forward prices and no leg
sizes were looked at.

---

## Phase 0 — market-status gate on DECISION notifications (built, separate commit)

`scripts/scheduled_brief.sh` drops a DECISION line from the notification
test and summary when that instrument's block carries the closed-market
banner `Market closed — analysis based on last close.` (rendered by
`regime_detection._market_status`, pinned by `test_wrapper_behavior.py`
g1–g9). ALERT, health, SHADOW, DIGEST and HEARTBEAT are not gated.

**Known defect left unfixed (one change at a time).** The DECISION trigger
tests a STATE, not an EDGE. An unchanged decision re-announces on every run
(the same GBP/JPY SHORT notified 8 times in week 2026-10-11), and a decision
that returns to STAND ASIDE notifies zero times: a thesis is withdrawn
silently. This needs its own spec.

---

## Shared definitions

**Source of decision history.** The day logs `logs/brief_YYYY-MM-DD.log`,
2026-07-29 onward. Each `===== <date> <time> <TZ> =====` header starts one
RUN; the header is written when the brief finishes. `trade_signal_log.csv` is
reported in the inventory and cross-checked, but it is not the episode
source: it was empty for 80 days (I23) and it is not written for every run.
Reading a day log is reading a contemporaneous record of what was decided at
that moment. It is not backfill (M23). No outcome that was never observed is
reconstructed. `logs/archive_prerebuild/` is a different framework and is
not used.

**Run time.** The header stamp, converted to UTC by its abbreviation: PDT
−7, PST −8, MDT −6, MST −7, CDT −5, CST −6, EDT −4, EST −5. An unknown
abbreviation is a parse ERROR, never a default.

**Per-run, per-instrument status** (exactly one of these):

| Status | Rule |
|---|---|
| RUN ERRORED | The run produced no decision for the instrument: its block reads `Framework error`, or the run has no block for it (empty output or crash). UNOBSERVED, never STAND ASIDE. |
| MARKET CLOSED | The instrument's block carries the closed-market banner. The decision it shows (LONG, SHORT or STAND ASIDE) is recorded but cannot be acted on. |
| STAND ASIDE | Market open and `DECISION     STAND ASIDE`. |
| LONG / SHORT | Market open and `DECISION     LONG` / `DECISION     SHORT`. |

These states are counted separately and never merged.

**Exclusion registry.** Applied at the point of USE, never at read. A run
whose UTC time is within 60 s of a registered row's timestamp, for the same
instrument and any ledger, is dropped from the episode sequence and listed.

**UNOBSERVED windows.** (a) every RUN ERRORED run; (b) every gap of more than
12 clock hours between consecutive run headers (the schedule is 02:30,
07:30 and 18:00 Pacific, so the longest scheduled gap is 10.5 h); (c)
everything before the first day log (2026-07-29).

**DECISION EPISODE.** A decision state is (instrument, direction), with
direction LONG or SHORT. The state sequence for an instrument is its
non-errored runs in time order, closed-market runs included, because a
closed run still records the framework's view. An ONSET is a run whose
direction is LONG or SHORT and differs from the previous non-errored run's
decision. An onset starts a new EPISODE only if its H4 bar index is at least
HORIZON = 30 bars after the previous episode start on that instrument.
Onsets inside that span are counted as ABSORBED. Bar index = the OANDA H4 bar
containing the run time (last bar whose open ≤ run time; `episodes.py`
`to_bar_index` semantics). An unchanged state that re-announces is not an
onset.

**Signal time (actionable anchor).** This is the first OPEN-market run inside
the episode that still carries the episode's direction: the onset run if the
market was open, otherwise the first open run after it. If the decision
changes before any open run carries it, the episode is NEVER ACTIONABLE. It
is counted and not graded.

**Signal price.** The `Price:` printed in that instrument's block at the
signal run. If the block flags the price as not live (`Price is the previous
daily close` or `Price source unknown`), the episode is PRICE NOT OBSERVED.
It is counted and not graded.

**Onset censoring.** An episode is ONSET-CENSORED if it has no earlier
non-errored run, or if an UNOBSERVED window lies between the previous
non-errored run and its onset run. Its true onset time is unknown, so a late
first observation would overstate lateness. It is counted and not graded.

**HORIZON window.** The 30 OANDA H4 bars whose open time is at or after the
signal time (same 30-bar horizon as the shadow grader). If fewer than 30
exist yet, the episode is PENDING.

**Pre-signal window.** The 119 H4 bars that CLOSED at or before the signal
time (open + 4 h ≤ signal time). That is the live H4 read's window: 120
fetched, the forming bar dropped (`regime_detection.py` around line 970).

**Fire-time ATR.** `compute_atr_series` (period 14) on the pre-signal
window, last value, in price units. This is the H4 ATR used by the loss
autopsy's `exhaustion_entry`.

**Feed validation (M13), before any statistic.** For every open-market,
non-errored run with a live printed price (not only episode signals), the
printed price must lie within [Low − 5 pips, High + 5 pips] of the OANDA H4
bar containing the run time. Pip = 0.0001 for GBP/AUD and 0.01 for GBP/JPY.
Report the run count, the disagreement count and rate, and the median
distance outside the range. Acceptance: disagreement rate ≤ 2% (the
data-map gate's rate). If it fails, no Measurement A statistic is computed
and the study reports FEED NOT VALIDATED. The numbers are reported either
way.

**Gradeable for A** = an episode that is not ONSET-CENSORED, NEVER
ACTIONABLE, PRICE NOT OBSERVED, PENDING, STRUCTURE UNDEFINED or SUB-MINIMUM.

**Episode-count cross-check.** `foundation/tools/episodes.py` is run on the
list of onsets (`--horizon 30`, bars = the OANDA H4 index). Its count per
instrument must equal the study's count. A disagreement is a defect to
resolve before any statistic.

**Stop rule.** If fewer than 10 episodes are gradeable for A (pooled), the
measurement is NOT RUN. The inventory is reported, and the owner decides
whether to run or wait.

---

## Measurement A — latency (BUILD)

### A1 — move capture ratio (primary)

For a LONG (SHORT mirrored: highs ↔ lows, signs flipped):

- `O` = leg origin = `_detect_structure(H, L, C)["latest_sl"]` on the
  pre-signal window (n = 3). This is the most recent close-confirmed swing
  low. For a SHORT it is `latest_sh`.
- STRUCTURE UNDEFINED: `_detect_structure` returns a partition or slope
  fallback instead of confirmed pivots. That happens when fewer than 2
  close-confirmed pivot highs or fewer than 2 close-confirmed pivot lows
  exist in the window, so the "swing" is not a swing. The study detects
  this by recomputing the same pivot-confirmation condition. Not graded.
- `P` = signal price.
- `E` = max(P, max High over the HORIZON window). Price that never got past
  P makes E = P, which means the move was fully spent at the signal.
- `behind = P − O`, `total = E − O`.
- SUB-MINIMUM: `total < 3.0 × fire-time ATR`. The episode is excluded and
  counted. A ratio on a leg smaller than about one daily range is noise.
  (Three H4 ATRs are roughly 1.2 daily ATRs on these pairs. The value is
  fixed here before any leg was measured.)
- `capture_behind = max(0, behind) / total`, reported as a percentage, in
  [0%, 100%]. If `behind < 0` (price already beyond the origin against the
  signal), capture is 0%: the signal arrived before the leg began. That
  clamp is conservative against the hypothesis. The clamped count is
  reported.

### A2 — ATR displacement at signal (secondary, no structure dependency)

`disp = (P − mean(last 20 closes of the pre-signal window)) / fire-time ATR`
for a LONG, sign flipped for a SHORT. This is the `exhaustion_entry`
construction (`shadow_signals._classify_loss`: 20-bar mean close, fire-time
ATR, 2.0 threshold), so it is directly comparable to the loss taxonomy.
A2 is DESCRIPTIVE: report median, mean, IQR, min, max, and the count with
`disp ≥ 2.0`. A2 carries no verdict.

### The one pre-committed threshold

> **The decision channel is SYSTEMATICALLY LATE if the MEDIAN
> capture_behind across independent gradeable episodes is ≥ 50%.**

The verdict population is POOLED (both instruments). Per-instrument figures
are reported and carry no verdict. Logic-version eras (before and after
`p5-2026-09-30`) are reported as counts only.

**Verdict rule (fixed now):**

- **SYSTEMATICALLY LATE**: requires all three of the following:
  - the pooled median is ≥ 50%;
  - the exact one-sided sign test on the count of episodes with
    capture_behind ≥ 50% (H0: p = 0.5) gives p ≤ 0.05;
  - the pooled median with the single most extreme episode removed is still
    ≥ 50%.
- **NOT SYSTEMATICALLY LATE**: the mirror case, which requires all three of
  the following:
  - the median is < 50%;
  - the sign test on the count < 50% gives p ≤ 0.05;
  - the median is still < 50% with the most extreme episode removed.
- **INCONCLUSIVE**: anything else.

"Most extreme episode" means the episode whose capture_behind is furthest
from the pooled median. A tie goes to the later signal.

**Always reported:** N gradeable, per instrument and pooled; median and mean
(M8); IQR; the median and mean with the most extreme episode removed (M9);
the sign-test count and p; the A2 distribution beside it; and every
exclusion count by reason.

**power_check (reported, not verdict-changing).**
`foundation/tools/power_check.py --rs <capture_behind − 0.50 per episode>`
gives the bootstrap bound on the mean against the threshold.
`--sd <observed SD of capture_behind> --n <N>` gives the smallest shift from
50% this N can detect at 80% power. The tool is built for R values. Here it
is used as a generic one-sided mean test on a fraction, and the report says
so.

**No post-hoc cuts.** No second threshold, sub-group or per-regime cut is
tested in this run. Anything interesting in a sub-group is recorded as a
HYPOTHESIS for a future pre-registered spec.

---

## Measurement B — decision quality (SPEC ONLY, do not build)

- Forward R per gradeable episode over the same HORIZON window, using the
  shadow grader's R math (`shadow_signals.grade_pending_shadow`). Entry is
  P. The stop is hit if any bar in the window trades through it, which
  scores −1R. Otherwise R = (close of bar 30 − P) / risk, sign flipped for
  a SHORT.
- **Synthetic invalidation.** The briefs print no stop price (a known
  display defect). The stop is therefore P ∓ 1.5 × the daily ATR the brief
  printed (`risk_config.RISK_RULES["stop_atr_multiplier"] = 1.5`). **This
  is a MODEL measurement, not a trade measurement.** It is not what the
  owner would have risked.
- Costs: none, the same as the grader. That is stated beside every figure,
  along with the swap caveat: GBP/JPY swap ≈ 0.1R per 5-day hold.
- **Expected result: INSUFFICIENT.** Detecting +0.15R against an SD of 1.2R
  at 80% power needs 396 independent episodes, or 667 across six
  candidate/pair cells at the Sidak alpha (power_check.py, run 2026-10-17).
  The available N is one to two orders of magnitude short.

## Measurement C — actionability (SPEC ONLY, do not build)

- From the signal time: did price trade within TOLERANCE of the `H1 LEVEL`
  the brief printed for that instrument (the `h1_entry_level` in the ENTRY
  CONFIRMATION block) within WINDOW, and how far did it run adversely from
  P before the first touch?
- **TOLERANCE = 0.25 × the daily ATR the brief printed. WINDOW = 48 market
  hours = 48 bars on OANDA's H1 index.** Both are frozen here.
- **Premise note.** The task described 0.25 × ATR as "matching the existing
  near-level tolerance". The live near-level tolerance is a fixed 25 pips
  (`entry_confirmation._M15_LEVEL_PROXIMITY_PIPS`). The two coincide for
  GBP/AUD at ATR ≈ 100 pips and differ for GBP/JPY (ATR ≈ 140 pips gives
  35). 0.25 × ATR is frozen as instructed.
- C measures whether a signal could have been acted on, not whether it was
  right.
