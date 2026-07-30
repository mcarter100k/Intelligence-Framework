# AGENTS.md — operating contract for AI agents in this repo

**Mission context:** quantitative FX decision framework (GBP/AUD, GBP/JPY).
Core philosophy: nothing is VALIDATED without honest non-overlapping sample
sizes; everything unproven is INFORMED PRIOR; the framework stands aside rather
than trade without evidence. Current phase: **EVIDENCE ACCUMULATION** — a frozen
shadow-signal ledger grading candidates on forward data.

**Success metric for agents: zero unreviewed changes to the tradeable path.**
Not lines shipped. Build capacity is not the bottleneck; discipline is.
Idle agents are correct behavior when the queue is empty.

---

## PROTECTED — team review required before any merge

**The 14 live core modules** (the tradeable path and its evidence loop):

```
decision_brief.py        run_outcome_check.py     regime_detection.py
official_decision.py     no_trade_filter.py       regime_classifier_logger.py
trade_outcome_logger.py  shadow_signals.py        session_memory.py
entry_confirmation.py    levels_context.py        intraday_context.py
oanda_feed.py            news_gate.py
```

(`news_gate.py` added 2026-07-30 per the team-approved spec in
`docs/specs/news_gate_spec.md` — protected-path specs become repo artifacts
before building.)

**Frozen candidate specs** — `shadow_signals.py` candidates (EARLY_MOMENTUM,
THRUST_PULLBACK, MOMENTUM_JOIN) are FROZEN. Parameter changes are NEVER edited
in place: any change starts a **new candidate id** (e.g. `EARLY_MOMENTUM_v2`)
with a **fresh ledger**. Review gates: FLAG at N=30 graded episodes, DECISION
at N=60. Episodes = non-overlapping 30-bar horizons, not raw rows.

**Data ledgers are evidence — append-only via the loggers, never by hand:**
`shadow_signal_log.csv`, `regime_classification_log.csv`,
`trade_signal_log.csv`, `session_context_log.csv`, `trade_log.csv`,
and everything under `logs/`. Agents never edit, regenerate, or delete them.
`logs/archive_prerebuild/` is historical record — untouchable.

**`validation_log.md` is append-only.** Corrections are new dated entries,
never rewrites of old ones (see the Honesty Correction banner for the format).

**`RANGE_TRADING_ENABLED` stays `False`** (`official_decision.py`) absent team
review + validation. Precedent: the counter-trend override was reviewed, met
all five conditions, fired 2026-05-15, and lost on a 280-pip rally.

**Quarantine zones** — `shadow/` (the legacy signal stack; 0 comparisons
logged, reactivation condition in its README) and `legacy_validators/`
(invalidated methodology; never cite their output). Promotion out of either
requires team review; their priors are not evidence.

---

## FREE ZONE — agents may build with tests green

- `studies/` — report-only research scripts (the methodology record; never
  deleted, never imported by the live path)
- `scripts/` — automation wrappers and launchd config
- Tests (new tests are always welcome; see the two floors below)
- Docs (`*.md`), this file included — but `validation_log.md` is append-only

---

## STANDING RULES

1. **Git safety.** The git repo root is the user's HOME directory
   (`/Users/quis`), not this project folder. Consequences: **explicit
   `git add` per file, NEVER blanket staging** (`git add -A` from the wrong
   cwd stages personal files); `git mv` for moves so history follows; after
   staging, verify nothing outside `Intelligence Framework/` and no
   gitignored ledgers are staged.

2. **Suite green before any commit.** Full run: `python -m pytest -q`
   (currently 1018 passed; shadow-stack tests run from `shadow/` via its
   conftest). Two floors that must never be weakened to make something pass:
   - the **banned-token display test** (`test_brief_display.py`) — rendered
     output stays plain-English: no ADX / pivot / HH-HL / LH-LL / ATR-ratio
   - the **stand-down consistency matrix** (`test_regime_detection_p1.py`,
     T34–T41) — `apply_filter` is the single stand-down authority

3. **Evidence honesty.** No VALIDATED label without non-overlapping N. Every
   study reports honest N (flag N<20 as INSUFFICIENT). No shadow candidate is
   ever proposed from in-sample grid selection. Negative results get logged in
   `validation_log.md` with the same care as positives.

4. **Plain-English rendering.** Anything a trader reads (REASON, EXIT IF,
   MARKET STATE, DATA BASIS, THE FULL PICTURE, notifications) uses plain
   words — enforced by test, not convention. Internal names, logs, and CSVs
   keep technical terms.

5. **Premise inspection before destructive or assumption-based action.** If
   the stated premise of an instruction fails inspection — the file isn't
   what it was described as, the target belongs to another project, the spec
   being "executed" doesn't exist — **STOP and report instead of proceeding.**
   Precedent: crontab entries assumed to be this repo's stale producers were
   inspected, found to belong to other projects, and left untouched.

6. **Report every run.** End with: files touched, diffstat, tests run and
   result, anything deferred for team review. A blocked task reported cleanly
   is a success; an unreviewed change to the tradeable path is the only
   failure mode that matters.

---

## Live entry points (what "reachable" means)

Daily brief: `python3 decision_brief.py GBP_AUD GBP_JPY`
Nightly grader: `python3 run_outcome_check.py`
Automation: `scripts/scheduled_brief.sh`, `scripts/scheduled_outcome_check.sh`
(launchd plists in `scripts/launchd/`), plus the test suite.
Anything not reachable from these is research (`studies/`), quarantined
(`shadow/`, `legacy_validators/`), or a manual tool (`trade_logger.py`,
`trade_management.py`, `update_calendar.py`).
