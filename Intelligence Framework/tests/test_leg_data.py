"""Pins studies/leg_data.py: legs are assembled with the cross archive's span
labels, trimmed to the cross archive's last session, refused on modern
weekend candles, and verified by research_archive.cmd_verify with the legs'
own pip sizes (planted defects fail). Synthetic data in tmp_path only."""
import json
import os
import sys
from datetime import date, timedelta

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "studies"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import leg_data as L  # noqa: E402
import research_archive as A  # noqa: E402
from test_research_archive import _session_bars, u  # noqa: E402


def _parts():
    sd, s4, s1 = _session_bars(u(2010, 7, 6, 21))                      # STUDY Wed 2010-07-07
    md, m4, m1 = {}, {}, {}
    for so in (u(2023, 2, 28, 22), u(2026, 9, 9, 21), u(2026, 9, 15, 21), u(2026, 11, 5, 22)):
        a, b, c = _session_bars(so)                                    # USED, boundary, FORWARD, late
        md.update(a), m4.update(b), m1.update(c)
    return {"D": sd, "H4": s4, "H1": s1}, {"D": md, "H4": m4, "H1": m1}


def test_assemble_labels_trims_and_drops_boundary():
    study, modern = _parts()
    out = L.assemble_instrument(study, modern, date(2026, 9, 16))
    bars, spans, dropped = out["H1"]
    assert Counter_of(spans) == {"STUDY": 24, "USED": 24, "FORWARD": 24}
    assert dropped == {"boundary_embargo": 24, "after_last_cross_session": 24}


def Counter_of(spans):
    out = {}
    for s in spans.values():
        out[s] = out.get(s, 0) + 1
    return out


def test_assemble_refuses_modern_weekend_candle():
    study, modern = _parts()
    modern["H1"][u(2023, 3, 4, 15)] = (1, 1, 1, 1)                     # Saturday session
    with pytest.raises(A.Refused):
        L.assemble_instrument(study, modern, date(2026, 9, 16))


def _archive(tmp_path):
    study, modern = _parts()
    arc = tmp_path / "legs"
    arc.mkdir()
    man = {"files": {}}
    for inst in L.INSTRUMENTS:
        for gran, (bars, spans, _) in L.assemble_instrument(study, modern, date(2026, 9, 16)).items():
            p = arc / f"{inst}_{gran}.csv"
            A._write(str(p), bars, spans)
            man["files"][p.name] = {"sha256": A.sha(str(p)), "rows": len(bars)}
    (arc / "manifest.json").write_text(json.dumps(man))
    return arc


def test_verify_passes_with_leg_pips_and_fails_on_planted_defect(tmp_path):
    arc = _archive(tmp_path)
    assert A.cmd_verify(str(arc), pairs=L.INSTRUMENTS, pip_map=L.PIP) is True
    p = arc / "USD_JPY_H1.csv"
    rows = p.read_text().splitlines()
    f = rows[1].split(",")
    f[2] = str(float(f[2]) + 0.05)
    rows[1] = ",".join(f)
    p.write_text("\n".join(rows) + "\n")
    man = json.loads((arc / "manifest.json").read_text())
    man["files"]["USD_JPY_H1.csv"]["sha256"] = A.sha(str(p))
    (arc / "manifest.json").write_text(json.dumps(man))
    assert A.cmd_verify(str(arc), pairs=L.INSTRUMENTS, pip_map=L.PIP) is False


def test_verify_fails_when_an_instrument_file_is_missing(tmp_path):
    arc = _archive(tmp_path)
    man = json.loads((arc / "manifest.json").read_text())
    del man["files"]["XAU_USD_H4.csv"]
    (arc / "manifest.json").write_text(json.dumps(man))
    assert A.cmd_verify(str(arc), pairs=L.INSTRUMENTS, pip_map=L.PIP) is False


def test_pips_cover_every_instrument():
    assert set(L.PIP) == set(L.INSTRUMENTS)
    assert L.PIP["USD_JPY"] == 0.01 and L.PIP["GBP_USD"] == 0.0001


def test_d1_tolerance_uses_the_legs_own_pip(tmp_path):
    """A 1-pip (0.01) error in a USD_JPY daily high must fail; with a wrong pip
    size the 0.5-pip tolerance would swallow it."""
    arc = _archive(tmp_path)
    p = arc / "USD_JPY_D.csv"
    rows = p.read_text().splitlines()
    f = rows[1].split(",")
    f[2] = repr(float(f[2]) + 0.01)
    rows[1] = ",".join(f)
    p.write_text("\n".join(rows) + "\n")
    man = json.loads((arc / "manifest.json").read_text())
    man["files"]["USD_JPY_D.csv"]["sha256"] = A.sha(str(p))
    (arc / "manifest.json").write_text(json.dumps(man))
    assert A.cmd_verify(str(arc), pairs=L.INSTRUMENTS, pip_map=L.PIP) is False
