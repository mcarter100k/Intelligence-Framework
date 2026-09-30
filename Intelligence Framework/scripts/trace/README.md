# scripts/trace: cross-process interleaving tracer (Gate-2 instrument)

This observes, and never changes, how the real scheduled wrappers' Python
processes interleave on the ledgers. `sitecustomize.py` is auto-loaded
through `PYTHONPATH`. It records every lock attempt (ok or busy), every
release, every ledger read, write and append, and every atomic replace.
Each event is stamped with the machine's shared wall clock, into
`$TRACE_OUT`.

    TRACE_OUT=/tmp/t.jsonl PYTHONPATH="$PWD/scripts/trace" <run the wrappers on a PROJECT COPY>
    python3 scripts/trace/analyze_trace.py /tmp/t.jsonl

- `TRACE_HOLD_READ="<prog>:<ledger>:<seconds>"` forces a collision: that
  program sleeps right after it first opens the ledger for reading, so the
  other process has to wait.
- Run it only on a project copy, never on the live folder. It adds a
  tracer, not a writer.
- Positive control (2026-09-30): a single process doing append, then a
  locked read, then a replace produced exactly those events in order.
