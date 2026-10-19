"""
test_shadow_tally.py — the shadow tally (docs/specs/shadow_tally_spec.md).

The brief showed "17 rows / 4 episodes, 16 graded, 5 wins, -79 avg pips" for
EARLY_MOMENTUM_v2; a reviewer turned that into -0.95R when the ledger says 3
episodes at mean -0.20R. Episodes are counted on the H4 bar index from
graded rows only, and the tally leads with R.
"""
import csv
import importlib.util
import os
from datetime import datetime, timezone

import pytest

import shadow_signals as ss
from _paths import ROOT

# EARLY_MOMENTUM_v2's real graded rows (timestamp, R) and today's open fire.
EM_V2 = [("2026-09-18T05:00:00Z", -0.55), ("2026-09-18T09:00:00Z", -0.65),
         ("2026-09-18T17:00:00Z", -0.8), ("2026-09-20T21:00:00Z", -0.53),
         ("2026-09-21T05:00:00Z", -1.0), ("2026-09-21T09:00:00Z", -1.0),
         ("2026-09-22T21:00:00Z", -1.0), ("2026-09-25T17:00:00Z", -0.39),
         ("2026-09-27T21:00:00Z", 0.05), ("2026-09-28T05:00:00Z", -0.34),
         ("2026-09-28T09:00:00Z", -0.46), ("2026-09-28T21:00:00Z", -1.0),
         ("2026-10-02T05:00:00Z", 2.3), ("2026-10-02T17:00:00Z", 0.34),
         ("2026-10-04T21:00:00Z", 0.62), ("2026-10-05T09:00:00Z", 0.49)]
OPEN = "2026-10-19T09:00:00Z"


def _row(ts, r=None, cid="EARLY_MOMENTUM_v2", inst="GBP_JPY", net=-79.0):
    row = {k: "" for k in ss._FIELDS}
    row.update({"candidate_id": cid, "timestamp": ts, "instrument": inst,
                "direction": "LONG", "entry": "210.0", "stop": "209.0", "atr": "0.5"})
    if r is not None:
        row.update({"outcome_filled": "True", "r_multiple": str(r),
                    "net_30bars_pips": str(net)})
    return row


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    path = tmp_path / "shadow.csv"
    monkeypatch.setattr(ss, "LOG_FILE", str(path))

    def write(rows):
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=ss._FIELDS)
            w.writeheader()
            w.writerows(rows)
    return write


def test_the_real_em_v2_ledger_is_three_episodes_not_four(ledger):
    ledger([_row(t, r) for t, r in EM_V2] + [_row(OPEN)])
    assert ss.get_shadow_tally("EARLY_MOMENTUM_v2")["episodes"] == 3


def test_a_weekend_does_not_split_an_episode(ledger):
    # 156 clock hours apart, but only 27 H4 bars: one episode.
    ledger([_row("2026-09-25T17:00:00Z", -0.39), _row("2026-10-02T05:00:00Z", 2.3)])
    assert ss.get_shadow_tally("EARLY_MOMENTUM_v2")["episodes"] == 1


def test_open_rows_are_not_episodes(ledger):
    # The second row carries an R but is not marked graded: the graded flag,
    # not the presence of a number, decides.
    half = _row("2026-10-12T09:00:00Z", -1.0)
    half["outcome_filled"] = "False"
    ledger([_row(OPEN), half])
    assert ss.get_shadow_tally("EARLY_MOMENTUM_v2")["episodes"] == 0


def test_the_tally_carries_episode_r(ledger):
    ledger([_row(t, r) for t, r in EM_V2] + [_row(OPEN)])
    t = ss.get_shadow_tally("EARLY_MOMENTUM_v2")
    assert t["episodes"] == 3 and t["episode_rs"] == [-0.55, -0.39, 0.34]
    assert (t["logged"], t["graded"]) == (17, 16)


def test_the_rendered_tally(ledger, monkeypatch, capsys):
    ledger([_row(t, r) for t, r in EM_V2])
    sig = {"candidate_id": "EARLY_MOMENTUM_v2", "timestamp": OPEN, "instrument": "GBP_JPY",
           "direction": "LONG", "entry": 210.917, "stop": 210.084, "atr": 0.5,
           "adx": 20.0, "adx_slope": 0.0, "structure": "UPTREND", "extra": ""}
    monkeypatch.setattr(ss, "check_shadow_signals", lambda inst: [sig])
    ss.run_and_report("GBP_JPY")
    lines = [l.rstrip() for l in capsys.readouterr().out.splitlines()]
    i = next(i for i, l in enumerate(lines) if "tally:" in l)
    assert lines[i:i + 4] == [
        "      tally: 3 independent episodes from 16 graded rows (1 still open)",
        "             per episode: avg -0.20R, median -0.39R, without the best one -0.47R",
        "             diagnostic only: avg -79 pips at bar 30 over the graded rows",
        "             (futility check at 20 episodes, flag at 30, review at 60)"]
    assert not any("wins" in l for l in lines)


def test_two_independent_implementations_agree_on_the_real_bar_index(ledger):
    """shadow_signals (trading-calendar index) against foundation/tools/
    episodes.py on the REAL OANDA H4 index committed in studies/."""
    spec = importlib.util.spec_from_file_location("episodes_tool", os.path.join(ROOT, "foundation", "tools", "episodes.py"))
    ep = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ep)
    bars = [r["time"] for r in csv.DictReader(open(os.path.join(ROOT, "studies", "decision_channel_h4_index_GBP_JPY.csv")))]
    times = [t for t, _ in EM_V2]
    idx = ep.to_bar_index(times, bars)
    starts = ep.count_episodes(idx, 30)
    independent = [times[idx.index(i)] for i in starts]
    ledger([_row(t, r) for t, r in EM_V2])
    # Same episodes, not just the same count: the clock-hour rule also counts
    # 3 here but starts one at 10-02 05:00 (+2.3R) instead of 17:00 (+0.34R).
    assert [e["timestamp"] for e in ss.graded_episodes("EARLY_MOMENTUM_v2")] == independent == [
        "2026-09-18T05:00:00Z", "2026-09-25T17:00:00Z", "2026-10-02T17:00:00Z"]


def test_one_episode_reads_singular_and_has_no_without_best_line(ledger):
    """M9's "without the best one" needs at least two episodes."""
    ledger([_row("2026-09-28T05:00:00Z", -0.33)])
    assert ss.tally_lines(ss.get_shadow_tally("EARLY_MOMENTUM_v2"))[:2] == [
        "1 independent episode from 1 graded row (0 still open)",
        "per episode: avg -0.33R, median -0.33R"]
