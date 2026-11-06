# Spec v2: WATCH FOR names only what a trade needs, and every stand-aside branch has a true sentence

**Status:** PROPOSED 2026-11-05, awaiting team review. Not built.
**Supersedes:** `watch_for_truth_spec.md`, unchanged on disk. The adversarial
reviewer rejected it as written; the code reviewer returned APPROVE WITH
CHANGES (validation_log 2026-11-05 TEAM REVIEW round 2). It also supersedes
§2, §3's "Changes if:" label and the §6 truth sweep of
`brief_summary_block_spec.md` (code review 9).

**Protected:**
- `decision_brief.py`: `_build_invalidation`, `_unconfirmed_exit_sentence`,
  the FULL PICTURE line in `_build_narrative`, and `_machine_flags` class (b);
- `session_memory.py`: one additive column;
- `regime_detection.py`: the input-assembly extraction in §5, behaviour
  identical.

**Owner decision applied (2026-11-05, decision 3).** The override is named
with its record: "one recorded use, May 2026, before this framework's records
and under earlier rules: lost". It is hard-coded by necessity, with a test
that fails if a second override trade ever appears in the ledger (§2.4).

## 1. Why

On a stand-aside run, WATCH FOR tells the owner what to wait for. The digest
quotes it, and FULL PICTURE repeats it as "This changes when …". v1 found
branches that name conditions that cannot produce a trade. Review round 2
found:
- **States with no failing clause.** Stand-aside states fail none of v1's
  N1–N7, so "name the failing clauses" has nothing true to say:
  - GBP/JPY compression (432 cells in the adversarial sweep);
  - news window;
  - missing weekly data;
  - grade C: 46,080 of 114,120 trending-daily stand-asides (40%), code reviewer.
- **FULL PICTURE claims sufficiency everywhere.** "This changes when
  <WATCH FOR>" prints in 614,712 of 614,712 stand-aside render cells
  (`decision_brief.py:1227-1228`).
- **Contradiction on EXHAUSTION.** v1 said "neither fades nor chases", while
  REASON on the same page says "The market is in an exhaustion move — fade,
  don't follow." (`no_trade_filter.py:217`).
- **Rounding across the threshold.** 17.96 shows as "18.0" beside "below 18".
  OBSERVED live in the 2026-11-05 07:33 brief: "trend strength 18/100" next to
  "drops below 18".
- **No rule-12 table.** v1 changed the `_machine_flags` exit-watch flags, an
  ALERT path, without one.
- **STRUCTURE_DISAGREES is unreachable.** It cannot come out of `get_regime`,
  because slope restates structure (`regime_detection.py:924-931`). v1's
  evidence for it came from input states the live path never produces.

## 2. Change

### 2.1 What every trade needs

In every trading cell of two independent sweeps (code reviewer: 1,179,360
live-input cells, 58,248 trading; adversarial: 379,080 cells), with
0 counter-cells each:

- **N1** The daily is not RANGING. Its strength is 18 or more, or its
  volatility jumped (GBP/AUD 1.2×, GBP/JPY 1.5×).
- **N2** The daily swing pattern is confirmed in the trade's direction.
- **N3** Either the daily is trending in the trade's direction, **or** (the
  counter-trend override) the 4-hour trends that way at strength 25+, the
  daily is under 32, and the weekly picture agrees.
- **N4** The weekly picture is not against the trade.
- **N5** The 4-hour is not trending against the trade, and not exhausted.
- **N6** Daily volatility is under 2× normal.
- **N7** GBP/JPY daily strength is under 35.
- **N8** GBP/JPY daily volatility is at least 0.8× normal (the compression
  floor, new in v2; 0 counter-cells with 4-hour volatility 0.7 in the grid).

Plus three state conditions that are not regime clauses:
- **D1** weekly data present (`block="weekly_unavailable"`,
  `no_trade_filter.py:186-192`);
- **D2** a valid volatility ratio (`no_trade_filter.py:147-157`);
- **G** no high-impact release in the news window (`no_trade_filter.py:162-176`).

**Evidence label: INFERRED, not VERIFIED** (adversarial review W5). Both
sweeps assemble inputs with a copy of `get_regime`'s builder. They become
VERIFIED only when Gate 1 runs the extracted real builder (§5).

These conditions are **necessary, not sufficient**. Grade can still stand a
cell aside, so WATCH FOR always ends "Revisit then.", never "trade then".

### 2.2 One true sentence per stand-aside branch, checked in this order

The first matching branch speaks. Ordering is part of the truth (W2): in
compression the clause that fails is never N3, because compression forces
VOLATILE.

| # | Branch (stand aside) | WATCH FOR (first sentence is what the digest quotes) |
|---|---|---|
| 1 | Error page | Unchanged: "Resolve framework error before re-running." (`_error_brief`). Never a market read |
| 2 | Missing data (D1, D2) | "Weekly trend data is missing this run, so the framework cannot check the weekly picture. Revisit at the next run." (D2: "The volatility reading is invalid this run. …") |
| 3 | News window (G) | "The <event> release passes (due about 7:30 AM). Revisit then." If other clauses also fail, branch 4–9's sentence follows as "Also needs: …" |
| 4 | GBP/JPY compression (N8) | "GBP/JPY daily volatility recovers to at least 0.8× normal (now 0.7×). Revisit then." |
| 5 | GBP/JPY exhaustion (N7) | "Daily trend strength falls back below 35 (now 41.2). Until then the framework does not follow this move, and it never trades the fade either (range trading is off). Revisit then." |
| 6 | Daily quiet range (N1) | "Watch for: the daily chart leaving its quiet range (trend strength 18 or more, now 15.2) with its swing pattern confirmed in one direction. Also needs: the daily trending that way, or the 4-hour trending strongly that way with the weekly agreeing — the counter-trend override (one recorded use, May 2026, before this framework's records and under earlier rules: lost). Revisit then." |
| 7 | Daily VOLATILE (transition, spike, unconfirmed) | Name the failing clauses of N2–N6 for the direction with the fewest failures, most restrictive first (direction-neutral wording on a tie). N6 is named only when volatility is ≥ 2×; spikes below 2× can trade through the override. For UNCONFIRMED_TREND, keep the concrete pending-pivot sentence (§2.3) |
| 8 | Daily TRENDING, a clause fails (N4, N5, N6) | Name it, for example "The 4-hour chart stops trending against the daily." or "The weekly picture stops pointing the other way." **Never the trend's end** (today: "D1 structure breaks", `decision_brief.py:857-862`) |
| 9 | Every clause holds, blocked by grade (`block="decision"`, `no_trade_filter.py:362-369`) | "Every condition the framework requires is in place, but the setup grades C (confidence 35/100), and C never trades. The grade is recomputed every run. Revisit then." |
| 10 | Anything else | "The daily chart's state is unclear this run. Revisit at the next run." **Never "ranging"**: ranging never trades (today's fallback, `:862`) |

- **The override clause** (branch 6, and branch 7 when N3 fails) always
  carries the R13 record in those words.
- **The EXHAUSTION sentence agrees with REASON.** REASON's "don't follow" is
  kept. The words "fade, don't follow" in REASON itself advise a trade the
  framework never takes (`RANGE_TRADING_ENABLED` is False). That REASON
  string belongs to the display-claims spec (item 6 family) and is flagged
  there, not changed here.
- **STRUCTURE_DISAGREES** (`decision_brief.py:837-842`). Its sentence
  ("turns to agree … or the structure breaks") is **deleted**. The branch
  falls through to branch 7. Gate 1 pins that `get_regime`'s assembly produces
  0 such cells.

### 2.3 The unconfirmed-trend sentences (code review 8)

- **Both sentences change.** "with the 4-hour chart aligned" becomes "with the
  4-hour chart not trending against it" in the concrete sentence
  (`decision_brief.py:1054`) **and** the fallback (`:847-850`). A trending
  daily trades with a VOLATILE 4-hour (sweep: "4-hour trending that way" not
  necessary, 44,640 counter-cells).
- **Its own test.** The pending-pivot sentence ("The low near X confirms as a
  swing low …") is outside the regime sweep. It gets a test that the pivot it
  names is the one `_detect_structure` would confirm on the next bars, using
  the synthetic bars of `unconfirmed_trend_display_spec.md`.

### 2.4 The override record and its tripwire (owner decision 3)

- **One cited constant.** The wording lives in one constant,
  `_OVERRIDE_RECORD`, with a comment citing `foundation/research_findings.md`
  R13 and AGENTS.md:58-60. No ledger holds the 2026-05-15 trade:
  - `trades.csv` and `trade_log.csv` have no regime or override column and no
    2026-05-15 row;
  - `trade_signal_log.csv`'s 13 rows are all trending-daily calls (OBSERVED
    today: 1 TRENDING_UP, 12 TRENDING_DOWN).
- **Where a second override would show.** `trade_signal_log.csv` is the only
  ledger where a new framework override is identifiable.
  `trade_outcome_logger.log_signal` writes every LONG/SHORT the brief issues
  (`decision_brief.py:292`). An override is the only route by which a
  **VOLATILE daily** trades (N3; the filter checks the override only under
  `d1 == "VOLATILE"`, `no_trade_filter.py:266-271`). So a row with
  `regime_d1 == "VOLATILE"` and `direction` in LONG/SHORT is an override
  signal. `trades.csv` cannot be used: it has no regime column.
- **The tests** (`tests/test_override_record.py`):
  - **R13 citation.** The R13 row exists and contains "lost" and "pre-repo".
  - **Tripwire.** Read the real `trade_signal_log.csv` read-only (precedent:
    `tests/test_ledger_headers.py`, which skips when a ledger is absent), apply
    `exclusions.filter_rows`, and count override signals. **It fails at ≥ 1**
    with the row's timestamp and the instruction "the hard-coded override
    record is stale; write a spec revision". It is conservative on purpose: a
    signal, not only a trade, triggers it, because a framework override trade
    always follows a logged signal.
  - **Positive control.** A planted VOLATILE LONG row in a temp copy makes
    the counter return 1.
  - **The invariant that makes the tripwire valid.** Over the §5 sweep,
    `override_fired` is True exactly when the daily is VOLATILE and the cell
    trades: 0 counter-cells either way.
  - **Mutation.** The string hard-coded outside the constant; the counter
    reading the wrong column.
- **Limits:**
  - A trade placed off-framework, with no logged signal, cannot be detected.
  - The suite is not scheduled, so detection waits for the next suite run.
    §7 question 2 offers a weekly heartbeat line as the scheduled backstop.

### 2.5 FULL PICTURE (code review 5)

- **Today.** "This changes when <WATCH FOR>" (`decision_brief.py:1227-1228`)
  claims sufficiency.
- **New.** "To watch: <WATCH FOR's first sentence, lowercased>. A trade needs
  that, but it is not enough on its own."
- **The grade-C branch.** Its sentence is "the grade is recomputed every
  run", so FULL PICTURE says it once, with no "needs" clause.

### 2.6 Numbers never cross their threshold (W3)

- **The rule.** On any brief whose WATCH FOR names a strength or volatility
  threshold, every rendering of that quantity is shown **rounded down to one
  decimal**. That covers MARKET STATE, REASON (`decision_brief.py:720`, today
  `:.0f`), FULL PICTURE and WATCH FOR's "now x". Rounding down to one decimal
  can never show a value on the other side of an integer threshold (17.96 →
  "17.9"; 34.96 → "34.9"), and is never equal to it when the true value is
  below.
- **Volatility ratios** (threshold 0.8) are rounded down to two decimals.

### 2.7 Exit-watch flags (`_machine_flags` class (b)) and rule 12 (W4, code review 7)

- **Today** (`decision_brief.py:1300-1313`):
  - (i) structure newly confirmed from TRANSITIONAL;
  - (ii) daily strength crossed 25 with the 4-hour ≥ 25.
  - (ii) is not a necessary condition: the override trades below 25, and
    "daily 25+" has 4,644 counter-cells.
- **New:**
  - **E1** (kept, reworded): structure TRANSITIONAL → UPTREND or DOWNTREND, with
    the decision STAND ASIDE. Text: "GBP/JPY: the daily swing pattern just
    confirmed a direction — one condition a trade needs; still stand aside.
    Check the brief."
  - **E2** (replaces (ii)): every regime condition (N1–N8, D1, D2, G) now holds
    for some direction, but did not on the previous compared run, with the
    decision still STAND ASIDE (grade is the only block). Text: "GBP/JPY: every
    condition the framework requires is now in place; the grade still blocks a
    trade. Check the brief." This needs one additive column, `conditions_met`
    (True/False), written by `log_session_snapshot`, compared only under the
    same `logic_version`.
  - **Removed:** (ii).

| # | Case | Expected |
|---|---|---|
| 1 | Structure TRANSITIONAL → UPTREND, stand aside both runs | ALERT E1 (decision unchanged, text says so) |
| 2 | Structure UPTREND → DOWNTREND | No E1 (a character change: digest, per session_compare_v2) |
| 3 | Daily strength 24 → 26, 4-hour 30, stand aside both | **No ALERT** (old → new: today flag (ii) fires) |
| 4 | `conditions_met` False → True, stand aside (grade C) | ALERT E2 |
| 5 | `conditions_met` True → True | No ALERT (no repeat) |
| 6 | `conditions_met` False → True and the filter now allows a trade | Only the decision-flip ALERT; no E2 (no double message) |
| 7 | Different `logic_version` between rows | No E2 |
| 8 | Market closed | No snapshot, no flag |
| 9 | Previous row has no `conditions_met` (pre-migration) | No E2 on that comparison ("not recorded" ≠ False, rule 9) |
| 10 | Evening run, before session_compare_v2 ships | No flag (no delta: today's UTC-day behaviour) |

## 3. Overlap with the display-claims spec, and merge order

- **This spec owns:** WATCH FOR, FULL PICTURE's "This changes when", the
  numbers rule (§2.6), and `_machine_flags` class (b).
- **The display-claims spec owns** inventory items 3–7:
  - the override REASON "D1 transition";
  - "strong uptrend on all timeframes";
  - SESSION notes;
  - the spike REASON;
  - research stated as fact, including the "fade, don't follow" note above.
- **Recommended merge order:**
  1. this spec, so exit-watch is true before evening comparisons start sending it;
  2. `session_compare_v2_spec.md`;
  3. the display-claims spec. It rebases on §2.6's numbers rule, because its
     REASON edits touch the same `decision_brief.py` lines (`:660-735`).

## 4. Out of scope

- Decision, filter and regime logic. §5's extraction must leave every output
  byte-identical.
- The summary block.
- Range trading (`RANGE_TRADING_ENABLED` stays False).
- The EXHAUSTION first-class-regime precondition (AGENTS.md).
- The digest's length budget beyond §6's joint test.

## 5. Gates

**Gate 1, the truth sweep (in the suite):**
- **Extract the input assembly.** `get_regime`'s input assembly becomes a pure
  helper in `regime_detection.py`, from (strength, volatility, structure,
  4-hour state, weekly closes, instrument, news state) to the regime dict.
  `get_regime` calls it.
  - Byte-identity: `get_regime` output is identical before and after on 40
    recorded real bar sets.
  - `test_decision_logic.py` is unchanged.
  - The sweep calls the helper, never a copy (W5).
- **For every branch in §2.2:**
  - **Necessity:** every trading cell satisfies the conditions the branch
    names.
  - **Non-vacuity:** at least one cell satisfying them trades (branch 9:
    raising conviction alone flips a C cell to a trade).
  - **Coverage:** every stand-aside cell lands in exactly one branch, and
    branches 1–9 together leave 0 stand-aside cells with nothing true to say.
  - **Old text:** each replaced sentence is shown non-necessary or vacuous.
    This is the positive control that the sweep catches today's text.
- **Pinned facts:**
  - the STRUCTURE_DISAGREES subtype count is 0 through the helper;
  - the §2.4 override invariant;
  - the §2.6 rule over every rendered number (render sweep).
- **Unchanged floors:** stand-down matrix T34–T41 and the banned-token test,
  unweakened. DECISION and the filter result are identical to `main` across
  `test_decision_logic.py`.
- **Digest:** the watch clause is the new first sentence. Nothing else in the
  line changes.
- **Rule 12:** every §2.7 row, through the real `__main__` with a mocked
  `get_regime` and the real wrapper (sandbox, stub notifier).

**Mutation** (each must be caught):
- restore each old sentence (one mutant per branch);
- swap branches 4 and 7;
- round half-up next to a threshold;
- fire E2 on True → True;
- restore flag (ii);
- hard-code the override string outside `_OVERRIDE_RECORD`;
- the tripwire reading `regime_h4`;
- FULL PICTURE back to "This changes when".

**Gate 2:** a real brief under `scripts/reality_run.py --code <worktree>`, with
WATCH FOR and FULL PICTURE shown before and after; project unchanged by hash.

**Gate 3, PENDING LIVE CONFIRMATION:**
- the owner reads a real digest watch clause and it names something that can
  happen;
- the first real E1 or E2 alert.

## 6. Length (cross-spec)

- **The problem.** Branch 6's full text is long. The digest quotes only its
  first sentence ("Watch for: …"), which ends before "Also needs".
- **The joint test.** One test, shared with `session_compare_v2_spec.md` §2.6
  and the pending shadow-digest v2, renders the longest first sentence of each
  branch together with the character-change and shadow markers, and checks
  them under the 400 cut and the osascript 220 cut. The markers survive both.

## 7. Questions for the team

1. **Branch 6 split** into "Watch for" plus "Also needs" (adversarial review
   W8): accept?
2. **Tripwire backstop.** Should `weekly_heartbeat.sh` also print "override
   signals since 2026-11-05: N" (stdlib csv, same rule), so a second override
   is seen within a week even when nobody runs the suite? Recommended: yes.
3. **E2:** worth an alert, or digest-only? The owner's decision 1 says
   exit-watch always alerts. E2 is listed as exit-watch, but its decision is
   still stand aside.
