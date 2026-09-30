"""Turn a tracer JSONL into the exact interleaving between the brief and the
grader: process lifetimes, lock-held intervals per ledger, contention, and
whether two processes ever held the same ledger's lock at once."""
import json
import sys
from collections import defaultdict

ev = [json.loads(l) for l in open(sys.argv[1])]
ev.sort(key=lambda r: r["t"])
t0 = ev[0]["t"]
ms = lambda t: (t - t0) / 1e6

# process lifetimes
life = {}
for r in ev:
    k = (r["pid"], r["prog"])
    life.setdefault(k, [r["t"], r["t"]])
    life[k][0] = min(life[k][0], r["t"]); life[k][1] = max(life[k][1], r["t"])
main = {k: v for k, v in life.items() if k[1] in ("decision_brief.py", "run_outcome_check.py", "backup_ledgers.py")}
print("PROCESS LIFETIMES (ms from first event):")
for (pid, prog), (a, b) in sorted(main.items(), key=lambda x: x[1][0]):
    print(f"  {prog:22s} pid {pid:6d}  {ms(a):9.1f} -> {ms(b):9.1f}")
bri = [v for k, v in main.items() if k[1] == "decision_brief.py"]
gra = [v for k, v in main.items() if k[1] == "run_outcome_check.py"]
if bri and gra:
    lo, hi = max(bri[0][0], gra[0][0]), min(bri[0][1], gra[0][1])
    print(f"  brief/grader lifetime overlap: {max(0.0, (hi - lo) / 1e6):.1f} ms"
          + (f"  ({ms(lo):.1f} -> {ms(hi):.1f})" if hi > lo else "  (none)"))

# lock-held intervals
held, open_since, busy = defaultdict(list), {}, defaultdict(int)
for r in ev:
    k = (r["pid"], r["prog"], r.get("lock"))
    if r["ev"] == "lock_ok":
        open_since[k] = r["t"]
    elif r["ev"] == "unlock" and k in open_since:
        held[r.get("lock")].append((open_since.pop(k), r["t"], r["prog"], r["pid"]))
    elif r["ev"] == "lock_busy":
        busy[(r.get("lock"), r["prog"])] += 1
print("\nLOCK-HELD INTERVALS (brief/grader/backup processes):")
violations = 0
for lock, iv in sorted(held.items()):
    iv.sort()
    rows = [x for x in iv if x[2] in ("decision_brief.py", "run_outcome_check.py", "backup_ledgers.py")]
    for a, b, prog, pid in rows:
        print(f"  {lock:38s} {prog:22s} {ms(a):9.1f} -> {ms(b):9.1f}  ({(b - a) / 1e6:6.2f} ms)")
    for i in range(len(iv)):
        for j in range(i + 1, len(iv)):
            a1, b1, p1, pid1 = iv[i]; a2, b2, p2, pid2 = iv[j]
            if pid1 != pid2 and a2 < b1 and a1 < b2:
                violations += 1
                print(f"  !! OVERLAPPING HOLD on {lock}: {p1} and {p2}")
print(f"\nMUTUAL EXCLUSION: {violations} overlapping holds by different processes on the same ledger lock")
print("CONTENTION (lock_busy attempts = a process found the lock held and waited):")
for (lock, prog), n in sorted(busy.items()):
    print(f"  {prog:22s} waited on {lock}: {n} retries of 20 ms")
if not busy:
    print("  none: the two processes' critical sections never collided in this run")

# ledger-touching events, in global order, for brief & grader only
print("\nINTERLEAVED LEDGER EVENTS (brief B / grader G / backup K):")
tag = {"decision_brief.py": "B", "run_outcome_check.py": "G", "backup_ledgers.py": "K"}
for r in ev:
    if r["prog"] in tag and r["ev"] in ("lock_ok", "lock_busy", "unlock", "open_read", "open_write",
                                         "open_append", "replace", "hold_begin", "hold_end"):
        what = r.get("lock") or r.get("file")
        print(f"  {ms(r['t']):9.1f} {tag[r['prog']]} {r['ev']:11s} {what}")
