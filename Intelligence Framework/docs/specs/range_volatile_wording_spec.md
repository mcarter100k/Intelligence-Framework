# Spec: plain, direction-neutral wording for "range + volatile 4-hour" stand-asides

**Status:** spec for team review, written 2026-11-03, before any build
(protected-path rule). It touches one PROTECTED module, `decision_brief.py`,
and only rendered text. **No decision, filter, regime or ledger value changes.**
It does not merge without team review.

## 1. The defect (observed)

- From Sun 2026-11-01 18:00 PST to Tue 2026-11-03 07:33 PST, every GBP/AUD
  brief gave this REASON:

  > Range breaking down — 4-hour chart volatile inside daily chart range
  > (trend strength 14.4/100). Wait for resolution before engaging.

- Over the same runs, GBP/AUD rose from **1.9042 to 1.9233** in the brief's
  own price line (`logs/brief_2026-11-01.log` to `logs/brief_2026-11-03.log`).
  The rally from the 2026-10-28 low was about 370 pips.
- The owner read "breaking down" as bearish while price was going up.
- The phrase means "the range regime is coming apart: the 4-hour chart is
  volatile inside a daily range". It carries **no direction**, but in a
  trading brief "breaking down" means falling price. That breaks AGENTS
  rule 4: what the trader reads must say what it means.
- Corroboration: the missed-move report (`feat/missed-moves`, 2026-11-03)
  counts this REASON on 6 of the 12 stand-aside runs during the rally.

## 2. Where the text comes from (code read 2026-11-03)

| Source | Reaches the trader? | Change |
|---|---|---|
| `decision_brief.py:535`: conflict path, `"Range breaking down — H4 volatile inside D1 range (ADX …). Wait for resolution before engaging."` | **Yes.** The REASON line, after `_plain()` | **Reworded** |
| `decision_brief.py:597`: STAND DOWN path, same sentence without ADX | **Yes.** The REASON line | **Reworded** |
| `regime_detection.py:219`: the composite table's `note` | No. Internal regime record and logs | Unchanged |
| `no_trade_filter.py:251`: `apply_filter` reason `"RANGING D1 + VOLATILE H4 — range breaking down, wait"` | No. Internal, pinned by `tests/test_exhaustion_display.py:107,113` | Unchanged |

Rule 4 allows technical terms in logs and CSVs. Changing the internal
strings would churn a pinned test for no reader benefit.

## 3. New wording

Both paths render, through `_plain()` as today:

> **4-hour chart is swinging hard inside a sideways daily chart (trend
> strength X/100) — no settled direction yet. Wait for it to settle before
> engaging.**

The STAND DOWN path has no strength figure and drops the parenthesis.

- **Direction-neutral by construction.** None of these words appear:
  down, up, rising, falling, breaking, collapse, rally, sell, buy.
- **Option B, NOT in this spec.** Adding the 4-hour direction of travel
  (e.g. "price has been rising for a day") needs bar data in the reason
  builder, and a definition that could itself mislead at turning points.
  It would be its own spec, and only if the team wants it.

## 4. What must not change (each pinned by a test)

- **W1, decisions.** The DECISION, CONFIDENCE, POSITION, `apply_filter`
  result and every logged regime field are identical before and after.
  Only the REASON string changes. Test: render both paths before and
  after, and compare every field except `reason`.
- **W2, plain English.** The new REASON passes the banned-token floor
  (`tests/test_brief_display.py::_assert_clean`). The floor is not edited.
- **W3, direction-neutral.** A test asserts that the rendered REASON for
  RANGING D1 + VOLATILE H4, on both paths, contains none of the §3 words
  (case-insensitive, whole words).
- **W4, no notification side effects (rule 12).** The new text contains
  none of the wrapper or digest triggers (`DECISION`, `SHADOW SIGNALS`,
  `Framework error`, `EXIT IF`, `WATCH FOR`, `STAND ASIDE`). It renders only
  inside the REASON line, which is already a stand-aside brief, so no
  notification category can change. An I3a-style run of the real
  `scheduled_brief.sh` on a rendered brief in this cell asserts no
  notification, against a control.
- **W5, nothing else reworded.** Every other REASON template renders
  byte-identically, checked by a sweep over the regime-cell matrix
  already used in `tests/test_decision_logic.py`.

## 5. Tests that change, old → new

- None known. No test pins the old rendered sentence: `grep -rn "Range
  breaking" tests/` finds only the internal filter string (unchanged).
- If the build finds one, it is listed here old → new before merge.

## 6. Verification

- **Gate 1:**
  - W1–W5.
  - Mutants: old text restored on each path separately; a directional word
    inserted; the `_plain()` step bypassed.
- **Gate 2:** `scripts/reality_run.py brief --code <worktree>` while a pair
  sits in this cell. On 2026-11-03 GBP/AUD was RANGING D1 + VOLATILE H4.
  The real REASON line is shown verbatim, and DECISION/CONFIDENCE/POSITION
  are compared with a `main` run at the same time.
- **Gate 3:** none needed. The text is visible on the next brief in this
  cell.

## 7. Out of scope (recorded so it is not lost)

- **An audit of every other REASON template for direction words that do
  not depend on direction.** "Range breaking down" was found by the owner,
  not by a test. A sweep of all templates against the §3 word list would
  find the next one. Proposed as a free-zone test, own commit, after this
  spec.
- Option B (§3).
- Any change to when the framework stands aside. The missed rally is a
  strategy question (see the first-pullback study), not a wording one.
