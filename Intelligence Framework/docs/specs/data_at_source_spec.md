# Spec: fix the data at the source (Phase 4 of the 2026-09-29 audit plan)

Status: this spec is committed before any build commit on
`feat/phase4-data-at-source`. The owner directed Phase 4 in session
2026-09-30. Merge is HELD for owner review, AND until the Phase 2/3 Gate-3
checks of the 02:30 brief and the 15:15 grader pass. Otherwise a failure in
those runs could not be attributed.

Protected files touched: `regime_detection.py`, `no_trade_filter.py`,
`decision_brief.py`, `regime_classifier_logger.py`,
`trade_outcome_logger.py`.

## Why

Each defect was reproduced on `main` (ce4cab6) on 2026-09-30 at 08:20 UTC,
before any change. Every measurement has a control showing it can report
"correct".

| # | Defect | Observed on main | Control |
|---|---|---|---|
| P1 | `current_price` is the previous D1 close, never the live price | GBP/AUD brief price **1.8938** = the last closed D1 close exactly, while OANDA's live mid was **1.90163**: **78.3 pips off**. GBP/JPY: 6.5 pips off | — |
| P2 | Market hours hard-coded at 21:00 UTC; holidays ignored | After US DST ends (2026-11-01): Sun 21:30Z (NY 16:30, closed) reads OPEN; Fri 21:30Z (NY 16:30, open) reads CLOSED. Christmas and New Year's Day read OPEN | summer Sun/Fri and midweek cases read correctly |
| P3 | A failed weekly fetch silently disables the 20-week trend gate | D1/H4 downtrend + weekly fetch failed → `weekly_context=RANGING`, filter "All filter conditions passed" | the same trade with weekly data present is blocked ("Short blocked: dominant 20-week trend is UPTREND") |

**Why P1 matters beyond the display.** `current_price` is recorded as
`trade_signal_log.price_at_signal` (the grader's entry price) and as
`regime_classification_log.price_at_log`. Every graded directional call has
been scored from yesterday's close, crediting or charging moves that happened
before the signal existed. The mechanism: `oanda_feed._get_bars` drops the
forming candle, so `_split_live_bar` never finds a live bar to split.

## Changes

1. **P1: the live price, labelled.**
   - `get_regime` takes `current_price` from OANDA's pricing endpoint
     (`oanda_feed.get_live_price`, the bid/ask mid). It sets
     `price_basis="live"`.
   - If the live price is unavailable, it falls back to the last closed D1
     close with `price_basis="prior_close"`. Never silently: the brief shows
     "Price is the previous daily close — the live price could not be
     fetched", and the reason goes to stderr (Phase 2 keeps it in the day log).
   - Indicators still use closed bars only; nothing about look-ahead changes.
2. **P1: every price row records its basis.**
   - A `price_basis` column is appended to `regime_classification_log.csv`
     and `trade_signal_log.csv`.
   - Existing rows get a blank basis. That is unambiguous: the audit showed
     every pre-fix row used the prior close, because the live branch was
     unreachable.
   - This is the ledger-version boundary Phase 7 needs: rows are separable
     by basis, not by guesswork.
3. **P1: controlled header migration AT MERGE (owner approves separately).**
   - The two ledgers gain the column through the loggers' own
     `migrate_header` (ledger_io, locked and atomic), run once right after
     merge, after `scripts/backup_ledgers.py` has taken a verified copy.
   - It is verified by comparing every pre-existing row value against the
     backup: they must be identical, with only the new blank column added.
   - Without it, `test_ledger_headers` fails on the live checkout until each
     logger's next write, and a trade signal can be weeks away.
4. **P2: market hours from New York time.**
   - The FX trading day D runs from 17:00 America/New_York on D−1 to 17:00
     on D, so trading date = (NY local time + 7h).date().
   - The market is **closed** when the trading date is a Saturday or Sunday,
     or is Dec 25 or Jan 1. Source: the OANDA D1 census for 2023–2026 found
     exactly those weekdays missing (foundation/market_data_facts.md).
   - `next_open_utc` is 17:00 New York on the day before the next open
     trading date, which is correct across both DST switches.
5. **P3: a weekly outage stands down.**
   - A missing, empty or too-short weekly fetch sets
     `weekly_context = lt_trend = st_trend = "UNAVAILABLE"` and
     `weekly_available=False`, mirroring the H4 outage sentinel.
   - `apply_filter` adds a hard block: "Weekly trend data unavailable — the
     20-week trend check cannot run, so standing aside."
   - `_plain()` renders UNAVAILABLE in plain English. That also covers the
     existing H4 sentinel, which printed raw.

## Out of scope (recorded)

- Removing the now-vestigial `_split_live_bar` calls. They split nothing,
  and their removal is a separate cleanup.
- Phase 5 decision-logic defects.
- Grading from `price_basis`, and the new ledger version: Phase 6/7.

## Verification (evidence-validation standard, AGENTS.md rule 11)

- **Gate 1.**
  - The P1–P3 measurement script re-run on the branch must show every
    defect fixed, with the controls unchanged.
  - The new tests must fail on main's code.
  - Mutation tests, with caches cleared and a re-run after each revert.
  - The full suite under the whole-project guard, plus the audit-hook
    probe.
  - `/code-review`, with every finding reproduced before fixing.
- **Gate 2.**
  - Real OANDA: the branch's `get_regime` price matches the live mid within
    3 pips on both pairs.
  - `reality_run` brief and grader against the live ledgers: the new rows
    carry `price_basis=live` in the ledger copies, and the project is
    UNCHANGED.
  - A forced live-price failure shows the `prior_close` label in the brief.
  - The real wrappers run end to end on a project copy.
- **Gate 3 (PENDING).**
  - The first scheduled briefs after merge log `price_basis=live` prices
    within 3 pips of the live mid.
  - The first real Sunday and Friday market-hour boundaries after
    2026-11-01 are handled correctly.

## Addendum (2026-09-30): design correction and `/code-review` findings

**Design correction (from V2/V3).** Only the displayed price and the trade
entry (`trade_signal_log.price_at_signal`, basis `live` / `prior_close`) use
the live mid. Classification inputs (`atr_pct`, the moving-average context,
`range_position`) and the regime ledger's `price_at_log` use
**`last_close`**, the closed D1 bar the classification was computed from,
with basis `d1_close`.

Why: the first build let the live mid leak into those inputs.
- Two runs on the same bars flipped `range_position` 0.0 ↔ 1.0, which
  drives the range-trade direction.
- Repeat logs of one state no longer de-duplicated.

The closed bar is also the right baseline for D1-bar regime outcomes.
Basis values: `live`, `prior_close` (fallback), `market_closed` (no pricing
request is made), `d1_close` (regime rows), and blank (pre-fix rows).

**Findings.** Each was reproduced on the branch before fixing, then
re-measured fixed with the same script. All 10 were confirmed.

| # | Finding | Fix |
|---|---|---|
| V1 | 20–22 weekly bars passed as "available" but the 20-week read needs 23, so the gate was skipped silently | `_WEEKLY_MIN_BARS = 23` |
| V2/V3 | The live mid leaked into classification and broke de-duplication | See the design correction above |
| V4 | Tests read the real news calendar; a planted event 59 min out failed them | conftest redirects `news_gate._CALENDAR_FILE` |
| V5 | A missing basis defaulted to "live" | Defaults to "unknown", shown as "Price source unknown" |
| V6 | `get_live_price` recorded no reason | Records `last_error` like the bar fetches |
| V7 | The stale-feed check ignored Dec 25 / Jan 1 (a false "feed stale" on Dec 28) | One `is_trading_day` calendar for both |
| V8 | A weekend quote was labelled live | `market_closed`, with no pricing request |
| V9 | The error path kept RANGING | UNAVAILABLE plus `weekly_available=False` |
| V10 | A dead `try` | Removed |
