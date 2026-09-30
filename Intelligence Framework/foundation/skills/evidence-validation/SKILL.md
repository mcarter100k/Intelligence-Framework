---
name: evidence-validation
description: The owner's standing rule is that nothing counts as done, fixed, working, safe or validated until observed evidence proves it, with no assumptions. Use this skill before claiming any task, fix, phase, merge or test is complete; before writing a status report, run report, commit message or validation_log entry; whenever you are about to say "works", "fixed", "passes", "verified", "validated", "done", "no longer", "never", "zero" or "safe"; when asked "did we validate this?" or "are you sure?"; and when judging someone else's claimed result. It covers labelling claims as verified or inferred, positive controls, mutation tests, before/after measurement with instruments that can't be bypassed, and a claims-and-evidence report.
---

# Evidence Validation

**The rule: every claim must rest on evidence you observed in this session.**
If you didn't see it happen, it isn't done. It is at best INFERRED, and you
must say so.

This exists because the way things fail in this owner's work is not loud
breakage. It is quiet false confidence:
- a test that could never fail;
- a check that was never shown to detect anything;
- an exit code of 0 on an error page;
- a count that masked a new problem behind an old one.

All of these happened in one session (examples below). Every one of them was
reported as success until someone asked for the evidence.

## The five questions (apply to every claim before stating it)

1. **What exactly am I claiming?** Write it as one testable sentence:
   "The default suite makes zero non-local network lookups", not "network
   is handled".
2. **What did I observe that shows it?** Name the command and the output
   you saw *this session*. Reasoning, code reading, "it should", and an
   earlier session's result are not observations.
3. **Could that check have failed?** A check that cannot fail proves
   nothing. Show it fails on a planted violation (**positive control**) or
   when the protection is removed (**mutation test**).
4. **Is the instrument trustworthy?** Prefer instruments that can't be
   bypassed:

   | Use | Instead of |
   |---|---|
   | hashes of every file | `ls` |
   | interpreter audit hooks | a monkeypatched function |
   | the exact set of PIDs | a process count |
   | the output content | the exit code |

5. **Is it time-dependent?** If only reality can perform it (a scheduled job
   firing, a ledger row being graded), it is **PENDING** until it happens.
   Never mark it done.

## Techniques

**Positive control: prove the detector can see.**
- Before trusting "found nothing", plant exactly the thing it should find
  and confirm it reports it.
- Example: a throwaway test that writes to its project and resolves
  `api-fxtrade.oanda.com`. The probe must report 1 write and 1 lookup.
  Only then does "0 lookups across 591 tests" mean anything.

**Mutation test: prove the test can fail.**
1. Break the code the test protects, in a disposable copy or worktree.
2. Confirm the edit actually applied. A substitution that silently matched
   nothing is a false pass, so check `git diff --numstat` shows lines
   changed.
3. Run the test: it must FAIL.
4. Revert, and confirm the revert (`grep -c MUTANT` returns 0).

**Controlled comparison, when changing a test:** run the old and new
versions against the same mutant. This proves the new one catches what the
old one missed, so "improved" becomes a measured claim.

**Before/after with the same instrument.**
- Measure the problem before fixing it, then again after, the same way.
- A fix with no "before" measurement cannot show it changed anything.

**Exact sets, not counts.**
- "2 orphans before, 2 after" hid a new leak behind an expiring old one.
- Diffing the *set* of PIDs showed the truth: old test +1 per run, fixed
  test +0.

**Exit codes are not certification.**
- Programs that "always exit 0" (launchd wrappers, briefs that render
  errors) need their output checked for failure markers: error pages,
  tracebacks, early exits.
- Then check that those markers don't fire on known-good output
  (false-positive check).

**Mechanism vs trigger.** "The alert fired" on a synthetic trigger proves
the mechanism, not that it works on real market movement. Say which one
you proved.

## Bundled instrument

`scripts/audit_probe.py` is a pytest plugin built on `sys.addaudithook`.
It records every network lookup and every file write outside temp
directories, per test, and tests cannot patch around it.
`scripts/audit_report.py` summarizes its output. Usage is in the probe's
docstring. Always run a positive control first.

## Reporting format

End any claim of completion with a claims table. Every row needs evidence
you observed; anything else goes in the INFERRED / NOT CHECKED rows,
stated plainly.

```
| # | Claim (one testable sentence) | Status   | Evidence (command -> observed output)       | Could it fail? (control / mutant) |
|---|-------------------------------|----------|---------------------------------------------|-----------------------------------|
| 1 | ...                           | VERIFIED | `pytest -p audit_probe` -> 0 lookups         | positive control caught 1 lookup  |
| 2 | ...                           | INFERRED | code reading only                           | not shown                         |
| 3 | ...                           | PENDING  | needs the 15:15 scheduled run (Gate 3)      | n/a                               |
```

Statuses:
- **VERIFIED:** observed, and the check was shown able to fail.
- **OBSERVED:** observed, but the check's ability to fail was not shown.
  Say so.
- **INFERRED:** reasoning only.
- **PENDING:** only time can perform it.
- **NOT CHECKED:** not looked at.

Only VERIFIED rows may be called done.

**If you discover you overclaimed, lead with it.** Say plainly what was
claimed without evidence. Then show the evidence gathered since, and log
a dated correction wherever the claim was recorded. Never quietly edit
the earlier claim.

## Real overclaims this skill exists to prevent (2026-09-29)

| Claimed | What was actually true | How it was caught |
|---|---|---|
| "Phase 1 finished" | Six claims were inferred, not observed | The owner asked "did we fully validate?" |
| "0 network calls" | The block was unit-tested, but the whole suite was never re-measured | An audit-hook probe, with a positive control |
| A reality-run tool "passed" | It certified an **error page**: options were silently ignored, and the brief exits 0 on errors | Reading the actual output, not the exit code |
| "The guard protects the ledgers" | It missed writes to `logs/` and new files | A planted violation passed the old guard |
| "No leaked processes" | The old test leaked 1 orphan per run; a count masked it | A PID-set diff, old vs new |
| "The new assertions catch crashes" | Unproven until a mutant crashed the brief | Mutant A: new tests 3 failed, old tests 3 passed |
