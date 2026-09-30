#!/bin/bash
# uninstall.sh — unload and remove the launchd agents from ~/Library/LaunchAgents.
DEST="$HOME/Library/LaunchAgents"

for name in \
    com.quis.intelligence.brief-london \
    com.quis.intelligence.brief-ny \
    com.quis.intelligence.brief-asia \
    com.quis.intelligence.outcomes \
    com.quis.intelligence.calendar \
    com.quis.intelligence.heartbeat; do
    plist="$DEST/${name}.plist"
    if [ -f "$plist" ]; then
        launchctl unload -w "$plist" 2>/dev/null || true
        rm -f "$plist"
        echo "removed $name"
    else
        echo "not installed: $name"
    fi
done

echo "Uninstalled."
