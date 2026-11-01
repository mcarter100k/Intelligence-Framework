# Covering everything that moves GBP/JPY and GBP/AUD: proposal for team review

**Date:** 2026-11-01. **Status:** PROPOSAL. Nothing here is approved, and
nothing in it changes the tradeable path.

**Owner's goal:** while the framework trades these two pairs, it should
cover everything that moves them, so we know how to position. Today it
reads price well and macro barely at all.

**How this was put together:**
- Four independent agent reviews: the GBP leg and global backdrop, the JPY
  leg, the AUD leg, and a read-only review of the framework's code and rules.
- Checks of the key repo findings, run in this session.

**Evidence labels:**
- **VERIFIED:** checked in this session against the repo, with a control.
- **WEB:** reported by web sources and **not** checked against primary data
  (BoE, RBA, BoJ, MoF, CFTC). All 2026 market levels below are WEB.
- **PRIOR:** reasoned, untested in this framework.

---

## 1. Two things the team needs to know first

### 1a. A protected live file was broken overnight. It has been restored.

**What happened:**
- At 2026-11-01 00:03:54 PDT, `levels_context.py` in the live checkout was
  modified. Line 98's `result["prev_week_high"]` became `result["n]`.
- That is a syntax error. `entry_confirmation.py` imports the module, so the
  02:30 scheduled brief would have hit it.
- Whose edit it was is unknown. No framework agent session was running, and
  it looks like a stray keystroke over selected text.

**What was done:**
- The broken file and its diff were saved to the session scratchpad.
- The file was restored to the committed version (`git checkout`).
- The full suite then ran on the live checkout: 888 passed, 2 deselected.
  The conftest evidence guard passed. (VERIFIED)

**Proposed control:** a pre-run syntax check of the live modules in
`scripts/live_guard.sh`, so a broken file alerts instead of failing quietly.
`scripts/` is free zone, but this needs a notification test (rule 12).

### 1b. The macro read has never been measurable

`setup_check.py` compares a trade idea with the bias in `storylines.md` and
marks it AGREES or CONFLICTS (the "FUEL" line). It never could:
- Its parser looks for lines like `GBP: neutral`.
- The real file writes `## GBP — …` and `Bias: NEUTRAL.`
- Against the live file, `parse_storylines()` returns `views: {}`.
- A control file in the expected format returns all three currencies.
  (VERIFIED)

Every FUEL result in `pre_trade_journal.csv` is `neutral` (4) or `stale`
(5). This is the fourth rule-9 case, where a check that can't fire reads as
"no conflict". The file has also been stale since 2026-09-10.

---

## 2. How the two pairs fit together (PRIOR, untested here)

| Shock | GBP/JPY | GBP/AUD | Positioning consequence |
|---|---|---|---|
| Sterling-specific (BoE, UK data, gilts, politics) | moves | moves the **same way** | Holding both is one GBP bet, doubled. The dormant shared-leg rule in `session_guard.py` exists for this |
| Global risk-off (equities fall, VIX jumps, carry unwinds) | **falls** (yen is a safe haven) | usually **rises** (AUD falls harder than GBP) | The pairs hedge each other. A long in both is partly offset |
| US dollar / US yields | Strong, through USD/JPY | Weaker; the cross cancels much of it | US events matter most for GBP/JPY, and they are not in the news gate today |

Academic anchor: dollar and carry factors explain 19–91% of same-day
developed-market currency moves (Verdelhan, *Journal of Finance* 2018). They
explain moves on the day, not future moves.

---

## 3. What moves each leg (condensed from the agent reviews)

Role key: **ctx** = shown to the trader; **gate** = stand aside; **test** =
worth pre-registering. "Have" = already in the framework.

### Shared GBP leg

| Driver | Why it matters | Data (cost) | Role | Have? |
|---|---|---|---|---|
| BoE decision vs market pricing (OIS/SONIA) | Largest repeat GBP driver. Moves both pairs together. Reactions often fade over 1–3 days | BoE yield curves, daily (free, ZIP files, no API); BoE surprise database (UKMPD) | ctx, gate, test | Gate only (calendar) |
| UK CPI, wages, GDP, PMIs | Surprise vs forecast drives the jump (Andersen et al., *AER* 2003) | ONS API (free); forecast from the existing ForexFactory feed, current week only | gate, test | Gate only |
| Gilts and fiscal stress | In a scare, rising yields *hurt* GBP (2022 mini-budget: GBP/USD about −5% in a day). Back in May 2026 under a political challenge | BoE curves (free) | ctx, gate | No |
| UK politics | Leadership and fiscal-rule fears flow through gilts | News | ctx (weekly note) | Manual |
| London 4pm fix, month-end | Peer-reviewed (Krohn, Mueller and Whelan, *JF* 2024). Small, but it skews fills | Clock rule | gate (avoid entries 15:45–16:15 London at month-end) | No |

### JPY leg (GBP/JPY)

| Driver | Why it matters | Data (cost) | Role | Have? |
|---|---|---|---|---|
| **MoF intervention / rate checks** | Largest single-day risk. Four 500–640-pip GBP/JPY drops in 2026 (WEB). ¥27tn spent this year, once jointly with the US | MoF monthly totals (free). Live signature: a USD/JPY fall of about 2% or more in an hour with no scheduled news | **gate**, ctx | Manual flag only |
| USD/JPY and the US–Japan yield gap | The dominant everyday driver | OANDA USD/JPY (same API, not fetched); FRED DGS2/DGS10 (free); MoF JGB yields (free) | ctx, test (as a filter on trend labels) | No |
| Carry unwind / risk-off | Rare, largest drawdown: about −2,800 pips (−13.5%) Jul–Aug 2024 | FRED VIX (free); CFTC COT (free, weekly) | gate (VIX spike), ctx | No |
| BoJ decision, Ueda press conference, press leaks | Direction is unreliable: the Sep 2026 hike *weakened* the yen. Leaks move price the week before | BoJ (free) | gate (include the press conference), ctx | Calendar gate + price-only "coil" |
| Japanese fiscal / JGB yields | Slow yen-weakness premium | MoF yields (free) | ctx | No |
| Tokyo 9:55 fix and gotobi days | **Peer-reviewed** (Ito and Yamada, *JIE* 2017). Large N, about 6 days a month | OANDA bars we already have | **test**, the best-supported candidate found | No |
| Holiday liquidity (Golden Week, Obon, year-end) | MoF has intervened in thin markets | Calendar | gate (soft) | No |

### AUD leg (GBP/AUD)

| Driver | Why it matters | Data (cost) | Role | Have? |
|---|---|---|---|---|
| **Global risk tone** | Largest and fastest GBP/AUD moves (Apr 2025 tariffs: about +5.6% in three sessions). The AUD leg dominates in risk shocks | FRED VIX (free); index CFDs on OANDA if the account allows | ctx, gate, test | No |
| RBA decision vs ASX futures pricing | Most active G10 hiker in 2026. Both recent hikes **reversed during the press conference** | RBA (free); ASX rate tracker (free, scrape only) | gate (extend through the press conference), ctx | Calendar gate (statement only) |
| AU CPI and labour data | They decide hike vs pause right now | ABS API (free) | gate, test | Gate |
| Iron ore / China | Medium-run anchor, little timing value (Chen, Rogoff and Rossi 2010) | World Bank, RBA index (free, monthly) | ctx | No |
| US data | Adds more AUD volatility than China data (RBA Bulletin, Mathews 2016) | Calendar (filtered out today) | gate candidate | No |
| AU–UK rate gap | Sets the swap sign. Long GBP/AUD now **costs** carry | RBA F2, BoE (free) | grading | No (carry already INCONCLUSIVE, R34) |

---

## 4. This week (WEB, not checked against primary sources)

| When (UK time) | Event | Priced | Gated today? |
|---|---|---|---|
| Tue 3 Nov 03:30 | RBA decision + Statement on Monetary Policy | Hike to 4.85%, about 70–90% | Yes (AUD, statement only) |
| Tue 3 Nov | US midterm elections | — | **No** |
| Thu 5 Nov 12:00 | BoE decision + Monetary Policy Report | Hike to 4.00%, about 94% | Yes (GBP) |
| Fri 6 Nov (unconfirmed) | US October jobs report | — | **No** |
| 9 Dec / 17 Dec / 17–18 Dec | Fed / BoE / BoJ | Fed hike about 84%, BoJ hike about 75% | Fed **No**; BoE, BoJ yes |

**Carry has flipped since 2024** (WEB rates, PRIOR direction):
- RBA 4.60% vs BoE 3.75%, so long GBP/AUD now costs swap.
- BoE 3.75% vs BoJ 1.25%, so long GBP/JPY earns about 2.5pp.
- None of this enters the shadow grading (R32).

---

## 5. What the framework can plug in today (VERIFIED from code unless noted)

**What the code uses now:**
- **Data:** OANDA only, live environment, mid prices, GBP_AUD and GBP_JPY.
- **Feed:** `_get_bars` takes any instrument, so USD/JPY, GBP/USD and AUD/USD
  need no feed change. `get_live_price` throws away bid/ask.
- **Calendar:** ForexFactory, HIGH-impact GBP/AUD/JPY events only. There is
  **no `actual` field**, and the file is **overwritten every fetch**, so no
  forecast history accumulates.

**What isn't known yet:**
- **Account region:** settled 2026-11-01 by the owner-approved probe
  (`studies/instrument_probe_report.md`). The account offers **currency
  pairs only** (68): no bond, index or commodity CFDs. USD/JPY, GBP/USD and
  AUD/USD have daily history from 2002. Yields, equities, VIX and
  commodities need outside sources. (VERIFIED)

**What exists only in git history:**
- `shadow/cross_market.py` (VIX, S&P), `cot_data.py`, `interest_rates.py`
  and `macro_regime.py`, at `4eb9241^`.
- They logged zero comparisons in their life (I13). Restoring any needs
  team review and an evidence path.

### Rule traps any plan must respect

- **T1 Frozen stamp.** Widening the news gate to USD would change the
  shadow candidates' `news_window` stamp partway through the ledger
  (`shadow_signals.py:245-253`). Show USD events as **context first**, keep
  the stamp on own-currency events, and gate later under a separate spec.
- **T6 Frozen R.** Never put spread or swap into `r_multiple` in place. Use a
  read-only cost-adjusted column or study, or a new candidate id.
- **Plain English.** The brief says "US 10-year yield", never `USB10Y_USD`
  (banned-token test).
- **Rule 8: a cadence requires a live writer.** Every new file goes into
  `artifact_freshness.py`. Human-written files get DUE, never STALE.
- **Rule 9: a zero from an unverified path is not data.** A failed
  cross-market fetch renders "not checked", never "flat".
- **Fail-open.** A stale calendar disables gating with a note. Any USD gate
  inherits that.
- **Data map.** The 2014-01-01 → 2021-04-25 SEALED EXAM stays closed. 2021
  onward is learning only.

---

## 6. Proposed plan, in order

Each step produces evidence before the next touches anything tradeable.

| # | Step | Zone | Needs |
|---|---|---|---|
| 0 | Syntax pre-check in `live_guard.sh` (1a) | Free | Notification test |
| 1 | **Make the macro read gradeable.** Add one machine-readable line per currency to `storylines.md` (`GBP: neutral`), refresh it weekly, and pre-register how a week's bias is graded before the first graded week | storylines: owner. Grader: free (`studies/`) | Owner time; no code change |
| 2 | **Account instrument probe**: which CFDs exist and how much history | Free (`reality_run.py script`) | Approval for a live read-only API call |
| 3 | **Cost-adjusted R study** over the shadow ledger (spread + swap, read-only) | Free | — |
| 4 | **Descriptive US-event study**: how FOMC, CPI and jobs move both crosses, on our own bars | Free | Pre-registration |
| 5 | **Spec: USD (and CNY) events as context only** in the brief; extend the RBA/BoJ windows through the press conference | Protected | Spec + team review |
| 6 | **Spec: forecast/actual archive writer** (append-only via `ledger_io`), so surprise studies become possible in about 2 years | Protected | Spec + review |
| 7 | **Spec: cross-market context line** (USD/JPY, both USD legs, US 10-year, VIX), shown as context only | Protected | Steps 2 and 4 first |
| 8 | **Pre-registered tests**: gotobi/Tokyo fix on GBP/JPY; risk-regime split of the shadow candidates; leg decomposition | Free | Pre-registration each |
| 9 | **Gates, only with evidence**: intervention signature, VIX spike, month-end fix, holiday weeks | Protected | Evidence from 4 and 8 + spec |

**Not proposed:** re-testing carry (R33/R34), level fades, compression or
fakeouts (R6–R9, R14), or restoring the legacy macro stack without an
evidence path.

---

## 7. Decisions needed from the team

1. **Storylines format (step 1):** add the machine-readable lines (no code
   change), or spec a parser fix in protected `setup_check.py`?
   Recommendation: the format lines now; the parser fix is unnecessary if
   the format is kept.
2. **Live probe (step 2):** approve one read-only instruments call against
   the live account.
3. **US events (step 5):** context-only first, as recommended because of
   trap T1, or straight to gating?
4. **Priority:** of steps 3, 4 and 8, which runs first? Recommendation: 4,
   because it decides whether US events belong in the gate at all.
5. **Origin of the 00:03 edit (1a):** if it was not the owner, find out who
   or what can write to the live checkout.

---

## Updates

- **2026-11-01, owner decisions on §7:** (1) format lines in
  `storylines.md`, no code change; (2) live probe approved and run, see §5;
  (3) US events come in as context first; (4) next study: US-event
  reactions. Recorded in validation_log.
- **2026-11-01, done:** step 0 (live guard code check, merged), storylines
  format test (merged), step 2 (instrument probe).
