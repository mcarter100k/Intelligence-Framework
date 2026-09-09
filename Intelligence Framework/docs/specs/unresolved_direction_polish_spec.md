# Spec: unresolved-direction polish (follow-up ruling, 2026-09-09)

**Status:** team-directed follow-up to the unconfirmed-trend merge; answers
the three open questions that entry logged. Display + one additive ledger
column; decisions byte-identical; classifier routing unchanged.
**Branch:** `feat/unresolved-direction-polish`. Merge held for review.

1. **"choppy" banned except quiet RANGING** (where it remains permitted,
   though quiet RANGING keeps "moving sideways"). `_DIR_WORDS[VOLATILE]`
   loses the word. **Transition-zone VOLATILE** gets its own subtype at the
   classifier's 18–25 branch — `TRANSITION_ZONE`, single-source pattern, no
   thresholds in the display layer — rendering "no clear direction yet
   (trend strength X/100, transition zone)" in MARKET STATE and the
   FULL PICTURE, both timeframes.
2. **H4 UNCONFIRMED_TREND renders** with the same falling/rising template,
   the fact being the signed pip change over the last 10 closed 4-hour
   bars, phrased honestly as "over the last 40 hours" (`h4_change_pips_10`
   exposed by get_regime; a session-count phrase would be a unit lie).
3. **DATA BASIS**: the evidence key (`VOLATILE` accuracy bucket) is
   UNCHANGED; only the display label becomes "daily unresolved-direction
   bucket (transition zone + unconfirmed trends)".
4. **regime_classification_log.csv**: additive `subtype` column (26th),
   loss_species migration pattern (logger rewrites the header additively
   before its next append; old rows blank; values verbatim). Populated on
   every new classification as `d1=<sub>;h4=<sub>` with empty parts
   omitted (blank when both empty) — recorded so the unresolved bucket can
   be SPLIT in future accuracy analysis. Schema pinned at 26 by test.
5. validation_log entry with the directed sentence on the structure rule's
   designed first-leg cost.

Gates: pinned tests (subtype source; transition-zone wording both
timeframes; H4 unconfirmed template; choppy ban across variants; DATA
BASIS label with key unchanged; ledger 26-column pin + lossless migration
+ populated subtype; routing + official decision unchanged). Gate 2: live
briefs on BOTH pairs.
