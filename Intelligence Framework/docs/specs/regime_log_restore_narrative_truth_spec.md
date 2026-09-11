# Spec: regime-log restore + narrative truth (team-directed, safety class)

**Date:** 2026-09-10
**Status:** Team-directed build (freeze exception, safety class). Stage 1
diagnostics were reported to and read by the team before this build began.
**Branch:** feat/regime-log-restore-narrative-truth — merge held for team
review (protected-path files touched: decision_brief.py wiring only; no
decision logic changed).

## Stage 1 findings this spec responds to (summary of record)

1. **Item 0 — (TRENDING_DOWN, VOLATILE) cell.** "Wait for H4 to resolve"
   exists ONLY in the cell's `note` string (regime_detection.py:244). No gate
   between the table lookup and a rendered ENTRY block reads H4 state:
   `apply_filter`'s H4-aware blocks all require D1 RANGING/VOLATILE;
   `_derive_direction(d1, exec_mode)` never sees H4; the only H4 influence on
   the outcome is the +5 conviction bonus at official_decision.py:135 (bonus,
   never a block); the ENTRY block renders for any LONG/SHORT and
   `get_entry_brief` is display-only. Tonight's live SHORT @0.5x is therefore
   **mechanically intended behavior** (the cell's machine fields flow to a
   signal by design) with **semantically ambiguous authorship** (the sibling
   REDUCED_MOMENTUM cells carry tradeable intent; this cell's note promises a
   wait the code does not implement).
2. **Item 3 — regime_classification_log.csv silence.** `log_regime`'s only
   caller ever was `shadow/market_brain.py:114` (exception-swallowed). The
   official brief path never called it — decision_brief.py imports only the
   read side (`get_regime_accuracy`). All 25 rows came from two manual bursts
   (2026-06-28, and 2026-07-28/29 during cleanup audit #2 verification). The
   2026-07-29 quarantine of the shadow stack (commit 2188ad5) removed the
   last reachable caller. Root cause class: **never wired into the live
   path**; the six-week "gap" is in fact the whole life of the scheduled
   system. The prior audit's open question ("log_regime has no live caller")
   is confirmed.

## Team rulings encoded here

- **The cell's behavior does not change in this build.** Adding an H4
  resolution gate is a live-trading-logic change: separate spec, separate
  review, and it needs the outcome data this build restores. Until then the
  cell trades at 0.5x as designed, and the prose must say what the code does.
- **No backfill.** The missing classification history is honest evidence
  loss and is recorded as such in validation_log.md.

## Build items

### 1. Regime classification logging on every live brief run
- decision_brief.py wires `log_regime(regime, instrument)` immediately after
  the session snapshot (§1b), guarded by: regime has no error (already
  guaranteed at that point) and `market_open` is True (a closed-market run
  re-reads Friday's bars; it is not a new prediction).
- Logger failure prints one stderr line (captured in the wrapper's log) and
  never breaks the brief. Persistent failure is caught by build item 4a —
  silence is never the failure signal again.
- The subtype column (added 2026-09-09) flows automatically via
  `_subtype_tag`; the logger's additive header migration handles the CSV.

### 2. REDUCED_MOMENTUM REASON renders per actual (d1, h4) cell
`_build_reason`'s REDUCED_MOMENTUM branch dispatches on the cell:
- d1 RANGING + h4 trending → "4-hour up/downtrend inside a sideways daily
  market — suspect move, size reduced. Treat as a range trade with momentum
  bias." (If d1 subtype is EXHAUSTION, the daily is described as an
  overextended one-way move, not as sideways — exhaustion honesty rule.)
- d1 trending + h4 VOLATILE → "Daily up/downtrend intact, but the 4-hour
  chart has not resolved in that direction — size reduced. Wait for the
  4-hour chart to resolve before entering." (Matches the resolution-table
  note; the wait is the entry-trigger wait, the signal itself stands.)
- Any other combination → neutral reduced-size wording.
No raw regime tokens (trending_down etc.) in any rendered field.

### 3. FULL PICTURE alignment derives from regime fields
For LONG/SHORT decisions the narrative compares the decision direction
against weekly (weekly_context + lt_trend), regime_d1, and regime_h4:
- All three agree → the existing "All three timeframes line up" sentence.
- Any timeframe unresolved (sign 0) → name it: "...has/have not resolved in
  that direction yet", plus the honest size sentence (reduced size named only
  when size_mult < 1.0).
- Any timeframe opposed → say so plainly: it "currently points the other
  way — the picture is not aligned."
The sentence is never derived from the existence of a decision.

### 4. Systemic guards (both pinned by tests)
- **(a) Artifact freshness per run** — scripts/artifact_freshness.py holds
  the expected-cadence table (hours):
  | artifact | cadence | basis |
  |---|---|---|
  | regime_classification_log.csv | 72h | 3 scheduled briefs/weekday; covers weekend |
  | session_context_log.csv | 72h | same runs |
  | logs/brief_<today|yesterday>.log | 30h | one dated log per weekday (weekend-aware: allowance runs from last Friday) |
  | calendar.csv | 192h (8d) | weekly fetch + midweek retry |
  | storylines.md | 216h (9d) | weekly Sunday session |
  | shadow_signal_log.csv | 504h (21d) | candidates fire irregularly — generous by design; cadence is an informed prior, revisit with data |
  The wrapper runs the check after each brief; a brief that succeeds while
  any artifact is stale records a health FAILURE (health_state.py), so the
  existing 2-consecutive/daily-repeat alert plumbing fires the UNHEALTHY
  path. The Sunday heartbeat prints the full freshness report and treats
  STALE as NEEDS ATTENTION.
- **(b) Narrative-truth test matrix** — for a matrix of regime states,
  rendered REASON / FULL PICTURE claims are asserted against the fields,
  including a timeframes-disagree-under-SHORT case and the raw-token leak.
  The banned-token floor is extended to raw snake_case tokens in rendered
  prose (shadow candidate IDs remain allowed by name — they are deliberate
  ledger identities).

## Gates
- Gate 1: full suite green with the new pinned tests.
- Gate 2: live run of `python3 decision_brief.py GBP_AUD GBP_JPY` — real
  OANDA, both pairs; verify honest narration on the live regime and that
  regime_classification_log.csv gains rows with the subtype column; real
  `artifact_freshness.py check` output in the run report.
- Gate 3 (PENDING LIVE CONFIRMATION, validation_log.md): first scheduled
  wrapper run writes a classification row; freshness UNHEALTHY path fires on
  a real (or deliberately induced) staleness, not only in tests.
