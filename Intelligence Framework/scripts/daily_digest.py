"""
daily_digest.py — one-line daily digest from a brief run's output.
Per docs/specs/daily_digest_spec.md. stdin = the run's stdout; stdout =
the single digest line. Never raises to the caller; always exits 0.

Line shape:
  GBP/AUD STAND ASIDE · GBP/JPY STAND ASIDE — watch: <condition>
With the market closed (every pair's block carries the closed banner):
  MARKET CLOSED until Sun 2:00 PM PDT — no live calls · last read:
  GBP/AUD long, GBP/JPY stand aside — watch: <condition>
A closed pair never shows as a bare direction (shadow_tally_spec §3).
The watch clause prefers a concrete pending-pivot sentence ("confirms as
a swing ...") from either pair's EXIT IF; else the first EXIT IF sentence;
a failed run digests as "run failed — see the log".
"""
from __future__ import annotations

import re
import sys


# Every pattern is anchored to a LABEL line (0-2 leading spaces): wrapped
# continuation lines start with 13+ spaces, so feed text in a brief (a US
# event title, a news REASON) can never pose as a label
# (docs/specs/us_events_context_spec.md §1.5, team review 2026-11-03).
_CLOSED = re.compile(r"^ ? ?Market closed — analysis based on last close\. Next open (.+?)\.\s*$", re.M)
_ERROR = re.compile(r"^ ? ?REASON +Framework error", re.M)


def _sections(text: str) -> list:
    """(pair, block) per pair; a block runs from its header to the next."""
    starts = [(m.group(1), m.start()) for m in re.finditer(r"^ ? ?(GBP/[A-Z]{3})\s+\|", text, re.M)]
    return [(name, text[start:starts[i + 1][1] if i + 1 < len(starts) else len(text)])
            for i, (name, start) in enumerate(starts)]


def _decision(name: str, block: str) -> str:
    dm = re.search(r"^ ? ?DECISION\s+(LONG|SHORT|STAND ASIDE)\b", block, re.M)
    return f"{name} {dm.group(1)}" if dm else f"{name} ?"


def pair_decisions(text: str) -> list:
    """Each pair's decision in one brief run, e.g. ["GBP/AUD LONG",
    "GBP/JPY STAND ASIDE"]. The one parser shared by the digest and the
    latest view. A pair's section runs from its header to the next pair's.
    The decision is matched by word because the brief renders "LONG  ▲ — …"
    and "SHORT ▼ — …"; anything else shows "?", never a guessed word."""
    return [_decision(name, block) for name, block in _sections(text)]


def _head(text: str) -> str:
    """The decisions part of the digest. A pair whose block says the market
    is closed shows as its last read, never as a call; if every pair is
    closed the line leads with when the market reopens."""
    parts, opens = [], []
    for name, block in _sections(text):
        d = _decision(name, block)
        closed = _CLOSED.search(block)
        if closed:
            opens.append(closed.group(1))
            parts.append((True, name + " last read " + d[len(name) + 1:].lower()))
        else:
            parts.append((False, d))
    if parts and all(c for c, _ in parts):
        return (f"MARKET CLOSED until {opens[0]} — no live calls · last read: "
                + ", ".join(p.replace(" last read ", " ") for _, p in parts))
    return " · ".join(p + " (market closed)" if c else p for c, p in parts)


def build_digest(text: str) -> str:
    try:
        if _ERROR.search(text) or not text.strip():
            return "run failed — see the log"
        head = _head(text) or "no pairs rendered"

        # watch condition from EXIT IF sections (unwrap the rendered lines)
        watches = []
        for m in re.finditer(
                r"^ ? ?(?:EXIT IF|WATCH FOR)\s+(.*?)(?:\n\s*\n|═)", text, re.S | re.M):
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
