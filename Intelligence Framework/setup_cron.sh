#!/bin/bash
# setup_cron.sh
# ─────────────
# Sets up the three scheduled framework runs on your Mac.
# Run once: bash setup_cron.sh
#
# What it does:
#   1. Finds your Python path
#   2. Creates a log directory
#   3. Installs three cron jobs:
#      11:30 PM PT — Pre-London  (most important)
#       4:30 AM PT — Pre-NY      (confirmation run)
#       1:30 PM PT — NY Close    (silent, log only)
#   4. Keeps Mac awake during each run using caffeinate
#
# To view your cron jobs: crontab -l
# To remove all jobs:     crontab -r
# To edit manually:       crontab -e

set -e

# ── Detect paths ──────────────────────────────────────────────────────────────
PYTHON=$(which python3)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
NOTIFY="$SCRIPT_DIR/notify.py"
LOG_DIR="$SCRIPT_DIR/logs"

echo ""
echo "  GBP/AUD Framework — Cron Setup"
echo "  ================================"
echo ""
echo "  Python:     $PYTHON"
echo "  Script dir: $SCRIPT_DIR"
echo "  Notify:     $NOTIFY"
echo ""

# ── Create logs directory ─────────────────────────────────────────────────────
mkdir -p "$LOG_DIR"
echo "  ✅ Log directory ready: $LOG_DIR"

# ── Build cron entries ────────────────────────────────────────────────────────
# Format: MIN HOUR * * * command
# PT timezone notes:
#   11:30 PM PT = 23:30 local (if Mac is set to PT)
#    4:30 AM PT = 04:30 local
#    1:30 PM PT = 13:30 local
#
# caffeinate -u -t 120 keeps Mac awake for 2 minutes during each run
# The -u flag asserts UserIsActive so display stays on

CRON_PRE_LONDON="30 23 * * 1-5 caffeinate -u -t 120 && cd '$SCRIPT_DIR' && $PYTHON '$NOTIFY' --threshold B+ >> '$LOG_DIR/cron.log' 2>&1"
CRON_PRE_NY="30 4 * * 2-6 caffeinate -u -t 120 && cd '$SCRIPT_DIR' && $PYTHON '$NOTIFY' --threshold B+ >> '$LOG_DIR/cron.log' 2>&1"
CRON_NY_CLOSE="30 13 * * 1-5 caffeinate -u -t 120 && cd '$SCRIPT_DIR' && $PYTHON '$NOTIFY' --silent >> '$LOG_DIR/cron.log' 2>&1"

# ── Install cron jobs (preserve existing, add new) ────────────────────────────
# Remove old GBP/AUD entries if they exist, then add fresh ones
(crontab -l 2>/dev/null | grep -v "notify.py" | grep -v "GBP/AUD Framework") | crontab -

# Add new entries
(crontab -l 2>/dev/null; echo "# GBP/AUD Framework — Pre-London (11:30 PM PT, Mon-Fri)"; echo "$CRON_PRE_LONDON") | crontab -
(crontab -l 2>/dev/null; echo "# GBP/AUD Framework — Pre-NY (4:30 AM PT, Tue-Sat)";     echo "$CRON_PRE_NY")     | crontab -
(crontab -l 2>/dev/null; echo "# GBP/AUD Framework — NY Close (1:30 PM PT, Mon-Fri)";   echo "$CRON_NY_CLOSE")   | crontab -

echo ""
echo "  ✅ Three cron jobs installed:"
echo ""
echo "  11:30 PM PT (Mon-Fri) — Pre-London  — notifies if B+ or above"
echo "   4:30 AM PT (Tue-Sat) — Pre-NY      — notifies if B+ or above"
echo "   1:30 PM PT (Mon-Fri) — NY Close    — silent log only"
echo ""
echo "  Current crontab:"
crontab -l | grep -A1 "GBP/AUD"
echo ""

# ── Mac permission reminder ───────────────────────────────────────────────────
echo "  ⚠️  IMPORTANT: Mac permissions needed"
echo ""
echo "  For notifications to work you need to grant Terminal"
echo "  permission to send notifications:"
echo ""
echo "  1. Open System Settings → Notifications"
echo "  2. Find 'Terminal' in the list"
echo "  3. Turn on 'Allow Notifications'"
echo "  4. Set alert style to 'Alerts' (stays until dismissed)"
echo ""
echo "  For cron to run while lid is open but screen is off:"
echo "  System Settings → Battery → turn off 'Enable Power Nap'"
echo "  (Power Nap can interfere with cron timing)"
echo ""

# ── Test notification ─────────────────────────────────────────────────────────
echo "  Sending test notification now..."
cd "$SCRIPT_DIR"
$PYTHON "$NOTIFY" --test
echo ""
echo "  If you saw a notification appear in the top-right corner,"
echo "  the system is working. ✅"
echo ""
echo "  To manually test a full framework run:"
echo "  cd $SCRIPT_DIR && python notify.py --force"
echo ""
