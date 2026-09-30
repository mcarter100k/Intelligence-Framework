#!/bin/bash
# build_skill.sh — assemble every skill under foundation/skills/ and install it.
# foundation/ is the source of truth; installed skills are build outputs.
#   trading-foundation  : SKILL.md + foundation/*.md as references/ + tools/ as scripts/
#   evidence-validation : SKILL.md + its own scripts/
# Usage: ./foundation/build_skill.sh [dest-root]   (default ~/.claude/skills)
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST_ROOT="${1:-$HOME/.claude/skills}"
mkdir -p "$DEST_ROOT"

for skill_dir in "$SRC"/skills/*/; do
    name="$(basename "$skill_dir")"
    out="$DEST_ROOT/$name"
    rm -rf "$out.tmp"
    mkdir -p "$out.tmp"
    cp "$skill_dir/SKILL.md" "$out.tmp/SKILL.md"
    if [ -d "$skill_dir/scripts" ]; then
        mkdir -p "$out.tmp/scripts"
        cp "$skill_dir"/scripts/*.py "$out.tmp/scripts/"
    fi
    if [ "$name" = "trading-foundation" ]; then
        mkdir -p "$out.tmp/references" "$out.tmp/scripts"
        for f in "$SRC"/*.md; do
            [ "$(basename "$f")" = "README.md" ] && continue
            cp "$f" "$out.tmp/references/"
        done
        cp "$SRC"/tools/*.py "$out.tmp/scripts/"
    fi
    rm -rf "$out"
    mv "$out.tmp" "$out"
    echo "built $name -> $out"
done
