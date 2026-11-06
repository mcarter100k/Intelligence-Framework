"""Session movement study replication: drives the UNMODIFIED runner on another
span (docs/specs/session_movement_replication_spec.md §3).

usage:
  python3 -I session_movement_replication.py control <study_h1_dir> <study_held_dir>
  python3 -I session_movement_replication.py modern <modern_dir>

Before anything runs, the three code files the computation depends on are
hashed and must equal their values at the original run (2f7c68b). The wrapper
then rebinds only the runner's hash table and day window and calls the
runner's own run(). `control` uses the 2005-2013 inputs through that same
rebinding path; its stdout must match the published run byte for byte, bar the
two timestamp lines. `modern` uses the USED span 2021-04-27 -> 2026-09-09.
"""
import hashlib
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

CODE_PINS = {
    "session_movement_study.py": "2302ab4203419186ca3341906bad017aed4b81e5a653c5ae78dd60883724935d",
    "session_movement_data.py": "3f2d43145eca863ace4ad30a2b7af542747f1ad2bf105bb91bc613c61b655ff1",
    "history_study_convert.py": "584ff76da113d3ab8d8eae277f95b6596981badfb8923634063b87de044ea553",
}

PERIODS = {
    "control": {
        "first": date(2005, 1, 3), "last": date(2013, 12, 30),
        "hashes": {
            "GBP_AUD_H1.csv": "9f9303621542ec5e66546132d24be79525054e8d69b483a461954ec2df82f4c3",
            "GBP_JPY_H1.csv": "e00361f23f416b3479d49f08901beb02a943ae3cb759b23e93a3c533c53399cf",
            "GBP_AUD_H4.csv": "a59db9940e8d7a1c4ff02441112390c5d7b7544e764d980943877dee51b0ff77",
            "GBP_AUD_D.csv": "661a9d49c09ed9fbaa7a26a1e3ae60a4fc07860d19ea3ec89342398a9db7d939",
            "GBP_JPY_H4.csv": "f06892d1ebf958cc1a52bebf399e6ce10bef8e73e5e2c5b6a7f5634644053764",
            "GBP_JPY_D.csv": "ca1602404c5c501dffc0ee8ec5eeb4bee4a2197fe2fc76d3bbf69be2c8fa000a",
        },
    },
    "modern": {
        "first": date(2021, 4, 27), "last": date(2026, 9, 9),
        "hashes": {
            "GBP_AUD_H1.csv": "7c8f899f31e4f1f4d92e6c932d202ff8d3375bd5c69eb8d684b8b3f5c3509fed",
            "GBP_JPY_H1.csv": "f0d2437c79778e9fbe003282a7d4f3ec5301b14b54f179f26a1c9640597e1cd3",
            "GBP_AUD_H4.csv": "623f0f5e09e2f8d39e2637eb1d307751a72be155d6214aa1fddf9deadcd77042",
            "GBP_AUD_D.csv": "3f17cd0e7d2b7ab3492d22044876dc4703423fbd60a5d77edfc202abf0530100",
            "GBP_JPY_H4.csv": "3d5131f99184ef1642b5aa075e3a8dea9cadcfb918e59cd42d6c9d7af6bfcf47",
            "GBP_JPY_D.csv": "3635903a1d7d573f1489d61fd1f8eada21d1e3429feccb8a83e717700fdbc3d6",
        },
    },
}


def check_code_pins(folder=HERE, pins=CODE_PINS):
    for name, want in pins.items():
        with open(os.path.join(folder, name), "rb") as fh:
            got = hashlib.sha256(fh.read()).hexdigest()
        if got != want:
            raise SystemExit(f"refused: {name} differs from the original run (sha256 {got})")


def configure(period):
    """Rebind the runner's three inputs; returns the runner module."""
    import session_movement_data as D
    import session_movement_study as M
    p = PERIODS[period]
    M.EXPECTED_HASHES = dict(p["hashes"])
    D.STUDY_FIRST_DAY, D.STUDY_LAST_DAY = p["first"], p["last"]
    return M


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["control"] and len(a) == 3:
        check_code_pins()
        configure("control").run(a[1], a[2])
    elif a[:1] == ["modern"] and len(a) == 2:
        check_code_pins()
        configure("modern").run(a[1], a[1])
    else:
        raise SystemExit(__doc__)
