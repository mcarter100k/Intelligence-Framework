# What a sharp FX trader reads, and what this framework covers

**As of 2026-10-31.** This list comes from reading the code and the
foundation docs, not from running anything. Re-check a row before relying
on it. "Have" means the framework covers the area, not that it has been
shown to help: nothing here is VALIDATED.

**Goal (owner, 2026-10-31):** the framework should make us sharp in the
markets. This file lists what matters for that and records which parts we
cover and which we don't. When an area is added or tested, update its row
with the date.

Status key: **HAVE** (live), **MANUAL** (exists, by hand), **PARTIAL**,
**NOT WIRED** (built, not running), **TESTED** (studied, result logged),
**MISSING**.

## Macro: what moves the currencies

| Area | Status | What we have / what's missing |
|---|---|---|
| Central-bank policy (BoE, RBA, BoJ): rate path and what the market prices | MANUAL | Written weekly in `storylines.md`. **Stale since 2026-09-10.** No data feed |
| Inflation, growth, jobs (CPI, GDP, employment) | MANUAL | Narrative only, in `storylines.md` |
| Economic calendar and event risk | HAVE | `news_gate.py` stands aside around high-impact GBP/AUD/JPY events. **USD events missing** |
| Surprise vs forecast (actual minus consensus) | MISSING | `calendar.csv` stores forecast and previous, but nothing uses them. The feed has no actual values, and the file is overwritten every fetch, so no history builds up |
| Interest-rate differentials and carry | TESTED | Carry after a quiet week: GBP/JPY REFUTED (R33), GBP/AUD INCONCLUSIVE (R34). Not a live input |
| Government action (yen intervention, fiscal news) | MANUAL | Intervention watch flag in `storylines.md`, read by `setup_check.py` |
| Whether the macro read improves decisions | MISSING | Agree/conflict with `storylines.md` has never been graded against outcomes. **It could not have been:** the `setup_check.py` parser finds zero biases in the real file's format (verified 2026-11-01 with a control). See `docs/driver_coverage_proposal.md` §1b |

## Cross-market and sentiment

| Area | Status | What we have / what's missing |
|---|---|---|
| US dollar and US yields (move GBP/JPY via USD/JPY) | MISSING | Mentioned by hand in the storylines "Backdrop" only |
| Risk-on / risk-off (equities, VIX); AUD is risk-sensitive | MISSING | |
| Commodities (AUD with iron ore, copper) | MISSING | |
| Positioning (COT, retail sentiment) | MISSING | |

## Price: the chart

| Area | Status | What we have / what's missing |
|---|---|---|
| Trend vs sideways, across weekly / daily / 4-hour | HAVE | `regime_detection.py` (thresholds are INFORMED PRIOR) |
| Exhausted, overextended moves (GBP/JPY) | HAVE | Exhaustion subtype; the framework stands aside on it |
| Key levels | HAVE | `levels_context.py`. Turns happen at levels about 90% of the time, but timing is unpredictable |
| Volatility (how far the pair typically moves) | HAVE | ATR-based; spike and compression stand-downs |
| Entry timing on hourly / 15-minute bars | HAVE | `entry_confirmation.py` |
| Profit targets | MISSING, by design | "Set your own; it must pay at least 1.5R after spread" |

## Micro: how the market trades and what it costs

| Area | Status | What we have / what's missing |
|---|---|---|
| Sessions and time of day (Tokyo, London, New York) | PARTIAL | Asian-session range used as a level only |
| Fixes and month-end flows (London 4pm, Tokyo fix) | MISSING | |
| Spread | PARTIAL | Fixed assumption (3.0 pips in studies, 4.0 in execution tools). Never measured live |
| Overnight financing (swap) | PARTIAL | Known to matter (R32: about 0.1R per 5-day GBP/JPY hold). **Not counted in the shadow ledger grading** |
| Liquidity, slippage, order flow, volume | MISSING | Prices are mid only; no bid/ask |

## Risk and the trader

| Area | Status | What we have / what's missing |
|---|---|---|
| Position sizing, stops, reward-to-risk | HAVE | `trade_management.py`, `risk_config.py` |
| Daily loss limit, position cap, two GBP pairs counted as one exposure | NOT WIRED | `session_guard.py`. Limits are **not enforced**. Must be wired before the first real-money trade |
| Trade management (breakeven, partials, trailing) | HAVE, as rules | `foundation/risk_and_execution.md` |
| Pre-trade checklist and journal | MANUAL | `setup_check.py`, `trade_logger.py`. Zero real trades so far (one paper test) |
| Grading the trader (process separate from outcome, weekly review) | NOT WIRED | Designed in `foundation/trader_review.md`, never run. The foundation calls this the biggest gap |

## Evidence: knowing what actually pays

| Area | Status | What we have / what's missing |
|---|---|---|
| Honest sample counting, power checks, pre-registration | HAVE | `foundation/tools/`, `foundation/methodology.md`. This is the framework's strongest part |
| Forward test of candidates | HAVE | `shadow_signals.py`. As of 2026-10-19: EARLY_MOMENTUM_v2 3 episodes (avg −0.20R), THRUST_PULLBACK 1, MOMENTUM_JOIN 1 |
| Tested ideas (34, most refuted) | HAVE | `foundation/research_findings.md`. Check here before testing an idea |
| Long-history test with costs (OANDA 2014–2021) | MISSING | The audit's recommended next evidence source |
| A proven edge | MISSING | |

## What would sharpen us most, in order

These are recommendations, not approved work. Changes to protected modules
need a spec and team review first (AGENTS.md).

1. **Reps, graded.** Start the `trader_review.md` loop on paper or at micro
   size.
2. **Refresh the macro read, then measure it.** Bring `storylines.md`
   current and log agree/conflict per decision so the market grades it.
3. **Add cross-market context**: USD events in the news gate, and a
   US-yields / risk-tone line in the brief as context only.
4. **Count costs**: spread and financing in shadow grading.
5. **Wire the circuit breaker** before any real money.
6. **Run the long-history cost-aware test** for honest sample size fast.
