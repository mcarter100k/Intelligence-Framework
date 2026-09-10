# Spec: state-dependent labels (freeze exception — label honesty, 2026-09-10)

**Status:** team-directed freeze exception, same class as the regime
subtype fixes: the words tell the truth about the state; decisions
byte-identical. **Branch:** `feat/state-dependent-labels`. Merge held.

## The dishonesty being fixed

Every brief labels its condition slot "EXIT IF" — but a STAND ASIDE brief
has no position to exit. There, the sentence is a WATCH condition (what
changes the framework's read), and labeling it an exit over-promises: the
concrete pivot sentence ("…the downtrend is confirmed then") reads like a
trade plan when confirmation only changes the READ.

## Rendering by state

- **STAND ASIDE:** the slot is labeled **WATCH FOR**. The concrete
  pending-pivot sentence gains the directed guard clause: "…the downtrend
  is confirmed then — the trade still depends on the filter, the
  calendar, and a valid stop. Revisit then." (uptrend mirror). Generic
  watch sentences are already read-changes, unchanged.
- **LONG / SHORT:** three slots — **ENTRY** (trigger + level, from the
  entry brief the trade path already computes; read-only fetch on this
  rare path), **EXIT IF** (the invalidation — meaning restored: a
  position exists, this is where it is wrong), **TARGET** (honest: the
  framework does not generate targets — "set your own; it must pay at
  least 1.5x what you risk after the spread — the pre-trade check does
  the math"). Inventing target levels would be a decision change; this is
  the truthful display of what exists.
- **THE FULL PICTURE** follows the same state logic: the stand-aside
  narrative already phrases the condition as "This changes when …" (watch
  semantics — the guard clause flows in via the shared sentence); the
  trade narrative already reads the stop as invalidation.
- The daily digest's watch extraction accepts both labels (WATCH FOR on
  stand-aside briefs, EXIT IF on trade briefs).

## Freeze/queue note

The POST-FREEZE QUEUE's first item is recorded with this spec but NOT
built: an "IF IT CONFIRMS" conditional plan on stand-aside briefs when
the WATCH FOR condition is within 2 sessions — play name, trigger, stop,
first target, noise-stop check pre-run, storyline agreement — explicitly
conditional, never a signal. Spec after 2026-09-16.

## Gates

- **Gate 1:** pinned per state — STAND ASIDE renders WATCH FOR and never
  EXIT IF; LONG renders ENTRY/EXIT IF/TARGET in order; the guard clause
  on the concrete sentence (both directions); digest watch extraction
  under both labels; banned tokens; decisions byte-identical (suite +
  official-decision pins).
- **Gate 2 (REALITY):** live briefs on both pairs — WATCH FOR label and
  the guarded concrete sentence on today's real GBP/AUD state.
