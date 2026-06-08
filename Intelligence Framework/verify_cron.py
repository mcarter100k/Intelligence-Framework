"""
verify_cron.py
──────────────
Health check for the scheduled alert system.
Run this manually anytime to confirm the system is operational.

Usage:
    python verify_cron.py

Plain English: this script checks whether the cron-based alert system
               is properly set up. It looks at four things:
               1. OANDA credentials — can the framework fetch live prices?
               2. Last framework run — is the context fresh enough to trade?
               3. Journal file — can session guard read today's trades?
               4. Cron log — has cron actually been running?

If any check fails, the reason tells you exactly what to fix.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_DIR = Path(__file__).parent


# ── Individual checks ─────────────────────────────────────────────────────────

def check_env_vars() -> dict:
    """
    Verify OANDA API credentials are available in the current environment.

    Plain English: the framework needs two environment variables to talk to
                   OANDA. If they are missing in the cron environment, every
                   run will show 'Price: N/A' and the framework degrades to
                   Grade C. Fix: add them to ~/.zshrc and re-run setup_cron.sh.
    """
    api_key = os.environ.get("OANDA_API_KEY", "")
    account = os.environ.get("OANDA_ACCOUNT_ID", "")
    missing = []
    if not api_key:
        missing.append("OANDA_API_KEY")
    if not account:
        missing.append("OANDA_ACCOUNT_ID")

    if not missing:
        return {"passed": True, "reason": "OANDA_API_KEY and OANDA_ACCOUNT_ID are set"}
    return {
        "passed": False,
        "reason": (
            f"Missing environment variable(s): {', '.join(missing)}. "
            f"Add them to ~/.zshrc and re-run bash setup_cron.sh."
        ),
    }


def check_last_run(path: Optional[Path] = None) -> dict:
    """
    Verify last_run.json exists and the context is not stale.

    Plain English: every time you run 'python main.py', it saves a snapshot
                   of the market conditions. The watcher uses this snapshot.
                   If the snapshot is older than 4 hours, the watcher blocks
                   all entries. This check tells you if you need to re-run.
    """
    p = path or (_DIR / "last_run.json")
    if not p.exists():
        return {
            "passed": False,
            "reason": "last_run.json not found — run 'python main.py' to create it",
        }
    try:
        data = json.loads(p.read_text())
        from entry_watcher import _context_age_hours
        from risk_config import HARD_LIMITS
        age    = _context_age_hours(data)
        expiry = HARD_LIMITS["context_expiry_hours"]
        fresh  = age <= expiry
        return {
            "passed": fresh,
            "reason": (
                f"Context is {age:.1f}h old — within the {expiry:.0f}h window ✓"
                if fresh else
                f"Context is {age:.1f}h old — EXPIRED (limit: {expiry:.0f}h). "
                f"Run 'python main.py' to refresh."
            ),
        }
    except Exception as e:
        return {"passed": False, "reason": f"Cannot read last_run.json: {e}"}


def check_journal(path: Optional[Path] = None) -> dict:
    """
    Verify the trade journal file exists.

    Plain English: the session guard reads this file to count today's trades
                   and calculate today's loss. Without it, the kill switch
                   cannot protect the account.
    """
    p = path or (_DIR / "run_journal.csv")
    if p.exists():
        return {"passed": True, "reason": f"run_journal.csv found ({p.stat().st_size} bytes)"}
    return {
        "passed": False,
        "reason": "run_journal.csv not found — session guard cannot read trade history",
    }


def check_cron_log(path: Optional[Path] = None) -> dict:
    """
    Verify cron has been running by inspecting the log file.

    Plain English: the cron log records every scheduled run. If it's empty
                   or missing, cron has not run yet — either setup_cron.sh
                   hasn't been run, or cron is not firing on schedule.
    """
    p = path or (_DIR / "logs" / "cron.log")
    if not p.exists():
        return {
            "passed": False,
            "reason": "cron.log not found — run 'bash setup_cron.sh' to install cron jobs",
        }
    lines = [l for l in p.read_text().strip().splitlines() if l.strip()]
    if not lines:
        return {"passed": False, "reason": "cron.log is empty — cron has not run yet"}

    last_line = lines[-1][:80]
    return {
        "passed": True,
        "reason": f"cron.log has {len(lines)} entries. Last: {last_line}",
    }


# ── Orchestrator ──────────────────────────────────────────────────────────────

def run_health_check(
    last_run_path: Optional[Path] = None,
    journal_path:  Optional[Path] = None,
    cron_log_path: Optional[Path] = None,
) -> dict:
    """
    Run all health checks and return a structured result.

    Args: optional path overrides for testing (defaults to real framework paths)
    Returns: {"all_passed": bool, "checks": {name: {"passed": bool, "reason": str}}}
    """
    checks = {
        "env_vars":  check_env_vars(),
        "last_run":  check_last_run(last_run_path),
        "journal":   check_journal(journal_path),
        "cron_log":  check_cron_log(cron_log_path),
    }
    all_passed = all(c["passed"] for c in checks.values())
    return {"all_passed": all_passed, "checks": checks}


# ── CLI output ────────────────────────────────────────────────────────────────

def main() -> None:
    W = 56
    print(f"\n{'═' * W}")
    print(f"  GBP/AUD FRAMEWORK — SYSTEM HEALTH CHECK")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'═' * W}\n")

    result = run_health_check()

    for name, check in result["checks"].items():
        icon   = "✅" if check["passed"] else "❌"
        label  = name.replace("_", " ").title()
        print(f"  {icon}  {label}")
        if not check["passed"]:
            print(f"      → {check['reason']}")
        else:
            print(f"      {check['reason']}")
        print()

    print(f"{'─' * W}")
    if result["all_passed"]:
        print(f"  ✅  All systems operational. Cron is armed.\n")
    else:
        failed = [n for n, c in result["checks"].items() if not c["passed"]]
        print(f"  ❌  {len(failed)} issue(s) need attention before the system is live.\n")


if __name__ == "__main__":
    main()
