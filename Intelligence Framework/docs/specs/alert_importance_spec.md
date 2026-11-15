# Spec: an alert reaches the owner only when the market is open and it is worth acting on

**Status:** owner-approved free-zone change, 2026-11-15. Committed before any
code. Owner's words, answering "what is wrong with the alerts?":
1. "alerts are coming when the market is closed";
2. "alerts should come when it's important";
3. "remove its noise".

**Scope:** `scripts/scheduled_brief.sh`, `scripts/scheduled_outcome_check.sh`,
`scripts/daily_digest.py`, `scripts/artifact_freshness.py`, one new helper
`scripts/alert_state.py`, and their tests. All free zone, but every one is a
notification path, so rule 12 applies: each is tested for whether it should
reach the owner. **No protected module is edited.** The one protected change
found (§4) is a proposal for team review only.

**Supersedes** `docs/specs/shadow_digest_only_spec.md` (PROPOSED 2026-11-05,
never built; owner decision then: shadow "Digest only"). Its design is
adopted in N3, and its two questions are answered there and in N4.

**Reverses two earlier decisions, stated openly:**
- `alert_expansion_spec.md` (team approved 2026-07-31) routed "regime change" flips to the phone. N2 stops the bare regime-change line; filter flips and exit-watch flips still reach the phone.
- `decision_channel_measurement_spec.md` Phase 0 gated only DECISION when the market is closed, "one change at a time", and left ALERT, SHADOW and DIGEST ungated. N1 gates them too. Phase 0 also named the known defect that "the DECISION trigger tests a STATE, not an EDGE … needs its own spec". This is that spec (N5).

---

## 1. What was measured before this file (2026-11-15; `notification_log.csv`, day logs, ledgers)

| # | Problem | Evidence |
|---|---|---|
| 1 | "BRIEF UNHEALTHY — STALE: trade_signal_log.csv" on every evening run ("8th consecutive failed run") | That ledger gains a row only for an open-market LONG/SHORT. The framework stood aside in every open-market run since 2026-10-13. All 6 LONG lines printed since then were in closed-market runs (logged by design as nothing). Its 720 h cadence calls a quiet month a failure |
| 2 | "GBP/JPY: the market regime changed" 5 times in 5 days | Only the 4-hour label flickered (VOLATILE ↔ TRENDING_DOWN ↔ RANGING). The composite regime stayed RANGING and the decision STAND ASIDE (`regime_classification_log.csv`, 11-09 → 11-13) |
| 3 | The same MOMENTUM_JOIN SHORT @ 211.026 notified 4 times over a closed weekend | One ledger row (bar 2026-11-13T18:00Z). Every closed-market run re-displays the last bar |
| 4 | Two identical SHADOW notifications at Sat 07:41 | Two brief runs stamped 07:41:07: launchd ran the missed 02:30 job and the 07:30 job together on wake |
| 5 | Garbled SHADOW text mixing two candidates ("is watching the EARLY_MOMENTUM_v2 candidate: · MOMENTUM_JOIN SHORT @ 211.026") | The summary greps candidate names anywhere in the brief. It took a wrapped FULL PICTURE line about one candidate (price cut off) and another candidate's signal |
| 6 | Market notifications while closed | Weekend DIGEST ("MARKET CLOSED … no live calls"), SHADOW and ALERT rows on Sat 10-31, Sun 11-01, Sat 11-07, Sun 11-08, Fri 11-13 evening, Sat 11-14 |

## 2. Definitions

- **System notification:** about the machine, not the market. Brief and grader health failure or recovery (`health_state.py`), the weekly HEARTBEAT, and any `##ALERT##` line not prefixed by a pair name (for example "EXCLUSION REGISTRY: …"). **Unchanged by this spec**, whatever the market.
- **Market notification:** DECISION, a pair's flip line (`GBP/AUD: …`), shadow, the review-gate alert (N4) and DIGEST.
- **Market open:** per instrument, the brief block does not carry the closed banner `Market closed — analysis based on last close.` (already pinned by `test_wrapper_behavior.py` g9). Where there is no brief (the grader), `regime_detection._market_status()["open"]`, the same function that renders the banner.

## 3. Changes

**N1. Market closed → no market notification.**
- **Brief:** a pair's flip line, DECISION and decision-state changes count only when that pair's block is open. If no pair is open, the run sends no market notification.
- **DIGEST:** sent only when at least one pair is open in that run. On a closed day there is none (Saturday, Sunday morning, Dec 25, Jan 1).
- **Grader:** the review-gate alert (N4) only when the market is open. A gate reached while closed is announced at the next open-market grader run.
- Everything stays in the day log as before.
- **Old → new tests:**
  - g4 "a flip alert still fires when closed" → a closed pair's flip line does not notify;
  - g6 "a shadow signal still fires when closed" → shadow never notifies (N3);
  - g8 "the digest still fires when closed" → a closed digest does not notify.
  - g5 (health when closed) and g7 (heartbeat after a closed brief) are unchanged.

**N2. Only flips you can act on.** A pair's flip line notifies only if it is one of:
- `conditions improved — the framework now allows a trade`;
- `conditions deteriorated — the framework has stood down`;
- `exit-watch fired …`.

Dropped from notifications (kept in the day log): `the market regime changed since the last run`, `conditions improved since the last run` and `conditions deteriorated since the last run`. These are the lines without a change in what the framework allows.

**N3. Shadow signals: digest only** (adopts `shadow_digest_only_spec.md` §2.1–2.2).
- The brief wrapper's SHADOW category is removed.
- The DECISION summary names decisions only; no candidate-name grep anywhere.
- `SHADOW_ERR` (a candidate raising) still rides the health plumbing.
- The digest adds a last clause when the shadow ledger has rows timestamped after the previous DIGEST: `· shadow (not traded): MOMENTUM_JOIN GBP/JPY SHORT 211.026 (+1 more)`. One fire is named, plus a count.
  - The source is `shadow_signal_log.csv` (excluded rows filtered), never brief text.
  - "Previous DIGEST" = the newest DIGEST row in `notification_log.csv`. With none, no clause.
  - (Answers the old spec's question 2 with the ledger instead of day logs: the ledger is the record, and it cannot be fooled by wrapped text.)

**N4. Grader: review gates, not nightly tallies.**
- The outcomes wrapper's nightly "shadow graded" notification is removed (the old spec's question 1).
- In its place, one notification when a candidate's graded independent episodes first reach **20** (the futility checkpoint), **30** (flag) or **60** (decision), per AGENTS.md. Example: `MOMENTUM_JOIN reached 20 graded episodes: the futility checkpoint is due (docs/specs/futility_rule_spec.md)`.
- The last announced gate per candidate is kept in `logs/alert_state.json`.

**N5. Decisions notify on a change, not on every run.**
- `logs/alert_state.json` keeps each pair's last open-market decision (LONG, SHORT or STAND ASIDE).
- An open-market run notifies DECISION only when the decision differs from that record:
  - a new LONG or SHORT;
  - a reversal (LONG ↔ SHORT);
  - **a directional decision going back to STAND ASIDE:** `GBP/JPY back to stand aside — the SHORT idea is withdrawn`.
- An unchanged decision never re-notifies.
- Closed-market runs and error briefs neither notify nor update the record.
- A pair with no record is recorded silently if STAND ASIDE, and notified if LONG or SHORT: one possible duplicate is better than a missed decision.

**N6. One brief run at a time.**
- `scheduled_brief.sh` takes a lock directory (`logs/.brief.lock`) before the brief. A second run waits for it (up to 10 minutes) and then runs, so it reads the first run's state and does not repeat its notifications.
- A lock older than 30 minutes is stale and is taken over.
- bash 3.2 compatible.

**N7. The trade-signal health check measures the writer, not the calendar.**
- `trade_signal_log.csv` leaves `CADENCES` and joins `READ_SIDE_NO_CADENCE`, with the reason that it is event-driven.
- New check, run with the others: **every `regime_classification_log.csv` row with `stand_down` = False in the last 30 days must have a `trade_signal_log.csv` row for the same instrument within 10 minutes.** A missing one prints `STALE:` and fails the run, as today.
- Positive control on the real ledgers, 2026-11-15: all 9 such rows since 2026-10-09 have their matching row. The regime log keeps its 72 h cadence, so a dead brief is still caught.
- On the first healthy run after merge, the brief's health returns to OK and one RECOVERED notification is sent (`health_state.py`, unchanged).

## 4. Protected: proposal for team review (NOT built)

**P1. Flips after 4 PM Pacific are never compared.**
- `session_memory._get_today_rows` keeps rows with the current **UTC** date, and UTC midnight is 4 PM PST.
- So the 6 PM run is always "the first reading of the day" and compares with nothing. A filter flip or exit-watch between the 07:30 and 18:00 runs is never alerted.
- Evidence: the Tue 11-10 and Wed 11-11 18:00 flips sent nothing; every flip alert in the log is at 02:xx or 07:xx.
- **Proposal:** compare with the previous snapshot of the same instrument within the last 24 hours, whatever its date.
- Also: `regime_changed`'s docstring says "did composite regime change?" while the code tests the daily or 4-hour label. N2 makes this harmless for notifications, but the docstring should say what the code does.
- Both are in `session_memory.py` (protected): spec and team review before any change.

## 5. Rule 12 tests (the real wrapper, stubbed notifier)

| Case | Expected |
|---|---|
| Both pairs closed: DECISION LONG, flip lines, shadow block | No market notification |
| Closed digest run | No DIGEST |
| Open digest run | DIGEST; shadow clause only if ledger rows are newer than the last DIGEST |
| One pair closed, the other open with a filter-flip line | Only the open pair's flip notifies |
| Open run, `the market regime changed …` only | Nothing |
| Open run, `conditions improved — the framework now allows a trade` | ALERT |
| Open run, `exit-watch fired …` | ALERT |
| Open run, a shadow block | No SHADOW notification |
| Open LONG, no record | DECISION, record LONG |
| Same LONG next run | Nothing |
| LONG then STAND ASIDE | DECISION "back to stand aside — the LONG idea is withdrawn" |
| LONG then SHORT | DECISION reversal |
| Error brief | No DECISION; record unchanged; health as today |
| Health failure while closed | ALERT, as today (g5) |
| Unprefixed `##ALERT##` (exclusion registry) while closed | ALERT (system) |
| Two runs started together | One set of notifications |
| Grader: a candidate reaches 20, market open | One review-gate notification; a second run sends nothing |
| Grader: reaches 20 while closed | Nothing; the next open run announces it |
| Freshness: a stand_down=False row with no trade row | STALE |
| Freshness: 30 days of stand-aside, no trade rows | No STALE |

## 6. Gates

- **Gate 1:**
  - every §5 row;
  - old → new for g4, g6, g8 and the shadow / outcomes routing tests, with dates;
  - no floor test touched.
- **Mutation, each must be caught:**
  - closed gate removed;
  - regime-change line allowed;
  - SHADOW category restored;
  - candidate grep restored;
  - decision state not checked (re-notify);
  - withdrawn decision not notified;
  - lock removed;
  - gate alert sent while closed;
  - the N7 matching window widened to never fail.
- **Gate 2:**
  - the real wrapper on a copy of the project, with real OANDA data and the notifier stubbed;
  - the live project hashed before and after;
  - the real 2026-11-13/14 closed-market brief outputs replayed through the new routing.
- **Gate 3, PENDING LIVE CONFIRMATION:**
  - the next closed weekend sends no market notification;
  - the next weekday 07:30 sends a DIGEST;
  - the first real LONG/SHORT sends one DECISION, and its withdrawal sends one;
  - the first evening run after merge clears the false STALE (one RECOVERED).

---

## 7. Amendments during the build (2026-11-15, recorded after the spec commit 10ffff9, not edited into it)

1. **A flip and a decision change in one run go in one ALERT.** The spec did not say what happens when both occur. Under N5 a decision change is recorded once, so sending only the ALERT (the old priority) would lose it for good. The ALERT's text now carries both.
2. **N7 counts only regime rows with a `logic_version`.** On the real ledgers, 10 rows from 2026-09-23/24/29/30 had `stand_down` False and no trade row. The briefs at those times say STAND ASIDE: before the 2026-09-30 decision logic, the filter could allow while the decision stood aside. Since `p5-2026-09-30`, allowed ⇔ traded is pinned by the 36,864-cell sweep (a floor test).
3. **N7 never gives an all-clear from a file it did not read.** With the regime log missing, it prints `unchecked:`, not "no trade call".
4. **A crashing freshness check now fails the run.** `artifact_freshness.main` swallowed every exception and printed nothing, which the wrapper read as healthy. It now prints a `STALE:` line.
5. **The N6 test checks that the run windows never overlap.** alert_state's own file lock already stops a doubled decision, so a notification count alone could not show the run lock works.
6. **The review-gate notification uses a new subtitle, `REVIEW`,** so it is never mistaken for a market alert.
