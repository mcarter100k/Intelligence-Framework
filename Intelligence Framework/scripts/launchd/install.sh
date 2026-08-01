#!/bin/bash
# install.sh — copy the launchd plists to ~/Library/LaunchAgents and load them.
# Idempotent: unloads any existing copy first. Run once to enable scheduling.
set -e

PROJ="/Users/quis/Intelligence Framework"
SRC="$PROJ/scripts/launchd"
DEST="$HOME/Library/LaunchAgents"
mkdir -p "$DEST"

# wrappers must be executable
chmod +x "$PROJ/scripts/scheduled_brief.sh" "$PROJ/scripts/scheduled_outcome_check.sh" \
         "$PROJ/scripts/scheduled_calendar.sh"
mkdir -p "$PROJ/logs"

for p in "$SRC"/com.quis.intelligence.*.plist; do
    name="$(basename "$p")"
    cp "$p" "$DEST/$name"
    launchctl unload "$DEST/$name" 2>/dev/null || true
    launchctl load -w "$DEST/$name"
    echo "loaded  $name"
done

echo
echo "Installed. Verify with:  launchctl list | grep com.quis.intelligence"
echo "Schedule (local time): brief 02:30 / 07:30 / 18:00, outcomes 15:15, calendar Sun 12:00."
