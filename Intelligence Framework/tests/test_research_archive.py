"""Pins studies/research_archive.py to data_map_spec §11.2 and §11.6: span
boundaries, the sealed block and boundary embargo, the modern-fetch guards,
the loader's refusals, and assemble + verify end to end on synthetic sources
(including planted defects that verify must catch). No network; every file
lives in tmp_path."""
import json
import os
import sys
from datetime import date, datetime, timedelta, timezone

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "studies"))
import research_archive as A  # noqa: E402
import history_study_gate_s3 as G  # noqa: E402

UTC = timezone.utc


def u(*a):
    return datetime(*a, tzinfo=UTC)


@pytest.mark.parametrize("day,span", [
    (date(2004, 12, 31), None), (date(2005, 1, 3), "STUDY"), (date(2013, 12, 30), "STUDY"),
    (date(2013, 12, 31), None), (date(2017, 6, 7), None), (date(2021, 4, 26), None),
    (date(2021, 4, 27), "USED"), (date(2026, 9, 9), "USED"), (date(2026, 9, 10), None),
    (date(2026, 9, 11), "FORWARD"), (date(2026, 11, 5), "FORWARD")])
def test_span_boundaries(day, span):
    assert A.span_of(day) == span


def test_sealed_block_edges():
    assert not A.in_sealed_block(u(2013, 12, 30, 21))
    assert A.in_sealed_block(u(2013, 12, 30, 22))
    assert A.in_sealed_block(u(2021, 4, 26, 20))
    assert not A.in_sealed_block(u(2021, 4, 26, 21))
    assert (A.SEALED_START, A.SEALED_END) == (G.BLOCK_START, G.BLOCK_END)


def test_modern_request_guard():
    with pytest.raises(A.Refused):
        A.guard_modern_request(u(2021, 4, 26, 21, 0))
    with pytest.raises(A.Refused):
        A.guard_modern_request(u(2019, 1, 1))
    A.guard_modern_request(u(2021, 4, 26, 21, 1))
    A.guard_modern_request(u(2024, 1, 1))


def test_modern_receipt_check():
    A.check_modern_received([u(2021, 4, 26, 21), u(2021, 4, 27, 1)])
    with pytest.raises(A.Refused):
        A.check_modern_received([u(2021, 4, 25, 21), u(2021, 4, 26, 21)])


def test_label_drops_boundary_and_sealed_sessions():
    bars = {u(2013, 12, 30, 18): (1, 1, 1, 1),      # STUDY
            u(2017, 6, 7, 12): (1, 1, 1, 1),        # sealed exam
            u(2026, 9, 9, 21): (1, 1, 1, 1),        # session 2026-09-10: boundary
            u(2026, 9, 10, 21): (1, 1, 1, 1)}       # session 2026-09-11: FORWARD
    kept, spans, dropped = A.label(bars)
    assert spans == {u(2013, 12, 30, 18): "STUDY", u(2026, 9, 10, 21): "FORWARD"}
    assert dropped == {"outside_spans": 1, "boundary_embargo": 1}


def test_d1_consistency():
    d1 = {u(2022, 3, 1, 22): (1.0, 1.5, 0.5, 1.2)}          # session 2022-03-02 (EST)
    h4 = {u(2022, 3, 1, 22): (1.0, 1.5, 0.9, 1.1), u(2022, 3, 2, 2): (1.1, 1.3, 0.5, 1.2)}
    assert A.d1_consistency(d1, h4, 0.1) == {u(2022, 3, 1, 22): (0.0, 0.0, 0.0, 0.0)}
    h4[u(2022, 3, 2, 2)] = (1.1, 1.3, 0.6, 1.2)
    assert A.d1_consistency(d1, h4, 0.1)[u(2022, 3, 1, 22)][2] == pytest.approx(1.0)


# ── end to end on synthetic sources ─────────────────────────────────────────

def _session_bars(session_open, n_h1=24, base=1.0):
    """One weekday session: H1 bars, H4 aggregates and a D1 bar, consistent."""
    h1 = {session_open + timedelta(hours=k): (base + k * 1e-4, base + k * 1e-4 + 5e-4,
                                              base + k * 1e-4 - 5e-4, base + (k + 1) * 1e-4)
          for k in range(n_h1)}
    ts = sorted(h1)
    h4 = {}
    for i in range(0, n_h1, 4):
        g = ts[i:i + 4]
        h4[g[0]] = (h1[g[0]][0], max(h1[t][1] for t in g), min(h1[t][2] for t in g), h1[g[-1]][3])
    d1 = {ts[0]: (h1[ts[0]][0], max(v[1] for v in h1.values()), min(v[2] for v in h1.values()),
                  h1[ts[-1]][3])}
    return d1, h4, h1


def _write_src(folder, pair, d1, h4, h1, h1_only=False, h4d_only=False):
    os.makedirs(folder, exist_ok=True)
    out = {}
    for gran, rows in (("D", d1), ("H4", h4), ("H1", h1)):
        if (h1_only and gran != "H1") or (h4d_only and gran == "H1"):
            continue
        p = os.path.join(folder, f"{pair}_{gran}.csv")
        G.save(p, rows)
        out[os.path.basename(p)] = A.sha(p)
    return out


def _build(tmp_path):
    held, h1d, mod, arc = (str(tmp_path / n) for n in ("held", "h1", "modern", "archive"))
    hh, h1h, mh = {}, {}, {}
    for pair in A.PAIRS:
        # STUDY: Wed 2010-07-07 session (opens Tue 21:00Z, EDT)
        d1, h4, h1 = _session_bars(u(2010, 7, 6, 21))
        hh.update(_write_src(held, pair, d1, h4, h1, h4d_only=True))
        h1h.update(_write_src(h1d, pair, d1, h4, h1, h1_only=True))
        # USED: 2023-03-01 (EST, opens 22:00Z); FORWARD: 2026-09-16; boundary 2026-09-10
        md, m4, m1 = {}, {}, {}
        for so in (u(2023, 2, 28, 22), u(2026, 9, 9, 21), u(2026, 9, 15, 21)):
            a, b, c = _session_bars(so)
            md.update(a), m4.update(b), m1.update(c)
        mh.update(_write_src(mod, pair, md, m4, m1))
    for folder, table in ((held, hh), (h1d, h1h)):
        with open(os.path.join(folder, "data_hashes.json"), "w") as fh:
            json.dump(table, fh)
    with open(os.path.join(mod, "data_hashes.json"), "w") as fh:
        json.dump({"fetched_utc": "x", "files": mh}, fh)
    A._outside_repo(arc)
    A.cmd_assemble(held, h1d, mod, arc)
    return arc


def test_assemble_then_verify_passes_and_spans_are_right(tmp_path, capsys):
    arc = _build(tmp_path)
    assert A.cmd_verify(arc) is True
    man = json.load(open(os.path.join(arc, "manifest.json")))
    f = man["files"]["GBP_JPY_H1.csv"]
    assert f["per_span"]["STUDY"]["rows"] == 24
    assert f["per_span"]["USED"]["rows"] == 24
    assert f["per_span"]["FORWARD"]["rows"] == 24
    assert f["dropped_unlabelled"]["boundary_embargo"] == 24
    assert man["spans"]["FORWARD"] == ["2026-09-11", "2026-09-16"]


def test_loader_refusals_and_selection(tmp_path):
    arc = _build(tmp_path)
    for bad in (None, set(), {"SEALED"}, {"STUDY", "EXAM"}, {"SEEN_NOT_PROOF"}):
        with pytest.raises(A.Refused):
            A.load(arc, "GBP_AUD", "H1", bad)
    study = A.load(arc, "GBP_AUD", "H1", {"STUDY"})
    both = A.load(arc, "GBP_AUD", "H1", {"STUDY", "USED"})
    assert len(study) == 24 and len(both) == 48
    assert all(t.year == 2010 for t in study)


def test_loader_refuses_tampered_file(tmp_path):
    arc = _build(tmp_path)
    p = os.path.join(arc, "GBP_AUD_H1.csv")
    with open(p, "a") as fh:
        fh.write("2017-06-07T12:00:00+00:00,1,1,1,1,USED\n")
    with pytest.raises(A.Refused):
        A.load(arc, "GBP_AUD", "H1", {"USED"})


def test_verify_catches_planted_sealed_bar_even_with_rehashed_manifest(tmp_path):
    arc = _build(tmp_path)
    p = os.path.join(arc, "GBP_AUD_H1.csv")
    with open(p, "a") as fh:
        fh.write("2017-06-07T12:00:00+00:00,1,1,1,1,USED\n")
    mp = os.path.join(arc, "manifest.json")
    man = json.load(open(mp))
    man["files"]["GBP_AUD_H1.csv"]["sha256"] = A.sha(p)
    man["files"]["GBP_AUD_H1.csv"]["rows"] += 1
    json.dump(man, open(mp, "w"))
    assert A.cmd_verify(arc) is False
    with pytest.raises(A.Refused):
        A.load(arc, "GBP_AUD", "H1", {"USED"})


def test_verify_catches_price_defect(tmp_path):
    arc = _build(tmp_path)
    p = os.path.join(arc, "GBP_JPY_H1.csv")
    rows = open(p).read().splitlines()
    parts = rows[1].split(",")
    parts[2] = str(float(parts[2]) + 0.01)            # raise one H1 high in STUDY
    rows[1] = ",".join(parts)
    open(p, "w").write("\n".join(rows) + "\n")
    mp = os.path.join(arc, "manifest.json")
    man = json.load(open(mp))
    man["files"]["GBP_JPY_H1.csv"]["sha256"] = A.sha(p)
    json.dump(man, open(mp, "w"))
    assert A.cmd_verify(arc) is False


def test_assemble_refuses_source_hash_mismatch(tmp_path):
    arc = _build(tmp_path)
    with open(tmp_path / "modern" / "GBP_AUD_H1.csv", "a") as fh:
        fh.write("\n")
    with pytest.raises(A.Refused):
        A.cmd_assemble(str(tmp_path / "held"), str(tmp_path / "h1"), str(tmp_path / "modern"), arc)


def test_archive_dir_inside_repo_is_refused():
    with pytest.raises(A.Refused):
        A._outside_repo(os.path.join(ROOT, "studies", "archive"))
