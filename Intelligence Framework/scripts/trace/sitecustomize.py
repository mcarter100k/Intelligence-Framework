"""Interleaving tracer for the scheduled wrappers' Python processes.

Loaded automatically at interpreter start via PYTHONPATH (site imports
sitecustomize). It records, with time.time_ns() (one wall clock shared by
every process on this machine), for each process:
  start / end (argv), lock open+attempt(ok|busy)+release per sidecar,
  ledger opens (read / write / append), os.replace targets.
Writes JSON lines to $TRACE_OUT with O_APPEND (each line one write()).

Optional forced contention: TRACE_HOLD_READ="<prog>:<ledger>:<seconds>"
makes that program sleep right after it first finishes opening that ledger
for READ. Used only to force a collision and observe that the other
process waits. Product code is never modified.
"""
import atexit
import builtins
import errno
import fcntl
import json
import os
import sys
import time

_OUT = os.environ.get("TRACE_OUT")
_PROG = os.path.basename(sys.argv[0]) if sys.argv and sys.argv[0] else "python"
_LEDGERS = ("regime_classification_log.csv", "session_context_log.csv",
            "shadow_signal_log.csv", "trade_signal_log.csv", "health_state.json",
            "excluded_rows.csv", "trades.csv", "pre_trade_journal.csv", "trade_log.csv")


def _emit(event, **kw):
    if not _OUT:
        return
    rec = {"t": time.time_ns(), "pid": os.getpid(), "prog": _PROG, "ev": event}
    rec.update(kw)
    line = (json.dumps(rec) + "\n").encode()
    fd = os.open(_OUT, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        os.write(fd, line)
    finally:
        os.close(fd)


if _OUT:
    _emit("start", argv=sys.argv[1:4])
    atexit.register(lambda: _emit("end"))

    _fd_path = {}
    _real_os_open = os.open

    def _traced_os_open(path, flags, mode=0o777, *a, **k):
        fd = _real_os_open(path, flags, mode, *a, **k)
        p = os.fspath(path)
        if p.endswith(".lock"):
            _fd_path[fd] = os.path.basename(p)
        return fd
    os.open = _traced_os_open

    _real_flock = fcntl.flock

    def _traced_flock(fd, op):
        name = _fd_path.get(fd, f"fd{fd}")
        if op & fcntl.LOCK_UN:
            _real_flock(fd, op)
            _emit("unlock", lock=name)
            return
        try:
            _real_flock(fd, op)
        except OSError as e:
            if e.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
                _emit("lock_busy", lock=name)
            raise
        _emit("lock_ok", lock=name)
    fcntl.flock = _traced_flock

    _hold = os.environ.get("TRACE_HOLD_READ", "")
    _hold_prog, _hold_ledger, _hold_s = (_hold.split(":") + ["", "", "0"])[:3]
    _held = {"done": False}
    _real_open = builtins.open

    def _traced_open(file, mode="r", *a, **k):
        f = _real_open(file, mode, *a, **k)
        if isinstance(file, (str, os.PathLike)):
            base = os.path.basename(os.fspath(file))
            if base in _LEDGERS:
                kind = "write" if "w" in mode else "append" if "a" in mode else "read"
                _emit(f"open_{kind}", file=base)
                if (kind == "read" and not _held["done"] and _PROG == _hold_prog
                        and base == _hold_ledger):
                    _held["done"] = True
                    _emit("hold_begin", file=base, seconds=float(_hold_s))
                    time.sleep(float(_hold_s))
                    _emit("hold_end", file=base)
        return f
    builtins.open = _traced_open

    _real_replace = os.replace

    def _traced_replace(src, dst, *a, **k):
        _real_replace(src, dst, *a, **k)
        _emit("replace", file=os.path.basename(os.fspath(dst)))
    os.replace = _traced_replace
