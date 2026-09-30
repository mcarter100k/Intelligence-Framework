# Risk and execution rules

Exact values, where they live, and their status. Sound rules, but **unexercised**: no real trade has run through them yet.

> Citations: `VL:n` = `validation_log.md` line n; `AUDIT §n` = `docs/audit_2026-09-29.md`; other paths are repo files. Line numbers are as of the 2026-09-29 audit (commit efd293e) — search by content if they have drifted.

> **Audit status:** `risk_config.py` and `session_guard.py` have **no live caller**. They are imported only by tests and quarantined files (VL:2573-2581; AUDIT §4). No real trade has ever run through them. The rules are sound for a trader; they are unexercised.

## 4a. Grade → risk (`risk_config.py:6-11,59-102,184-193`)

| Grade | Risk % of account | Adjusted score + quality | Stated frequency |
|---|---|---|---|
| A+ | **1.5%** | ≥85 and HIGH | "1–2x per week maximum" |
| A | **1.0%** | ≥70 and HIGH | "3–4x per week on good weeks" |
| B+ | **0.5%** (base) | ≥55 and ≥MEDIUM | "Most common tradeable setup" |
| B | **0.25%** | ≥40 and ≥MEDIUM | "Take only when B+ conditions are close" |
| C | **0.0%, NO TRADE** | otherwise | "Never trade these" |

**Score adjustments.** All are unvalidated heuristics from the quarantined stack (`risk_config.py:127-165`).

| Adjustment | Points |
|---|---|
| fakeout confirmed | +7 |
| sweep confirmed | +8 |
| value-aligned | +5 |
| London or NY session | +5 |
| London/NY overlap | +8 |
| counter-trend | −10 |
| HTF conflict | −8 |

- **Tokyo** caps alignment at 69 (B+ max).
- **Swing trades** with structural score <60 are capped at 55.
- **Event risk** or quality "DO NOT TRADE" means an immediate C.

**Contradiction (audit):** the live brief shows grade C with "75% size", while risk_config defines C as NO TRADE (AUDIT §1).

## 4b. Hard limits and risk rules

| Rule | Value | Where |
|---|---|---|
| Max daily loss (R) | **2.0R**, peak-to-trough of today's realized R curve → HALTED | `session_guard.py:50`; `risk_config.py:32` |
| Max daily loss (%) | **2.0%** (enforced when `return_pct` exists) | `session_guard.py:51` |
| Trades per session | **2** (leg-grouped positions) → SESSION_CLOSED | `session_guard.py:52` |
| Shared currency leg | Positions opened the same UTC day that share a leg count as **ONE** (connected components: A+B, B+C ⇒ one). "Long GBP/AUD + short GBP/JPY is one pound bet wearing two hats" | `risk_config.py:51-56`; `session_guard.py:155`; `circuit_breaker_promotion_spec.md:50-58` |
| Realized R | `sign·(close−open)/\|open−stop\|` per CLOSE row. UTC day boundary. PAPER rows count | `session_guard.py:24-26`; `circuit_breaker_promotion_spec.md:28-47` |
| Fail mode | Absent/empty ledger → ACTIVE. Corrupt or wrong columns → **HALTED (fail-closed)**. "A broken circuit breaker must stop trading, not permit it" | `session_guard.py:28-32` |
| Min R:R after spread | **1.5**. Effective = (reward − spread) / (risk + spread) | `risk_config.py:34`; `trade_management.py:32,106-121` |
| Spread assumption | **4.0 pips** (execution), vs 3.0 in studies | `risk_config.py:35`; `trade_management.py:31` |
| Max open risk | **2.0%** | `risk_config.py:43` |
| Min alignment to trade | 45; min quality MEDIUM | `risk_config.py:45-46` |
| Event lockout | **2.0h before, 0.5h after** | `risk_config.py:47-48` |
| News gate (live) | HIGH-impact events in the pair's **own** currencies within **120 min** → hard stand-down. USD out of scope (v1 boundary). Calendar >**7 days** old → gate INACTIVE with an honest note ("stale data never gates and never pretends coverage") | `news_gate.py:28-40`; VL:1307-1319. Audit: staleness is judged by the newest event, not coverage (fail-open, AUDIT §2 #14) |
| Context expiry | Discard framework output older than **4h** | `risk_config.py:36` |
| No swing in Tokyo | True | `risk_config.py:49` |
| Stop ATR multiplier (default) | **1.5×ATR** | `risk_config.py:50` |
| Max stop width | **1.5× daily ATR** (MAX_STOP_ATR_MULTIPLE; wider = oversized: "size down or find closer structure") | `trade_management.py:29`; `setup_check.py:420-434` |
| Min stop width (noise flag) | **0.3× daily ATR** (MIN_STOP_ATR_MULTIPLE, INFORMED PRIOR from Episode 1). Closer = "hit by accident, not by being wrong"; a flattering R:R warning follows | `setup_check.py:53-59,422-445` |
| Extreme ATR spike | ratio **≥2.0x** → hard block | VL:586-591 |
| Counter-trend override | Needs all 5 conditions; **size 0.35x**, conviction capped at **45**, confidence LOW. Status: UNVALIDATED, and lost 2026-05-15 | VL:593-602, VL:743; `no_trade_filter.py:64` |
| Range trading | `RANGE_TRADING_ENABLED = False`. Precondition before enabling: a first-class EXHAUSTION regime | `official_decision.py:30`; AGENTS.md:58-68 |
| JPY 1.0–1.2x ATR | −20 conviction on JPY trend trades (from R4, N=16) | VL:794-796 |
| Targets | "The framework does not generate targets. Set your own; it must pay ≥1.5x after the spread" | VL:2141-2144 |
| Lot size | lots = (balance × risk%) / ((stop_pips + spread) × pip_value). Spread is added to the stop. Min lot warning <0.01 | `risk_config.py:260-324` |
| Storyline freshness | >**8 days** = stale (can't count as evidence) | `setup_check.py:51` |

## 4c. In-trade management (`trade_management.py:10-37`)

| Step | Trigger | Action |
|---|---|---|
| 1 | **+1.0R** | Stop to breakeven **and** close **50%** |
| 2 | **+1.5R** | Start the trailing stop **0.5R** behind price |
| 3 | Target | Close the remainder |
| Invalidation | A **15-minute close back through the entry key level** | Exit immediately, regardless of P&L |

- A+/A grades: consider skipping the Step-1 partial.
- B+/B grades: always take it.
- A plan is refused if the geometry is incoherent: stop on the wrong side, target on the wrong side, zero risk, or effective R:R <1.5 (`:84-132`).
- The audit lists `check_management_action` and `PARTIAL_R` as unreferenced (AUDIT §4).

## 4d. Pre-trade discipline (`setup_check.py`)

The pre-trade stack has six lines: BIAS, REGIME, PLAY, CLOCK, FUEL, RISK.

- **PLAY must be nameable:** coil-break, base-break, first-pullback or retest-fade. Otherwise: "If you can't name it, it's a feeling, not a trade."
- **Soft gate:** every check is logged to `pre_trade_journal.csv`. Overrides capture the human's read. Trading against the framework is FLAGGED, not blocked.
- **VERDICT:** blanks, a stop in noise, or a storyline conflict produce "Nothing here says NOW."

Sources: `setup_check.py:1-35,159-200,252-297`; VL:1916-1954.

---
