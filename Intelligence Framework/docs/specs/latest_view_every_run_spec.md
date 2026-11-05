# Spec: every brief alert opens the latest run, not the whole day

**Status:** PROPOSED 2026-11-05, awaiting team review. Not built. The
2026-09-09 ruling (`daily_digest_spec.md`, validation_log) built only the
digest's slice of the latest view and held "the full every-run regeneration
and repointing of all notifications" for review. This spec asks for that
review. `scripts/` is free zone, but a ruling holds this item, so it does not
merge on tests alone.

## 1. Why

- The owner clicked through to a brief alert and read `logs/brief_2026-11-03.log`:
  341 lines and three runs, for a day whose every decision was STAND ASIDE
  (owner, 2026-11-05: "why is the read so long"). That the click was the route
  is inferred from the wiring: SHADOW, DECISION, ALERT and RECOVERED open the
  day log, and three of that day's four notifications were SHADOW.
- `logs/latest_brief.log` already gives the newest run, one line per earlier
  run, the day's alert lines and a pointer to the record, but only the 07:30
  digest regenerates it. At any other hour it is stale.

## 2. Change

In `scripts/scheduled_brief.sh`:

1. **Regenerate the view on every run**, after the run's block and its health
   and `DUE:` lines are in the day log, and before the first `notify`.
2. **Repoint the brief wrapper's notifications** to `logs/latest_brief.log`:
   ALERT, DECISION, SHADOW and RECOVERED. DIGEST already points there.
3. **Never open a stale view.** `latest_view.py` always exits 0 and leaves the
   old file on failure, so an exit code proves nothing. Before pointing at the
   view, the wrapper checks that it contains this run's `=====` header line. If
   not, that notification points at the day log, as it does today.

Unchanged: the outcomes wrapper and heartbeat (their own logs); the day log,
which stays the append-only record; every firing condition; every category;
every summary line except its `→ <file>` pointer; the digest's argument gate.

## 3. Known behaviour to accept or reject

- **An older alert opens a newer run.** The view is overwritten by each run, so
  clicking yesterday's alert shows the latest run. The view's first line states
  that run's time, its alert lines cover today only, and it names the full
  record.
- **The notification ledger's summary text changes** to the new pointer on new
  rows. Old rows stay. Nothing is known to parse the pointer; the build must
  confirm that by search.
- **The view itself is still about 118 lines.** This spec fixes which file
  opens, not how long a run reads. `brief_summary_block_spec.md` covers that.

## 4. Gates

**Gate 1, against the real wrapper (`test_wrapper_behavior.py` style):**
- Each of ALERT, DECISION, SHADOW and RECOVERED opens the view, and the view's
  first block is this run.
- A non-digest run regenerates the view and still posts no DIGEST.
- Stale-view control: with view generation failing and an old view in place, the
  notification points at the day log, never the old view.
- The day log's bytes for a run are identical before and after this change.

**Rule 12, whether it should reach the owner:** for the existing wrapper cases
(closed market, stand-aside only, shadow fire, flip, failed run), the set of
notifications sent, their categories and their summaries are identical to
`main` apart from the pointer. This change must add and remove nothing.

**Mutation:** view regeneration removed; freshness check removed; one category
left on the day log; regeneration moved after `notify`. Each must be caught.

**Gate 2:** a real wrapper run under `scripts/reality_run.py`, showing the
actual view and the actual `-open` target; `/bin/bash` 3.2 syntax
(`test_shell_syntax.py`).

**Gate 3, PENDING LIVE CONFIRMATION:** the first scheduled non-digest alert after
merge opens a one-run view when the owner clicks it. Only a human can click.

## 5. Out of scope

Whether shadow signals should notify at all. That decision is the owner's, and
is open as of this spec.
