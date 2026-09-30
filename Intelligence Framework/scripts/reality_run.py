"""
reality_run.py — Gate-2 REALITY runs with every side effect neutralized
(AGENTS.md rules 7 and 10; Phase 1 of the 2026-09-29 audit plan).

A Gate-2 run must use real OANDA data, real code and real ledger contents,
and must write nothing to the real ledgers. The earlier approach, patching
the loggers one by one, missed two of three writers on 2026-09-16 and
contaminated two append-only rows that can never be removed. This tool
does not rely on knowing the writers. Instead it:

  1. hashes every file in the project (except venv/, caches, .git);
  2. copies the root-level ledgers into a fresh temp working directory;
  3. runs the target there, with the project on PYTHONPATH and the
     credentials from .env (a bare env, exactly as launchd sees it). The
     loggers' relative ledger paths therefore land in the temp copies;
  4. re-hashes the project and FAILS (exit 2) if anything changed.

The temp directory is kept, so the run's output and its ledger copies
(showing exactly which rows the real run appended) can be inspected and
cited in a REALITY GATE section.

Usage:
  python3 scripts/reality_run.py brief                 # decision_brief.py GBP_AUD GBP_JPY
  python3 scripts/reality_run.py grader                # run_outcome_check.py
  python3 scripts/reality_run.py script <file.py> [args...]
  --code <dir>   run the code from a worktree (default: this project)
  --no-env       do not load .env (e.g. to force a no-credentials failure)

Exit: the target's exit code; 2 if the project changed; 3 if the
target reported a failure (error page, traceback, grader early exit)
even with exit code 0.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

_SKIP_DIRS = {"venv", "__pycache__", ".pytest_cache", ".git"}


def project_digest(root: str) -> dict:
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                with open(path, "rb") as f:
                    out[os.path.relpath(path, root)] = hashlib.sha256(f.read()).hexdigest()
            except OSError:
                pass
    return out


def load_env_file(path: str) -> dict:
    """KEY=VALUE lines, as `set -a; . .env` would export them."""
    env = {}
    if not os.path.exists(path):
        return env
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.removeprefix("export ").strip()] = v.strip().strip('"').strip("'")
    return env


def reality_run(project: str, argv: list[str], code: str | None = None,
                use_env: bool = True, python: str | None = None) -> int:
    code = code or project
    python = python or (os.path.join(project, "venv", "bin", "python")
                        if os.path.exists(os.path.join(project, "venv", "bin", "python"))
                        else sys.executable)
    before = project_digest(project)

    work = tempfile.mkdtemp(prefix="reality_run_")
    for name in os.listdir(project):
        if name.endswith(".csv") and os.path.isfile(os.path.join(project, name)):
            shutil.copy2(os.path.join(project, name), work)
    copies_before = {n: open(os.path.join(work, n), "rb").read()
                     for n in os.listdir(work)}

    env = {"HOME": os.environ.get("HOME", ""), "PATH": "/usr/bin:/bin",
           "PYTHONPATH": code, "PYTHONDONTWRITEBYTECODE": "1"}
    if use_env:
        env_file = os.path.join(project, ".env")
        if not os.path.exists(env_file):
            print(f"##ALERT## no .env at {env_file}: the run has no "
                  f"credentials and cannot reach OANDA")
        env.update(load_env_file(env_file))

    with open(os.path.join(work, "stdout.txt"), "w") as out, \
         open(os.path.join(work, "stderr.txt"), "w") as err:
        rc = subprocess.run([python, *argv], cwd=work, env=env,
                            stdout=out, stderr=err).returncode

    after = project_digest(project)
    changed = sorted(k for k in set(before) | set(after)
                     if before.get(k) != after.get(k))

    print(f"REALITY RUN: {' '.join(os.path.basename(a) for a in argv[:1])} "
          f"{' '.join(argv[1:])}".rstrip())
    print(f"  exit code        : {rc}")
    print(f"  output directory : {work}")
    for n, data in sorted(copies_before.items()):
        now = open(os.path.join(work, n), "rb").read()
        if now != data:
            nl = b"\n"
            print(f"  ledger copy changed: {n} "
                  f"({data.count(nl)} -> {now.count(nl)} lines)")
    new = sorted(n for n in os.listdir(work)
                 if n not in copies_before and n.endswith(".csv"))
    for n in new:
        print(f"  ledger copy created: {n}")
    failed = _failure_markers(os.path.join(work, "stdout.txt"),
                              os.path.join(work, "stderr.txt"))
    if changed:
        print(f"##ALERT## REALITY RUN CHANGED THE PROJECT: {', '.join(changed)}")
        print("  A side effect escaped the temp directory. Treat any ledger "
              "row it wrote as contaminated (AGENTS.md rule 10).")
        return 2
    print("  project files    : UNCHANGED (verified by hash)")
    if failed:
        # The brief exits 0 even when it renders an error page, so the exit
        # code alone cannot certify a run. An error page is not REALITY.
        print(f"##ALERT## TARGET REPORTED FAILURE ({failed}): this is NOT a "
              f"valid REALITY GATE. See {work}/stdout.txt")
        return 3
    return rc


_FAILURE_MARKERS = ("Framework error", "Traceback (most recent call last)",
                    "GRADER EARLY EXIT", "not configured")


def _failure_markers(*paths: str) -> str:
    found = []
    for path in paths:
        try:
            text = open(path, errors="replace").read()
        except OSError:
            continue
        found += [m for m in _FAILURE_MARKERS if m in text and m not in found]
    return ", ".join(found)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", choices=["brief", "grader", "script"])
    ap.add_argument("rest", nargs="*",
                    help="for `script`: the file and its arguments (use -- "
                         "before arguments that start with a dash)")
    ap.add_argument("--code", help="directory to run the code from (e.g. a worktree)")
    ap.add_argument("--project", help=argparse.SUPPRESS)   # tests only
    ap.add_argument("--no-env", action="store_true")
    # Intermixed: options may follow the target. With REMAINDER, a trailing
    # `--project/--code` was silently swallowed as script arguments and the
    # run used the wrong project with no credentials (caught 2026-09-29).
    a = ap.parse_intermixed_args()

    project = os.path.abspath(a.project or os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    code = os.path.abspath(a.code) if a.code else project
    if a.target == "brief":
        argv = [os.path.join(code, "decision_brief.py"), "GBP_AUD", "GBP_JPY"]
    elif a.target == "grader":
        argv = [os.path.join(code, "run_outcome_check.py")]
    else:
        if not a.rest:
            ap.error("script needs a path")
        argv = [os.path.abspath(a.rest[0]), *a.rest[1:]]
    return reality_run(project, argv, code=code, use_env=not a.no_env)


if __name__ == "__main__":
    sys.exit(main())
