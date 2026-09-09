"""
latest_view.py <day-log> <out-file> — regenerated VIEW beside the
append-only record (docs/specs/daily_digest_spec.md; layout per the held
latest-view spec). The day log is never touched; the view is a
non-evidence file the automation layer rewrites, like health_state.json.
Always exits 0 — a broken view must never break a run.
"""
from __future__ import annotations

import os
import re
import sys


def build_view(text: str, day_log_name: str) -> str:
    headers = [m for m in re.finditer(r"(?m)^=====.*?=====\s*$", text)]
    if not headers:
        return (f"No run blocks found in today's log yet.\n\n"
                f"Full record: {day_log_name}\n")
    starts = [m.start() for m in headers] + [len(text)]
    blocks = [text[starts[i]:starts[i + 1]] for i in range(len(headers))]

    out = []
    ts_last = headers[-1].group(0).strip("= \n")
    out.append(f"LATEST RUN — {ts_last.strip()}")
    out.append(blocks[-1].rstrip())
    out.append("")
    if len(blocks) > 1:
        out.append("── TODAY SO FAR " + "─" * 30)
        for h, b in zip(headers[:-1], blocks[:-1]):
            ts = h.group(0).strip("= \n").strip()
            if "Framework error" in b:
                out.append(f"{ts}  error")
                continue
            decs = []
            for pm in re.finditer(r"(GBP/[A-Z]{3})\s+\|", b):
                seg = b[pm.start():pm.start() + 2000]
                dm = re.search(r"DECISION\s+([A-Z][A-Z ]*?)(?:\s+—|\s*$)",
                               seg, re.M)
                decs.append(f"{pm.group(1)} {dm.group(1).strip()}"
                            if dm else pm.group(1))
            out.append(f"{ts}  {' · '.join(decs) if decs else 'no output'}")
        out.append("")
    signals = [ln for ln in text.splitlines()
               if ln.startswith(("ALERT:", "RECOVERED", "##ALERT##"))]
    if signals:
        out.extend(signals)
        out.append("")
    out.append(f"Full record: {day_log_name}")
    return "\n".join(out) + "\n"


def main(argv) -> int:
    try:
        day_log, out_file = argv[1], argv[2]
        with open(day_log, errors="replace") as f:
            text = f.read()
        view = build_view(text, os.path.basename(day_log))
        with open(out_file, "w") as f:
            f.write(view)
    except Exception:
        pass                               # view failure never breaks a run
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
