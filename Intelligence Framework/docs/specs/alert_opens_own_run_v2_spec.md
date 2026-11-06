# Spec v2: each brief alert opens a saved copy of its own run (outside logs/, kept 90 days)

**Status:** PROPOSED 2026-11-05, awaiting team review. Not built.

**Supersedes:** `alert_opens_own_run_spec.md`, which is unchanged on disk.
Both reviewers returned APPROVE WITH CHANGES (validation_log 2026-11-05 TEAM
REVIEW round 2). v1 itself superseded `latest_view_every_run_spec.md`.

**Scope (free zone, but a notification path):** rule 12 applies, and the
2026-09-09 ruling held this area for review. Files touched:
- `scripts/scheduled_brief.sh`
- a new `scripts/run_view.py`
- `scripts/latest_view.py` (signal-line times only)
- `.gitignore`
- AGENTS.md: one line declaring `views/` non-evidence

**Owner decision applied (2026-11-05, decision 4):** "Run files go outside
logs/, kept 90 days. Confirm nothing reads run files as if they were the
record."

## 1. Why

- Brief alerts open the whole day log: 341 lines on 2026-11-03.
- The rejected v0 pointed every alert at `logs/latest_brief.log`. Each run
  overwrites that file, so a click could show a later run.
- v1 fixed that with one file per run but had four gaps:
  - **No alert line.** The run file was built from `$OUT`, but `##ALERT##`
    lines and tracebacks go to stderr. The wrapper writes stderr to `$ERRTMP`
    (`scheduled_brief.sh:57-58`) and deletes it at `:75`, before any view step.
  - **Garbled earlier runs.** The "earlier runs" lines came from parsing the
    day log. DEMONSTRATED: the 2026-09-14 parse renders "no output / no output
    / GBP/AUD ? · …".
  - **Pruning under `logs/`.** It would delete files there, which AGENTS.md
    calls evidence.
  - **No defined behaviour** for a click on a pruned file.

## 2. Change

### 2.1 Where, and what it is

- **Location: `views/runs/<YYYYMMDD-HHMMSS>-<pid>.log`** under the project root.
  - The directory is gitignored.
  - It is outside `logs/`: AGENTS.md lists "everything under `logs/`" as
    evidence that agents never delete, and the owner chose "outside logs/".
  - The build adds to AGENTS.md's ledger paragraph: "`views/` holds
    convenience copies of runs, not evidence; the day log
    `logs/brief_<date>.log` stays the append-only record."
  - `views/` did not exist on 2026-11-05 (OBSERVED, `ls`).
- **Time zone.** The stamp is local display time (`DISPLAY_TZ`), the same
  clock as the day log header. The PID keeps names unique through the DST
  fall-back hour.
- **Written once.**
  - The file is written by an exclusive create (`O_CREAT|O_EXCL`), so it can
    never overwrite.
  - It is not written with `ledger_io.atomic_write_text`: that function takes
    a lock and leaves a `.NAME.lock` sidecar per file (`ledger_io.py:190-198`;
    such sidecars persist, e.g. `logs/.latest_brief.log.lock`). One exclusive
    create needs no lock and leaves no sidecar.
  - It is written to a temp name in the same directory, then linked to the
    final name with `os.link`, which fails if the name exists. A partial file
    is never visible.

### 2.2 Contents, in order (code review 2; review R1)

1. **Header line:** `RUN <token> — <display time>`.
2. **This run's brief:** `$OUT`, verbatim, including any SHADOW block it
   contains.
3. **This run's stderr:** the alert lines, warnings and traceback, verbatim,
   under `----- stderr (exit N) -----`, exactly as the day log gets it
   (`:62-64`).
   - The wrapper keeps `$ERRTMP` until the run file is written, then deletes
     it. `rm -f "$ERRTMP"` moves after the view step.
4. **Health and DUE lines** for this run.
5. **Earlier runs today:** one line each, with its time and both pairs'
   decisions.
   - These come from the **earlier run files' first lines and decision
     lines**, never from parsing the day log (review R2).
   - A run with no file (before the build, or a failed write) reads
     "<time>: no saved copy — see the day log".
6. **Pointer:** "Full day: logs/brief_<date>.log".

### 2.3 When it is written

- **Before the first notification of the run.** That is after the health
  state is computed (`scheduled_brief.sh:102-114`) and **before** the health
  `notify` (`:121`), so RECOVERED and health ALERTs can point to it too
  (code review 2).
- The health echo moves into the run-file content. The day log still gets it
  first, unchanged.

### 2.4 Repointing

- **Where each notification points:**
  - The brief wrapper's **ALERT, DECISION, RECOVERED** and **health ALERT**
    point at the run file.
  - **DIGEST keeps `logs/latest_brief.log`**, with its freshness check
    (`:199-206`).
  - **SHADOW is unchanged** until the shadow-digest v2 is decided.
  - `live_guard`'s ALERTs stay on the day log, because they fire before the
    run exists.
- **Fallback.** Before notifying, the wrapper checks that the run file exists
  and its first line is this run's header. If not, it opens the day log, and
  the failure is written to the day log through `notify`'s record argument.
- **The pointer text changes.**
  - It becomes "→ views/runs/20261105-180001-12345.log" (36 characters at a
    5-digit PID; macOS PIDs stay under 100,000).
  - The arithmetic: a 180-character ALERT summary + " → " + the pointer is
    219 characters, just under the osascript cut at 220 (`notify.sh:56`).
    Multibyte characters in the summary make it tighter, because under launchd's
    default locale `cut -c` may count bytes (INFERRED; the test settles it).
  - A test pins it at the longest real summary (review R4, code review 7).
    If the test fails, the visible pointer shortens to the file name alone.
    The clickable `-open` URL is unaffected either way.
  - The recorded `summary` in `notification_log.csv` changes only in that
    pointer.

### 2.5 Retention: 90 days, and a pruned click (review R3)

- **When it runs.** At each brief run, after notifying, the wrapper prunes run
  files older than 90 days.
- **Tombstones instead of deletion.** A pruned file is **replaced by a
  one-line tombstone**: "This run's saved copy was removed after 90 days. The
  full record is logs/brief_<date>.log, run at <time>."
  - Why: Notification Center keeps old notifications. A deleted file would
    make an old click open a missing file. A tombstone gives every click a
    defined result.
  - Tombstones are about 120 bytes and are kept: about 1,100 a year.
- **Safety:**
  - The prune touches only `views/runs/` and only names matching
    `^[0-9]{8}-[0-9]{6}-[0-9]+\.log$`.
  - It is idempotent; two wrappers pruning at once is safe, because a
    tombstone rewrite of a tombstone is a no-op.
  - It never follows symlinks.
- **Volume:** about 3 runs a day, roughly 270 full files at 90 days.

### 2.6 Readers: nobody reads run files as the record (owner decision 4)

**Re-verified by grep on 2026-11-05 (this spec):**

| Reader | What it reads | How | Affected? |
|---|---|---|---|
| `studies/decision_channel_inventory.py` | `logs/brief_*.log` | `:65` | no |
| `studies/decision_gate_replay.py` | `logs/brief_*.log` | `:102` | no |
| `studies/decision_channel_followups.py`, `studies/long_side_diagnosis.py` | through `decision_channel_inventory.parse_runs` | `:63` / `:69`, `:140` | no |
| `studies/missed_moves.py` | `logs/brief_*.log` | `:227` | no |
| `scripts/run_count.py` | `logs/<kind>_*.log` | `:118` | no |
| `scripts/latest_view.py` | named day files `brief_<date>.log` | `:45-62` | no |
| `scripts/trader_review.py` | `logs/latest_brief.log` | `:62` | no |
| `scripts/health_state.py`, `scripts/backup_ledgers.py` | `logs/health_state.json` | — | no |

- **Nothing globs `views/`, and nothing reads the notification pointer text**
  except `tests/test_wrapper_behavior.py`:
  - `:400` asserts the DECISION summary "GBP/AUD LONG → logs/brief_";
  - `:488` asserts a digest fallback "logs/brief_".
  - These become dated old → new changes.
- **The build must re-run this grep** (`views/`, `runs/`, `brief_*`,
  `latest_brief`, "→ ") and record the result, because a reader added between
  now and the build would be missed.

### 2.7 Other

- **Signal lines in `latest_brief.log` carry their run time** (v1 §2.4,
  unchanged).
- **bash 3.2** (`test_shell_syntax.py`): no arrays beyond what the wrapper
  uses, and no `printf -v`. The file writing is done by `scripts/run_view.py`,
  which must be stdlib-only (the launchd interpreter, see
  `test_wrapper_behavior.py:512-515`).
- **The run lock in `session_compare_v2_spec.md` §2.1** makes concurrent runs
  sequential. Without it, run files are still distinct (PID), and the
  earlier-run lines list whichever files exist.

## 3. Rule 12

**Same notifications as `main`.** Every existing wrapper case (closed market,
stand-aside, flip, failed run, LONG, RECOVERED) sends the same categories and
the same summaries up to " → ". Only the pointer differs.

**The click lands on the run it was about:**

| # | Case | Expected |
|---|---|---|
| 1 | DECISION LONG at 18:00, then STAND ASIDE at 02:30 | The 18:00 notification's file still shows LONG, ENTRY and EXIT IF |
| 2 | ALERT at 02:44 | Its file is the 02:44 run, with the `##ALERT##` line in the stderr section |
| 3 | Crashed run (traceback, exit 1) | Health ALERT opens a file containing the traceback |
| 4 | RECOVERED after fail, fail, succeed | Opens the succeeding run's file |
| 5 | Two wrappers in the same second | Two files; each notification opens its own |
| 6 | Run file write fails (directory not writable) | Notification opens the day log; the failure is recorded in the day log; the notification still sends |
| 7 | Click on a 100-day-old notification | Opens the tombstone naming the day log and time |
| 8 | Market closed, nothing to send | No notification; the run file is still written (harmless; the next run lists it) |
| 9 | 07:30 digest | Unchanged: opens `logs/latest_brief.log` when fresh, else the day log |

## 4. Out of scope

- The content of the brief.
- The digest line.
- Which notifications fire. That belongs to `session_compare_v2_spec.md` and
  the shadow-digest v2.

## 5. Gates

**Gate 1:**
- The real wrapper in a sandbox project with the recording terminal-notifier
  stub. Its pattern is in `tests/test_notify_helper.py`; the stub in
  `test_d3_…` records nothing (code review 6). Tests cover:
  - every §3 row;
  - RECOVERED via fail, fail, succeed;
  - prune: a 91-day-old file becomes a tombstone, an 89-day-old file is
    untouched, a non-matching name is untouched, and a second prune leaves
    bytes identical;
  - the day log's bytes for a run are identical with and without the view
    step;
  - no `.lock` sidecar is created under `views/`;
  - the osascript text at the longest summary keeps the full pointer.

**Mutation** (each must be caught):
- all runs write one shared file;
- no PID in the token;
- stderr omitted;
- earlier-run lines from the day log;
- the freshness check removed;
- `live_guard` repointed;
- the prune deletes instead of tombstoning;
- the prune touches a non-matching name;
- the write placed after the health notify.

**Gate 2:** a real non-digest wrapper run in a sandbox copy of the project
(real `decision_brief.py`, copies of the ledgers and credentials, through
`scripts/reality_run.py --code <worktree>`). It shows the run file, its stderr
section and the `-open` URL. The project must be unchanged by hash, with
bash 3.2 syntax.

**Gate 3, PENDING LIVE CONFIRMATION:**
- the owner clicks a real alert and sees that run alone;
- the first real tombstone after 90 days (around February 2027).

## 6. Questions for the team

1. **Tombstones:** use them, as proposed? Or delete outright and accept that
   old clicks open nothing?
2. **The short block:** should the run file start with it once
   `brief_summary_block_spec.md` is approved? Recommended: yes, as one line in
   that spec, not here.
