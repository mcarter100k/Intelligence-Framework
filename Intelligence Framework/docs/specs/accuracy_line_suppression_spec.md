# Spec: stop showing the invalid regime-accuracy percentage (2026-10-19)

**Status:** team review given 2026-10-19. Committed before the build.
`decision_brief.py` is protected.

**Problem.** Every brief's DATA BASIS line shows a regime-accuracy
percentage once a bucket has 20 or more outcomes. Today's line reads:
"daily unresolved-direction bucket: 49 outcomes logged, 0% accuracy
(developing)". Read plainly, it says the framework was wrong 49 times out
of 49. It wasn't. The measure behind it is known to be invalid (audit
2026-09-29 item 2, incident I18):
- MR_WIN tests against the outcome window's own mean;
- VOL_EXPANSION scored 0/12;
- N is inflated about 2x.

It has been shown as evidence every morning since. M24 applies: a number
from a path not proven valid is not data.

**Change.** In `_build_regime_log` (display only), for any bucket with N
of 20 or more:
- show the outcome count;
- show no percentage;
- show no tier label ("developing", "flag threshold", "validated sample");
- show no accuracy-driven advice ("REVISE thresholds", "FLAG, watch
  closely");
- say plainly that accuracy is not shown because the way it is measured is
  known to be wrong and is under repair.

The under-20 wording and the no-outcomes wording are unchanged.

**Not changed.**
- The logging and grading: `regime_classification_log.csv` rows,
  `check_pending_outcomes`, and `get_regime_accuracy`. Only the display
  changes.
- The nightly grader's own accuracy report (logs only, not the brief).
- Any decision: `regime_log` is read only by the DATA BASIS line.

**Verification.**
- Gate 1: tests on the 20+ path (they fail on the current code); the
  banned-token display test still passes.
- Gate 2: the real brief through `scripts/reality_run.py` on main's code
  and on the branch, run back to back. Only DATA BASIS lines may differ.
  Decision lines and ledger copies must be identical; live prices are
  normalized, because the market is open.

**Restoring the percentage** needs a repaired measure (MR_WIN and
VOL_EXPANSION) with its own spec and validation.
