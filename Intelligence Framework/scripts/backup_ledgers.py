"""
backup_ledgers.py — dated, hash-verified copies of every evidence file
(docs/specs/safe_ledger_writes_spec.md). Stdlib only; always exits 0.

Runs at the START of the nightly outcome wrapper, before the grader rewrites
anything, so a bad grader write is always recoverable from that day's copy.

  backups/<UTC date>/<files>      one folder per day; the FIRST backup of a
  backups/<UTC date>/MANIFEST.txt day is kept, never overwritten
                                  (name, bytes, sha256 per file)

Each file is copied while holding that file's ledger lock (so the copy is a
consistent snapshot), then re-hashed; the day folder is built under a temp
name and renamed into place only when every copy verified, so a partial day
folder can never look complete.

Stdout protocol (one line):
    backup <date>: N files, B bytes, all sha256 verified -> backups/<date>
    backup <date>: already taken earlier today (kept first of day)
    BACKUP FAILED: <reason>
Restore a file:   cp backups/<date>/<name> <name>   (check MANIFEST.txt first)

Honest limit: this protects against a bad write or a crash, NOT against
losing the disk or the laptop. An off-machine copy is a separate decision.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sys
from datetime import datetime, timezone

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE = [
    "regime_classification_log.csv", "session_context_log.csv",
    "shadow_signal_log.csv", "trade_signal_log.csv", "excluded_rows.csv",
    "trades.csv", "pre_trade_journal.csv", os.path.join("logs", "health_state.json"),
]


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def backup(proj: str = PROJ, date: str | None = None) -> str:
    if proj not in sys.path:
        sys.path.insert(0, proj)
    from ledger_io import locked

    date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    root = os.path.join(proj, "backups")
    dest = os.path.join(root, date)
    if os.path.exists(os.path.join(dest, "MANIFEST.txt")):
        return f"backup {date}: already taken earlier today (kept first of day)"
    tmp = os.path.join(root, f".{date}.partial-{os.getpid()}")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    manifest, total = [], 0
    try:
        for rel in EVIDENCE:
            src = os.path.join(proj, rel)
            if not os.path.exists(src):
                manifest.append(f"{rel}\tABSENT")
                continue
            dst = os.path.join(tmp, rel.replace(os.sep, "__"))
            with locked(src):
                shutil.copy2(src, dst)
                want = _sha256(src)
            got = _sha256(dst)
            if got != want:
                raise RuntimeError(f"hash mismatch copying {rel}")
            size = os.path.getsize(dst)
            total += size
            manifest.append(f"{rel}\t{size}\t{got}")
        with open(os.path.join(tmp, "MANIFEST.txt"), "w") as f:
            f.write("\n".join(manifest) + "\n")
        if os.path.exists(dest):              # a partial folder from a crash
            shutil.rmtree(dest)
        os.rename(tmp, dest)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    n = sum(1 for m in manifest if not m.endswith("ABSENT"))
    return (f"backup {date}: {n} files, {total} bytes, all sha256 verified "
            f"-> backups/{date}")


def main(argv) -> int:
    try:
        print(backup())
    except Exception as exc:
        print(f"BACKUP FAILED: {type(exc).__name__}: {exc}")
    return 0                                # always (exit-0 discipline)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
