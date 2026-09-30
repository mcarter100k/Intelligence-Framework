# Spec: exclusion registry fixes (Phase 0 of the 2026-09-29 audit plan)

Status: this spec is committed before any build commit on
`feat/exclusion-registry-fixes`. The owner directed Phase 0 in session
2026-09-29.
Protected files touched: `exclusions.py`, `regime_classifier_logger.py`,
`trade_outcome_logger.py`, `shadow_signals.py`, `session_memory.py`.
Merge is HELD for owner review.

## Why

The `/code-review` of `feat/exclusion-registry` in the 2026-09-29 audit
found that the registry's central promise, "an excluded row cannot reach
any tally", is broken in three ways, and that two of the tests meant to
prove the promise cannot detect its failure.

## Defects and fixes

### D1. A malformed registry silently turns off every exclusion

- **Evidence.** `_load()` catches only `OSError`. Two inputs get past it:
  - A hand-appended short row: `DictReader` fills the missing columns with
    `None`, so `r.get("ledger", "").strip()` raises `AttributeError`.
  - A non-UTF-8 byte raises `UnicodeDecodeError`.

  Either exception propagates to 7 call sites. Each one wraps the lookup in
  `try/except Exception` and substitutes an empty set, with no message. The
  nightly grader would then grade the contaminated
  `2026-09-16T09:08:08Z_GBP_AUD` row and write nothing to stderr. That
  violates the module's own rule: "Fail OPEN, loudly."
- **Also:** a *missing* registry returns `[]` with no message, although the
  docstring promises stderr.
- **Fix.**
  1. `_load()` catches every error while reading the file. A bad row is
     skipped *individually* and loudly; the valid rows still apply. That
     is safer than dropping every exclusion because of one bad line.
  2. A missing file, an unreadable file, a wrong header or a skipped row
     each print one line starting with `##ALERT## EXCLUSION REGISTRY`.
     That prefix matters: the brief wrapper keeps only `##ALERT##` lines
     from stderr, so an ordinary warning would be discarded
     (audit O3). With the prefix, the line reaches the day log and an
     ALERT notification.
  3. Each distinct message prints at most once per process, so a run that
     consults the registry from 7 places does not print 7 copies.
  4. The copy-pasted `try/import/except → set()` block at the 7 call sites
     is replaced by one helper, `exclusions.excluder(ledger)`. It returns a
     predicate `row -> bool` and never raises. The two `filter_rows` sites
     lose their silent `except Exception: pass` for the same reason.
     `exclusions` becomes a plain top-level import: it imports nothing from
     the repo, so there is no cycle, and if the module is missing that is a
     real error that must not be swallowed.

### D2. The shadow grader and the brief's pending-signal line ignore the registry

- **Evidence.**
  - `grade_pending_shadow` fills `outcome` / `r_multiple` for an excluded
    row.
  - `latest_pending_signal` can surface an excluded row as the pair's
    pending signal in the brief narrative.
  - By contrast, the regime and trade graders skip excluded rows.
- **Fix.** Both functions skip excluded rows. The grader passes them
  through to the rewrite untouched; the ledger is append-only, so the
  row stays in the record and simply never earns an outcome.

### D3. Two "cannot reach a tally" tests pass with exclusion switched off

- **Regime accuracy.**
  - *Problem:* the fixture's GOOD and BAD rows share instrument,
    prediction, price and ADX, one day apart. `_independent_states`
    already merges them into one observation, so `n == 1` holds with or
    without the registry.
  - *Fix:* also assert `n_raw == 1` and `correct == 1`, which fail when
    exclusion is off.
- **Session delta.**
  - *Problem:* `_get_today_rows` keeps only rows stamped with the *real*
    current UTC date. On any day other than 2026-09-16 no rows return and
    both assertions pass trivially.
    `monkeypatch.setattr(sm, "datetime", sm.datetime)` changes nothing.
  - *Fix:* freeze the clock at 2026-09-16 and assert the two honest rows
    ARE returned.

**Every new or fixed test must be shown to fail with exclusion disabled**
(Gate 1 includes a "would it have caught it" run).

## Out of scope (recorded, not fixed here)

- **Coarse shadow identity.** A shadow row's identity is
  `timestamp[_instrument]`, so a bare-timestamp exclusion removes every
  candidate on both pairs for that bar. The conservative reading is kept
  for now; per-candidate identity would be a registry schema change.
- **`test_ledger_headers::..._would_have_caught_the_2026_09_16_drift`** does
  not call the real checker. It moves to Phase 1 (test-harness safety).
- **A shared `_neutralize_side_effects` helper** (rule 10 names one; none
  exists). Also Phase 1.

## Verification

- **Gate 1:** the new tests cover a short row, a non-UTF-8 byte, a missing
  file and a wrong header. Each must stay fail-open, emit the alert exactly
  once, and keep honoring valid rows. The fixed D3 tests must fail with
  exclusion disabled. The full suite must be green.
- **Gate 2:**
  - Run the real nightly grader and the real brief from a temp working
    directory against copies of the real ledgers and the real registry.
    Hash the project before and after (rule 10).
  - Confirm the two registered rows stay ungraded and out of every tally,
    and that the registry produces no alert when healthy.
  - Confirm that a deliberately corrupted *copy* of the registry produces
    the alert line.
- **Gate 3 (pending live):** the first scheduled 15:15 grader run after the
  merge leaves `2026-09-16T09:08:08Z_GBP_AUD` ungraded (already listed in
  PENDING LIVE CONFIRMATION).
