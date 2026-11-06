# Decision paper v2: which shadow candidates keep running after FCS-1

**Status:** PROPOSED 2026-11-05. **This is a decision for the team, not a build.**
It supersedes `fcs1_retirement_decision_spec.md` (v1). That body is kept as
written.

v1 review:

| Reviewer | Verdict |
|---|---|
| Code reviewer | APPROVE WITH CHANGES |
| Adversarial reviewer | REJECT as written |

Both endorsed retiring EARLY_MOMENTUM_v2 and THRUST_PULLBACK GBP/AUD. v1's case
for keeping MOMENTUM_JOIN GBP/AUD breaks an approved frozen rule (§3). Its
mechanics did not stop retired cells from reaching the owner (§6). This
version fixes both, and adds what each kept cell can ever decide (§5).

Nothing is retired by this file. A retirement is built under its own build
spec and review (`shadow_signals.py` is protected).

## 1. The question

The owner asked (2026-11-05): "Was it a pre-registered run with an honest N,
or an in-sample look? If it's the former, the question isn't how to word the
shadow block — it's whether these three should still be running at all."

**Answer: pre-registered, with honest N.** The spec, runner and data hashes
were committed (81f25bb, 23:20:05) before the counts (af004a3, 23:20:51) and
the single full run (20117d4, 23:24:14).

| Reviewer check | Result |
|---|---|
| Counts stage timed | 17.7 s and 19.7 s, consistent with that order |
| Candidates designed on this span? | No. Frozen 07-29 (640fc81) and 09-09 (2626b96); the STUDY span opened after 09-11 / 10-22 |

**Limit, stated by the adversarial reviewer:** commit order shows that the text
existed at commit time. It cannot show that nothing ran before. That part
rests on trust. The span had also already been used by three other studies
(carry, US releases, first pullback); those never touched these candidates.

## 2. The evidence

Pre-registered verdicts (`studies/frozen_candidates_study_result.md`, R40–R42):

| Cell | Episodes | Mean R (era costs) | 90% upper bound | Verdict |
|---|---|---|---|---|
| EARLY_MOMENTUM_v2 GBP/JPY | 246 | −0.099 | +0.042 | **REFUTED** |
| THRUST_PULLBACK GBP/AUD | 51 | −0.130 | +0.035 | **REFUTED** |
| MOMENTUM_JOIN GBP/AUD | 98 | −0.095 | +0.117 | **REFUTED** |
| MOMENTUM_JOIN GBP/JPY | 96 | −0.012 | +0.222 | INCONCLUSIVE |
| THRUST_PULLBACK GBP/JPY | 39 | +0.056 | +0.312 | INCONCLUSIVE |

## 3. The pre-registered verdicts stand (what v1 got wrong)

v1 proposed keeping MOMENTUM_JOIN GBP/AUD because its bound at today's spread
is +0.166R. That is not admissible, for three reasons.

1. **An approved frozen rule forbids it.**
   - `data_map_spec.md:110-112`: "Modern costs on old data manufacture profit
     that never existed; no result computed under a different schedule is
     citable."
   - FCS-1 had also pre-registered the flat 3-pip spread as a secondary that
     "never changes a verdict" (spec §11). Its mean was published at −0.045R:
     still negative.
2. **The premise was wrong: the live grader charges no costs.**
   - `shadow_signals.grade_pending_shadow` grades R before any spread or
     financing. A grep of `shadow_signals.py` for spread, cost and financing
     finds nothing.
   - A kept cell is judged forward at zero cost, where history's bound is
     +0.209R.
   - The futility rule only catches clear losers, so it would almost certainly
     never retire such a cell.
3. **The robustness columns were applied selectively.** v1 relaxed one
   assumption at a time and called two cells "refuted under every assumption".
   Both reviewers re-ran the method and reproduced v1's columns. Stacking
   today's spread with the family correction (98%) gives:

   | Cell | Stacked bound | Refuted on this basis? |
   |---|---|---|
   | EARLY_MOMENTUM_v2 | +0.170 | no |
   | THRUST_PULLBACK GBP/AUD | +0.166 | no |
   | MOMENTUM_JOIN GBP/AUD | +0.301 | no |

   So the line between "robust" and "fragile" depends on which adjustments are
   stacked. At the repo's own GBP/AUD spread of 4.0 pips (`risk_config.py:35`),
   MOMENTUM_JOIN GBP/AUD's bound is +0.157, 0.007R from the bar (code
   reviewer).

   **The only rule applied the same way to every cell is the pre-registered
   one.** Post-hoc sensitivities are reported for context and never decide.

## 4. The forward ledger and what reaches the owner

Rows (`get_shadow_tally` on a ledger copy, through `reality_run.py`; both
reviewers reproduced it):

| Cell | Rows | Graded | Episodes (first-fire R) |
|---|---|---|---|
| EARLY_MOMENTUM_v2 GBP/JPY | 24 | 20 | 4: −0.55, −0.39, +0.34, −1.00 |
| MOMENTUM_JOIN GBP/AUD | 5 | 5 | 1: −1.00 |
| MOMENTUM_JOIN GBP/JPY | 2 | 2 | 1: −1.00 |
| THRUST_PULLBACK GBP/JPY | 2 | 2 | 2: −0.33, +1.94 |
| THRUST_PULLBACK GBP/AUD | 0 | 0 | none ever |
| EARLY_MOMENTUM v1 (retired 2026-09-09) | 3 | | 1: −1.00 |

**Notifications** (`notification_log.csv`, which starts 2026-10-20; code
reviewer): 15 SHADOW notifications.
- 10 came from brief fires: 7 EARLY_MOMENTUM_v2, 2 MOMENTUM_JOIN, 1 THRUST_PULLBACK.
- 5 came from the nightly grader, and every one named EARLY_MOMENTUM_v2.

**Retiring on paper has not stopped the display.** v1 said the v1 candidate's
rows "stay out of every tally". That is false: `get_shadow_tally("EARLY_MOMENTUM")`
returns 1 episode. The grader's 2026-11-05 23:15 notification still reads
"EARLY_MOMENTUM: 1ep avg -1.00R | EARLY_MOMENTUM_v2: 4ep …", two months after
v1 was retired. I verified this by reading `notification_log.csv`.

## 5. What each kept cell could ever decide

Forward cadence is inferred from FCS-1's episode rate times the live
harness's share of bars checked (about 2/3; that share is NOT CHECKED here).

| Cell | Episodes a year, live (INFERRED) | Futility check at N=20 | FLAG at N=30 | Sealed-exam eligible (`data_map_spec` §1, ≥ 8 a year) |
|---|---|---|---|---|
| MOMENTUM_JOIN GBP/JPY | about 7 | about 2029 | about 2030 | **yes**: about 10.7 a year, so roughly 78 episodes in 2014–21 |
| THRUST_PULLBACK GBP/JPY | about 3 | about 2032 | later | no (4.3 a year) |

THRUST_PULLBACK came from an in-sample grid sweep (R10). AGENTS.md rule 3 now
forbids proposing a candidate that way. It was frozen on 2026-07-29, before
the rule. Its GBP/AUD sibling is refuted twice: the R17 walk-forward at −0.10R
and FCS-1.

## 6. Mechanics, if anything is retired (both reviewers' design)

- **Leave the frozen machinery unfiltered.** `_CANDIDATES` and
  `check_shadow_signals` stay as they are. Then:
  - FCS-1's bar-by-bar comparison with live code keeps working, including its
    `_CANDIDATES` swap at `frozen_candidates_study.py:350-356`;
  - the three suite tests that assert EARLY_MOMENTUM_v2 fires keep working:
    `test_news_gate.py::test_shadow_signals_fire_through_news_window`,
    `test_decision_logic.py::test_v6_shadow_stamp_ignores_the_post_release_buffer`
    and `test_shadow_signals.py::test_idempotent_double_eval_no_duplicate_rows`.
- **Filter retired cells at every path that reaches the owner,** from one
  registry of retired cells:
  1. `run_and_report`, the only live caller: never log, never print a retired cell.
  2. `latest_pending_signal`, which feeds THE FULL PICTURE, whose text the
     wrapper's candidate-name grep lifts into notifications
     (`decision_brief.py:378,1234`; `scheduled_brief.sh` ~175).
  3. The grader notification tally (`scheduled_outcome_check.sh:86-94`),
     which hard-codes four names, including the retired v1.
  4. The weekly heartbeat tally (`weekly_heartbeat.sh:66-75`).
- **The registry includes EARLY_MOMENTUM v1,** which closes the two-month leak in §4.
- **Pending rows still grade.** `grade_pending_shadow` never reads
  `_CANDIDATES` (verified by grep), so the record completes. That they grade
  correctly is INFERRED.
- **The grader notifies once per run, not once per row.** A run sends one
  notification with the pooled tally.
- **Rule 12: the build spec must carry a test table** with at least these rows:
  - a retired row graded alone;
  - a kept row graded (retired cells excluded from the text);
  - both graded in one run;
  - nothing graded;
  - a retired cell's would-be fire during a brief;
  - a retired pending row in THE FULL PICTURE while a DECISION fires;
  - the heartbeat line;
  - a closed market.

## 7. Recommendation (for the team to accept, amend or reject)

| Cell | Recommendation | Basis |
|---|---|---|
| EARLY_MOMENTUM_v2 GBP/JPY | **Retire** | Pre-registered REFUTED, at the best power of any cell. Forward 4 episodes averaging −0.40R. Most notifications |
| THRUST_PULLBACK GBP/AUD | **Retire** | Pre-registered REFUTED. Never fired live |
| MOMENTUM_JOIN GBP/AUD | **Retire** | Pre-registered REFUTED. v1's rescue withdrawn (§3) |
| MOMENTUM_JOIN GBP/JPY | **Keep**, with a team date to reconsider (proposed 2027-05-01) | Inconclusive. The only cell that could ever reach a decision: the forward futility check around 2029, or sooner through the sealed exam, which is the team's one-shot call (`data_map_spec` §7) |
| THRUST_PULLBACK GBP/JPY | **Retire** (a judgment, not a refutation) | It cannot reach any decision this decade (§5). It was grid-selected, and its sibling is refuted twice. The alternative is keeping it as an explicit no-claim watch that says so on every display |

If accepted:
- MOMENTUM_JOIN GBP/JPY is the only live shadow candidate, with about 7
  episodes a year and roughly one notification every month or two.
- The shadow block and the digest spec describe one cell.

Undoing a retirement means a new candidate id with a fresh ledger at any time.
The sealed exam remains unopened.

## 8. Questions for the team

1. Accept, amend or reject each row of §7.
2. Futility pooling (`futility_rule_spec.md` §2) pools a candidate's episodes
   across pairs. If MOMENTUM_JOIN GBP/AUD retires, does its 1 forward episode
   (−1.00) stay in MOMENTUM_JOIN's count? Changing that frozen spec needs a new
   spec. EARLY_MOMENTUM_v2's checkpoint becomes moot.
3. MOMENTUM_JOIN GBP/JPY: forward ledger only, or propose it for the sealed exam?
4. The reconsideration date for any kept cell.
5. Whether the four open EARLY_MOMENTUM_v2 rows' grading notifies at all, or
   goes only to the record.

## Not in scope

- Building.
- Frozen parameters.
- Opening the sealed exam.
- The every-bar cadence item.
