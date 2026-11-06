# Execution readiness: state of items A1–A5 (2026-11-06)

**For the team.** Each item's state was checked before anything was built.
Specs are committed for review; nothing on the protected path is built.

| Item | State found | Action taken |
|---|---|---|
| A1 Wire the circuit breaker | Not wired: no live caller (grep) | Spec PROPOSED: `docs/specs/circuit_breaker_wiring_spec.md` |
| A2 Planned entry in the journal | **Built 2026-10-15 on `feat/decision-reasoning`, never merged, never reviewed** | No new spec; review request below |
| A3 Broker question | Answered as far as read-only access allows | Report below |
| A4 Stop and target in the brief | **Built 2026-10-15 on the same branch, never merged, never reviewed** | No new spec; review request below |
| A5 Computed position size | A function exists (`risk_config.calculate_lot_size`) but is unwired and has two wrong defaults | Report below; not built (waits for A1) |

## A2 and A4: built, held, and now three weeks behind

- **Where they are:** both are on `feat/decision-reasoning`: 13 commits and
  23 files from merge-base `a3e070b` (2026-10-15). The protected files it
  touches are `decision_brief.py`, `setup_check.py`, `session_memory.py`,
  `regime_detection.py`, `entry_confirmation.py`, `news_gate.py` and
  `oanda_feed.py`.
- **Its own validation_log entry,** present only on the branch, is headed
  "Merge HELD for team review".
- **`main` has no record of it.** Its spec (`docs/specs/decision_reasoning_spec.md`)
  exists only on the branch, and `main`'s validation_log never mentions the
  change set.
- **A2 as built:** `pre_trade_journal.csv` gains `price_at_check`,
  `planned_entry` and `planned_entry_source`, by additive migration.
  - Every distance is computed from `price_at_check`.
  - The spec records that earlier rows are UNOBSERVED for entry precision,
    with no backfill (M23). The branch counts 6 such rows.
- **A4 as built:** the option chosen is "stop referencing it" (spec 5F). The
  sentence "The stop marks where that idea would be proven wrong" is replaced
  by a pointer to the EXIT IF line the brief does show. The branch reports
  decision parity "0/324" and its own mutation counts.
- **Why no new specs were written:** writing them would duplicate a spec and
  an implementation that already exist.
- **The review decision:**
  - **(i)** review the branch as it stands;
  - **(ii)** split out A2 and A4 as a narrow slice, re-based on current
    `main`, for a smaller review;
  - **(iii)** reject it and re-spec.
- **Either way, the branch must be re-based before any merge.** `main` has
  moved its tests under `tests/` and changed `decision_brief.py` since
  2026-10-15.

**New finding that strengthens A2:**
- `setup_check` measured every distance from `regime["current_price"]`.
  Before 2026-09-30 (data_at_source_spec P1) that was **the previous daily
  close**, not the market.
- For the journal's GBP/AUD rows, the price the distances were measured
  from equals the previous daily close: to 0.00 pips on four rows, and 0.40
  on the fifth (rounding to 4 decimals). It lies outside the hour's actual
  range on every row.
- **So the recorded `stop_pips`, `stop_atr_multiple` and the "stop inside
  noise" verdicts in all six rows describe distances from yesterday's close.**
  - The 2026-09-09 "7.2-pip" stops were 0.2–1.1 pips from the market.
  - The 2026-09-11 "92.6-pip" stop was about 106–115.
- **This is recorded, not corrected.** The journal is append-only; an
  annotation would go through the exclusion registry, which is protected.
  (Details: `studies/journal_scoring_report.md`.)

## A3: what the OANDA account can do (read-only probe, 2026-11-06)

Source: `studies/broker_capability_probe.py`, GET requests only, run through
`reality_run.py`. **No order was placed.** Balance and account id were not
printed.

| Question | Answer |
|---|---|
| Environment | live (`api-fxtrade`) |
| Account currency | USD |
| Hedging | disabled |
| Guaranteed stops | disabled |
| Account margin rate | 0.02; GBP_AUD and GBP_JPY 0.05 each (20:1) |
| Minimum trade size | 1 unit; whole units (`tradeUnitsPrecision` 0) |
| Maximum order | 100,000,000 units (GBP_AUD); 50,000,000 (GBP_JPY) |
| Trailing stop distance | 5 pips to 10,000 pips (GBP_AUD 0.0005–1.0; GBP_JPY 0.050–100.000) |
| Orders, trades, positions endpoints | all answer the read (HTTP 200), with 0 items each |
| History | `/positions` lists every instrument that has ever held a position on the account (OANDA's documented meaning, INFERRED here). It returned none: **the account appears never to have traded.** |
| Can it place, modify, cancel orders? | **Not verified.** The v3 API supports MARKET, LIMIT, STOP, MARKET_IF_TOUCHED, TAKE_PROFIT, STOP_LOSS, GUARANTEED_STOP_LOSS (disabled here) and TRAILING_STOP_LOSS orders. Whether this token may place them can only be shown by placing one, which was not done. |

**Reading:**
- The account is a live, tradeable-configured USD account that has so far
  served only as the data feed.
- Live execution there looks like a small step technically: unit-level
  sizing, native stop-loss and trailing-stop orders.
- **Unverified:** order permission.
- **The owner's question, not the account's:** where the owner actually
  executes today.

## A5: what a computed position size would take

`risk_config.calculate_lot_size` exists but has no caller. It computes:

> lots = balance × risk% ÷ ((stop pips + spread pips) × pip value per lot)

To be correct for this account it needs:

1. **The account balance:** the same open decision as A1 §4.
2. **Risk % per trade:** the conviction tiers in `GRADE_CONFIG`: A+ 1.5%,
   A 1.0%, down to the base 0.5% in `RISK_RULES`. These exist.
3. **The stop distance from the market price at the check.** That is live
   since 2026-09-30, but recorded only once A2 lands. The six existing rows
   show what happens without it (above).
4. **Pip value in USD, not the default $10 a lot:**
   - GBP_AUD's pip is 0.0001 AUD per unit, so it needs the live AUD/USD
     rate.
   - GBP_JPY's pip is 0.01 JPY per unit, so it needs the live USD/JPY rate.
   - The $10 default overstates both.
5. **Units, not lots:** OANDA sizes in whole units from 1. The function
   rounds to 0.01 lots (1,000 units) and warns below 0.01 lots, which is
   coarser than the account allows.
6. **The real spread:** the 2026-11-06 measurement gives GBP_AUD a median of
   5.1 pips against the 4.0 default.
7. **The breaker and open-risk caps:** `max_open_risk_pct` 2.0, and the
   shared-currency grouping (A1 §9).

Order of work: A1, then A2, then sizing. A size calculated without the
breaker behind it is the wrong order, as the task states.
