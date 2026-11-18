# Spec: the configuration detector (proposed id CCD-1), Track A of "catch the configuration"

**Status: PROPOSED, for the owner's signature.** Nothing is built.
- This file fixes every threshold before the detector is run on any bar.
- After signature the thresholds are frozen. A change means a new id
  (CCD-2) and is never edited in place.

**What this is:**
- A detector that states, while it is happening, that one chart
  configuration is present, with exact prices.
- It forecasts nothing, recommends nothing and makes no claim that the
  configuration pays. Whether it pays is Track B's question, and that
  question is open.

**What it is not:** a signal, a shadow candidate or an edge.
- Its detections are never graded under this spec.
- Its existence is not evidence for Track B (owner brief, B4).

**Disclosure about data already seen:**
- The thresholds below were chosen from existing framework conventions and
  stated reasons. No study bar (2006–2013) and no 2021–2026 bar was looked
  at for this purpose.
- Tonight's gold hourly bars (Mon 2026-11-16 15:00 PT to Tue 21:00 PT)
  were printed in this session before the thresholds were written.
- So "before any data is seen" holds for every study and 2021–2026 bar,
  but not for the worked example.
- The worked example (§9) is run once after this file is committed, and
  its result is reported without retuning.

## 1. Instruments and data

| Item | Value | Why |
|---|---|---|
| Instruments | gold (XAU_USD), GBP/AUD, GBP/JPY | Owner brief A4: gold, plus the two pairs the owner can trade today, kept even while their candidates are paused |
| Bars | OANDA mid candles, closed bars only, through `oanda_feed` | The feed the live brief already uses; Part 0 showed it serves gold unchanged |
| Hourly bars fetched | the last 200 closed | 72 for the hourly trend + up to 120 for the range + 3 for swing confirmation, with room to spare |
| 4-hour bars fetched | the last 120 closed | The window `regime_detection.get_regime` already uses for the 4-hour structure |
| Daily bars fetched | the last 220 closed | The window `get_regime` already uses for the daily read |
| ATR | daily ATR(14), `regime_detection.compute_atr_series` on closed daily bars, taken from the last daily bar closed before the event bar | Every threshold below is in daily ATR, the unit of every R45/R50 figure the alert prints. One unit throughout, no dollars |

## 2. Swings

A **swing high** is an hourly (or 4-hour, or daily) bar whose high is the
highest of the 3 bars on each side, ties counting. It is **confirmed** once
a later close falls below it. Swing lows mirror this.

This is the rule in `regime_detection._detect_structure` (n = 3), and the
k = 3 of R45. One swing rule runs everywhere the owner reads a trend.

## 3. The trend (described for a downtrend; an uptrend mirrors every line)

**Test: structural, on both timeframes.**
- **4-hour:** on the last 120 closed 4-hour bars, the latest confirmed
  swing high is below the one before it, AND the latest confirmed swing low
  is below the one before it.
- **Hourly:** the same test on the 72 closed hourly bars that end at the
  bar **before** the event bar. 72 is the window `entry_confirmation` uses.

**"Established" means real swings only:**
- At least 2 confirmed swing highs and 2 confirmed swing lows on that
  timeframe.
- `_detect_structure` falls back to a first-half/second-half comparison
  when swings are scarce. That fallback does **not** count as an
  established trend here.

**Why structural rather than a measured filter (such as a moving-average
slope or a trend-strength reading):**
1. **It is the live engine's own definition.** The owner sees the same
   trend word in the brief, and it adds no new parameter.
2. **It can be checked by eye** on the owner's own chart.
3. **A measured filter would add tuned numbers to a tool that claims
   nothing.** On GBP/AUD daily level breaks, the trend filter was
   associated with worse results, not better (R44). There is no evidence
   that a fancier filter would detect "established" better.

**Why the hourly window stops before the event bar:** the trend must exist
before the break, not be created by it.

**A known property, stated so it is not discovered later:**
- At the bar before the break, the latest hourly swings are usually the
  range's own swings.
- The hourly test therefore passes only when the range itself steps down:
  a lower high and a lower low inside it.
- A flat-bottomed range under a falling top (the owner's "descending
  trendline") passes only if its last swing low is below its previous one.
- This is a consequence of the definition, not a threshold to tune.

## 4. The range

**On hourly bars, the range is the longest run of bars that meets all of
the following:**
- the run ends at the bar before the event bar;
- the run is at most 120 bars (5 sessions) and at least 12 bars (half a
  session);
- the run contains at least 2 confirmed swing highs and 2 confirmed swing
  lows (confirmation uses closes up to the bar before the event bar);
- every hourly close in the run lies inside [range low, range high];
- the width is 0.30–1.20 daily ATR.

**Range high** = the highest confirmed swing high in the run. **Range low**
= the lowest confirmed swing low in the run.

**Why these bounds:**
- **The width floor (0.30 ATR)** keeps the two 0.10-ATR touch zones (§5)
  from covering most of the range.
- **The width ceiling (1.20 ATR)** keeps out ranges wider than a normal
  day, which on hourly bars are trend legs, not consolidations.
- **12 bars** is half a session; anything shorter is a pause, not a range.
- **120 bars** matches the 4-hour window's span.

The trend leg into the range ends the run naturally: a close beyond the
later range low (or high) is not inside, so the run cannot extend past it.

## 5. The tested boundary (described for a downtrend)

**In a downtrend, the tested boundary is the range high.** That is the side
where price was turned back against the trend.

| Term | Definition |
|---|---|
| Touch zone | from the range high down to 0.10 daily ATR below it |
| A touch | one visit: a run of consecutive hourly bars in the range whose highs reach the zone. A run of touching bars counts once; the next touch needs at least one bar whose high stays below the zone in between |
| Held | a touch with no hourly close above the range high. Every touch inside the range holds, by construction of §4 |
| Required | **3 or more touches** |

**Where touches are counted:**
- Touches of either boundary count only from the range's **first confirmed
  swing** (high or low) onward.
- Bars of the run before that swing are the leg into the range, and are not
  touches.
- *Amendment 1, 2026-11-17, before any data run:* the first text counted
  every bar of the run. The prototype's synthetic control showed this
  scoring the bar that falls into the range from above as a "touch" of the
  range high, which is not price being turned back.

**Why 3:** two touches define a level; the third is the first test of a
level that already exists. The owner's example describes four, which
qualifies. Three was not chosen to fit it.

**Why 0.10 ATR:** with the 0.30-ATR width floor, the two zones together
cover at most two-thirds of the narrowest allowed range.

## 6. The event

**The event is the first hourly close below the range low, while §3–§5
hold at the bar before.** Any distance below counts, and the distance is
printed.

**One detection per range.** The duplicate key is instrument, direction,
range low to the cent and the range's first bar. A re-test and a second
close lower are not new detections.

## 7. What every alert states (owner brief A2)

**Prices:**
- gold to the cent;
- GBP/AUD to 5 decimals;
- GBP/JPY to 3 decimals.

**Times:** Pacific, via `display_time`.

**Instrument name:** written in plain words ("gold", "GBP/AUD"), never as
an internal identifier.

1. **The bar.** The hourly bar that closed below, with its open and close
   time in Pacific, and its close price.
2. **The broken level.** The range low to the cent, and the swing that set
   it (the time of that hourly bar).
3. **That level's history.**
   - How many times price came within 0.10 ATR above it (touches).
   - How many of those held: no close below. All of them, by construction
     until this bar.
   - When it was last tested.
4. **The tested boundary.** The range high, its number of touches, and when
   it was last touched.
5. **The trend.** For each timeframe, the four swing prices behind it: the
   last two highs and the last two lows on the 4-hour and the hourly
   charts.
6. **Stops, in dollars (or pips) and as a price, at the current daily ATR:**

   | Hold | Rule | Basis |
   |---|---|---|
   | Same session | the larger of 0.30 × daily ATR, and the distance from the close to the range high plus 0.05 × daily ATR | R50 next-close median adverse move among winners. The 0.05-ATR buffer is GMW-1's (R49) |
   | 10 sessions | 0.60 × daily ATR and 0.84 × daily ATR, both printed | R50, 10-session median adverse move among winners |

   Printed under them, every time: *"A stop at the median adverse move
   stops about half of the winners by construction. These are floors, not
   recommendations."*
7. **The invalidation.** An hourly close back above the range low (back
   inside the range) means the break failed. This is R45's and R43's
   definition of a failed break, and its price is printed.
8. **The next level below.** The nearest confirmed swing low below the
   close, on the 4-hour (last 120 bars) or daily (last 220 bars) chart. It
   is given in dollars (or pips) and in daily ATR, with which chart and
   which bar set it.
   - If there is none: *"no confirmed 4-hour or daily low below this price
     in the bars checked"*.
   - It never prints an empty figure as if it were a level (AGENTS rule 9).
9. **The measured base rate, with its scope.** It is never stretched beyond
   that scope:
   - **Gold:**
     - "A daily close beyond a confirmed daily swing came back inside
       within 3 days 43% of the time in 2006–2013 and 45% in 2021–2026
       (R45)."
     - Then: "That was measured on daily swings. This level is hourly,
       which has not been measured on gold."
   - **GBP/AUD:** "A first hourly close beyond a confirmed hourly swing was
     followed by a close back inside on the next hour 30.7% of the time,
     2005–2013 (R43)." R43 used hourly swings with 5 bars each side, not 3,
     and the alert says so.
   - **GBP/JPY:** "No break base rate has been measured for GBP/JPY."
10. **The two fixed sentences, verbatim, in every alert:**
    - *"This configuration being present is not evidence that it pays.
      Whether it does is an open question (Track B)."*
    - *"No direction is recommended."*

## 8. What it must never say (owner brief A3)

**Banned in alert and brief text, enforced by test:**
- the words LONG, SHORT, BUY, SELL, "go long" and "go short";
- "this is a sell", "this is a buy", "entry" and "target";
- any probability or chance of success;
- the display floor tokens (`tests/test_brief_display.py`).

**The base rate is printed as what happened, in the past tense.** It is
never phrased as an expected win rate.

**The R50 stop figures are labelled floors,** never a recommended stop.

## 9. Worked example (run once, after this file is committed)

- **Input:** gold, hourly bars through Tue 2026-11-17 21:00 PT, read-only
  through `scripts/reality_run.py`.
- **Output:** whether the frozen definition detects tonight's breakdown,
  and if so the full §7 alert text; if not, which condition failed and by
  how much.
- **Neither result changes a threshold.** If the owner wants the detector to
  catch tonight's chart and it does not, changing a threshold is a new id
  (CCD-2).
- **A definition tuned to one chart** is a hand-picked configuration. It
  may still serve Track A, which claims nothing. It must be disclosed as
  such wherever Track B uses it (AGENTS rule 3; R44's scope note).

## 10. How it runs and notifies (owner brief A5)

**What gets built (after signature):**

| Item | What | Protected? |
|---|---|---|
| `config_detector.py` | **New** module: §2–§7 as pure functions, plus a `main` that reads the bars and writes one ledger row per detection | Added to the protected list: it alerts and writes a ledger |
| `configuration_log.csv` | **New** append-only ledger, one row per detection, written through `ledger_io.append_row`. The columns are the §7 fields | Evidence ledger rules apply. It is never graded under this spec |
| `scripts/scheduled_detector.sh` | **New** wrapper: runs the detector for the three instruments and sends one notification per new detection through `scripts/notify.sh` | Free zone |
| `scripts/launchd/com.quis.intelligence.detector.plist` | **New**: every hour at minute 2, Pacific time | Free zone |
| `scripts/notify.sh` | One new subtitle, `BREAK`. Nothing else changes | Free zone |
| `decision_brief.py` | **Not changed by this spec.** Showing the latest detection inside the gold brief belongs to GDB-1's spec | Protected; untouched |

**When a detection may reach the owner.** All of these must hold, each with
its own should-it-reach-the-owner test (AGENTS rule 12):
1. **The mute switch is off.** `notify.sh` already enforces this:
   `ALERTS_MUTED` present means nothing is sent and a `MUTED` line is
   logged.
2. **The instrument's market is open.**
   - Pairs: `regime_detection._market_status`.
   - Gold: the same weekend rule, plus closed during its daily break,
     17:00–18:00 New York time (14:00–15:00 PT). Part 0 observed the last
     tick at 13:59:05 PT and live ticks again by 15:05:58 PT.
3. **The event bar is fresh.** It is the latest closed hourly bar, and it
   closed within the last 70 minutes. A late or catch-up run never alerts
   on an old bar; it only logs it.
4. **It is new.** Its duplicate key (§6) is not in `logs/detector_state.json`.

**Ledger rows.** A detection that fails 1 or 2 is still written to the
ledger. One that fails 3 is written with a `stale` flag. One that fails 4 is
not written again.

## 11. Tests (owner brief A6)

**Gate 1 — named mutants.** Each must be killed. Each is confirmed applied,
reverted, and re-run clean with bytecode caches cleared:

| Area | Mutant |
|---|---|
| Touch count | the requirement becomes 2 or more touches |
| Touch count | the zone becomes 0.20 ATR |
| Touch count | adjacent touching bars each count as a touch |
| Touch count | a touch counted on the broken side instead of the tested side |
| Trend filter | the 4-hour requirement removed |
| Trend filter | the half-split fallback accepted as established |
| Trend filter | the hourly window includes the event bar |
| Trend filter | an uptrend accepted for a downside break |
| Range | the width floor removed |
| Range | the width ceiling removed |
| Range | a close outside the range allowed inside the run |
| Stop arithmetic | "larger of" becomes "smaller of" |
| Stop arithmetic | 0.30 becomes 0.25 |
| Stop arithmetic | the buffer subtracted instead of added |
| Stop arithmetic | 0.84 becomes 0.80 |
| Stop arithmetic | the ATR taken from the event day's unfinished bar |
| Gates | the gold daily break ignored |
| Gates | the freshness limit removed |
| Gates | the duplicate check removed |
| Gates | the mute ignored |

**Render sweep.** Every sentence the alert prints changes when its input
changes, across a grid of inputs: each price, count, time, ATR, direction,
instrument, and next level present or absent.
- The two fixed sentences of §7.10 are the only constant text, and the
  sweep asserts they are always present.
- A banned-word sweep over every rendered alert enforces §8.

**Gate 2 — reality.** The real detector on real OANDA bars, run through
`reality_run.py`, with the project unchanged by hash.
- The report shows the actual output.
- The run avoids 15:15 PT, the nightly grader's slot, so that the hash
  check stays attributable.

**Gate 3 — PENDING LIVE CONFIRMATION.** These are entered in
`validation_log.md`:
- the first scheduled hourly run;
- the first live detection;
- the first delivered (or muted) BREAK notification.

## 12. Open for the owner before signature

1. **Mute.** `ALERTS_MUTED` has been present in the live project since
   2026-11-16 21:45 PT (owner, 2026-11-16: "cut all alerts off").
   - While it exists, A5's "respect the mute switch" means no BREAK
     notification reaches the owner.
   - The choices are to unmute, or to exempt BREAK from the mute (a
     `notify.sh` change that this spec does not make).
2. **GBP alerts.** GDB-1 Part 4.1 says stop the GBP pairs alerting; A4 says
   keep them in the detector. This spec sends BREAK alerts for GBP/AUD and
   GBP/JPY, reading A4 as the later and more specific instruction. Confirm
   or reverse.
3. **Every threshold in §3–§6:**
   - the 3-bar swing;
   - the 120 / 72 bar windows;
   - the range, 12–120 bars and 0.30–1.20 ATR;
   - the touch zone, 0.10 ATR;
   - 3 or more touches;
   - the 0.05-ATR buffer.

   Change any of them now; after signature they are frozen.
4. **Which ATR prints the stops (found after the data runs, not applied).**
   - R50's stop multipliers (0.30, 0.60, 0.84) were measured against a simple
     average of the last 14 completed daily true ranges
     (`first_pullback_study.bar_context`).
   - §1 takes ATR from `compute_atr_series`, which is Wilder's smoothing.
     Tonight the two differ: about $88.09 Wilder against $96.11 simple.
   - Proposed: keep Wilder for detection (§4–§5, as already run), and use
     R50's simple 14-session ATR for the §7.6 stop figures, so that each
     multiplier is applied to the ATR it was measured in.
   - This changes printed stops only, not what is detected or counted.
5. **The worked example did not detect tonight** (validation_log
   2026-11-17, CCD-1 entry).
   - Signing as written means the detector would not have caught tonight's
     chart.
   - Changing a threshold so that it does is CCD-2, and is a definition
     tuned to one chart (§9).

