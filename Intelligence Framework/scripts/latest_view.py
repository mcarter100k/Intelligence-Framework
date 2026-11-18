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


def _shown(hdr: str, style: str = "full") -> str:
    """A run header's stamp as the owner reads it: display_time's 12-hour PT
    clock (display_timezone_spec addendum 2026-11-18). The day-log headers
    themselves stay as written; they are records. Stamps are in the display
    zone, so they are read in it. The raw stamp is kept if anything fails."""
    raw = hdr.strip("= ").strip()
    try:
        m = _HDR.match(hdr.strip())
        from display_time import display_zone, to_display
        loc = datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M:%S") \
            .replace(tzinfo=display_zone())
        return to_display(loc, style=style) or raw
    except Exception:
        return raw


def _body(block: str) -> str:
    """The block without its ===== header line, which LATEST RUN restates."""
    first, _, rest = block.partition("\n")
    return rest if _HDR.match(first.strip()) else block


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
            out.append(f"LATEST RUN — {_shown(hdr)}")
            out.append(_body(block).rstrip())
            out.append("")
            out.append(f"Full record: {src}")
            return "\n".join(out) + "\n"
        return (f"No run blocks found for {today} yet.\n\n"
                f"Full record: (no day files found)\n")

    latest_hdr, latest_block, _ = blocks[-1]
    out.append(f"LATEST RUN — {_shown(latest_hdr)}")
    out.append(_body(latest_block).rstrip())
    out.append("")
    if len(blocks) > 1:
        out.append("── TODAY SO FAR " + "─" * 30)
        for hdr, block, _src in blocks[:-1]:
            ts = _shown(hdr, style="time")
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
    if argv[1:2] == ["--shown"]:
        # The wrapper's "is the view THIS run?" check compares the view's first
        # line with this, so both come from _shown (display_timezone_spec
        # addendum 2026-11-18).
        print(_shown(argv[2] if len(argv) > 2 else ""))
        return 0
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
