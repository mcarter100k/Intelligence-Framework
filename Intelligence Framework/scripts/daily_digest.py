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


def pair_decisions(text: str) -> list:
    """Each pair's decision in one brief run, e.g. ["GBP/AUD LONG",
    "GBP/JPY STAND ASIDE"]. The one parser shared by the digest and the
    latest view. A pair's section runs from its header to the next pair's.
    The decision is matched by word because the brief renders "LONG  ▲ — …"
    and "SHORT ▼ — …"; anything else shows "?", never a guessed word."""
    starts = [(m.group(1), m.start()) for m in re.finditer(r"(GBP/[A-Z]{3})\s+\|", text)]
    out = []
    for i, (name, start) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(text)
        dm = re.search(r"^\s*DECISION\s+(LONG|SHORT|STAND ASIDE)\b", text[start:end], re.M)
        out.append(f"{name} {dm.group(1)}" if dm else f"{name} ?")
    return out


def build_digest(text: str) -> str:
    try:
        if "Framework error" in text or not text.strip():
            return "run failed — see the log"
        head = " · ".join(pair_decisions(text)) or "no pairs rendered"

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
