"""
test_decision_channel_inventory.py — the Phase 2 parser's distinctions
(docs/specs/decision_channel_measurement_spec.md, shared definitions).

The inventory is only as honest as its state classification. The failure it
must never make is the 39-day outage's: an error page renders
"DECISION STAND ASIDE", and counting it as a stand-aside would turn an
unobserved run into a decision.
"""
import importlib.util
import os

import pytest

_ROOT = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "decision_channel_inventory",
    os.path.join(_ROOT, "studies", "decision_channel_inventory.py"))
inv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(inv)


def _block(pair, decision, closed=False, error=False):
    lines = [f"  {pair}  |  Fri 16 Oct 2026 6:12 PM PDT", "  Price: 1.9189  |  ATR: 100.9 pips"]
    if closed:
        lines.append("  Market closed — analysis based on last close. Next open Sun 2:00 PM PDT.")
    lines += ["", f"  DECISION     {decision} — x", ""]
    if error:
        lines += ["  REASON       Framework error — do not trade: OANDA",
                  "               not configured", ""]
    return lines


def _write(tmp_path, runs):
    d = tmp_path / "logs"
    d.mkdir()
    text = []
    for stamp, body in runs:
        text += [f"===== {stamp} =====", *body, ""]
    (d / "brief_2026-10-16.log").write_text("\n".join(text) + "\n", encoding="utf-8")
    return str(d)


def test_an_error_page_is_run_errored_never_stand_aside(tmp_path):
    logs = _write(tmp_path, [("2026-10-16 07:30:00 PDT",
                              _block("GBP/AUD", "STAND ASIDE", error=True)
                              + _block("GBP/JPY", "STAND ASIDE", error=True))])
    r = inv.parse_runs(logs)[0]["inst"]
    assert r["GBP_AUD"]["status"] == r["GBP_JPY"]["status"] == "RUN ERRORED"
    assert "OANDA" in r["GBP_AUD"]["cause"]


def test_closed_open_and_missing_blocks_are_distinct_states(tmp_path):
    logs = _write(tmp_path, [
        ("2026-10-16 18:12:44 PDT", _block("GBP/AUD", "LONG ▲", closed=True)
                                    + _block("GBP/JPY", "STAND ASIDE", closed=True)),
        ("2026-10-15 07:30:00 PDT", _block("GBP/AUD", "SHORT ▼")),
    ])
    runs = inv.parse_runs(logs)
    wed, fri = runs[0]["inst"], runs[1]["inst"]          # sorted by UTC time
    assert wed["GBP_AUD"]["status"] == "SHORT"
    assert wed["GBP_JPY"]["status"] == "RUN ERRORED"      # no block = unobserved
    assert fri["GBP_AUD"]["status"] == "MARKET CLOSED" and fri["GBP_AUD"]["decision"] == "LONG"
    assert fri["GBP_JPY"]["status"] == "MARKET CLOSED" and fri["GBP_JPY"]["decision"] == "STAND ASIDE"
    assert runs[1]["t"].isoformat() == "2026-10-17T01:12:44+00:00"


def test_concurrent_copies_merge_only_when_they_agree(tmp_path):
    agree = _block("GBP/AUD", "STAND ASIDE") + _block("GBP/JPY", "SHORT ▼")
    logs = _write(tmp_path, [("2026-09-14 09:16:50 PDT", agree)] * 3)
    runs = inv.parse_runs(logs)
    assert len(runs) == 1 and runs[0]["concurrent"] == 3
    assert runs[0]["inst"]["GBP_JPY"]["status"] == "SHORT"


def test_concurrent_copies_that_disagree_are_unobserved(tmp_path):
    a = _block("GBP/AUD", "STAND ASIDE") + _block("GBP/JPY", "SHORT ▼")
    b = _block("GBP/AUD", "STAND ASIDE") + _block("GBP/JPY", "STAND ASIDE")
    logs = _write(tmp_path, [("2026-09-14 09:16:50 PDT", a), ("2026-09-14 09:16:50 PDT", b)])
    r = inv.parse_runs(logs)[0]["inst"]
    assert r["GBP_JPY"]["status"] == "RUN ERRORED"
    assert r["GBP_AUD"]["status"] == "STAND ASIDE"


def test_an_unknown_header_zone_is_an_error_not_a_default(tmp_path):
    logs = _write(tmp_path, [("2026-10-16 07:30:00 XYZ", _block("GBP/AUD", "LONG ▲"))])
    with pytest.raises(ValueError, match="XYZ"):
        inv.parse_runs(logs)


def test_onsets_are_state_changes_and_reannouncements_are_not(tmp_path):
    seq = [("2026-10-13 07:30:00 PDT", "STAND ASIDE"), ("2026-10-13 18:00:00 PDT", "SHORT ▼"),
           ("2026-10-14 02:30:00 PDT", "SHORT ▼"), ("2026-10-14 07:30:00 PDT", "SHORT ▼"),
           ("2026-10-14 18:00:00 PDT", "STAND ASIDE"), ("2026-10-15 02:30:00 PDT", "SHORT ▼")]
    logs = _write(tmp_path, [(s, _block("GBP/JPY", d)) for s, d in seq])
    runs = inv.parse_runs(logs)
    from datetime import datetime, timedelta, timezone
    t0 = datetime(2026, 10, 13, tzinfo=timezone.utc)
    bars = [t0 + timedelta(hours=4 * i) for i in range(60)]
    onsets, eps = inv.episodes_for("GBP_JPY", runs, {}, bars)
    assert [o["run"]["local"] for o in onsets] == ["2026-10-13 18:00:00 PDT",
                                                   "2026-10-15 02:30:00 PDT"]
    assert len(eps) == 1 and onsets[1]["episode"] is False      # inside 30 bars: absorbed
