# Gold plan: what to gather to day and swing trade gold, both directions

**Status:** PROPOSAL, written 2026-11-14 at the owner's request ("create a
detailed plan to implement all of this"). Nothing here is approved. The
team rulings in §2 come before any phase that needs them. The gaps this plan
closes are listed in `docs/capability_inventory.md` (Gold section).
**Progress** is tracked in §0 (last updated 2026-11-16). **§0a is a blocking item (2026-11-17).**

**The goal:** find out, honestly, whether there is a way to day or swing
trade gold (long and short) that pays after costs, and become a trader who
reads gold well enough to use it. **"No" is an acceptable answer.** If the
evidence says no, gold stays a practice chart (§5).

**Where we start (2026-11-14):**
- Gold is **not tradeable** on the OANDA account. It is a paper and markup chart.
- We have 2006–2013 and 2021–2026 price history, and one study of when gold
  moves during the day.
- No rule has been tested on gold. Nothing from the 42 GBP findings
  transfers until it is measured on gold.

---

## 0a. BLOCKING: there is no venue (team ruling J5, 2026-11-17)

**Above every remaining Tier 1–4 item.** Phase E (venue and costs) was
already a prerequisite the gold specs were running ahead of. It is now worse
than unmeasured: **there is no venue.** Gold is not tradeable on the OANDA
account (HTTP 404 `INSTRUMENT_NOT_TRADEABLE`, re-checked 2026-11-17,
validation_log "GLS-1 v4"), so no broker spread, financing rate, day count
or order permission for gold exists to verify against.

- **Any future PASS on any gold rule is uninterpretable** until a venue is
  chosen and its costs are measured on its own platform (Phase E "done
  when").
- **The sealed exam cannot be opened without it**, whatever ruling T1 says.
- Descriptive work may continue with labelled placeholder costs (GLS-1 runs
  under two cost structures for this reason, spec §4.5). A test that would
  write a verdict may not.
- **Cleared when:** the owner names a venue they can open (O2), and Phase E1
  measures its instrument, spread, commission, overnight cost and order
  permission.

## 0. Progress (updated 2026-11-16)

| Item | State | Evidence |
|---|---|---|
| A1 swing tool in dollars | **DONE**, except one check (below) | validation_log 2026-11-14 "GOLD PHASE A"; merge b72490f |
| A1 check: one printed swing price matches the same candle on the owner's TradingView | **NOT CHECKED.** Only a candle close was matched (3884.685), not a swing price | To do with the owner in the W47 markup |
| A2 idea log takes gold as practice | **DONE** | Same entry; reality run logged, scored and reviewed a gold idea in a temp copy |
| A3 playbook gold section | Open; waits for O3 (the W47 Friday review) | — |
| B weekly reps | Starts W47 (2026-11-16) | — |
| **C1 move size in percent of price** | **DONE: R47** (descriptive) | validation_log 2026-11-16 "GOLD C1/C3"; `studies/gold_move_size_report.md` |
| **C2 breakouts** | **DONE: R45** (descriptive) | validation_log 2026-11-14 "GOLD BREAKOUT STUDY (C2)"; `studies/gold_breakout_report.md`; merge d0f55be |
| **C3 pullback depth** | **DONE: R48** (descriptive) | Same entry; `studies/gold_pullback_depth_report.md` |
| C4–C6 | Not started | — |
| **Price-action program screen (M41)** | **Done 2026-11-17** (`docs/reports/gold_program_screen.md`): every GBP replication shelved; never-tested patterns unscreenable by M41 (no estimate) and able to see only edges of +0.19R or more; recommended reading: nothing survives | owner rulings E1–E8 |
| **Hand-drawn zones (the owner's journal)** | **Starts Friday 2026-11-20**: forward Friday scoring of the weekly markup zones; exploratory (20 zones ≈ the futility minimum; no prior estimate) | owner ruling E5 |
| **F: one rule tested (GMW-1, the 4–7 AM PT window)** | **DONE: R49, REFUTED both cells** (2026-11-17), run ahead of Phases C4–C6 and E with owner sign-off and placeholder costs | validation_log 2026-11-17 "GMW-1 RESULT"; `studies/gold_morning_window_result.md` |
| D, E, F, G | Not started | — |

**Where the build differed from this plan (recorded, not hidden):**
- **A1:** gold prices print with **3** decimals, not the 2 written in A1. That is OANDA's precision and matches the owner's TradingView (3,884.685).
- **A2:** the spread is **OANDA's measured quote, $0.47** (median ask − bid at the hourly close, 720 candles 2026-10-01 → 11-13 PT), labelled as not a venue's spread. A2 said "marked unmeasured until Phase E"; a measured proxy was judged more honest than zero. A venue's own spread still comes from Phase E.
- **C ordering:** C2 ran before C1 at the owner's request ("start your breakout study now"). C2 measures distance in daily average ranges (ATR) directly, so it did not need C1's percent-of-price unit.

**Found while building, open for the team:**
- **T4:** `scripts/reality_run.py --code <worktree> script <relative path>` runs the live folder's script, not the worktree's. Script paths resolve against the current directory (line 189), so a branch check can certify `main`'s code. Fix in its own `scripts/` task.
- **T5:** `studies/markup_swings.py` fetches 150 monthly candles, which reach back to mid-2014, inside the 2014–2021 span (sealed for the GBP pairs; proposed for gold under T1). The data map does not say whether a monthly chart read counts. Either rule that it does not, or start the monthly fetch at 2021-04-26.

**Low priority, not a live candidate (owner rulings R10 and A3, 2026-11-16):** gold's low is set by 7 AM PST on 73.1% of days (+6.0 SE above a driftless baseline) while its high is at chance (67.0%), 2021–2026. That span was mostly rising, and "low early, high late" is what upward drift produces, so the asymmetry may be drift, not an overnight-versus-daytime effect. Not worth specifying until it is tested against a drift-matched baseline (`docs/reports/timing_claims_sweep.md`).

**New hypothesis from C2 (not tested):** in each era, breaks against that era's big trend failed more often (2006–2013 upside breaks held more; 2021–2026 downside wicks failed 77%). A candidate question for Phase F, or for its own descriptive study first.

---

## 1. Rules every phase follows

These come from AGENTS.md and the foundation. They are listed here so each
phase does not repeat them.

1. **Free zone unless stated.** `studies/`, `scripts/`, tests and docs. No
   protected module is touched before Phase G, and Phase G needs its own spec
   and team review.
2. **One study = spec first, then code, then one run.** The spec is
   committed before the code that computes anything. It runs once through
   `scripts/reality_run.py`, and its output goes to `validation_log.md`
   whatever it says. Each result gets a finding number in
   `foundation/research_findings.md`, and its inventory row is updated with
   the date.
3. **Report each era separately, never pooled.** 2006–2013 (STUDY) and
   2021–2026 (USED). Gold was a different market in each.
4. **Measure up and down separately.** Most of our gold history is a rising
   market, so a buying rule looks good and a selling rule looks bad for
   reasons that have nothing to do with the rule. Every test of a rule
   compares it with random entries in the same direction, held for the same
   time.
5. **Percent of price where eras are compared.** A $45 move meant 7% of gold
   at $600 and about 1% at $4,000. Dollar figures stay for today's chart.
6. **Honest counts.** Count independent episodes, not rows. Any cell under
   20 is INSUFFICIENT and carries no verdict.
7. **Never touch 2014–2021 gold data** until the team rules on it (T1) and,
   later, opens it once for one frozen rule (Phase F).

---

## 2. Decisions needed first

| # | Who | Decision | Recommendation | Blocks |
|---|---|---|---|---|
| T1 | Team | Declare gold's 2014-01-01 → 2021-04-25 its **sealed exam** now, before anything fetches it, as a dated amendment to `docs/specs/data_map_spec.md` | **Yes.** It is the only gold data nobody has looked at, and an exam can only be sealed before it is seen. **Note (2026-11-14):** the markup tool's monthly fetch has already shown gold's monthly candles from that span (a 2015 low printed in the Phase A before-run; see T5). No daily, 4-hour or hourly gold bar from 2014–2021 has been fetched | Phase F5; also guards Phases C and D from fetching it by accident |
| T2 | Team | All gold studies start at the **2006-03-21** session (gold's first OANDA hours have no 4-hour bar; validation_log 2026-11-05) | **Yes**, the same choice the leg study made. **ADOPTED 2026-11-14** for C2, following the leg study's owner-approved start; noted for the team rather than waited on | Phase C |
| T3 | Team | Gold may be added to `studies/research_archive.py`'s span labels (STUDY / USED / FORWARD), so every gold bar carries its span | **NO RULING NEEDED (2026-11-14):** it already exists. `~/intel_study_archives/research_archive_legs/XAU_USD_D.csv` labels every gold bar by span, and its hash matches the archive manifest | — |
| O1 | Owner | Day trading, swing trading, or both? | Keep both open until Phase E's sizing table. The account size may decide it | Phase F thesis |
| O2 | Owner | Which venues can you open where you live? | Owner research (Phase E1) | Phases E, F costs, G |
| O3 | Owner | Add gold's dollar thresholds to `markups/README.md` at a Friday review (the playbook changes one rule at a time) | Yes, at the W47 Friday review | Phase A3 |

---

## 3. The phases

Each phase lists what it is for, the steps, what comes out, and **what
"done" means**. "Done" always means observed evidence (AGENTS rule 11), not a
claim.

### Phase A: make the tools speak dollars (small; can start now)

**Why:** the markup tool and the idea log were built for GBP pairs. On gold
they would print sizes in "pips" that are wrong by a factor of 10,000, or
refuse the instrument.

| Step | What | Where |
|---|---|---|
| A1 | Give `markup_swings.py` a unit table (`XAU_USD: 1.0`, labelled "dollars") instead of the FX-only pip rule. Print the live price with two decimals for gold | `studies/markup_swings.py` + a test |
| A2 | Let the idea log accept `XAU_USD` as a **paper-only** instrument, with its own unit and a spread **marked unmeasured** until Phase E | `scripts/trader_review.py` + tests |
| A3 | A short gold section in the markup playbook: zone width ≤ about half a day's move (≈ $45 now), "held" = about half a day's move away, ignore wicks in the 2 PM PT break, screenshot names `XAUUSD_W47_start.png` | `markups/README.md` (after O3) |

**Done when:**
- The suite is green.
- A test fails when the gold unit is reverted to the FX pip rule (mutation shown).
- A `reality_run.py script` run of the markup tool on `XAU_USD` prints a
  daily average range in dollars (near the ≈ $75–90 of the owner's notes,
  not ≈ 900,000).
- One swing price it prints matches the same candle on the owner's
  TradingView chart (`OANDA:XAUUSD`, the same feed).

### Phase B: weekly reps (owner; starts W47, 2026-11-16, never stops)

**Why:** skill comes from reading charts and being graded, not from
studies. Process scores mean something long before edge numbers do.

| Step | What |
|---|---|
| B1 | Sunday: the owner's top-down read (monthly → hourly), then mentor review, then the saved markup. Exact swing prices from the markup tool |
| B2 | Friday after 2 PM PT: score every zone (reached / held / broke / never reached) with gold's dollar thresholds. One lesson, at most one rule change |
| B3 | Every gold setup seen, **long or short, taken or passed**, goes in the idea log with an outcome score and a process score |

**Done when (first checkpoint):** 8 weeks scored (up to 48 zones) and 20 or
more ideas logged. Then the first descriptive read of how gold zones behaved.
Below 20 in any count it is INSUFFICIENT and gets no verdict.

### Phase C: gold's basic facts (learning only; after A and T2)

**Why:** every markup choice (zone width, whether to trust a break, how deep
to expect a pullback, whether to hold through news) currently borrows
GBP numbers. These studies replace them with gold's own. **All descriptive:
no entries, no R, no claim that anything pays.** Each uses 2006–2013 and
2021–2026, reported separately.

| # | Question | Method to reuse | Why it matters |
|---|---|---|---|
| C1 | How far does gold move per day, 4 hours and hour, in percent of price, per era and today? | ATR as percent of price | Makes eras comparable; turns "$45 zones" into a rule that still works when gold is at $3,000 or $6,000 |
| C2 | When price closes beyond a confirmed daily swing (3 candles each side), how often is it back inside within 3 days? By how far the break went (in daily ranges). **Upside and downside breaks separately** | R24's method | Tells you whether to trust a breakout or expect a fake |
| C3 | How deep does gold's first pullback go (23.6 / 38.2 / 50 / 61.8%)? **Pullbacks in rallies vs bounces in falls** | R39's leg definition (`first_pullback_study_spec.md` §4) | Where to put zones and stops on a gold fib |
| C4 | Do US CPI, jobs and Fed days give gold bigger ranges? How much of the day-0 move is kept by days 1, 3 and 5? | R35/R36 (`us_event_reaction_spec.md`) and R25. The 2005–2013 event table exists (`studies/us_events_2005_2013.csv`); a 2021–2026 table must be assembled and checked | Whether to stand aside, or hold, around US news |
| C5 | Do falls behave differently from rallies? Speed (percent per day), length in days, and how deep the counter-moves go | New, using C3's legs | The core of trading both directions: a short may need different stops and targets from a long |
| C6 | How big are weekend gaps, and how often does one jump past the smallest allowed stop (0.3 of a day's move)? | New | Whether a swing trade can hold over a weekend |

**Ordering:** C1 first (the others use its unit), then C2 and C3 (they feed the
markup straight away), then C4, C5, C6. **Actual:** C2 ran first at the owner's
request (§0); C1 and C3 ran on 2026-11-16 (R47, R48); C4, C5, C6 are next.

**Watch for:**
- 2021–2026 gold was mostly rising, and so were 2006–2011. The falls are mainly 2011–2013 and a few shorter drops. Report how many falls each era holds; the downside cells may be INSUFFICIENT.
- 2014–2021 stays untouched (T1).

**Done when:** for each study, the spec commit comes before the code commit,
there is one run's output verbatim in validation_log, a finding number is
assigned, and the inventory row is updated. A study whose check never
showed it could fail is not done.

### Phase D: what moves gold (context only; can run alongside C)

**Why:** on the monthly and weekly charts, gold follows money and rates more
than patterns. These are context for the read, **never entry signals**
unless a later pre-registered test earns that.

| Step | What |
|---|---|
| D1 | Fetch, outside the repo, with hashes: the US 10-year real yield and a broad dollar index (FRED), and weekly futures positioning for gold (CFTC). Store under `~/intel_study_archives/gold_drivers/`. Positive control: three hand-picked dates match the source website |
| D2 | Descriptive: the rolling 1-year correlation of weekly gold moves with changes in real yields and in the dollar, per era. Shows when the textbook link held and when it broke (reported 2022–2024) |
| D3 | The owner writes one gold line a week (rates, dollar, positioning, what that suggests) in the markup file, logged so it can be graded later. **First, test that whatever reads that line actually finds it.** The `storylines.md` parser once found zero biases in the real file (inventory, Macro section) |

**Done when:** the archive is verified (positive control shown), the D2 report
is logged, and four weeks of D3 lines exist.

### Phase E: venue, costs and position size (owner research; can start now)

**Why:** a rule that cannot be sized on your account, or that costs more
than it makes, is not a plan. This phase may decide day versus swing on its own.

| Step | What |
|---|---|
| E1 | For each venue you can open: the instrument (spot, micro futures = 10 oz, standard futures = 100 oz), dollars per $1 move, commission, typical spread in quiet hours **and at 5:30 AM PT news**, margin, overnight cost, trading hours |
| E2 | Sizing table: account size × risk per trade (0.25 / 0.5 / 1%) × stop ($27 / $45 / $90 / $135, i.e. 0.3 / 0.5 / 1 / 1.5 days' move) → how many contracts, or "cannot size" |
| E3 | **If futures:** the chart you mark up must be the futures chart, or the gap to spot must be stated. Futures sit apart from spot by the carry and roll every quarter. Levels drawn on OANDA spot do not transfer one-to-one. Feed validation comes before any statistic (methodology) |
| E4 | Overnight cost: spot charges nightly financing; futures build it into the price. Either way it goes into the Phase F cost model (financing was the size of the edge on GBP/JPY, R32) |

**Done when:** one venue is chosen, with its spread measured on its own
platform at the quiet hours and the busy hours, and the cost model is written
into the Phase F spec.

### Phase F: one rule, tested properly (after B's first checkpoint, C, E and T1)

**Why:** this is where an edge is found or ruled out. It comes last because
choosing a rule before knowing gold's basic behaviour and real costs is how
the GBP candidates were born from a few memorable charts (and none showed an
edge).

| Step | What |
|---|---|
| F1 | **Write one thesis before computing anything new.** It needs a reason to work that does not come from our own charts. Two to weigh, **not chosen yet**: (a) swing: trade in the direction of gold's 6–12-month trend (trend-following over 1–12 months is documented across commodities), entering on pullbacks; (b) day: a rule built around the 4–7 AM PT window, where most of the day's range forms. Never from a grid search of parameters (AGENTS rule 3) |
| F2 | Long and short are separate cells, each against random entries in the same direction and held for the same time. Costs = Phase E spread + financing. Graded on the stop: a stopped trade is −1R |
| F3 | **Power, before running** (`power_check.py`): about 400 independent episodes to detect +0.15R. Over the exam's 7.3 years that means about 55 a year. A day-trade rule can reach that; a swing rule probably cannot. If it cannot, the spec says so up front: the test can only refute, not validate |
| F4 | One pre-registered run on 2006–2013 (STUDY). The same frozen spec on 2021–2026 as a learning check, reported separately |
| F5 | **Only if SUPPORTED on STUDY**, and the exam spec states the expected N and the smallest detectable edge before opening: the team opens gold's 2014–2021 exam once, for this one rule (data_map_spec §7, §11.6) |

**Done when:** a verdict label (REFUTED / INCONCLUSIVE / SUPPORTED, or VALIDATED
only after F5) is logged with its numbers: independent N, mean and median R,
mean without the best episode, lower confidence bound, and costs included.

### Phase G: forward, then small real money (only after a SUPPORTED or VALIDATED rule)

| Step | What |
|---|---|
| G1 | Paper forward log of the frozen rule under a new candidate id with a fresh ledger. Adding gold to `shadow_signals.py` is a protected change, so it needs a spec and team review; a separate paper log is the free-zone alternative |
| G2 | **Before the first real-money trade:** the circuit breaker (`session_guard.py`, `risk_config.py`) must be wired and exercised (AGENTS prerequisite), and extended so a gold position counts toward the two-position cap. Gold and the GBP crosses are only weakly linked week to week (weekly correlation −0.23 to +0.06, leg study, validation_log 2026-11-05), so gold counts as its own exposure. Protected modules: spec and team review |
| G3 | Smallest size the venue allows. Every trade journaled. Both scores (outcome and process). No change to the rule; a change means a new id |

**Done when:** 20 or more forward trades are graded before any claim about live
performance, and the circuit breaker is shown blocking a trade it should block.

---

## 4. Order at a glance

| Phase | Needs | Who | Size | Can start |
|---|---|---|---|---|
| T1–T3 rulings | — | Team | Small | Now |
| A: tools in dollars | O3 for A3 only | Agent | Small | Now |
| B: weekly reps | A1 helps | Owner (+ mentor) | Ongoing | Now (W47) |
| **E: venue and sizing (BLOCKING, §0a)** | O2 | Owner | Medium | Now |
| C: gold's facts | A, T2 | Agent, owner reads | 6 studies | After A |
| D: drivers | — | Agent + owner | Medium | Alongside C |
| F: one rule | B checkpoint, C, E, T1 | Agent + owner + team | Large | After those |
| G: forward and live | A positive F verdict | All; team for G2 | Large | Only if F passes |

**Suggested first week:** T1–T3 to the team, A1 and A2 built, W47 markup
scored, and E1 started by the owner.

---

## 5. When to stop

Decided now, before any result, so a disappointing number cannot move the goalposts:
- **Phase F refuted, or inconclusive with an unreachable N:** gold stays a
  practice chart. No tweak-and-retest of the same idea. A genuinely new
  thesis is a new id and a new spec, and spends no exam data.
- **No venue fits the account (Phase E2 says "cannot size" at 1% risk):**
  paper only, until it can.
- **Markup scoring after 8 weeks shows more zones broken than held:** review
  the method at the Friday review, one rule change at a time. Not a reason to
  abandon gold; a reason to learn why.

## 6. What this plan does not do

- Touch any of the 21 protected modules (until Phase G, with its own spec).
- Fetch or look at gold's 2014–2021 data.
- Propose any trade now. Gold is paper-only, and no rule exists.
- Treat any driver, level or session fact as an entry signal.
