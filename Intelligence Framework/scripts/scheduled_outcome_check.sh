#!/bin/bash
# scheduled_outcome_check.sh
# ──────────────────────────
# Scheduling + notification WRAPPER only. Runs the daily outcome grader, appends
# full output to a dated log, and fires a macOS notification ONLY when a SHADOW
# outcome was graded this run (including the updated tally). Always exits 0.

PROJ="/Users/quis/Intelligence Framework"
cd "$PROJ" || exit 0
[ -f "venv/bin/activate" ] && source "venv/bin/activate"
mkdir -p logs

DATE="$(date +%F)"
LOG="logs/outcomes_${DATE}.log"

OUT="$(python3 run_outcome_check.py 2>&1)"
{ echo "===== $(date '+%Y-%m-%d %H:%M:%S %Z') ====="; echo "$OUT"; echo; } >> "$LOG"

# Notify only if a shadow-signal outcome was graded this run.
if printf '%s\n' "$OUT" | grep -q 'shadow-signal outcomes filled'; then
    TALLY="$(python3 - <<'PY'
from shadow_signals import get_shadow_tally, episode_count
parts = []
for c in ("EARLY_MOMENTUM", "THRUST_PULLBACK", "MOMENTUM_JOIN"):
    t = get_shadow_tally(c)
    if t["graded"] > 0:
        parts.append(f"{c}: {t['graded']}/{episode_count(c)}ep {t['wins']}W {t['avg_net']:+.0f}p")
print(" | ".join(parts) if parts else "shadow outcomes graded")
PY
)"
    SAFE="$(printf '%s' "$TALLY" | sed 's/"/\\"/g' | cut -c1-200)"
    osascript -e "display notification \"$SAFE\" with title \"Intelligence Framework — Outcomes\"" >/dev/null 2>&1
fi

exit 0
