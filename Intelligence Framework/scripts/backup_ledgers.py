"""
backup_ledgers.py — dated, hash-verified copies of every evidence file
(docs/specs/safe_ledger_writes_spec.md). Stdlib only; always exits 0.

Runs at the START of the nightly outcome wrapper, before the grader rewrites
anything, so a bad grader write is always recoverable from that day's copy.

  backups/<UTC stamp>/<files>     one folder PER RUN, named by its UTC time
  backups/<UTC stamp>/MANIFEST.txt (e.g. 2026-09-30T221512Z); never
                                  overwritten (name, bytes, sha256 per file)

  Per run, not per day (review R1/R6): a daily slot keyed by UTC date could
  be taken by a late-firing run, so the next day's grader ran with no fresh
  backup; and replacing an existing day folder could delete a complete one.

Each file is copied while holding that file's ledger lock (so the copy is a
consistent snapshot), then re-hashed; the day folder is built under a temp
name and renamed into place only when every copy verified, so a partial day
folder can never look complete.

Stdout protocol (one line):
    backup <stamp>: N files, B bytes, all sha256 verified -> backups/<stamp>
    BACKUP FAILED: <reason>
The wrapper runs the grader ONLY after the success line (review R2/R10).
Restore a file:   cp backups/<stamp>/<name> <name>   (check MANIFEST.txt first)

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
    "trades.csv", "pre_trade_journal.csv", "trade_log.csv",
    os.path.join("logs", "health_state.json"),
]


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def backup(proj: str = PROJ, stamp: str | None = None) -> str:
    if proj not in sys.path:
        sys.path.insert(0, proj)
    from ledger_io import locked

    stamp = stamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    root = os.path.join(proj, "backups")
    dest = os.path.join(root, stamp)
    n_try = 1
    while os.path.exists(dest):               # never touch an existing backup
        n_try += 1
        dest = os.path.join(root, f"{stamp}-{n_try}")
    name = os.path.basename(dest)
    tmp = os.path.join(root, f".{name}.partial-{os.getpid()}")
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
        os.rename(tmp, dest)
    except Exception:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    n = sum(1 for m in manifest if not m.endswith("ABSENT"))
    return (f"backup {name}: {n} files, {total} bytes, all sha256 verified "
            f"-> backups/{name}")


def main(argv) -> int:
    try:
        print(backup())
    except Exception as exc:
        print(f"BACKUP FAILED: {type(exc).__name__}: {exc}")
    return 0                                # always (exit-0 discipline)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
