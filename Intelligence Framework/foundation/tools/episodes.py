"""
episodes.py — count independent (non-overlapping) episodes honestly.

A signal that fires on consecutive bars is ONE observation, not many. The
framework's 2026-06-29 invalidation found overlapping forward windows had
inflated N ~20x; the 2026-09-29 audit found the replacement counter still
over-counted because it measured the horizon in clock hours (30 H4 bars =
120h) when a 30-bar horizon spans ~168h once weekends are included.

Rule: measure the horizon in BARS on the instrument's own bar index, and
count only GRADED fires. A fire starts a new episode only if it is at least
`horizon` bars after the start of the current episode.

Usage (CSV with a timestamp column; bar index = sorted unique bar stamps):
  python episodes.py fires.csv --time-col fire_time --horizon 30 \
      --bars h4_bars.csv --bars-time-col time [--graded-col outcome]
"""
from __future__ import annotations

import argparse
import bisect
import csv


def count_episodes(fire_bar_idx: list[int], horizon: int) -> list[int]:
    """Return the bar indices that START an independent episode."""
    starts: list[int] = []
    for i in sorted(fire_bar_idx):
        if not starts or i - starts[-1] >= horizon:
            starts.append(i)
    return starts


def to_bar_index(times: list[str], bar_times: list[str]) -> list[int]:
    """Map each fire timestamp to the index of the bar it fired on.

    ISO-8601 strings in the same format and timezone sort chronologically,
    so a string bisect is sufficient.
    """
    bars = sorted(set(bar_times))
    return [max(bisect.bisect_right(bars, t) - 1, 0) for t in times]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fires")
    ap.add_argument("--time-col", required=True)
    ap.add_argument("--horizon", type=int, default=30, help="horizon in bars")
    ap.add_argument("--bars", required=True, help="CSV of the instrument's bars")
    ap.add_argument("--bars-time-col", default="time")
    ap.add_argument("--graded-col", help="only rows where this column is non-empty count")
    ap.add_argument("--group-col", help="count separately per value (e.g. instrument, candidate)")
    a = ap.parse_args()

    with open(a.fires) as f:
        rows = list(csv.DictReader(f))
    with open(a.bars) as f:
        bar_times = [r[a.bars_time_col] for r in csv.DictReader(f)]
    if a.graded_col:
        rows = [r for r in rows if (r.get(a.graded_col) or "").strip()]

    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r[a.group_col] if a.group_col else "all", []).append(r)
    for g, rs in sorted(groups.items()):
        idx = to_bar_index([r[a.time_col] for r in rs], bar_times)
        eps = count_episodes(idx, a.horizon)
        flag = "   INSUFFICIENT (<20)" if len(eps) < 20 else ""
        print(f"{g}: {len(rs)} rows -> {len(eps)} independent episodes{flag}")


if __name__ == "__main__":
    main()
