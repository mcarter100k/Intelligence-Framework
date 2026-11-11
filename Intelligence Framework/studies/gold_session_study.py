"""Gold session movement study: the UNMODIFIED session runner on XAU_USD,
2021-04-27 -> 2026-09-09 (docs/specs/gold_session_study_spec.md).

usage: python3 -I gold_session_study.py <leg_modern_dir>

Checks the runner's code pins (the same as the replication), then rebinds only
the inputs the spec names: the instrument list, the unit (1.0, so every
"pips" figure is US dollars), the data hashes, the day window, and the
complete-day hours minus gold's daily 17:00 New York break. Then it calls the
runner's own run().
"""
import os
import sys
from datetime import date
from zoneinfo import ZoneInfo

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import session_movement_replication as R  # noqa: E402  code pins

NY = ZoneInfo("America/New_York")
GOLD_HASHES = {
    "XAU_USD_H1.csv": "f57466f89b9e1ee8f5bb4f85967ab018a0a57b6ec325df2271afc0579fac2ef0",
    "XAU_USD_H4.csv": "4b47947d319735a068560e2e20411426cbeb286fdb751e2e5e57a10c39a96892",
    "XAU_USD_D.csv": "3f78111011d647aa223e51984249e805534747cdf9ecfe12c0fd74f4e0493f0a",
}
BREAK_HOUR_NY = 17


def configure():
    import session_movement_data as D
    import session_movement_study as M
    fx_expected = D.expected_hours
    M.PAIRS = ("XAU_USD",)
    M.PIP = {"XAU_USD": 1.0}
    M.EXPECTED_HASHES = dict(GOLD_HASHES)
    D.STUDY_FIRST_DAY, D.STUDY_LAST_DAY = date(2021, 4, 27), date(2026, 9, 9)

    def gold_expected_hours(day, _fx=fx_expected):
        return [t for t in _fx(day) if t.astimezone(NY).hour != BREAK_HOUR_NY]

    D.expected_hours = gold_expected_hours
    return M


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    R.check_code_pins()
    configure().run(sys.argv[1], sys.argv[1])
