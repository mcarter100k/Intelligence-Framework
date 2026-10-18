"""
decision_gate_replay.py — the Phase 0 market-status gate measured on real
brief text (docs/specs/decision_channel_measurement_spec.md, Phase 0).

Every run block in the day logs is fed, verbatim, through the REAL
scheduled_brief.sh at two revisions: OLD (before the gate) and NEW (with
it). Each runs under /bin/bash 3.2, as launchd does, in a throwaway
sandbox whose notifier is a stub that records its arguments. The output is
the number of DECISION notifications each wrapper would have sent.

It reads the day logs read-only and writes only to a temp directory and
--out. It touches no ledger and makes no network call.

Usage (from the project root):
  python3 studies/decision_gate_replay.py --project "/Users/quis/Intelligence Framework" \
      --old a3e070b --new 9283552 [--current <stdout.txt of a reality run>] \
      --out studies/decision_gate_replay_report.md

Figures first produced 2026-10-17 (validation_log, "The decision channel was
never graded"): week of 10/11 old 12 -> new 6; all run blocks 28 -> 16.
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timedelta, timezone

HDR = re.compile(r"^===== (\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) ([A-Z]{3,4}) =====$")
OFF = {"PDT": -7, "PST": -8, "MDT": -6, "MST": -7, "CDT": -5, "CST": -6,
       "EDT": -4, "EST": -5}
WRAPPER = "Intelligence Framework/scripts/scheduled_brief.sh"
LEDGERS = ("regime_classification_log.csv", "session_context_log.csv",
           "shadow_signal_log.csv", "trade_signal_log.csv")


def git_show(repo_file_dir: str, rev: str, path: str) -> str:
    return subprocess.run(["git", "-C", repo_file_dir, "show", f"{rev}:{path}"],
                          capture_output=True, text=True, check=True).stdout


def sandbox(root: str, name: str, project: str, wrapper_src: str) -> dict:
    base = os.path.join(root, name)
    p = os.path.join(base, "proj")
    os.makedirs(os.path.join(p, "logs"))
    shutil.copytree(os.path.join(project, "scripts"), os.path.join(p, "scripts"),
                    ignore=shutil.ignore_patterns("__pycache__", "launchd"))
    with open(os.path.join(p, "scripts", "scheduled_brief.sh"), "w") as f:
        f.write(wrapper_src)
    shutil.copy(os.path.join(project, "ledger_io.py"), p)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 3600))
    for n in LEDGERS:                              # fresh stubs, never the real ledgers
        with open(os.path.join(p, n), "w") as f:
            f.write(f"timestamp,x\n{stamp},1\n")
    with open(os.path.join(p, "calendar.csv"), "w") as f:
        f.write("time,currency,event,actual,forecast,previous,impact\n")
    with open(os.path.join(p, "storylines.md"), "w") as f:
        f.write("notes\n")
    with open(os.path.join(p, "calendar_fetch.py"), "w") as f:
        f.write("print('calendar ok')\n")
    src = os.path.join(base, "brief.txt")
    with open(os.path.join(p, "decision_brief.py"), "w") as f:
        f.write(f"import sys\nsys.stdout.buffer.write(open({src!r}, 'rb').read())\n")
    g = lambda *a: subprocess.run(["git", "-C", p, *a], check=True, capture_output=True)
    g("init", "-q", "-b", "main")
    g("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "init")
    b = os.path.join(base, "bin")
    os.makedirs(b)
    notes = os.path.join(base, "notes.txt")
    with open(os.path.join(b, "osascript"), "w") as f:
        f.write(f'#!/bin/bash\nprintf "%s\\n" "$*" >> "{notes}"\n')
    os.chmod(os.path.join(b, "osascript"), 0o755)
    home = os.path.join(base, "home")
    os.makedirs(home)
    return {"proj": p, "src": src, "notes": notes, "bin": b, "home": home}


def run(box: dict, text: str) -> tuple[bool, str]:
    with open(box["src"], "wb") as f:
        f.write(text.encode("utf-8"))
    if os.path.exists(box["notes"]):
        os.remove(box["notes"])
    env = {"HOME": box["home"], "PATH": f"{box['bin']}:/usr/bin:/bin",
           "INTEL_NO_ENV_FILE": "1", "INTEL_PROJ": box["proj"]}
    r = subprocess.run(["/bin/bash", os.path.join(box["proj"], "scripts", "scheduled_brief.sh")],
                       env=env, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"wrapper exited {r.returncode}: {r.stderr}")
    n = open(box["notes"]).read() if os.path.exists(box["notes"]) else ""
    return 'subtitle "DECISION"' in n, n


def blocks(logs: str) -> list[tuple[str, str, str]]:
    """(stamp, zone, stdout text) per run header, stdout cut at the
    wrapper's appended stderr section."""
    out = []
    for f in sorted(glob.glob(os.path.join(logs, "brief_*.log"))):
        cur = None
        for line in open(f, encoding="utf-8", errors="replace"):
            m = HDR.match(line.rstrip("\n"))
            if m:
                cur = {"stamp": m[1], "tz": m[2], "lines": [], "cut": False}
                out.append(cur)
            elif cur is not None and not cur["cut"]:
                if line.startswith("----- stderr"):
                    cur["cut"] = True
                else:
                    cur["lines"].append(line)
    return [(c["stamp"], c["tz"], "".join(c["lines"])) for c in out]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", required=True)
    ap.add_argument("--old", default="a3e070b", help="revision before the gate")
    ap.add_argument("--new", default="9283552", help="revision with the gate")
    ap.add_argument("--week-start-utc", default="2026-10-11T07:00",
                    help="start of the reported week (Sun 00:00 PDT)")
    ap.add_argument("--current", help="stdout.txt of a live reality run, replayed too")
    ap.add_argument("--out")
    a = ap.parse_args()

    old_src = git_show(a.project, a.old, WRAPPER)
    new_src = git_show(a.project, a.new, WRAPPER)
    if "CLOSED_MARKER" in old_src or "CLOSED_MARKER" not in new_src:
        raise SystemExit("--old must predate the gate and --new must contain it")
    L = [f"# Phase 0 gate replay\n",
         f"Wrappers: old `{a.old}`, new `{a.new}` (scripts/scheduled_brief.sh). "
         f"Day logs: `{a.project}/logs` (read-only). Run {datetime.now(timezone.utc):%Y-%m-%dT%H:%M}Z.\n"]
    with tempfile.TemporaryDirectory() as root:
        old = sandbox(root, "old", a.project, old_src)
        new = sandbox(root, "new", a.project, new_src)
        if a.current:
            text = open(a.current, encoding="utf-8").read()
            o, on = run(old, text)
            n, nn = run(new, text)
            L.append(f"Live brief `{a.current}`: old DECISION notified={o}, new={n}.\n")
        w0 = datetime.fromisoformat(a.week_start_utc)
        tot = {"runs": 0, "old": 0, "new": 0}
        wk = {"runs": 0, "old": 0, "new": 0}
        rows = []
        for stamp, tz, text in blocks(os.path.join(a.project, "logs")):
            if tz not in OFF:
                raise SystemExit(f"unknown zone {tz!r} at {stamp}")
            utc = datetime.strptime(stamp, "%Y-%m-%d %H:%M:%S") - timedelta(hours=OFF[tz])
            o, _ = run(old, text)
            n, _ = run(new, text)
            for d in (tot,) + ((wk,) if w0 <= utc < w0 + timedelta(days=7) else ()):
                d["runs"] += 1
                d["old"] += o
                d["new"] += n
            if w0 <= utc < w0 + timedelta(days=7):
                rows.append(f"| {stamp} {tz} | {int(o)} | {int(n)} | "
                            f"{'yes' if 'Market closed' in text else 'no'} |")
    L.append(f"**All run blocks:** {tot['runs']} | DECISION notifications old {tot['old']}, "
             f"new {tot['new']}\n")
    L.append(f"**Week from {a.week_start_utc}Z:** {wk['runs']} runs | old {wk['old']}, "
             f"new {wk['new']}\n")
    L += ["| run | old | new | closed banner |", "|---|---|---|---|", *rows]
    text = "\n".join(L) + "\n"
    print(text)
    if a.out:
        with open(a.out, "w") as f:
            f.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
