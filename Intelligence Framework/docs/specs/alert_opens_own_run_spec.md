# Spec: each alert opens a saved copy of the run that sent it

**Status:** PROPOSED 2026-11-05, awaiting team review. Not built.
**Supersedes:** `latest_view_every_run_spec.md` (unchanged on disk; the
adversarial reviewer rejected it, validation_log 2026-11-05 TEAM REVIEW).
**Scope:** `scripts/scheduled_brief.sh`, a new `scripts/run_view.py`,
`scripts/latest_view.py` (free zone; a notification path, so rule 12, and the
2026-09-09 ruling held this area for review).

## 1. Why

- Brief alerts open the whole day log, which is 341 lines on 2026-11-03.
- The rejected spec pointed every alert at `logs/latest_brief.log`. Each run
  overwrites that file, so a click on an earlier DECISION or ALERT could show a
  later run. Demonstrated: an 18:00 LONG's entry and exit level vanished after
  the next run (review 1.1).

## 2. Change

1. **One file per run.**
   - After the run's block, health and `DUE:` lines are in the day log, the
     wrapper writes `logs/runs/<YYYYMMDD-HHMMSS>-<pid>.log` from this run's own
     `$OUT`.
   - The file starts with a header line `RUN <token> — <display time>`, then the
     run's health/DUE lines, then one line per earlier run today (with its time),
     then a pointer to the day log.
   - It is written with `ledger_io.atomic_write_text` and never overwritten.
   - The token is the stamp plus PID, so same-second runs (OBSERVED 2026-10-08,
     2026-09-14) get distinct files (review 1.3).
2. **Repoint** the brief wrapper's ALERT, DECISION and RECOVERED to the run
   file. SHADOW leaves per `shadow_digest_only_spec.md`.
   - If the run file was not written (it is checked to exist and start with this
     run's token), the notification opens the day log.
   - `live_guard`'s ALERTs stay on the day log, because they fire before the run
     exists (review 1.5).
3. **DIGEST keeps `logs/latest_brief.log`.** Part 1 of this round adds the
   digest's freshness check (separate branch).
4. **Signal lines in `latest_brief.log` carry their run time** (review 1.2). The
   same goes for the run file's earlier-run lines.
5. **Failure records always go to the day log.** `notify.sh` gains a separate
   record-path argument (part 1 of this round, separate branch; review 1.4).
   This spec depends on it.
6. **Prune** run files older than 30 days at each run. They are a view, not
   evidence; the day log stays the append-only record.
7. **Consumers.**
   - `trader_review.framework_read` keeps reading `latest_brief.log`; part 1
     fixes its error-page read (review 1.6).
   - No other reader of the brief's pointer text is known. The build must
     confirm that by search.
   - `test_wrapper_behavior.py:400` asserts the old pointer: a dated old → new
     change.
8. **Pointer text** in the osascript fallback, which cannot be clicked, names
   the run file. That path does not change, so the text stays true.
9. **bash 3.2** (`test_shell_syntax.py`): no arrays beyond what the wrapper
   already uses, and no `printf -v`.

## 3. Rule 12

**Same notifications as `main`:** the same categories and summaries for every
existing wrapper case (closed market, stand-aside, flip, failed run, LONG).
Only the pointer differs, and SHADOW moves out per its own spec.

**The click lands on the run it was about:**

| Case | Expected |
|---|---|
| DECISION LONG at 18:00, then a STAND ASIDE run at 02:30 | The 18:00 notification's file still shows LONG, ENTRY and EXIT IF |
| ALERT at 02:44 | Its file is the 02:44 run, with the alert line and time |
| Two wrappers in the same second | Two files; each notification opens its own |
| Run file write fails | Notification opens the day log; the failure is recorded in the day log |

## 4. Out of scope

- The content of the brief (`brief_summary_block_spec.md`).
- The digest line.
- Which notifications fire.

## 5. Gates

**Gate 1:**
- The real wrapper with a stub terminal-notifier that records `-open` (the
  existing pattern in `test_d3_the_terminal_notifier_path_writes_a_row_too`).
- Every §3 row.
- RECOVERED via fail, fail, succeed.
- Prune keeps files newer than 30 days.
- The day log's bytes for a run are unchanged by the view step.

**Mutation:**
- All runs write one shared file.
- No PID in the token.
- Freshness check removed.
- `live_guard` repointed.
- Signal lines without time.
- Prune deletes a current file.

Each must be caught.

**Gate 2:** a real non-digest wrapper run under `scripts/reality_run.py`,
showing the run file and the `-open` URL; project unchanged by hash; bash 3.2
syntax.

**Gate 3, PENDING LIVE CONFIRMATION:** the owner clicks a real alert and sees
that run alone.

## 6. Questions for the team

1. Prune age: 30 days?
2. Should the run file also start with the short block once
   `brief_summary_block_spec.md` is approved? Recommended: yes, as one line in
   that spec, not here.
