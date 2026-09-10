"""
daily_digest.py — one-line daily digest from a brief run's output.
Per docs/specs/daily_digest_spec.md. stdin = the run's stdout; stdout =
the single digest line. Never raises to the caller; always exits 0.

Line shape:
  GBP/AUD STAND ASIDE · GBP/JPY STAND ASIDE — watch: <condition>
The watch clause prefers a concrete pending-pivot sentence ("confirms as
a swing ...") from either pair's EXIT IF; else the first EXIT IF sentence;
a failed run digests as "run failed — see the log".
"""
from __future__ import annotations

import re
import sys


def build_digest(text: str) -> str:
    try:
        if "Framework error" in text or not text.strip():
            return "run failed — see the log"

        # per-pair decision: pair header then its DECISION line
        pairs = []
        for m in re.finditer(r"(GBP/[A-Z]{3})\s+\|", text):
            pairs.append((m.group(1), m.start()))
        decisions = []
        for i, (name, start) in enumerate(pairs):
            end = pairs[i + 1][1] if i + 1 < len(pairs) else len(text)
            block = text[start:end]
            dm = re.search(r"DECISION\s+([A-Z][A-Z ]*?)(?:\s+—|\s*$)",
                           block, re.M)
            decisions.append(f"{name} {dm.group(1).strip()}" if dm
                             else f"{name} ?")
        head = " · ".join(decisions) if decisions else "no pairs rendered"

        # watch condition from EXIT IF sections (unwrap the rendered lines)
        watches = []
        for m in re.finditer(
                r"(?:EXIT IF|WATCH FOR)\s+(.*?)(?:\n\s*\n|═)", text, re.S):
            watches.append(re.sub(r"\s+", " ", m.group(1)).strip())
        watch = ""
        for w in watches:                     # prefer a concrete pivot watch
            if "confirms as a swing" in w:
                watch = w
                break
        if not watch and watches:
            watch = watches[0]
        if watch:
            watch = watch.split(". ")[0].rstrip(".")
            return f"{head} — watch: {watch}"
        return head
    except Exception:
        return "digest unavailable — see the log"


if __name__ == "__main__":
    print(build_digest(sys.stdin.read()))
    sys.exit(0)
