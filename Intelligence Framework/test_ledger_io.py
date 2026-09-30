"""
test_ledger_io.py — the write primitives every evidence file goes through
(docs/specs/safe_ledger_writes_spec.md). Real processes and real signals
where the claim is about concurrency or crashes: an in-process simulation
could not show that a lock excludes another process or that a SIGKILL
leaves the old file intact.
"""
import csv
import os
import signal
import subprocess
import sys
import textwrap
import time

import pytest

import ledger_io

_ROOT = os.path.dirname(os.path.abspath(__file__))
FIELDS = ["timestamp", "x"]


def _rows(p):
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def _py(code, **kw):
    return subprocess.Popen(
        [sys.executable, "-c", textwrap.dedent(code)],
        env=dict(os.environ, PYTHONPATH=_ROOT, PYTHONDONTWRITEBYTECODE="1"), **kw)


# ── append_row ────────────────────────────────────────────────────────────────

def test_append_writes_the_header_once(tmp_path):
    p = str(tmp_path / "l.csv")
    ledger_io.append_row(p, FIELDS, {"timestamp": "t1", "x": "1"})
    ledger_io.append_row(p, FIELDS, {"timestamp": "t2", "x": "2"})
    assert open(p).read() == "timestamp,x\nt1,1\nt2,2\n"


def test_append_to_an_empty_file_writes_the_header(tmp_path):
    p = tmp_path / "l.csv"
    p.write_text("")
    ledger_io.append_row(str(p), FIELDS, {"timestamp": "t1", "x": "1"})
    assert p.read_text() == "timestamp,x\nt1,1\n"


# ── atomic_write_rows ─────────────────────────────────────────────────────────

def test_an_exception_mid_rewrite_leaves_the_original_and_no_temp(tmp_path, monkeypatch):
    p = tmp_path / "l.csv"
    p.write_text("timestamp,x\nt1,1\nt2,2\n")

    def boom(self, rows):
        raise OSError("disk full (simulated)")
    monkeypatch.setattr(csv.DictWriter, "writerows", boom)
    with pytest.raises(OSError):
        ledger_io.atomic_write_rows(str(p), FIELDS, [{"timestamp": "t9", "x": "9"}])
    assert p.read_text() == "timestamp,x\nt1,1\nt2,2\n"
    assert [f for f in os.listdir(tmp_path) if f.endswith(".tmp")] == []


def test_a_sigkill_mid_rewrite_leaves_the_original_intact(tmp_path):
    """The reproduced defect: a SIGKILL during open('w') rewrite took a copy
    of the real regime ledger from 114 rows to 0."""
    p = tmp_path / "l.csv"
    original = "timestamp,x\n" + "".join(f"t{i},{i}\n" for i in range(200))
    p.write_text(original)
    proc = _py(f"""
        import csv, time, ledger_io
        orig = csv.DictWriter.writerow
        def slow(self, r):
            time.sleep(0.01); return orig(self, r)
        csv.DictWriter.writerow = slow
        csv.DictWriter.writerows = lambda self, rs: [slow(self, r) for r in rs]
        ledger_io.atomic_write_rows({str(p)!r}, ["timestamp", "x"],
            [{{"timestamp": "new", "x": str(i)}} for i in range(200)])
    """)
    time.sleep(0.8)                       # mid-write: 200 rows x 10 ms
    proc.send_signal(signal.SIGKILL)
    proc.wait()
    assert p.read_text() == original


def test_the_file_mode_is_preserved(tmp_path):
    p = tmp_path / "l.csv"
    p.write_text("timestamp,x\n")
    os.chmod(p, 0o600)
    ledger_io.atomic_write_rows(str(p), FIELDS, [{"timestamp": "t", "x": "1"}])
    assert (os.stat(p).st_mode & 0o777) == 0o600


# ── locked ────────────────────────────────────────────────────────────────────

def test_the_lock_is_reentrant_within_a_process(tmp_path):
    p = str(tmp_path / "l.csv")
    with ledger_io.locked(p):
        with ledger_io.locked(p):          # would deadlock on BSD flock
            ledger_io.append_row(p, FIELDS, {"timestamp": "t", "x": "1"})
    assert len(_rows(p)) == 1


def test_another_process_waits_for_the_lock(tmp_path):
    """A second process's append lands only after the holder releases."""
    p = str(tmp_path / "l.csv")
    ledger_io.atomic_write_rows(p, FIELDS, [{"timestamp": "first", "x": "0"}])
    with ledger_io.locked(p):
        proc = _py(f"""
            import ledger_io
            ledger_io.append_row({p!r}, ["timestamp", "x"],
                                 {{"timestamp": "from-other-process", "x": "1"}})
        """)
        time.sleep(0.8)
        assert [r["timestamp"] for r in _rows(p)] == ["first"]   # still blocked
        ledger_io.atomic_write_rows(p, FIELDS, [{"timestamp": "rewritten", "x": "2"}])
    proc.wait(timeout=30)
    assert [r["timestamp"] for r in _rows(p)] == ["rewritten", "from-other-process"]


def test_a_held_lock_times_out_loudly_instead_of_writing_unlocked(tmp_path):
    p = str(tmp_path / "l.csv")
    holder = _py(f"""
        import time, ledger_io
        with ledger_io.locked({p!r}):
            print("held", flush=True)
            time.sleep(5)
    """, stdout=subprocess.PIPE, text=True)
    assert holder.stdout.readline().strip() == "held"
    with pytest.raises(ledger_io.LedgerLockTimeout):
        with ledger_io.locked(p, timeout=0.5):
            pass
    holder.kill()
    holder.wait()
    assert not os.path.exists(p)           # nothing was written unlocked


def test_the_lock_survives_an_atomic_replace(tmp_path):
    """The lock is a sidecar file because os.replace swaps the ledger's
    inode; a lock on the ledger itself would be silently lost."""
    p = str(tmp_path / "l.csv")
    ledger_io.atomic_write_rows(p, FIELDS, [])
    with ledger_io.locked(p):
        ledger_io.atomic_write_rows(p, FIELDS, [{"timestamp": "a", "x": "1"}])
        other = _py(f"""
            import ledger_io, sys
            try:
                with ledger_io.locked({p!r}, timeout=0.5):
                    sys.exit(1)            # acquired: the lock was lost
            except ledger_io.LedgerLockTimeout:
                sys.exit(0)
        """)
        assert other.wait(timeout=30) == 0



# ── review findings R7, R8, R9 ────────────────────────────────────────────────

def test_r7_a_new_file_gets_normal_permissions(tmp_path):
    p = tmp_path / "new.csv"
    umask = os.umask(0)
    os.umask(umask)
    ledger_io.atomic_write_rows(str(p), FIELDS, [])
    assert (os.stat(p).st_mode & 0o777) == (0o666 & ~umask)


def test_r8_a_symlinked_ledger_shares_the_real_files_lock(tmp_path):
    real = tmp_path / "x.csv"
    real.write_text("a\n")
    link = tmp_path / "x_link.csv"
    link.symlink_to(real)
    holder = _py(f"""
        import time, ledger_io
        with ledger_io.locked({str(link)!r}):
            print("held", flush=True)
            time.sleep(5)
    """, stdout=subprocess.PIPE, text=True)
    assert holder.stdout.readline().strip() == "held"
    with pytest.raises(ledger_io.LedgerLockTimeout):
        with ledger_io.locked(str(real), timeout=0.5):
            pass
    holder.kill()
    holder.wait()


def test_r9_migrate_header_is_additive_and_verbatim(tmp_path):
    p = tmp_path / "l.csv"
    p.write_text("timestamp,x\nt1,1\nt2,\n")
    assert ledger_io.migrate_header(str(p), ["timestamp", "x", "new_col"]) is True
    assert p.read_text() == "timestamp,x,new_col\nt1,1,\nt2,,\n"
    assert ledger_io.migrate_header(str(p), ["timestamp", "x", "new_col"]) is False


def test_r9_migrate_header_leaves_missing_and_empty_files_alone(tmp_path):
    assert ledger_io.migrate_header(str(tmp_path / "none.csv"), FIELDS) is False
    e = tmp_path / "empty.csv"
    e.write_text("")
    assert ledger_io.migrate_header(str(e), FIELDS) is False
    assert e.read_text() == ""
