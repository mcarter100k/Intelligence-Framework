#!/bin/bash
# build_skill.sh — assemble the trading-foundation skill from foundation/.
# foundation/ is the source of truth; the installed skill is a build output.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="${1:-$HOME/.claude/skills/trading-foundation}"

rm -rf "$DEST.tmp"
mkdir -p "$DEST.tmp/references" "$DEST.tmp/scripts"
cp "$SRC/skill/SKILL.md" "$DEST.tmp/SKILL.md"
for f in "$SRC"/*.md; do
    [ "$(basename "$f")" = "README.md" ] && continue
    cp "$f" "$DEST.tmp/references/"
done
cp "$SRC"/tools/*.py "$DEST.tmp/scripts/"
rm -rf "$DEST"
mv "$DEST.tmp" "$DEST"
echo "trading-foundation skill built at: $DEST"
ls -R "$DEST"
