"""
latest_view.py <logs-dir> <out-file> — regenerated VIEW beside the
append-only records (docs/specs/daily_digest_spec.md; "today" is the
DISPLAY-ZONE day per the display_timezone_spec addendum). Day logs are
never touched; the view is a non-evidence file the automation layer
rewrites, like health_state.json. Always exits 0 — a broken view must
never break a run.

"Today" = the current date in DISPLAY_TZ. Runs can span two day files
(file names roll on the system clock — records, not display), so the
candidate files D−1/D/D+1 are read and blocks are kept when their =====
header carries today's display date (headers are written in the display
zone since 2026-09-10; a block stamped in another zone groups by its
stamped date — one-time transition quirk). The closing line names every
file the section drew from.
"""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timedelta, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _p in (_ROOT, _HERE):                     # display_time / ledger_io, daily_digest
    if _p not in sys.path:
        sys.path.insert(0, _p)

from daily_digest import pair_decisions, _ERROR   # the one decision parser and error-line anchor

_HDR = re.compile(r"(?m)^=====\s*(\d{4}-\d{2}-\d{2}) ([0-9:]{8}) ([A-Z]{2,5})\s*=====\s*$")
_SIGNAL = ("ALERT:", "RECOVERED", "##ALERT##")


def _display_today() -> str:
    try:
        from display_time import display_zone
        return datetime.now(timezone.utc).astimezone(display_zone()) \
            .strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


def collect(logs_dir: str, today: str):
    """Blocks whose header date == today, across the candidate day files.
    Returns (blocks, sources, fallback_block):
      blocks   : [(header_line, block_text, filename)] in file/date order
      sources  : filenames actually contributing today's blocks
      fallback : the newest block seen anywhere (for an empty today)
    """
    base = datetime.strptime(today, "%Y-%m-%d")
    candidates = [(base + timedelta(days=d)).strftime("brief_%Y-%m-%d.log")
                  for d in (-1, 0, 1)]
    blocks, sources, fallback = [], [], None
    for name in candidates:
        path = os.path.join(logs_dir, name)
        if not os.path.exists(path):
            continue
        try:
            text = open(path, errors="replace").read()
        except OSError:
            continue
        hdrs = list(_HDR.finditer(text))
        starts = [m.start() for m in hdrs] + [len(text)]
        for i, m in enumerate(hdrs):
            block = text[starts[i]:starts[i + 1]]
            fallback = (m.group(0).strip(), block, name)
            if m.group(1) == today:
                blocks.append((m.group(0).strip(), block, name))
                if name not in sources:
                    sources.append(name)
    return blocks, sources, fallback


def build_view(blocks, sources, today: str, fallback=None) -> str:
    out = []
    if not blocks:
        if fallback:
            hdr, block, src = fallback
            out.append(f"No runs yet for {today} (display day). "
                       f"Most recent run:")
            out.append(f"LATEST RUN — {hdr.strip('= ').strip()}")
            out.append(block.rstrip())
            out.append("")
            out.append(f"Full record: {src}")
            return "\n".join(out) + "\n"
        return (f"No run blocks found for {today} yet.\n\n"
                f"Full record: (no day files found)\n")

    latest_hdr, latest_block, _ = blocks[-1]
    out.append(f"LATEST RUN — {latest_hdr.strip('= ').strip()}")
    out.append(latest_block.rstrip())
    out.append("")
    if len(blocks) > 1:
        out.append("── TODAY SO FAR " + "─" * 30)
        for hdr, block, _src in blocks[:-1]:
            ts = hdr.strip("= ").strip()
            if _ERROR.search(block):           # a label line, never feed text (spec §1.5)
                out.append(f"{ts}  error")
                continue
            decs = pair_decisions(block)
            out.append(f"{ts}  {' · '.join(decs) if decs else 'no output'}")
        out.append("")
    signals = []
    for _hdr, block, _src in blocks:
        signals.extend(ln for ln in block.splitlines()
                       if ln.startswith(_SIGNAL))
    if signals:
        out.extend(signals)
        out.append("")
    out.append("Full record: " + ", ".join(sources))
    return "\n".join(out) + "\n"


def main(argv) -> int:
    try:
        logs_dir, out_file = argv[1], argv[2]
        if logs_dir.endswith(".log"):
            # backward-compat: a day-file path — use its directory
            logs_dir = os.path.dirname(logs_dir) or "."
        today = _display_today()
        blocks, sources, fallback = collect(logs_dir, today)
        view = build_view(blocks, sources, today, fallback)
        from ledger_io import atomic_write_text   # never a half-written view
        atomic_write_text(out_file, view)
    except Exception:
        pass                               # view failure never breaks a run
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
