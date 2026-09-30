#!/bin/bash
# weekly_heartbeat.sh — Sunday proof-of-life (docs/specs/heartbeat_spec.md
# item 3). ALWAYS notifies, healthy or not — positive confirmation, so a
# MISSING Sunday notification is itself the alarm. Appends the full report to
# logs/heartbeat_<date>.log. Always exits 0.

PROJ="/Users/quis/Intelligence Framework"
cd "$PROJ" || exit 0
[ -f "venv/bin/activate" ] && source "venv/bin/activate"
mkdir -p logs

if [ -z "${INTEL_NO_ENV_FILE:-}" ] && [ -f "$PROJ/.env" ]; then
    set -a; . "$PROJ/.env"; set +a
fi

# Shared notification helper (docs/specs/notify_click_through_spec.md).
. "$PROJ/scripts/notify.sh"

DATE="$(date +%F)"
LOG="logs/heartbeat_${DATE}.log"
# The live checkout must be on main (scripts/live_guard.sh).
. "$PROJ/scripts/live_guard.sh"
live_guard "$LOG"
YDAY="$(date -v-1d +%F 2>/dev/null || date -d yesterday +%F)"

REPORT="$(python3 - "$YDAY" <<'PY'
import os, sys, csv, subprocess
from datetime import datetime, timezone

yday = sys.argv[1]
lines = []

# 1. health state (consecutive failures / last success)
st = subprocess.run(["python3", "scripts/health_state.py", "status"],
                    capture_output=True, text=True).stdout.strip()
lines.append(f"health: {st or 'state unavailable'}")

# 2. scheduled runs from yesterday: present? error content?
for kind in ("brief", "outcomes"):
    p = f"logs/{kind}_{yday}.log"
    if not os.path.exists(p):
        lines.append(f"{kind} {yday}: NO LOG — runs missing")
        continue
    txt = open(p, errors="replace").read()
    runs = sum(1 for ln in txt.splitlines() if ln.startswith("====="))
    bad = ("Framework error" in txt or "GRADER EARLY EXIT" in txt
           or "not configured" in txt or "SHADOW CANDIDATE ERROR" in txt)
    lines.append(f"{kind} {yday}: {runs} run header(s), "
                 f"{'ERRORS PRESENT' if bad else 'no error markers'}")

# 3. shadow rows graded per candidate (valid rows only, via the guard)
try:
    from shadow_signals import get_shadow_tally, episode_count
    parts = []
    for c in ("EARLY_MOMENTUM", "EARLY_MOMENTUM_v2",
              "THRUST_PULLBACK", "MOMENTUM_JOIN"):
        t = get_shadow_tally(c)
        if t["logged"]:
            parts.append(f"{c} {t['graded']}/{t['logged']} graded "
                         f"({episode_count(c)} ep)")
    lines.append("shadow: " + ("; ".join(parts) if parts else "no valid rows"))
except Exception as e:
    lines.append(f"shadow: tally unavailable ({e})")

# 4. calendar.csv age + newest event
try:
    age_h = (datetime.now(timezone.utc).timestamp()
             - os.path.getmtime("calendar.csv")) / 3600
    rows = list(csv.DictReader(open("calendar.csv")))
    newest = max((r["time"] for r in rows), default="none")
    lines.append(f"calendar: {age_h:.0f}h old, {len(rows)} event(s), "
                 f"newest {newest}")
except Exception:
    lines.append("calendar: MISSING or unreadable")

# 5. storylines.md header age
try:
    head = open("storylines.md", errors="replace").readline().strip()
    age_d = (datetime.now(timezone.utc).timestamp()
             - os.path.getmtime("storylines.md")) / 86400
    stale = " — STALE (>7d)" if age_d > 7 else ""
    lines.append(f"storylines: {age_d:.0f}d old{stale} | {head[:70]}")
except Exception:
    lines.append("storylines: MISSING")

# 6. evidence-artifact freshness (regime_log_restore spec item 4a)
try:
    sys.path.insert(0, "scripts")
    import artifact_freshness
    lines.extend(artifact_freshness.check())
except Exception as e:
    lines.append(f"freshness: check unavailable ({e})")

print("\n".join(lines))
PY
)"

{ echo "===== heartbeat $(TZ="${DISPLAY_TZ:-America/Los_Angeles}" date '+%Y-%m-%d %H:%M:%S %Z') ====="
  echo "$REPORT"; echo; } >> "$LOG"

# One-line summary for the notification: worst signal first.
if printf '%s\n' "$REPORT" | grep -qE 'UNHEALTHY|NO LOG|ERRORS PRESENT|MISSING|STALE'; then
    SUMMARY="NEEDS ATTENTION | $(printf '%s\n' "$REPORT" \
        | grep -E 'UNHEALTHY|NO LOG|ERRORS PRESENT|MISSING|STALE' | head -1)"
else
    SUMMARY="healthy | $(printf '%s\n' "$REPORT" | grep '^shadow:' | head -1)"
fi
notify "HEARTBEAT" "$(printf '%s' "$SUMMARY" | cut -c1-200)" "$LOG"

exit 0
