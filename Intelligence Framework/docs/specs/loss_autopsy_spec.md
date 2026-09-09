# Spec: loss autopsy (Spec C of the 2026-09-09 post-audit directive)

**Status:** team-directed 2026-09-09, sequenced after Spec B. Motivated by
the founding exhibit: the first graded shadow episode lost −1.0R to a
32.9-pip stop and then ran 809 pips in the signal's direction
(validation_log 2026-09-09). Losses are not one thing; the program exists
to say WHICH thing each one was, at honest N, before anyone touches a stop
parameter.
**Branch:** `feat/loss-autopsy` (stacked on `feat/circuit-breaker`).
Merge held for team review.

## Where it hooks (directive): the grading seam

`shadow_signals.grade_pending_shadow`, after the outcome `r.update(...)`
and before the file rewrite. Everything needed is already in scope — entry,
stop, direction, risk, the 30-bar future window, and the full pre-entry
H/L/C history. **Triggers are untouched; frozen candidate specs are
untouched.** One column appends to `_FIELDS`: `loss_species` (empty for
wins and for unclassifiable rows).

Because the ledger's header predates the column, the logger performs a
one-time additive header migration on its next write (existing rows gain
an empty `loss_species`; nothing else changes — recorded in
validation_log). Reading tools that address columns by name are
unaffected.

## The species (frozen definitions; first match wins)

Classified only for R-losing rows (`hit_stop` True or negative net) that
pass the invalid_spec guard — unscoreable rows are never autopsied.

1. **event_window** — the row's fire-time `extra` carries
   `news_window=true` (the news-gate stamp). Honest limitation, stated
   plainly: this is the only event marker the ledger records;
   reconstructing past calendars would be manufactured hindsight.
2. **stopped_then_reversed** (noise stop) — the stop was hit, and AFTER
   the stop-hit bar price ran ≥ 2R beyond entry in the signal's direction.
   The trade was right; the stop was inside the noise.
3. **exhaustion_entry** — at entry the close sat ≥ 2.0 fire-time ATR
   beyond the 20-bar mean in the trade direction: the signal chased an
   already-extended move.
4. **never_onside** — MFE < 0.25R: the trade was wrong from the first bar.
5. **bled_out** — everything else: no meaningful excursion either way, or
   a grind into the stop late in the window.

Priority order is part of the frozen definition (a stopped-then-reversed
row in a news window is an event_window row — the event owns the tape).

## Backfill

`backfill_loss_species(instrument)` classifies already-graded valid rows
whose `loss_species` is empty, using the same code path and a fresh H4
fetch (count=500 reaches ~83 days — covers the July rows). Invoked
manually (it is how Gate 2 grades the founding exhibit); scheduled runs
classify at grading time from now on.

## Gates

- **Gate 1:** pinned synthetic paths, one per species; priority pins
  (event_window beats stopped_then_reversed; stopped_then_reversed beats
  exhaustion); wins stay unclassified; invalid rows never classified;
  header migration preserves every existing row byte-for-byte in the old
  columns.
- **Gate 2 (REALITY):** real backfill on the live ledger — the founding
  exhibit (row 1) must classify `stopped_then_reversed` from real H4 data;
  rows 2–3 stay untouched (invalid_spec); the ledger's other columns
  byte-identical before/after except the appended column.
- **Gate 3:** first loss classified at scheduled grading time (needs a
  future graded loss — only time provides one).

## Explicitly not in scope

No parameter changes to any candidate; no stop-width tuning "informed" by
species counts until a review gate (FLAG N=30 of GRADED outcomes per
candidate) is reached — species tallies below that N are anecdotes, and
the honest-N rules apply to autopsy conclusions exactly as to win rates.
