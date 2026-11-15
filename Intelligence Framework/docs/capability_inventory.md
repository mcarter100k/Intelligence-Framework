# What a sharp FX trader reads, and what this framework covers

**As of 2026-10-31; rows updated 2026-11-04 carry that date.** This list comes from reading the code and the
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
| Economic calendar and event risk | HAVE | `news_gate.py` stands aside around high-impact GBP/AUD/JPY events. Tested 2026-11-01 (R35, R36): scheduled US releases are INCONCLUSIVE on both pairs, so they come in as context, not a gate. **US events shown as context since 2026-11-03** (`US DATA` line in the brief, merge `99919de`); first live render 2026-11-04 after the 02:33 PST calendar fetch wrote 4 US events |
| Surprise vs forecast (actual minus consensus) | MISSING | `calendar.csv` stores forecast and previous, but nothing uses them. The feed has no actual values, and the file is overwritten every fetch, so no history builds up |
| Interest-rate differentials and carry | TESTED | Carry after a quiet week: GBP/JPY REFUTED (R33), GBP/AUD INCONCLUSIVE (R34). Not a live input |
| Government action (yen intervention, fiscal news) | MANUAL | Intervention watch flag in `storylines.md`, read by `setup_check.py` |
| Whether the macro read improves decisions | MISSING | Agree/conflict with `storylines.md` has never been graded against outcomes. **It could not have been:** the `setup_check.py` parser finds zero biases in the real file's format (verified 2026-11-01 with a control). See `docs/driver_coverage_proposal.md` §1b |

## Cross-market and sentiment

| Area | Status | What we have / what's missing |
|---|---|---|
| US dollar and US yields (move GBP/JPY via USD/JPY) | MISSING | Mentioned by hand in the storylines "Backdrop" only. USD/JPY, GBP/USD, AUD/USD are on the account with daily history from 2002; yields are not (instrument probe, 2026-11-01) |
| Risk-on / risk-off (equities, VIX); AUD is risk-sensitive | MISSING | The account offers no index products: needs an outside source such as FRED |
| Commodities (AUD with iron ore, copper) | MISSING | The account offers no commodities: needs an outside source |
| Positioning (COT, retail sentiment) | MISSING | |

## Price: the chart

| Area | Status | What we have / what's missing |
|---|---|---|
| Trend vs sideways, across weekly / daily / 4-hour | HAVE | `regime_detection.py` (thresholds are INFORMED PRIOR) |
| Exhausted, overextended moves (GBP/JPY) | HAVE | Exhaustion subtype; the framework stands aside on it |
| Key levels | HAVE | `levels_context.py`: previous day and week highs and lows, session high and low, Asian range. Turns happen at levels about 90% of the time, but timing is unpredictable |
| Swing structure levels, zones, Fibonacci (a hand markup) | MANUAL (method only) | Added 2026-11-04: `foundation/chart_reading_method.md`, every rule tagged UNTESTED or with its finding. Nothing in the brief draws swing levels, zones or Fibonacci lines. Pullback depth is descriptive only (R39: most first pullbacks reach 38.2%); buying the touch shows no edge (R37, R38) |
| Volatility (how far the pair typically moves) | HAVE | ATR-based; spike and compression stand-downs |
| Entry timing on hourly / 15-minute bars | HAVE | `entry_confirmation.py` |
| Breakout confirmation (two hourly closes beyond a level) | TESTED (2026-11-14) | R43, GBP/AUD 2005–2013: 31% of first closes are fakes and the second close filters them, but confirmed breaks, first-close entries and retest entries all lost after costs (REFUTED, N 1,082–1,494). A filter for staying out, not an entry edge |
| Breaks of weekly/daily levels with the daily trend, obstacle check and 1.5R/2.5R targets (the owner's method, mechanised) | TESTED (2026-11-14) | R44, GBP/AUD 2005–2013: all four cells REFUTED (−0.28 to −0.35R after costs, N 55–64); the filters did not help. 2021–2026 replication also negative |
| Profit targets | MISSING, by design | "Set your own; it must pay at least 1.5R after spread" |

## Micro: how the market trades and what it costs

| Area | Status | What we have / what's missing |
|---|---|---|
| Sessions and time of day (Tokyo, London, New York) | PARTIAL | Asian-session range used as a level only (live). **Described 2026-11-05** on 2005–2013 hourly data (`studies/session_movement_report.md`, descriptive, not a strategy): two busy windows (London morning 07–09 UTC, London/New York overlap 12–15 UTC; peak 14:00 UTC = 06:00 PST), busiest hour about 1.8–1.9× the quietest; by 07:00 PST about 7 days in 10 already have their high, and the same for their low. Not used by the live path. Asian-range breakout question spec'd, not run. **Replicated 2026-11-05 on 2021-04 → 2026-09** (`studies/session_movement_replication_report.md`): same shape and peak hour; concentration stronger (busiest/quietest 2.40 GBP/AUD, 2.53 GBP/JPY); the pre-set day-trading precondition FAILS for both pairs |
| Fixes and month-end flows (London 4pm, Tokyo fix) | MISSING | |
| Spread | PARTIAL | Fixed assumption (3.0 pips in studies, 4.0 in execution tools). **Measured 2026-11-06** (one month of bid/ask hourly closes): GBP/AUD median 5.1 pips, GBP/JPY 3.5. The tools still use 4.0 (team amendment pending) |
| Overnight financing (swap) | PARTIAL | Known to matter (R32: about 0.1R per 5-day GBP/JPY hold). **Not counted in the shadow ledger grading.** Today's broker rates (2026-11-01): GBP/JPY long +1.6%/yr, GBP/AUD long −1.89%/yr |
| Liquidity, slippage, order flow, volume | MISSING | Prices are mid only; no bid/ask |

## Risk and the trader

| Area | Status | What we have / what's missing |
|---|---|---|
| Position sizing, stops, reward-to-risk | HAVE | `trade_management.py`, `risk_config.py` |
| Daily loss limit, position cap, two GBP pairs counted as one exposure | NOT WIRED | `session_guard.py`. Limits are **not enforced**. Must be wired before the first real-money trade. **Measured 2026-11-05** (`studies/leg_decomposition_report.md`): in stress weeks the two crosses correlate −0.10 (2005–2013) and +0.33 (2021–2026); "count as one" is not supported in either era (needs ≥ 0.7); 2021–2026 reads as about 1.5 independent positions. Team to rule |
| Trade management (breakeven, partials, trailing) | HAVE, as rules | `foundation/risk_and_execution.md` |
| Pre-trade checklist and journal | MANUAL | `setup_check.py`, `trade_logger.py`. Zero real trades so far (one paper test) |
| Grading the trader (process separate from outcome, weekly review) | MANUAL (built 2026-11-04, not yet used) | `scripts/trader_review.py`: log every idea taken or passed, score outcome R and process separately, weekly review with one lesson and at most one rule change (`foundation/trader_review.md` §0). Zero real ideas logged so far: it starts counting when the owner uses it |

## Evidence: knowing what actually pays

| Area | Status | What we have / what's missing |
|---|---|---|
| Honest sample counting, power checks, pre-registration | HAVE | `foundation/tools/`, `foundation/methodology.md`. This is the framework's strongest part |
| Forward test of candidates | HAVE | `shadow_signals.py`. As of 2026-10-19: EARLY_MOMENTUM_v2 3 episodes (avg −0.20R), THRUST_PULLBACK 1, MOMENTUM_JOIN 1 |
| Tested ideas (44, most refuted; count updated 2026-11-14) | HAVE | `foundation/research_findings.md`. Check here before testing an idea |
| Long-history test with costs | TESTED for the candidates (2026-11-04) | The three frozen candidates on 2005–2013 STUDY data, every H4 bar, era costs and financing (FCS-1, R40–R42): no edge; 3 of 5 cells REFUTED, 2 INCONCLUSIVE. The 2014–2021 SEALED EXAM stays closed (only the team opens it, for one candidate) |
| Long-history research archive | HAVE (2026-11-05) | `studies/research_archive.py`: daily, 4-hour and hourly GBP/AUD and GBP/JPY for 2005–2013 (STUDY), 2021-04 → 2026-09 (USED) and 2026-09-11 → build date (FORWARD), each bar labelled by span, hash-pinned, consistency-verified (`studies/research_archive_report.md`). The 2014–2021 sealed exam stays out (data_map_spec §11.6). Research only; none of it is proof |
| A proven edge | MISSING | Still none after FCS-1 (2026-11-04) |

## Gold (XAU/USD): practice chart (section added 2026-11-14)

**Gold is not tradeable on the OANDA account** (instruments probe,
validation_log 2026-11-05); the candles endpoint serves it, so it is a
paper and markup chart only. Prices are in **US dollars**, not pips. Nothing
from the GBP findings (R1–R42) transfers to gold until it is measured on
gold. The plan for closing these gaps is `docs/gold_plan.md` (a proposal;
its team rulings are open).

**How gold behaves**

| Area | Status | What we have / what's missing |
|---|---|---|
| Price history | PARTIAL | 2006-03-21 → 2013 (STUDY) and 2021-04 → 2026-09 (USED), fetched and validated 2026-11-05 (`studies/leg_data_report.md`, validation_log 2026-11-05). STUDY gold has answered one weekly-correlation question only (G1). **2014–2021 has never been fetched for gold**; gold is outside the data map's partition, so whether that span becomes gold's sealed exam is an open team ruling |
| Sessions and time of day | TESTED, descriptive (2026-11-10) | `studies/gold_session_report.md`, USED span: busiest 4–7 AM PST (5 AM peak), second bump 5 PM PST; the 4–8 AM overlap carries a median 67% of the day's range; by 7 AM PST the day's high is set on 67% of days and the low on 73%. Learning only |
| Typical move size | MANUAL | Daily ≈ $75 (2026-11-10 probe in the session report); the owner's markup notes use ≈ $90 daily, $34 4-hour, $15 hourly (2026-11-14, not re-measured here). No era-comparable measure yet (dollar ranges mix $550 and $4,000 gold; a percent-of-price figure would not) |
| Breakouts holding | TESTED, descriptive (2026-11-14) | R45, `studies/gold_breakout_report.md`: a wick through the latest daily swing failed 51% (2006–13) / 66% (2021–26) of the time; a daily close beyond failed 43% / 45%. Gold ≈ GBP/AUD in 2021–26. No entry rule, no costs |
| Pullback depth | MISSING | R39's 38.2% / 50% shares are GBP-only |
| Reaction to US releases (CPI, jobs, Fed) | MISSING | The owner's notes say US news moves gold most; unmeasured. R35/R36 are GBP-only. 2005–2013 event dates exist (`~/intel_study_archives/us_events_2005_2013`) |
| Falls vs rallies (does gold drop differently from how it climbs?) | MISSING | Matters for trading both directions; 2006–2013 holds both a long climb and the 2011–2013 fall |
| Weekend gaps and the daily 5–6 PM New York break | PARTIAL | The break is pinned in the session study; gap size and how often a gap jumps a typical stop are unmeasured |

**What moves gold** (all INFORMED PRIOR; none tested by us)

| Area | Status | What we have / what's missing |
|---|---|---|
| US real interest rates | MISSING | Widely reported as the main driver, with a reported break in 2022–2024. A free public series exists (FRED); not fetched |
| US dollar | PARTIAL | USD pairs are on the account with history; no gold-vs-dollar measure. Weekly gold correlation with the GBP crosses: −0.14 / −0.23 (GBP/AUD), +0.06 / −0.01 (GBP/JPY), 2005–2013 / 2021–2026 (G1, descriptive) |
| Fed expectations | MISSING | |
| Central-bank and ETF buying | MISSING | Slow, monthly; context for the monthly and weekly read only |
| Positioning (futures traders) | MISSING | Weekly public report (CFTC); not fetched |
| A written gold macro read | MISSING | No gold line in `storylines.md` |

**Trading it**

| Area | Status | What we have / what's missing |
|---|---|---|
| A venue | MISSING | No account that can trade gold. Contract sizes, costs and hours depend on the venue the owner picks |
| Spread, slippage, financing | MISSING | Mid-price candles only. A futures venue would also mean a futures chart, which sits apart from the spot chart by the carry |
| Position size against the account | MISSING | The stop rule (0.3–1.5 daily ATR ≈ $27–$135 at $90 a day) on a 10-ounce contract is $270–$1,350 at risk per contract (arithmetic, not checked against any venue) |
| Hand markup tools | HAVE (2026-11-14) | `studies/markup_swings.py` prints gold in US dollars (unit table; an unknown metal is refused). Reality run 2026-11-14: daily average range $89.6, 4-hour $33.6, hourly $15.4 (validation_log 2026-11-14, Phase A). Its 150 monthly candles reach back into 2014–2021: open item for ruling T1 |
| Idea log | HAVE (2026-11-14) | `scripts/trader_review.py` takes XAU_USD as a practice instrument: scored on paper with OANDA's quoted $0.47 spread (median, Oct–Nov 2026; not a venue's), framework read "not covered", its own line in the weekly review. Not yet used for a real idea |
| Weekly markup and Friday scoring | MANUAL (first week W47, 2026-11-16) | `markups/README.md`; its widths and examples are GBP/AUD's. The gold equivalents (zones ≤ ≈ $45, "held" = ≈ $45 away) live in the owner's notes only |
| A proven gold edge | MISSING | No rule has been tested on gold, in either direction |

## What would sharpen us most, in order

These are recommendations, not approved work. Changes to protected modules
need a spec and team review first (AGENTS.md).

1. **Reps, graded.** Start the `trader_review.md` loop on paper or at micro
   size.
2. **Refresh the macro read, then measure it.** Bring `storylines.md`
   current and log agree/conflict per decision so the market grades it.
3. **Add cross-market context**: a US-yields / risk-tone line in the brief
   as context only. (USD events: done as context 2026-11-03.)
4. **Count costs**: spread and financing in shadow grading.
5. **Wire the circuit breaker** before any real money.
6. **Run the long-history cost-aware test** for honest sample size fast.
