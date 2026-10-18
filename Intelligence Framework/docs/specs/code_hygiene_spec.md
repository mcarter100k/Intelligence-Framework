# Spec: protected-path code hygiene (2026-10-18). TEAM REVIEW REQUIRED before merge

**Status:** committed before any build commit on `chore/protected-hygiene`.
It comes from a five-dimension review with an adversarial verifier per
dimension (dead code, redundancy, structure, hygiene, comments; 72 findings,
43 confirmed, 29 corrected). Only the protected-path items are here; the
free-zone items already merged (c483c5b).

**Intent: no decision changes.** Every change below either (a) edits only
comments and docstrings, or (b) removes code that nothing reaches. Two
items change printed text, and both are named. The floors are untouched:
- T34–T41 in `tests/test_regime_detection_p1.py`;
- the banned-token test in `tests/test_brief_display.py`;
- the 36,864-cell decision grid.

`REQUIRED_KEYS` in the floor file is a schema list outside T34–T41. It
loses only the keys deleted below.

## A. Comments and docstrings (no code change)

Proven by AST equality with docstrings removed (`ast.dump` of each module
identical to main).

- `oanda_feed.py` module docstring. It described a yfinance fallback and three files that do not exist. The new one says: OANDA only, complete bars only, never raises. On failure it returns None, and `last_error()` names the cause for bar fetches; the live price's no-quote path records none.
- `regime_detection.py`:
  - The module header now covers both pairs, OANDA, and the real trend-strength bands (18 / 25 / 35 for GBP/JPY exhaustion).
  - `get_regime` gets a docstring.
  - `_classify_ex`'s docstring had 32+ for GBP/JPY exhaustion; it is now 35. It also no longer offers a "size down" path for 18–25 that does not exist, or calls an INFORMED PRIOR "validated".
  - `_detect_structure` gets its real pivot rule: ties count, the halves comparison runs when either side has fewer than 2 swings, and the under-18-bar path is unreachable from `get_regime`.
  - The slope comment: slope restates the structure, so STRUCTURE_DISAGREES cannot come out of `get_regime`.
  - The weekly-constants provenance now says INFORMED PRIOR; `htf_structure` no longer exists.
- `official_decision.py`: the inputs are INFORMED PRIOR, not "validated". The note pointing to `decision_engine` and shadow mode is removed. The GBP/JPY N=16 finding is marked INSUFFICIENT.
- `no_trade_filter.py`:
  - The module header lists the stand-down checks in code order. The counter-trend override skips the 20-week and table checks, and that is now stated.
  - The news window is 2h before to 30m after.
  - The 22-line history in the weekly gate becomes 3 lines.
- `decision_brief.py`:
  - `get_decision_brief` names its ledger writes (open market only), and the CLI's shadow log.
  - Step comments are added.
  - The incident narratives become one-line pointers. "Cause 3a/3b" stays, because decision_logic_spec records Cause 2 as removed.
  - The DATA BASIS docstring flags the known-broken accuracy measure (audit item 2).
- `regime_classifier_logger.py`:
  - The USAGE block has the real signatures and callers.
  - A comment says `composite_regime` holds the DAILY label.
  - The `_measure_outcome` docstring states MR_WIN's known defect.
- `shadow_signals.py`:
  - The episode-count comments state its known overcount (clock hours, ungraded rows).
  - `grade_pending_shadow` gets a docstring.
  - The incident narratives are shortened. The EARLY_MOMENTUM_v2 freeze contract (v1 trigger plus one guard; a further change starts v3) is kept in place.
- `run_outcome_check.py`: `main` gets a docstring.
- Small stale facts:
  - `trade_outcome_logger` (TradeSignal);
  - `session_memory` (7 readings; daily structure);
  - `entry_confirmation` (INFORMED PRIOR);
  - `levels_context` (both pairs);
  - `regime_detection` 2025-06-28, corrected to 2026-06-28.

## B. Unreachable code removed

Proven by the full suite, by a real-brief diff and a grader diff (main vs
branch, same ledgers, `reality_run`), and by the mirror test (direction
pairs unchanged).

1. **`_split_live_bar`** never splits. The feed drops the forming candle, and a complete candle's open is always at least one bar old. Closes the backlog entries at data_at_source_spec "Out of scope" and validation_log 2026-07-29.
   - Replaced by an age-only helper.
   - Removed: the `live_bar_d1` branch, the `live_bar_in_progress` key and field, and the unreachable "Daily bar in progress" line.
   - `last_closed_bar_age_hours` stays: the staleness warning reads it.
2. **Outputs of `get_regime` that nothing reads.** In both `get_regime` and `_error_result`:
   - the fuel / range block (`today_high/low`, `range_used/remaining`, `fuel_pct/label`), which was computed from the last CLOSED day;
   - `range_high/low`;
   - `filter_summary` and `no_trade_filter.get_filter_summary`;
   - `FilterResult.override_conditions`;
   - the `atr_compression_min` key (the PairConfig attribute stays);
   - `adx_exhaustion_note`;
   - the legacy `regime_label` / `trade_guidance` / `vol_note` prose, about 90 lines; the brief builds its own wording.
3. **Data-format guards.** Nine yfinance-era MultiIndex flattening guards (`if hasattr(x.columns, "levels")`). OANDA frames are always flat. The shadow_signals sites are data plumbing, not frozen candidate parameters, so no new candidate id is needed.
4. **Dead members:**
   - `PairConfig.ticker` and `_DEFAULT_PAIR` (with their test asserts);
   - `to_pips` / `from_pips` (with their tests);
   - `exclusions.is_excluded`, a test-only duplicate of `excluder`; the tests move to `excluder`;
   - the `MIN_SAMPLES_FOR_REVIEW` alias, whose importer was removed in 46dab4e;
   - the five `EntryBrief` fields nothing reads.
   - `LOSS_SPECIES` stays and is pinned by a test as the statement of the frozen species set.
5. **`shadow_signals.backfill_loss_species`**: a one-time path that has already run. The nightly grader classifies every loss itself. Git history keeps it, and loss_autopsy_spec gets a dated note.
6. **Duplicated writers:**
   - `calendar_fetch` writes through `ledger_io.atomic_write_rows`. Its own temp-file write had no fsync and no lock. "Keep the existing file on any failure" still holds.
   - `levels_context._current_session` reads `_SESSIONS` instead of repeating the hours, keeping the "Asian" fallback for 22–23 UTC.

**Printed-text changes** (named, because the trader reads them):
- `run_outcome_check`'s review hint pointed to a removed folder and a root-level script. It now names `studies/validate_thresholds_v2.py`.
- `oanda_feed.get_live_price`: no text change. Its comments now stop promising that every failure path records a reason.

## C. Not done here: decisions for the owner or team

- **Renames.** The names are unclear, but each costs a protected change for naming alone. Proposed, not executed:
  - `trade_outcome_logger.py` → `trade_signal_ledger.py`. It writes and grades `trade_signal_log.csv`; "logger" hid the grading half.
  - `session_memory.py` → `session_snapshot.py`. `session_context.py` is unavailable: it is the path of a deleted legacy module.
  - `intraday_context.py`: fold it into `levels_context.py`, or rename it to `asian_session_range.py`.
  - `trade_logger.py` stays: it is the trader's command, and its docstring says "Manual trade journal".
  - Each rename needs `git mv`, every import and mock.patch string, LIVE_CORE and AGENTS.md, a dated validation_log mapping, and a Gate 2 run. The guard added in c483c5b fails if LIVE_CORE and AGENTS.md drift.
- **`session_guard.py` and `risk_config.py`.** Nothing calls them, and `risk_config`'s grade table contradicts `official_decision`'s. Wire them or delete them. Deleting them also moves the foundation citations that name `risk_config` line numbers.
- **One pip-size helper** next to `PAIRS`, raising on an unknown pair instead of silently using 0.0001 (incident I5). Raising would stop the shadow grader on a stray row, so raise vs skip-and-alert is a decision.
- **Episode counting.** `shadow_signals.episode_count` counts clock hours and ungraded rows (audit item 3). Fixing it is a methodology correction with its own spec.
- **`trade_management.py`.** The protected `setup_check` imports it, so it is on the execution boundary: protect it, or record why not.
- **`oanda_feed.get_live_price`'s silent paths.** Its no-quote path records no reason, and its closeout path keeps a stale error. Fixing them is a small behaviour change.
