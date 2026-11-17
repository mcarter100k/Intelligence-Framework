# GLS-1: gold lower-timeframe structure, a descriptive catalogue

**Status: DRAFT, definitions only. No outcome has been measured.** Every
definition below is fixed before any 30/15/5-minute gold outcome is looked at
(team addition 4, 2026-11-17). Committing this file is the pre-registration
timestamp. A change after a measurement starts gets a new id (GLS-2), never an
edit here.

**What this is:** descriptive work under owner ruling E4. It uses no family
slots and M41 does not apply. Every output is stamped **DESCRIPTIVE, not
tradeable**, as R39 and R48 are. Reaching a level is not holding it, and a
pattern appearing is not a pattern paying.

**What this is not:** a signal, a classifier, or an input to any decision. The
live display (team addition 3b) is a separate change to the protected path and
gets its own spec; it inherits no claim from this catalogue.

Source: team additions 1–7 (2026-11-17), pasted to the session that drafted
this file.

---

## 1. Data (team addition 2: measured before anything else)

Probe finished 2026-11-17 10:43 AM PT through `scripts/reality_run.py` (exit 0,
project unchanged by hash). Every request was a bounded window passed through
`history_study_gate_s3.guard`, so no sealed-block candle could be returned.
56 two-week windows (quarterly 2006–2026, plus the last STUDY weeks and the
first USED weeks), 520 requests.

| | 30-minute | 15-minute | 5-minute |
|---|---|---|---|
| Earliest candle OANDA serves | 2006-03-19 20:00Z | 2006-03-19 20:15Z | 2006-03-19 20:25Z |
| Archive H1 starts | 2006-03-20 00:00Z | same | same |
| STUDY bars / (archive H1 × bars per hour) | 2.01 / 2 | 3.96 / 4 | 11.68 / 12 |
| STUDY hours with every sub-bar present | 98.1% | 96.4% | 92.6% |
| USED hours with every sub-bar present | 99.9% | 99.9% | 99.8% |
| Aggregated sub-bars vs archive H1, within $0.05 (STUDY / USED) | 99.8% / 100% | 99.9% / 100% | 99.9% / 100% |
| Largest disagreement (STUDY / USED) | $2.00 / $0.00 | $2.00 / $0.00 | $2.00 / $0.00 |

- All three timeframes exist for both STUDY (2006-03 → 2013-12) and USED
  (2021-04 → 2026-09). The study is **not** limited to 2021–2026.
- STUDY 5-minute coverage is thinner: 87.6% of expected bars in the two
  sampled mid-2006 windows, at least 95% in every window from October 2006 on. OANDA prints no candle
  for a 5-minute period with no price change, so a missing bar is a quiet
  period, not a hole to fill. **No bar is forward-filled.**
- A few STUDY hours disagree with the archive by up to $2.00. The fetch
  (§7.1) reports how many, and which.

## 2. Spans (RULING NEEDED, see §9 question 1)

Proposed: **USED (2021-04-26 → 2026-09-09) only.** STUDY stays unread at the
lower timeframes so that anything this catalogue suggests can later be tested
on data it never touched. The precedent the other way is R48, which ran on
both eras. FORWARD (after 2026-09-09) and the sealed exam (2014-01-01 →
2021-04-25) are never read.

## 3. Common objects

Every object below is known only at the close of the bar where it is
confirmed. Nothing uses a later bar to decide an earlier one.

- **Timeframes T:** 30-minute, 15-minute, 5-minute (OANDA mid candles).
- **Swing point on T:** a bar whose high is strictly above the highs of the 4
  bars on each side (swing high), or whose low is strictly below the 4 lows on
  each side (swing low). This is the screen's k = 4 rule. It is confirmed at
  the close of the 4th bar after it.
- **Daily ATR:** 14-day average true range of daily bars, as of the last daily
  bar completed before the event.
- **T-ATR:** 14-bar average true range on T, as of the bar before the event.
- **Structure stop on T:** for a long, the lowest low of the most recent
  confirmed T swing low at or below the entry price. For a short, the mirror.
  Its distance is entry minus stop.
- **Session:** the 5 PM New York day, the same as GMW-1.
- **Spread:** reported, not subtracted, in the excursion tables. Where a net
  figure is shown, the cost is the GMW-1 placeholders: **$0.50** primary,
  **$1.00** stress. No 2021-era spread has been measured; the measured 2026
  quote ($0.46–0.48 mid-session) is the only one.

## 4. Maximum adverse excursion (team addition 1: reported first)

### 4.1 Population A (main): every lower-timeframe structure break

On each T, a **long entry** is the close of the first T bar that closes above
the most recently confirmed T swing high. Short is the mirror. One entry per
swing level. This population is chosen without hindsight.

### 4.2 Population B (secondary, hindsight): the breaks at a 4-hour swing start

The subset of A whose entry falls inside the window of a **4-hour swing
start** (§5.1) in the same direction. Selected with hindsight, labelled so.

### 4.3 Winner, excursion and outcome

- **Winner:** price reaches entry + 1.0 daily ATR (long; short mirrored)
  within 10 sessions, measured on T bars' highs and lows.
- **Maximum adverse excursion (MAE):** the furthest price went against the
  entry, from the bar after entry up to and including the bar where the
  winner target was first reached. If one bar touches both, the adverse
  extreme counts as first (conservative).
- MAE is also reported for **all** entries, over the full 10 sessions: what a
  stop sees whether or not the trade would have worked.

### 4.4 What is reported, for each T, long and short separately

1. Counts: entries, winners, distinct sessions.
2. Winners' MAE, p25, median, p75, p90, in dollars and as a share of daily
   ATR, with 95% intervals from a session-block bootstrap (2,000 resamples,
   seed 20261117).
3. The structure stop's distance, at the same quantiles, in dollars and daily
   ATR.
4. **The decisive number:** the share of winners whose MAE reached the
   structure stop (a T-structure stop would have taken them out for −1R
   before the move), with a 95% Wilson interval.
5. Spread as a share of the median structure stop, at $0.50 and $1.00. This
   replaces the 1.9% / 16.7% illustration with measured stops.
6. Population B, the same rows.

## 5. The catalogue (team addition 3a)

### 5.1 4-hour swing start

A confirmed 4-hour swing low (k = 4) from which price rose at least 1.0 daily
ATR before trading below that low, within 60 4-hour bars. Short is the
mirror. A **failed swing** is a confirmed 4-hour swing low that was traded
below before rising 1.0 daily ATR. The **window** of either is the T bars from
the open of the 4-hour swing bar to the close of the next 4-hour bar (8 hours).

### 5.2 Structures (team addition 4: definitions fixed here)

Thresholds in T-ATR are the screen's daily-ATR thresholds
(`gold_program_screen.py`, commit c5e03c6) expressed in the timeframe's own
ATR. Every structure has a direction and a **completion bar**: the bar at
whose close it first becomes known.

| Structure | Definition (bullish; bearish is the mirror) | Completion bar |
|---|---|---|
| **Engulfing** | Exactly `entry_confirmation._detect_engulfing`: the bar closes up, its close ≥ the higher of the prior bar's open and close, and its open ≤ the lower of them. No size filter (the live definition has none) | The engulfing bar |
| **Engulfing at a level** | Engulfing whose low is within 0.15 T-ATR of the most recent confirmed T swing low | The engulfing bar |
| **Pin bar** | Range ≥ the mean range of the prior 14 bars; body ≤ 1/3 of the range; lower wick ≥ 2/3 of the range | The pin bar |
| **Pin bar at a level** | Pin bar whose low is within 0.15 T-ATR of the most recent confirmed T swing low | The pin bar |
| **Break and retest** | Level = the most recently confirmed T swing high. Break = the first close above it. Retest = the first bar within the next 12 bars whose low touches the level. **Held** if that bar closes above the level; **failed** if it closes below | The retest bar |
| **Consolidation** | The 12 most recent completed bars span (highest high − lowest low) ≤ 2.0 T-ATR, with T-ATR taken at the bar before the 12. It resolves at the first later close outside the span; its direction is the side of that close | The resolving bar |
| **Double bottom** | Two consecutive confirmed T swing lows within 0.6 T-ATR of each other; the neckline (highest high between them) at least 1.2 T-ATR above the higher low. Completes on the first close above the neckline within 60 bars of the second low's confirmation, before any close below the lower low | The breaking bar |
| **Double top** | The mirror of double bottom | The breaking bar |
| **Inverse head and shoulders** (bearish form: head and shoulders, the mirror) | Three consecutive confirmed T swing lows; the middle one (the head) at least 0.6 T-ATR below both shoulders; the shoulders within 0.6 T-ATR of each other; neckline = the higher of the two peaks between them (the mirror of the screen's lower-of-two-troughs). Completes on the first close beyond the neckline within 60 bars of the right shoulder's confirmation, before any close beyond the head | The breaking bar |

Differences from the screen's H4 detectors, stated so nobody mistakes one
for the other: the screen's engulfing required an opposite-coloured prior bar
and a range filter; here the live definition is used unchanged. The screen
measured its pattern thresholds in daily ATR on 4-hour bars; here each
timeframe uses its own ATR. The screen's 0.25 and 0.5 daily ATR on 4-hour bars
become 0.6 and 1.2 four-hour ATR (× √6 ≈ 2.45, a random-walk assumption, not
a measurement), and the same multiples are then used on every T: the same
shape at each timeframe's own scale.

### 5.3 What is reported

For each T and each structure, long and short separately:

1. **How often:** occurrences per 1,000 T bars, overall.
2. **At swing starts:** the share of 4-hour swing-start windows containing at
   least one completion, beside the same share for failed-swing windows and
   for all 8-hour windows (the base rate), each with a 95% Wilson interval.
   A structure is only interesting if the swing-start share sits outside the
   base rate's interval; the report says plainly when it does not.
3. **What it resolved into (team addition 7):** from the completion close,
   the signed move in the structure's direction at the next session close,
   +2, +5 and +10 sessions, in daily ATR; mean, median, SD, and the share
   positive. Each beside the **drift-matched baseline**: the same measure
   from every T close in the same direction over the same span (E7: a
   rising span makes any long look like an edge). Net of the $0.50 and $1.00
   placeholders as a share of daily ATR. Occurrences overlap; N is reported
   as occurrences and distinct sessions, and intervals use the session-block
   bootstrap.

## 6. Pullback continuation versus reversal (team addition 6)

**Not a classifier.** The starting answer is R48's base rate: roughly one move
in five is wholly given back within 10 sessions.

### 6.1 Populations

- **R48 legs:** R48's detector unchanged (`first_pullback_study.find_entries`).
  Pre-registered, and small.
- **4-hour swing legs:** an impulse from a confirmed 4-hour swing low to the
  next confirmed swing high, at least 1.5 daily ATR tall. Larger, and new.

### 6.2 Outcome

For legs whose pullback reached 38.2%, 50% and 61.8% (measured from the
impulse's extreme): **continued** if price made a new extreme beyond the
impulse before retracing 100%; **reversed** if it retraced 100% first;
**unresolved** if neither within 60 4-hour bars. Base rates with 95% Wilson
intervals.

### 6.3 Candidate separators (each a simple split, reported with a Newcombe interval on the difference)

1. **Speed:** 4-hour bars from the impulse's extreme to the touch of the
   level, split at the population's median.
2. **Lower-timeframe structure inside the pullback:** at the touch, the
   direction of the most recent 15-minute structure break (§4.1's rule).
   15-minute only, to keep one test per question.

### 6.4 Resolution, stated before measuring

R48's populations are too small to separate the cases. With an even split
and 50% shares, the 95% interval on a difference is about **±26 to ±42
percentage points** (computed 2026-11-17 from R48's leg counts: 38.2% level,
falls STUDY ±26, rallies USED ±34; 61.8% level, rallies USED ±42). A
separator would have to move continuation by about 30 points to show. The
4-hour swing population exists to narrow that; its count is reported (§7.2)
before any outcome. **If no split's interval excludes zero, the report says
none of them separates the two cases.**

## 7. Run order

1. **Fetch** 30/15/5-minute mid candles for the ruled span through the
   guarded fetch, written outside the repo, hashed, and checked against the
   archive H1: share of fully covered hours within $0.05 must be ≥ 99%, every
   larger disagreement listed. Fail = stop and report.
2. **Counts stage:** every population and structure counted, no outcome
   computed, logged in validation_log before stage 3 (the GMW-1 order).
3. **One run** of §4, then §5, then §6, through `reality_run.py --no-env`.
   Every number printed is reported, including the ones that show nothing.
4. The runner is written after this file is committed, with tests and named
   mutants (a look-ahead mutant for every confirmation delay; a winner/stop
   order mutant; a drift-baseline mutant).

## 8. Output stamp

Every table header and the report's first line: **DESCRIPTIVE, not tradeable.
Structures counted on history; none is a signal.**

## 9. Questions for the team before the fetch

1. **Span:** USED only (proposed), or USED and STUDY as R48 did?
2. **Population B and the 4-hour swing start (§5.1)** are hindsight objects
   by design. Keep them, or report Population A only?
3. **Thresholds in §5.2** follow the screen through a square-root-of-time
   conversion. Accept, or set them directly?
4. **The 15-minute choice in §6.3** (one timeframe, one test). Accept, or name
   another?
