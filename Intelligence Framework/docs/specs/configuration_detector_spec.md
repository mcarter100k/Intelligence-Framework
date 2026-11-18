# Spec: the configuration detector (proposed id CCD-1), Track A of "catch the configuration"

**Status (owner rulings 2026-11-17, M1–M6 and L1):**
- **BREAK (§1–§11) is SIGNED as written** (ruling L1).
  - Its thresholds are frozen. Any change is a new id (CCD-2), never edited
    in place.
  - No recency variant was declared; the window for declaring one closed
    with ruling L1.
- **The ARRIVAL, BRIEFING and RELEASE parts (§13–§16) are ruled** (M2–M6).
  The level list was chosen by ruling M3's rule (§15).
- **Gold only** (ruling M1).
- **Nothing is built yet.** Build order (M6): BRIEFING, then ARRIVAL, then
  BREAK.

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
| Instruments | **gold (XAU_USD) only** | Ruling M1, 2026-11-17: every GBP/AUD and GBP/JPY job, alert and candidate logging is stopped. This supersedes brief A4's "keep the GBP pairs in the detector" |
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
| `scripts/scheduled_detector.sh` | **New** wrapper: runs the detector on gold and sends one notification per new detection through `scripts/notify.sh` | Free zone |
| `scripts/launchd/com.quis.intelligence.detector.plist` | **New**: every hour at minute 2, Pacific time | Free zone |
| `scripts/notify.sh` | New subtitles `BRIEFING`, `ARRIVAL`, `RELEASE` and `BREAK`. **Exempt from `ALERTS_MUTED`** (ruling M4, owner ruling L2): every other category stays muted, and the switch is not removed. Each exempt send is still logged and recorded in `notification_log.csv`. A test pins that exactly these four are exempt | Free zone |
| `decision_brief.py` | **Not changed by this spec.** Showing the latest detection inside the gold brief belongs to GDB-1's spec | Protected; untouched |

**When a detection may reach the owner.** All of these must hold, each with
its own should-it-reach-the-owner test (AGENTS rule 12):
1. **The mute switch does not apply to this alert** (ruling M4). Every
   other category stays muted while `ALERTS_MUTED` exists.
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
| Gates | the exemption widened to another category, or BREAK muted |

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

## 12. Open for the owner before signature — all resolved 2026-11-17

**Resolutions:**
- Item 1, the mute: ruling M4. These four alert types are exempt; there is
  no global unmute.
  - The mute's reason was the owner's switch to gold and the GBP hold
    ("hold off on GBP/AUD and GBP/JPY, cut all alerts off, focus on gold",
    validation_log 2026-11-16).
  - It was not the fire rate, which the addendum had stated. Correction
    accepted by the owner (M4).
- Item 2, GBP alerts: ruling M1, gold only.
- Item 3, thresholds: ruling L1, signed as written.
- Item 4, the stop ATR: the simple 14-day ATR (§13.2; addendum A7).
- Item 5, tonight's miss: ruling L1, signed as written. It does not catch
  tonight.

The text below is kept as it was raised.

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


---

# Addendum (owner, 2026-11-17): three alert types, A7–A11

**What this adds.** The owner wants to be told when price arrives somewhere
worth looking, and when a session or a release is coming. Track A therefore
has three alert types:
- **HEADS-UP** (§14, A8): fires on a schedule.
- **ARRIVAL** (§13, A7): fires on price.
- **BREAK** (§1–§10, CCD-1): fires on the configuration.

**Build order (A11):**
1. HEADS-UP;
2. ARRIVAL;
3. BREAK.

**Status:** this addendum is PROPOSED with the rest of the file. It was
written before any arrival or heads-up count was made.

## 13. ARRIVAL alert (A7)

### 13.1 Qualifying levels, fixed before any count

| # | Level type | Definition |
|---|---|---|
| 1 | Daily swing | a confirmed daily swing (§2 rule) among the last 220 closed daily bars, **still intact**: no daily close beyond it since it formed |
| 2 | 4-hour swing | a confirmed 4-hour swing among the last 120 closed 4-hour bars, still intact (no 4-hour close beyond it since it formed) |
| 3 | Range boundary | the current hourly range's high and low, by §4, when a range exists |
| 4 | Prior session | the high and low of the last completed daily bar |
| 5 | Prior week | the high and low of the last completed trading week (Monday–Friday by trading date, the New York 17:00 day used by `_market_status`) |

**Why "intact":** a level that price has already closed through no longer
bounds price.

**Live note (2026-11-17, found by the seven-day replay, N4):**
- OANDA's live daily series omits the session in progress.
- "Prior session" must therefore be the last daily bar in the list once the
  hour is past that bar's 24-hour span, not the one before it. The same
  applies to the simple ATR's last 14 completed days.
- The prototype had this wrong for live hours. It is fixed in
  `ccd1_arrival_calibration.session_index`, with a test and a mutant. The
  archive counts were re-run and are byte-identical.
- The live build uses the same rule.

### 13.2 ATR

**The simple 14-day ATR:** the mean of the last 14 completed daily true
ranges. This is R50's own definition (`first_pullback_study.bar_context`),
so the 0.30 / 0.60 / 0.84 multipliers apply to the ATR they were measured
in.
- It is used for the arrival tolerance and for every figure in an ARRIVAL
  or HEADS-UP alert.
- This also settles §12 item 4 for the BREAK alert's printed stops.
- BREAK detection itself keeps the Wilder ATR it was run with.

### 13.3 Arrival, cooldown, grouping

| Term | Definition |
|---|---|
| Tolerance | **0.10 × simple ATR** (ruling M3) |
| Level types that fire | daily swings, range boundaries, prior session, prior week: §13.1 types 1, 3, 4 and 5. **4-hour swings do not fire an ARRIVAL** (ruling M3, §15), but they still count as levels for the distances in §13.4 item 3 |
| Arrival | a closed hourly bar whose range comes within the tolerance of an armed level (its low ≤ level + tolerance and its high ≥ level − tolerance) |
| Armed | a level is armed once an hourly close has been at least 0.50 × ATR from it, counted from when the level formed or from its last arrival. This is the per-level cooldown: one approach fires once, and the level re-arms only after price has clearly left it |
| Grouping | at most one ARRIVAL alert per instrument per hourly bar. Every level arrived at in that bar is listed in the one alert |

### 13.4 What every ARRIVAL alert states

1. **The level.**
   - Gold to the cent; pairs to 5 decimals (GBP/AUD) and 3 decimals
     (GBP/JPY).
   - Its type, and the bar or session that set it, with the time in
     Pacific.
2. **Its history.**
   - Touches: separate visits within the tolerance since it formed.
   - How many held, and how many broke.
   - When it was last tested.
   - A touch, a hold and a break are as ruled 2026-11-18 (§14.1, rulings
     R1–R3).
3. **Both sides, never one** (accepted, ruling M5).
   - The distance to the nearest qualifying level on the other side of
     price.
   - The distance to the next qualifying level beyond this one.
   - Both in dollars (or pips) and in ATR.
   - *Why both:* printing only the far side implies the level will hold;
     printing only the level beyond implies it will break. Either one alone
     is a direction (A9).
4. **The minimum stop, at the simple ATR:**
   - 0.30 × ATR for the same session;
   - 0.60 and 0.84 × ATR for a 10-session hold (R50);
   - with the §7.6 "floors, not recommendations" sentence.
5. **The base rate, only where one was measured:**
   - **Gold daily swing (R45, 2021–2026):** a wick beyond failed 66% of the
     time; a daily close beyond came back inside 45% of the time.
   - **GBP/AUD daily swing (R45 benchmark, 2021–2026):** wick 69%, close
     46%.
   - **Every other type:** *"No break base rate has been measured for this
     kind of level."*
6. **The next scheduled release.**
   - Taken from `calendar.csv` (High impact, any of the instrument's
     currencies; US for gold).
   - Its time in Pacific and the time until it.
   - If the calendar is stale or missing, it says so (rule 9).
7. **The clock against gold's 4–8 AM PT window.** Before, inside (with the
   minutes left), or after. Then the §16 window sentence.
8. **Volatility.**
   - The simple ATR as a share of price, and its percentile against the
     trailing 250 days.
   - The tercile by R50's cut points, 1.206% and 1.480%.
   - Gold only. The cut points were measured on gold, and the pairs print
     "not measured for this pair".
9. **The two fixed sentences of §7.10.**

## 14. BRIEFING and RELEASE warnings (A8, split by ruling M2)

**BRIEFING: a daily read, not an interruption. Not counted in any alert
budget.**
- 03:45 PT on each trading day, before gold's 4–8 AM PT window.
- Contents as listed under "What it states".

**RELEASE warning: an ALERT, counted in the 5–10 a week budget.**
- 30 minutes before each High-impact US release on the live calendar (gold
  only, ruling M1).
- Same-time releases share one warning.
- **A release inside 04:00–08:00 PT also gets its 30-minute warning**
  (ruling N2, 2026-11-17).
  - It is listed in the BRIEFING as well.
  - The BRIEFING is the planning read. The warning fires at the decision
    moment.
  - These are gold's most important scheduled events, landing in the one
    window whose range concentration survived the chance sweep.

**What it states:**
- Gold's price and the time of that price, which flags a stale price
  (Part 0).
- The nearest qualifying level above and below, in dollars and ATR. It uses
  all five §13.1 types: the BRIEFING has no budget, so it uses the richest
  list.
- The releases scheduled before the next morning alert, in Pacific.
- Volatility as in §13.4 item 8.
- The §16 window sentence.
- The two fixed sentences.

**When it stays silent:** whenever gold's market is closed (§10 gate 2).
The mute switch does not apply (ruling M4).

### 14.1 Alert history in the BRIEFING (owner directive, 2026-11-18)

**Why.** The owner is asleep for most alerts. Last week's fired at
6:00 AM, 7:00 AM and 6:00 PM PT. The BRIEFING is where the owner catches up.

**The case that shows it, $3,870.32:**
- It produced ARRIVALs at Thu 12 Nov 7:00 AM PT and Fri 13 Nov 6:00 AM PT.
- It broke at Sun 15 Nov 10:00 PM PT.
- Read as three separate alerts, that is noise. Read as a sequence, it is a
  level tested twice and then given way.

**What the history section states, for the trailing 7 days (the 168 hours
before the BRIEFING's own time):**

1. **Every ARRIVAL and LEVEL BREAK sent, oldest first.**
   - The level to the cent, and its type in plain words.
   - The time sent, in 12-hour Pacific.
   - Where that level stands now, as one of:
     - "broke at <time>";
     - "still watched";
     - "no longer watched: it stopped qualifying at <time>". A level stays
       watched only while a firing-type qualification exists at its price
       (§17, ruling P4), and a prior-session low, for example, rolls off.
2. **Every level currently watched** (the §17 watch set): the price, its
   type, the side price approached from, and its touch and hold counts (see
   the open item below).

**Where "sent" comes from:**
- `notification_log.csv` is the existing ledger of every notification
  actually sent: one row per send, written by `notify()` through
  `ledger_io` after the send command exits 0.
- An alert counts as sent only if its row is there. A recomputation from
  bars would list alerts that never reached the owner.
- The ARRIVAL build makes each row's level prices recoverable exactly. That
  is either a fixed form in the summary or a column added with
  `migrate_header`; the build decides which, with a test.

**Where "now" comes from:**
- The status of each level is computed at BRIEFING time by the same §17
  watch code the live LEVEL BREAK uses.
- If that code says a level broke but no LEVEL BREAK row exists (the sender
  was down, or the alert was muted), the line says both: "broke at <time>;
  no LEVEL BREAK alert was sent". A silent gap never reads as "still
  watched".

**Before ARRIVAL is live (AGENTS rule 9):**
- The section prints "ARRIVAL and LEVEL BREAK alerts are not live yet, so
  there is no alert history to show."
- It never prints "no alerts in the last 7 days" until the sender has been
  shown able to write a row.

**No interpretation.**
- Just the history, in order.
- Nothing says that repeated tests make a level stronger, weaker, likelier
  to hold or likelier to break. The owner's directive cites R50: the
  appearance of a pattern carries no information.
- The §16 language test covers this section like any other.

**Times.** Every time in this section is 12-hour Pacific with the "PT"
label (display_timezone_spec addendum 2026-11-18).

**Touches and holds: RULED 2026-11-18 (owner rulings R1–R3).** These
replace the open item below them, which is kept as the record of what was
asked.

- **R1. A touch is a visit, not an ARRIVAL** (option (a)).
  - A visit is one continuous stay inside the tolerance band (0.10 × the
    simple ATR either side of the level). Price enters the band, stays any
    number of hourly bars, and leaves: one visit. It returns later: a second
    visit.
  - An hourly bar is inside the band when its range overlaps it.
  - *Why:* the count must match what the owner sees on the chart. The
    ARRIVAL cooldown exists to limit alert volume, and an alert budget must
    not distort a descriptive count.
- **R2. Held versus broke uses the LEVEL BREAK rule** (§17, ruling Q1).
  - A visit BROKE if any hourly close during it went 0.10 × the simple ATR
    or more beyond the level. Otherwise it HELD.
  - The ATR is the one in force at that close, the same as LEVEL BREAK uses.
  - *Why:* "held" and "broke" must never disagree about the same close. Price
    sitting on a level by cents is not that level breaking.
- **R3. Each visit's outcome is fixed at the time of the visit and never
  revised.**
  - "Beyond" is judged from the side price approached from: the side of the
    close before the visit's first bar (that bar is outside the band, so its
    close is clearly on one side).
  - Nothing after a visit ends can change its outcome. A visit still under
    way at the BRIEFING's time reads "under way" until it ends or breaks.
  - *Why:* a count that changes retroactively tells the owner nothing they can
    rely on.
- **What this settles for $3,870.32:** Thursday's closes, $0.29 and $0.19
  through, are under the margin, so Thursday held. The counts under these
  rulings are in the 2026-11-18 validation_log entry, from a read-only run.
- **The BRIEFING prints the counts under R1–R3.** The "until ruled" line
  below no longer applies.

**OPEN ITEM (ruled 2026-11-18 above; kept as the record): what "held" means.** Found while checking the
$3,870.32 case. The run was read-only, through `reality_run`, and the
project was unchanged by hash.

- **§13.4 item 2 as built** (`ccd1_arrival_lastweek.history`): a visit
  "held" if no hourly close in it was beyond the level.
- **Under that rule, the Friday alert reads "2 earlier visits, 1 held".**
  Thursday's visit is the one counted as not held: its hourly closes were
  $3,870.03 and $3,870.13, which are $0.29 and $0.19 through (0.003 and
  0.002 ATR).
- **Ruling Q1 calls a close by cents "price sitting ON the level", not a
  break.** That is the owner's own reading: "held both times".
- **The rule as built also judges "beyond" against the current close's
  side, not the side price approached from.** So the Fri 30 Oct visit was
  counted as not held at Thursday's alert and as held at Friday's.
- **Two questions need a ruling.** The read-only checks below were run
  through `reality_run`, and the project was unchanged by hash each time.
  Times are the hourly bar's start, in Pacific.

  **Question 1: what is one touch?**
  - **(a) A visit:** a run of consecutive hourly bars within the tolerance
    (§13.4 as written). A single hour away splits it. $3,870.32 then has
    four visits:
    - Fri 30 Oct 11:00 AM–1:00 PM PT;
    - Thu 12 Nov 6:00 AM–4:00 PM PT;
    - Fri 13 Nov 5:00 AM PT;
    - Fri 13 Nov 7:00 AM–Sun 15 Nov 3:00 PM PT.
  - **(b) An armed approach:** one ARRIVAL by §13.3, where the level re-arms
    only after a close at least 0.50 ATR away. Between Thursday's and
    Friday's ARRIVALs the farthest close was 0.52 ATR away (Thu 12 Nov
    7:00 PM PT), so Friday is a second touch. After Friday's ARRIVAL the
    farthest close before the break was the break itself, 0.34 ATR, so the
    level never re-armed. Thursday and Friday are two touches, matching the
    owner's "tested twice".

  **Question 2: when did a touch hold?**
  - **Proposed:** a touch held if it ended without an hourly close at least
    0.10 × the simple ATR beyond the level. "Beyond" is measured from the
    side price approached from, which is the close before the touch began.
    This is the LEVEL BREAK rule (§17, Q1), so "held" and "broke" can never
    disagree about one close.
  - **Under (a) with the proposed rule:** all four visits held; the largest
    close beyond was 0.003 ATR, on Thursday. The break followed on Sun
    15 Nov 10:00 PM PT.
  - **Under (b) with the proposed rule:** Thursday's touch held. Friday's
    touch never re-armed and ended in the Sun 15 Nov 10:00 PM PT break. That
    is the same break the LEVEL BREAK alert reports, once per arrival.
  - **The owner's "held both times, then broke on Sunday"** fits (a), and
    fits (b) if "held" means "no break in the hours around the touch".
    These data cannot choose between them; it is a definition.
- **Until ruled:** the BRIEFING build leaves the counts out, and does not
  print them under the rule as built.

## 15. Fire-rate calibration (A10)

**This calibration is not a hypothesis test, and M41 does not apply.**
- These alerts make no claim about outcomes, so there is no edge to
  overfit.
- Tuning the tolerance and the level list to a fire rate is legitimate.
- Nothing after an arrival bar is read, except the bars needed to re-arm a
  level.
- Nobody may screen this tuning as if it were a candidate. Nobody may cite
  a fire count as evidence that a level matters.

**Method:**
- Count ARRIVAL fires per week, per instrument and in total, on 2021-04-27
  → 2026-09-09 (the USED span; no FORWARD bar, no sealed bar).
- Count across a grid of tolerance (0.05, 0.10, 0.15, 0.20 ATR) and level
  list (all five types; without 4-hour swings; without prior session;
  daily swings and prior week only).
- **HEADS-UP fires** cannot be counted on 2021–2026: no calendar history
  exists for that span. The archive holds US releases for 2005–2013 only.
  They are estimated from the live calendar's observed weeks and labelled
  as an estimate.

**Target (ruling M2):** 5 to 10 ALERTS a week on gold. ALERTS means
ARRIVAL, RELEASE warnings and BREAK. The BRIEFING is not counted.

**Measured** (`studies/ccd1_gold_alert_budget.py`; gold, 2021-04-26 →
2026-09-09, 281 trading weeks; tolerance 0.10):
- "Measured" is ARRIVAL plus BREAK, week by week. BREAK is CCD-1 as signed,
  47 detections, 0.17 a week.
- "Total" adds an **estimate** of 2 RELEASE warnings a week: the live
  calendar's week of 2026-11-16 had 3 US releases, 1 of them inside the
  window.
- That estimate comes from one week. Weeks with more releases (a jobs-report
  week, for example) will run higher, and the busy-week column does not
  capture that.

| Level list | Measured a week | Median week | 90th-pct week | Busiest week | Total a week (estimate) | 90th-pct week + 2 | Weeks over 10 |
|---|---|---|---|---|---|---|---|
| all five | 7.1 | 7 | 11 | 19 | 9.1 | 13 | 26% |
| **no 4-hour swings** | **5.2** | **5** | **8** | **14** | **7.2** | **10** | **6%** |
| no prior session | 6.5 | 6 | 10 | 18 | 8.5 | 12 | 20% |
| daily swings + prior week | 2.5 | 2 | 5 | 9 | 4.5 | 7 | 1% |

**After ruling N2** (a warning before every US release, inside the window
too), the release estimate becomes 3 a week (the same live week).
- The chosen list then runs at about 8.2 a week, with a busy week of about
  11.
- **The owner accepted that** (N2): "the band constrains noise, not value".
- **N3 (2026-11-17)** confirmed the choice below and the split: all five
  types in the BRIEFING and in the two-sided distances.

**Chosen (ruling M3: the richest list that keeps ALERTS in 5–10 on gold):
"no 4-hour swings" at tolerance 0.10.** That is daily swings, range
boundaries, prior session and prior week.
- **The rule applied:** the average must be in the band, AND the
  90th-percentile week must stay at 10 or below.
- "All five" fits on average (9.1), but its busy week reaches 13, and a
  quarter of weeks exceed 10. That is the bunching the old budget tolerated
  and the new one does not.
- "No prior session" has the same number of level types and more alerts,
  but its busy week reaches 12.
- If the owner reads "in the band" as the average only, "all five" is the
  richest list.

## 16. Language (A9), enforced by test

**An alert may say that price has arrived at a level.** It may never call a
level any of these:
- a buy area or a sell area;
- support or resistance "to trade";
- a zone of interest, an opportunity or a setup.

It may never use any other wording that implies direction. Added to the §8
banned list:
- buy area, sell area, zone of interest, opportunity, setup;
- look for, bounce, reject, rejection, fade.

**The window sentence, printed verbatim in every ARRIVAL and HEADS-UP
alert:**
- *"Gold's 4–8 AM PT hours usually carry most of the day's range. That
  says movement is likely available, not which way it goes."*
- *"A trade on this window was tested and REFUTED (R49). Volatility
  clusters; direction does not."*

**Source for the first sentence:** the gold session study, 2021–2026. In
the 4–8 AM PST block, the median share of the day's range was 67%, against
59% for a volatility-shaped random walk, +10.6 SE (timing claims sweep,
2026-11-16).
- **Caveat:** the study's block is fixed in UTC (12:00–16:00).
- That matches 4–8 AM in Pacific standard time. In daylight time the same
  UTC hours are 5–9 AM PDT.
- Whether the busy block follows the clock in New York (and so stays at 4–8
  AM Pacific all year) has not been measured.

## 17. LEVEL BREAK alert (owner ruling P1, 2026-11-17)

**A fourth alert type**, distinct from CCD-1's configuration BREAK and much
simpler.
- It says only that the level the owner was told about has given way.
- It has no trend filter, no configuration and no claim.
- It is written before any LEVEL BREAK count.

**Watched level:**
- A price that produced an ARRIVAL alert becomes watched from that alert's
  bar.
- **Which side:** the side of the level that price was on is the close of
  the bar *before* the arrival bar (above or below the level).

**Still qualifies (ruling P4):**
- A level's qualification can change during the day. At the 2026-11-17
  break bar, $3,832.46 was still a range edge but no longer the
  prior-session low: the session that opened at 15:00 PT had its own low
  of $3,836.96.
- **A watched price stays watched while any qualification holds:** while
  any level of a firing type (§13.3: daily swing, range boundary, prior
  session, prior week) in the current hour's set has that price, to the
  cent.
- It does not matter under which qualification it was first alerted.

**Invalidated (no longer watched)** in either of these cases:
- (a) no firing-type level at that price remains in the set;
- (b) its LEVEL BREAK has fired. One break per arrival. A later ARRIVAL at
  the same price watches it afresh.

**The event (amended by owner ruling Q1, 2026-11-18):**
- An hourly bar closes **at least 0.10 × the simple 14-day ATR** beyond a
  watched price, on the opposite side from where price was before the
  arrival. The distance is printed.
- **A close beyond by less is not a break.** The level stays watched.
  - That is price sitting on the level, not through it, and calling it a
    break would mislabel the state for an owner learning to read structure
    (Q1).
  - In the arrival's own hour, such a bar is reported as the ARRIVAL it is.
- Constant: `BREAK_MARGIN = 0.10` in `studies/ccd1_arrival_calibration.py`.
  The live module uses the same value.
- The check starts with the arrival bar itself. If the bar that arrived also
  closed beyond, one alert is sent, the LEVEL BREAK, stating that price
  arrived and closed through in the same hour.

**The cooldown does not apply to it (P1):**
- The §13.3 cooldown governs repeated *approaches* to a level, and it stays.
- It never suppresses a break of a watched level.
- On 2026-11-17 the cooldown, applied to the one event type that existed,
  is what cost the notification at the break.

**Grouping:** at most one LEVEL BREAK alert per instrument per hourly bar,
listing every watched price closed through in that bar.

**What it states:**
- The level to the cent, with its qualification at the arrival and its
  qualifications now.
- The time of the ARRIVAL that watched it.
- The bar (Pacific), its close, and the distance beyond the level in
  dollars and ATR.
- The same items as every ARRIVAL alert (§13.4, items 3–9):
  - the two-sided distances (ruling M5);
  - the stop figures;
  - the measured base rate, where one exists (R45, for a daily swing), else
    the "not measured" sentence;
  - the next release;
  - the clock and the window sentence;
  - volatility;
  - the two fixed sentences.
- **Language:** §16 applies. "Closed through" and "given way" are
  descriptions; nothing about what happens next.

**The mute switch does not apply** (ruling M4 extended): `LEVEL` is added to
the exempt subtitles.

**Budget (ruling P2):**
- LEVEL BREAK is counted on 2021–2026 before it ships, and reported with
  ARRIVAL, BREAK and the release warnings.
- If it pushes the busy week past 11, that is reported with a
  recommendation, never tightened silently. "The level you were just told
  about broke" is high-value by construction (the N2 reasoning).

**Measured (ruling P2):** `studies/ccd1_level_break_budget.py` and
`studies/ccd1_level_break_budget_result.md`. Gold, 2021–2026, 281 trading
weeks; the chosen ARRIVAL list at 0.10; counts only.
- **LEVEL BREAK: 3.31 a week.**
  - Of 1,623 watched prices, 1,084 (67%) were closed through while still
    qualifying. The rest stopped qualifying first.
  - 370 of the breaks came in the arrival's own hour, and were sent as one
    alert. The median gap from arrival to break is 1 hour; the 90th
    percentile is 8.
- **ALERT total** (ARRIVAL sent separately 4.13, LEVEL BREAK 3.31, BREAK
  0.17, release warnings 3 as an estimate): **10.6 a week**.
  - The median week is 10 and the 90th-percentile week is **15**.
  - 39% of weeks exceed 11, against 8.2 / 11 / 6% before P1.
- **It pushes the busy week past 11, so it is reported here, not
  tightened.**

**Options measured, not applied:**

| Option | LEVEL BREAK a week | Total a week | 90th-pct week | Weeks over 11 |
|---|---|---|---|---|
| as written | 3.31 | 10.6 | 15 | 39% |
| close ≥ 0.05 ATR beyond | 2.93 | 10.5 | 15 | 38% |
| close ≥ 0.10 ATR beyond | 2.59 | 10.3 | 15 | 35% |
| close ≥ 0.20 ATR beyond | 2.12 | 10.1 | 14 | 32% |
| ≥ 2 hours after the arrival | 2.97 | 11.2 | 16 | 48% |
| ARRIVAL list "daily swings + prior week", break as written | 1.68 | 6.7 | 10 | 6% |

**Ruled (Q1, Q2, 2026-11-18):** ship LEVEL BREAK with the 0.10 ATR margin,
overruling the recommendation below on accuracy, not volume.
- **Accepted volume:** about 10.3 a week, with a busy week of about 15
  (figures re-confirmed after the at-least fix; see the validation_log
  2026-11-18 entry).
- **The ARRIVAL list is not to be shrunk now.**
- **Review at four weeks of live alerts.** If the volume is too much then,
  the ARRIVAL list is the lever.

**Recommendation (as made, then overruled by Q1): ship LEVEL BREAK as written.**
1. **Tightening the break barely moves the total.** A break that is filtered
   out in its arrival's hour is sent as an ARRIVAL instead, so the alert is
   not saved. A wait after the arrival makes it worse, because it splits
   one alert into two.
2. **The only option that holds the busy week at 10 is the smaller ARRIVAL
   list,** and that list drops range edges and prior sessions.
   - $3,832.46 was both, so under that list the 2026-11-17 break produces no
     alert at all.
   - It removes exactly the event P1 exists for.
3. **Watch it live.** After 4 weeks of live alerts, compare the real weekly
   count with this estimate (Gate 3).
   - If the volume proves noisy, the measured lever with real effect is the
     ARRIVAL list, not the break rule.
   - A margin of 0.10 ATR is the next-best option. It would drop
     closes-through-by-cents like three of last week's five ($0.29, $0.88,
     $0.98), at a cost of about 0.3 alerts a week.

**Replay of the last seven days** (`studies/ccd1_arrival_lastweek_level_break_result.md`):
- 5 LEVEL BREAKs, including **Tue 11-17 17:00 PT: $3,832.46 closed through
  by $17.48 (0.18 ATR)**. The break was caught, qualifying as a range edge
  after its prior-session qualification lapsed at 15:00 PT (P4).
- With same-hour merges, the week's alerts were 3 ARRIVAL and 5 LEVEL
  BREAK, plus release warnings.

**Completed-period fields (ruling P3):** every field this alert path takes
from a completed period is covered by `tests/test_completed_periods.py`
(methodology M42, incident I33).
