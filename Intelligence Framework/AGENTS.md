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

**The 21 live core modules** (the tradeable path and its evidence loop):

```
decision_brief.py        run_outcome_check.py     regime_detection.py
official_decision.py     no_trade_filter.py       regime_classifier_logger.py
trade_outcome_logger.py  shadow_signals.py        session_memory.py
entry_confirmation.py    levels_context.py        intraday_context.py
oanda_feed.py            news_gate.py             calendar_fetch.py
setup_check.py           session_guard.py         risk_config.py
display_time.py          exclusions.py            ledger_io.py
```

(`news_gate.py` added 2026-07-30 per the team-approved spec in
`docs/specs/news_gate_spec.md` — protected-path specs become repo artifacts
before building. `calendar_fetch.py` and `setup_check.py` added 2026-09-09
per the post-audit directive: both were built 2026-07-31 to repo specs but
never listed — `calendar_fetch.py` runs inside the scheduled wrapper and
`setup_check.py` writes the pre-trade journal, so the review boundary must
match the execution boundary. `session_guard.py` and `risk_config.py`
promoted out of `shadow/` 2026-09-09 per
`docs/specs/circuit_breaker_promotion_spec.md` — the circuit breaker reads
the live `trades.csv` two-row ledger and carries the shared-currency-leg
standing rule; where it GATES the live path is a separate pending spec.
`display_time.py` added 2026-09-10 per docs/specs/display_timezone_spec.md —
the single point where times become human-readable.)

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
**Every write goes through `ledger_io.py`** (added 2026-09-30,
docs/specs/safe_ledger_writes_spec.md). Use `append_row` for appends,
`atomic_write_rows` for rewrites, and `migrate_header` for schema changes,
and hold `locked(path)` from the read to the write of any read-modify-write.
A bare `open(ledger, "w"/"a")` loses concurrent rows, and a crash mid-write
empties the file; both were reproduced. `backups/<UTC stamp>/` holds
hash-verified copies taken before every nightly grade; never edit them.

**`validation_log.md` is append-only.** Corrections are new dated entries,
never rewrites of old ones (see the Honesty Correction banner for the format).

**`RANGE_TRADING_ENABLED` stays `False`** (`official_decision.py`) absent team
review + validation. Precedent: the counter-trend override was reviewed, met
all five conditions, fired 2026-05-15, and lost on a 280-pip rally.
Additionally (2026-09-09): **RANGING is overloaded** — the label covers both
a quiet market (ADX < 18) and the GBP/JPY exhaustion state (ADX ≥ 35: violent
one-way move, fade don't follow; surfaced as `regime_*_subtype="EXHAUSTION"`;
since 2026-09-30 also a decision input — `apply_filter` stands aside on it,
docs/specs/decision_logic_spec.md D1). **PRECONDITION: promoting EXHAUSTION to a first-class regime —
classifier, composite table, conflict logic, tests — is REQUIRED before
`RANGE_TRADING_ENABLED` may ever be set True.** A range-trading gate keyed on
`RANGING` would otherwise fade 60-ADX exhaustion moves as if they were quiet
ranges.

**Former quarantine zones — REMOVED 2026-09-29** (owner-approved audit,
`docs/audit_2026-09-29.md`). `shadow/` (the legacy signal stack; 0
comparisons ever logged, superseded by `shadow_signals.py`) and
`legacy_validators/` (invalidated overlapping-window methodology) are gone
from the tree and live only in git history. Their priors are not evidence;
restoring either requires team review and a concrete evidence path.

---

## FREE ZONE — agents may build with tests green

- `studies/` — report-only research scripts (the methodology record; never
  deleted, never imported by the live path)
- `scripts/` — automation wrappers and launchd config
- Tests (new tests are always welcome; see the two floors below)
- `foundation/` — the curated "what is proven good" knowledge base and the
  source of the `trading-foundation` skill (`foundation/build_skill.sh`).
  Add new findings, incidents and rules here with citations.
- Docs (`*.md`), this file included — but `validation_log.md` is append-only

---

## STANDING RULES

1. **Git safety.** The git repo root is the user's HOME directory
   (`/Users/quis`), not this project folder. Consequences: **explicit
   `git add` per file, NEVER blanket staging** (`git add -A` from the wrong
   cwd stages personal files); `git mv` for moves so history follows; after
   staging, verify nothing outside `Intelligence Framework/` and no
   gitignored ledgers are staged.

1b. **Branch workflow (adopted 2026-07-30). Never build directly on `main`.**
   - **The project folder is the LIVE checkout and stays on `main`**
     (amended 2026-09-29). launchd runs whatever is checked out there; from
     2026-09-16 to 2026-09-29 it ran an unmerged branch for 13 days.
     `scripts/live_guard.sh` alerts on every scheduled run when it is not
     on `main`.
   - Each task starts a feature branch off up-to-date `main` **in a git
     worktree outside the project folder**, including doc-only changes:
     `git -C /Users/quis worktree add -b feat/<short-name> <dir> main`.
     Remove the worktree after merge (`git worktree remove <dir>`).
   - Verification runs that call real code from a worktree must still
     neutralize side effects (rule 10). Run from a temp working directory
     so relative ledger paths land there, and hash the project before and
     after.
   - All commits happen on the branch (spec artifact first for protected-path
     work, then build commits). The branch is where testing AND team review
     happen.
   - Merge to `main` only when: full suite green on the branch, live
     verification done (brief/wrapper runs where relevant), and — for
     PROTECTED files — team review given.
   - Then push `main`; delete the merged branch locally. Branches stay local
     unless review needs them remote. `main` is never the testing ground.

2. **Suite green before any commit.** Full run: `python -m pytest -q`
   (currently 763 passed on the live checkout — 2026-09-30, after the Phase 5 merge and ledger migration). `conftest.py` isolates EVERY test:
   each runs in its own tmp_path (relative ledger paths land there), the
   absolute-path writers are redirected, unit tests cannot reach the network
   (mark real-network tests `@pytest.mark.integration`), and the session
   FAILS if ANY file in the project (logs/ included; caches, venv/ and .git
   excepted) was created, changed or deleted. Never weaken these to make a
   test pass. Two floors that must never be weakened to make something pass:
   - the **banned-token display test** (`test_brief_display.py`) — rendered
     output stays plain-English: no ADX / pivot / HH-HL / LH-LL / ATR-ratio
   - the **stand-down consistency matrix** (`test_regime_detection_p1.py`,
     T34–T41) — `apply_filter` is the single stand-down authority
   Floor changes happen only with the owner's explicit authorization, each
   documented old → new in the test and its spec. The one so far:
   2026-09-30 (docs/specs/decision_logic_spec.md). T10/T11/T12/T15 now
   require agreeing structure at ADX ≥ 32. T37 feeds the emitted conflict
   type instead of a phantom token. The single-authority rule is now exact:
   `apply_filter` runs the official decision and allows **iff** it trades
   (grade C and no-direction included), swept over 36,864 cells in
   `test_decision_logic.py`.

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

7. **Two-Gate Verification Standard (adopted 2026-07-31).**
   - **Gate 1 — controlled-input tests:** failure paths, rare conditions,
     pinned values. Required, NEVER sufficient. No merge on Gate 1 alone.
   - **Gate 2 — pre-merge reality verification (mandatory):** real OANDA,
     real files, real scheduled paths. Every run report carries a
     **REALITY GATE** section showing actual output. Mock results may never
     appear in it. Run it with `scripts/reality_run.py brief|grader|script`,
     which neutralizes every side effect and certifies it (see rule 10). An
     exit code is not a certification: the brief exits 0 on an error page,
     and the tool treats that as a failure (exit 3).
   - **Gate 3 — PENDING LIVE CONFIRMATION:** anything only time can prove
     (a scheduled job firing, an alert on a real flip, a ledger graded by
     the market) gets an entry in `validation_log.md`'s PENDING LIVE
     CONFIRMATION section; entries are cleared with date + evidence when
     reality performs them. Never claim a time-dependent behavior works
     until reality has performed it.

8. **A CADENCE REQUIRES A LIVE WRITER (adopted 2026-09-16).** Artifacts
   with no live producer are inventoried (`READ_SIDE_NO_CADENCE` in
   `scripts/artifact_freshness.py`) and never alarmed on — a permanent
   alarm is indistinguishable from a broken one, and the first response to
   a channel that always screams is to stop reading it. Precedents:
   `trades.csv` (2026-09-16), `trade_log.csv` (2026-09-16).

9. **A ZERO FROM AN UNVERIFIED PATH IS NOT DATA (adopted 2026-09-16).**
   Every ledger-derived display must distinguish **"no observations"** from
   **"path not proven live."** Three times a can't-fire has rendered as a
   no-setup: `log_regime` (2026-09-09), THRUST_PULLBACK, and
   `trade_signal_log` (2026-09-16 — an empty ledger graded nightly read as
   a framework that issued no signals, when it had issued at least one).
   A zero never shown capable of being non-zero is absence of evidence,
   not evidence of absence, and the display must say which.

10. **VERIFICATION RUNS MUST NEUTRALIZE EVERY SIDE EFFECT ON THE PATH THEY
    EXERCISE (adopted 2026-09-16)**, not only the one under test.
    `get_decision_brief` writes three ledgers; a Gate-2 run that redirects
    one contaminates two. Precedents: `trades.csv` test spill
    (2026-09-11), `session_context_log` + `regime_classification_log`
    contamination (2026-09-16). Use `scripts/reality_run.py` for any run
    that touches real code and real data. It runs the target from a temp
    working directory with copies of the ledgers and the `.env` credentials,
    then hashes the whole project before and after and fails (exit 2) if
    anything changed. It needs no knowledge of which writers exist, which is
    exactly what the 2026-09-16 run lacked. Add `--code <worktree>` to verify
    a branch against the live ledgers. A contaminated evidence row can
    never be removed — the ledgers are append-only — so the only remedy is
    a registry entry (`exclusions.py`) keeping it out of every tally
    forever. Prevention is the whole of the cure.

11. **NO CLAIM WITHOUT OBSERVED EVIDENCE (owner-directed 2026-09-29).**
    Nothing is reported as done, fixed, working, safe or validated unless it
    was observed this session with a check shown able to fail. That means a
    positive control for "found nothing" and a mutation test for "the test
    catches it". Label every claim VERIFIED / OBSERVED / INFERRED / PENDING /
    NOT CHECKED; only VERIFIED may be called done. Exit codes, counts and `ls`
    are not certification. When an overclaim is discovered, lead with it and
    log a dated correction. Precedent: Phase 1 was reported finished with six
    inferred claims (validation_log 2026-09-29 CORRECTION). Method and report
    format: the `evidence-validation` skill (`foundation/skills/`).

---

## Live entry points (what "reachable" means)

Daily brief: `python3 decision_brief.py GBP_AUD GBP_JPY`
Nightly grader: `python3 run_outcome_check.py`
Automation: `scripts/scheduled_brief.sh`, `scripts/scheduled_outcome_check.sh`,
`scripts/scheduled_calendar.sh`, `scripts/weekly_heartbeat.sh` (launchd
plists in `scripts/launchd/`; launchd runs `/bin/bash` 3.2 — see
`test_shell_syntax.py`), plus the test suite.
Anything not reachable from these is research (`studies/`) or a manual tool
(`setup_check.py`, `trade_logger.py`, `trade_management.py`). Note:
`session_guard.py` and `risk_config.py` are protected but have NO live
caller (2026-09-29 audit) — wire them or delete them.
