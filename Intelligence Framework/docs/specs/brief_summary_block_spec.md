# Spec: a short answer at the top of the brief, and a truthful WATCH FOR

**Status:** PROPOSED 2026-11-05, awaiting team review. Not built. Touches
`decision_brief.py` (protected). No decision, filter, regime or ledger logic
changes; the proof is in §6.

## 1. Why

Owner, 2026-11-05, on the 2026-11-03 day log: "is this something that can be
easily understood? why is the read so long".

Measured on `logs/brief_2026-11-03.log`:
- 565 words per run, 341 lines for three runs, every decision STAND ASIDE.
- THE FULL PICTURE is nearly half of a run. It mostly restates MARKET STATE and
  WATCH FOR.
- STAND ASIDE, "Confidence 0/100, Rating C" and "0% of standard size" are one
  fact stated three ways.
- "Conditions unchanged", the most useful fact on an unchanged run, is in the
  middle of the page.

## 2. Defect: WATCH FOR is wrong on a range-labelled daily chart

`decision_brief.py` (`if d1 == "RANGING"`) renders, after plain-English
translation: "daily chart trend strength drops below 18 or 4-hour chart
resolves to clean trend — revisit then." The 07:30 digest quotes this line as
the day's watch condition.

**Neither clause leads to a trade:**
- **"Drops below 18":** on quiet range days the strength is already below 18
  (15 and 17 in the 2026-11-03 log). Below 18 is what `RANGING` means
  (`regime_detection.py:713`).
- **"4-hour resolves to clean trend":** at 18:00 on 2026-11-03 GBP/JPY's 4-hour
  chart read "trending up", and the decision was still STAND ASIDE, with the
  same WATCH FOR line.
- **Ledger, OBSERVED:** `session_context_log.csv` under logic version
  `p5-2026-09-30` has 58 RANGING-daily rows, 0 allowed. The 19 allowed rows are
  all September, before that logic and with no version stamped.

**What the classifier requires (read from code, INFERRED until the §6 sweep):**
a daily chart counts as trending only at strength 25 or more with an agreeing
swing pattern and slope. 18–25 is `VOLATILE / TRANSITION_ZONE`, still stand
aside. `RANGING` also covers 35+ (EXHAUSTION; 44 of the 93 RANGING rows), where
"drops below 18" is meaningless as well.

**Proposed wording, for the team to settle:**
- Quiet range: "The daily chart picks a direction: trend strength reaches 25
  with its swing pattern agreeing. Revisit then."
- Exhaustion: wording per the current EXHAUSTION rule, written from the code at
  build time. The wording must never suggest fading or chasing.

## 3. The short block

One block above the first pair, for every run:

```
    GBP/AUD 1.9313   STAND ASIDE   no change since 7:33 AM
      Why: <the REASON, unwrapped>
      Changes if: <the WATCH FOR, unwrapped>
```

**Rules:**
- **One source of truth.** Why and Changes-if are the existing REASON and WATCH
  FOR strings, never a second set of sentences that can drift from them. A
  decision other than STAND ASIDE adds the existing EXIT IF and POSITION values
  and nothing new.
- **Change status comes from `session_memory.get_session_delta`.** Rule 9
  applies: "no change" only when a prior run was actually compared. With no
  prior run, the line says so ("first run today"). A failed read says "not
  checked", never "no change". The third run of 2026-11-03 shows no SESSION line
  at all; the build must find out why, not assume it.
- **Indent every line 4 or more spaces.** The wrapper, digest and latest view
  read labels at 0–2 spaces (`us_events_context_spec.md` §1.4). The pair header
  pattern `^ ? ?[A-Z]{3}/[A-Z]{3}( |$)` would otherwise match the block's first
  line: it would restart the closed-market scope, add a phantom pair to the
  notification ledger and split digest sections.
- **Feed text stays sanitized.** Any headline inside REASON keeps its existing
  path; the block adds no raw feed text.
- **Plain English.** The banned-token floor applies to the block unchanged.
- **The error page** gets no block, or one that says the run failed. It must
  never show STAND ASIDE as if it were a market read.

## 4. Smaller wording fixes

- `strong uptrend on all timeframes` sits beside "Daily chart: moving sideways".
  It renders the weekly label `ESTABLISHED_UPTREND`. Proposed: "strong uptrend".
- "Moving sideways" beside "confirmed stair-step pattern of higher highs and
  higher lows" reads as a contradiction. Both are true: the first comes from low
  trend strength, the second from the swings. The sentence should say so.
- `DUE: … last written 1295h ago, your cadence is 216h`: show days
  (`scripts/artifact_freshness.py`, free zone; can ship separately).

## 5. Questions for the team

1. **Collapse repetition on a stand-aside run?** Hide CONFIDENCE and POSITION
   when both are zero. Recommended, if the tests allow it without touching a
   floor.
2. **Trim THE FULL PICTURE on a stand-aside run?** Recommended: keep it only when
   the decision is not STAND ASIDE, or when something changed. Its sentences are
   pinned by tests, so this needs an explicit old → new record.
3. **DATA BASIS** ("43 outcomes logged — accuracy not shown…"): keep it in the
   log but move it out of the top section? Rule 9 says a display must distinguish
   no observations from an unproven path; it does not say the owner must read it
   first.
4. **Should WATCH FOR also ship alone, first?** Recommended: yes. It is a truth
   defect the digest repeats every morning, and it needs none of the block.

## 6. Gates

**Gate 1:**
- **Truth sweep for §2:** over the existing regime grid, for every RANGING-daily
  cell, the named condition is the one that can reach a tradeable state, and
  neither old clause alone does. This is the check that turns §2 from INFERRED
  into VERIFIED. If it disagrees with §2, stop and report.
- **Decisions unchanged:** DECISION, the filter result, CONFIDENCE and POSITION
  are identical to `main` across `test_decision_logic.py`'s sweep. Stand-down
  matrix T34–T41 and the banned-token test pass unweakened.
- **The block triggers nothing:** real wrapper, digest and latest-view runs with
  the block present give the same notifications, the same ledger state and the
  same digest line, including closed market, a LONG, and hostile feed text in the
  REASON. A positive control at 0–2 spaces must be shown to trigger.
- **Change status:** prior run, no prior run and a failed read each render their
  own text.
- **Rule 12:** no new notification path. Existing cases send exactly what `main`
  sends, except where the digest's watch clause carries the corrected wording.

**Mutation:** block indent reduced to 2; old WATCH FOR restored; "no change" shown
when no prior run exists; block built from a copied sentence rather than the
REASON. Each must be caught.

**Gate 2:** a real brief under `scripts/reality_run.py`, shown in the run report,
with the word count before and after.

**Gate 3, PENDING LIVE CONFIRMATION:** the owner reads a real scheduled run and
says whether it is now easy to understand. That is the actual test.

## 7. Limits

This makes the brief easier to read. It does not make the framework catch more
moves, and it adds no evidence of an edge: no such edge is shown (R40–R42).
