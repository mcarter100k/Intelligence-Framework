"""
episodes.py — count independent (non-overlapping) episodes honestly.

A signal that fires on consecutive bars is ONE observation, not many. The
framework's 2026-06-29 invalidation found overlapping forward windows had
inflated N ~20x; the 2026-09-29 audit found the replacement counter still
over-counted because it measured the horizon in clock hours (30 H4 bars =
120h) when a 30-bar horizon spans ~168h once weekends are included.

Rule: measure the horizon in BARS on the instrument's own bar index, and
count only GRADED fires (sentinels like "pending" are ungraded, and the
number dropped is printed). A fire starts a new episode only if it is at least
`horizon` bars after the start of the current episode.

A fire that cannot be placed on the bar index (before the first bar, after
the last, or an unparseable or timezone-less stamp) is an ERROR, never a
default (incident I5).

Usage (CSV with a timestamp column; bar index = sorted unique bar stamps):
  python episodes.py fires.csv --time-col fire_time --horizon 30 \
      --bars h4_bars.csv --bars-time-col time [--graded-col outcome]
"""
from __future__ import annotations

import argparse
import bisect
import csv
from datetime import datetime, timezone

UNGRADED = frozenset({"", "pending", "none", "na", "n/a", "null", "false"})


def count_episodes(fire_bar_idx: list[int], horizon: int) -> list[int]:
    """Return the bar indices that START an independent episode."""
    starts: list[int] = []
    for i in sorted(fire_bar_idx):
        if not starts or i - starts[-1] >= horizon:
            starts.append(i)
    return starts


def parse_utc(ts: str) -> datetime:
    """Parse an ISO-8601 stamp to a UTC-aware datetime, or raise naming it."""
    try:
        dt = datetime.fromisoformat(ts.strip())
    except (ValueError, AttributeError):
        raise ValueError(f"unparseable timestamp: {ts!r}") from None
    if dt.tzinfo is None:
        raise ValueError(f"timestamp has no timezone: {ts!r} (append Z for UTC)")
    return dt.astimezone(timezone.utc)


def to_bar_index(times: list[str], bar_times: list[str]) -> list[int]:
    """Map each fire timestamp to the index of the bar it fired on.

    Instants are compared, not strings, so "...Z" and "...+00:00" agree.
    A fire before the first bar or after the last bar's open raises: the
    bar file must cover every fire.
    """
    bars = sorted(set(parse_utc(b) for b in bar_times))
    out = []
    for t in times:
        dt = parse_utc(t)
        if not bars or dt < bars[0] or dt > bars[-1]:
            span = f"{bars[0].isoformat()} .. {bars[-1].isoformat()}" if bars else "no bars"
            raise ValueError(f"fire {t!r} is outside the bar index ({span})")
        out.append(bisect.bisect_right(bars, dt) - 1)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fires")
    ap.add_argument("--time-col", required=True)
    ap.add_argument("--horizon", type=int, default=30, help="horizon in bars")
    ap.add_argument("--bars", required=True, help="CSV of the instrument's bars")
    ap.add_argument("--bars-time-col", default="time")
    ap.add_argument("--graded-col", help="only rows where this column holds a real grade count")
    ap.add_argument("--ungraded-value", action="append", default=[],
                    help="extra value meaning ungraded (repeatable; case-insensitive). "
                         f"Always ungraded: {sorted(UNGRADED)}")
    ap.add_argument("--group-col", help="count separately per value (e.g. instrument, candidate)")
    a = ap.parse_args()

    with open(a.fires) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if a.graded_col and a.graded_col not in (reader.fieldnames or []):
        ap.error(f"--graded-col {a.graded_col!r} is not a column of {a.fires}")
    with open(a.bars) as f:
        bar_times = [r[a.bars_time_col] for r in csv.DictReader(f)]
    if a.graded_col:
        ungraded = UNGRADED | {v.strip().lower() for v in a.ungraded_value}
        kept = [r for r in rows if (r.get(a.graded_col) or "").strip().lower() not in ungraded]
        print(f"dropped as ungraded ({a.graded_col}): {len(rows) - len(kept)} of {len(rows)} rows")
        rows = kept

    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r[a.group_col] if a.group_col else "all", []).append(r)
    try:  # map every group before printing any, so an error leaves no partial table
        counts = [(g, len(rs), len(count_episodes(
                      to_bar_index([r[a.time_col] for r in rs], bar_times), a.horizon)))
                  for g, rs in sorted(groups.items())]
    except ValueError as e:
        ap.error(str(e))
    for g, n_rows, n_eps in counts:
        flag = "   INSUFFICIENT (<20)" if n_eps < 20 else ""
        print(f"{g}: {n_rows} rows -> {n_eps} independent episodes{flag}")


if __name__ == "__main__":
    main()
