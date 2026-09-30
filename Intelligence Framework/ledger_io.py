"""
ledger_io.py — the ONE way evidence files are written
(docs/specs/safe_ledger_writes_spec.md, Phase 3 of the 2026-09-29 audit).

Why this exists. Every ledger writer used a bare open("w")/open("a") with no
locking. Reproduced on main before this module existed:
  * each of the three graders read the whole ledger, changed it, and wrote it
    back, destroying a row a second process appended in between (the
    2026-09-14 brief and grader ran 1 second apart);
  * a SIGKILL during a rewrite took a copy of the real regime ledger from
    114 rows to 0.
An append-only ledger can never re-observe a lost row, so prevention is the
whole of the cure.

Primitives (stdlib only, Python 3.9+, macOS/Linux):
  locked(path)                  exclusive lock; hold it across any
                                read-modify-write. Re-entrant per process.
  atomic_write_rows(path, fieldnames, rows)
                                temp file + fsync + os.replace: a crash
                                leaves the old file or the new one, never a
                                partial one.
  append_row(path, fieldnames, row)
                                locked append; writes the header when the
                                file is new or empty.
  atomic_write_text(path, text) the same guarantee for a non-CSV file
                                (e.g. logs/health_state.json).
"""
from __future__ import annotations

import csv
import errno
import fcntl
import os
import tempfile
import time
from contextlib import contextmanager
from typing import Dict, Iterable, List

LOCK_TIMEOUT_SECONDS = 60.0


class LedgerLockTimeout(RuntimeError):
    """Raised instead of ever writing a ledger without its lock."""


# realpath of the ledger -> [lock fd, depth]. flock locks belong to an open
# file description; a second open()+flock of the same file in the SAME
# process would block forever on BSD/macOS. The depth count makes nested
# locked() calls (e.g. a grader holding the lock and calling a helper that
# also locks) safe.
_held: Dict[str, list] = {}


def _lock_path(path: str) -> str:
    d, name = os.path.split(os.path.abspath(path))
    return os.path.join(d, f".{name}.lock")


@contextmanager
def locked(path: str, timeout: float = LOCK_TIMEOUT_SECONDS):
    """Exclusive lock on `path` (via a sidecar `.name.lock` file, because
    os.replace changes the ledger's inode and a lock on the ledger itself
    would not survive an atomic rewrite)."""
    key = os.path.realpath(path)
    if key in _held:
        _held[key][1] += 1
        try:
            yield
        finally:
            _held[key][1] -= 1
        return
    lp = _lock_path(path)
    os.makedirs(os.path.dirname(lp), exist_ok=True)
    fd = os.open(lp, os.O_RDWR | os.O_CREAT, 0o644)
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as e:
                if e.errno not in (errno.EWOULDBLOCK, errno.EAGAIN):
                    raise
                if time.monotonic() >= deadline:
                    raise LedgerLockTimeout(
                        f"could not lock {os.path.basename(path)} within "
                        f"{timeout:.0f}s; refusing to write it unlocked")
                time.sleep(0.02)
        _held[key] = [fd, 1]
        try:
            yield
        finally:
            del _held[key]
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)


def _replace_atomically(path: str, write) -> None:
    """Write via `write(fileobj)` to a temp file beside `path`, fsync it, then
    os.replace it over `path`. Keeps the existing file's permissions."""
    d = os.path.dirname(os.path.abspath(path)) or "."
    mode = None
    try:
        mode = os.stat(path).st_mode & 0o777
    except FileNotFoundError:
        pass
    fd, tmp = tempfile.mkstemp(prefix=f".{os.path.basename(path)}.",
                               suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            write(f)
            f.flush()
            os.fsync(f.fileno())
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    try:                                   # make the rename itself durable
        dfd = os.open(d, os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    except OSError:
        pass


def atomic_write_rows(path: str, fieldnames: List[str],
                      rows: Iterable[Dict]) -> None:
    """Replace the whole CSV atomically. Takes the lock (re-entrant, so a
    caller already holding it for its read keeps it continuously)."""
    rows = list(rows)

    def _w(f):
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    with locked(path):
        _replace_atomically(path, _w)


def append_row(path: str, fieldnames: List[str], row: Dict) -> None:
    """Append one row under the lock, writing the header first when the file
    is new or empty. Flushed and fsynced before the lock is released."""
    with locked(path):
        needs_header = (not os.path.exists(path)) or os.path.getsize(path) == 0
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            if needs_header:
                w.writeheader()
            w.writerow(row)
            f.flush()
            os.fsync(f.fileno())


def atomic_write_text(path: str, text: str) -> None:
    """Replace a non-CSV file atomically, under its lock."""
    with locked(path):
        _replace_atomically(path, lambda f: f.write(text))
