"""
test_loss_autopsy.py
────────────────────
Pins the loss-species taxonomy (docs/specs/loss_autopsy_spec.md): one pin
per species, the priority order, wins unclassified, invalid rows never
autopsied, and the additive header migration.

Run: pytest tests/test_loss_autopsy.py
"""
import csv

import shadow_signals as ss


# ── _classify_loss unit pins (price units; risk=1.0 unless stated) ─────────────

def _cl(direction="SHORT", entry=100.0, stop=101.0, risk=1.0, extra="",
        hit=True, mfe_price=0.1, fut_h=None, fut_l=None,
        ei=25, C=None, atr=1.0):
    n = ss.HORIZON
    return ss._classify_loss(
        direction, entry, stop, risk, extra, hit, mfe_price,
        fut_h if fut_h is not None else [100.5] * n,
        fut_l if fut_l is not None else [99.9] * n,
        ei, C if C is not None else [100.0] * 26, atr)


def test_event_window_owns_the_tape():
    # would otherwise be stopped_then_reversed — the news stamp wins
    fut_h = [101.5] + [100.0] * (ss.HORIZON - 1)
    fut_l = [99.5] + [97.0] * (ss.HORIZON - 1)
    assert _cl(extra="adx=20|news_window=true",
               fut_h=fut_h, fut_l=fut_l) == "event_window"

def test_stopped_then_reversed():
    # SHORT: stop hit on bar 0 (high 101.5 >= 101), then price falls to
    # 97.0 — 3R beyond entry in the signal's direction
    fut_h = [101.5] + [100.0] * (ss.HORIZON - 1)
    fut_l = [99.5] + [97.0] * (ss.HORIZON - 1)
    assert _cl(fut_h=fut_h, fut_l=fut_l, mfe_price=3.0) == "stopped_then_reversed"

def test_reversal_below_2r_is_not_noise_stop():
    fut_h = [101.5] + [100.0] * (ss.HORIZON - 1)
    fut_l = [99.5] + [98.6] * (ss.HORIZON - 1)   # post-stop run only 1.4R
    assert _cl(fut_h=fut_h, fut_l=fut_l,
               mfe_price=1.4) != "stopped_then_reversed"

def test_exhaustion_entry():
    # LONG chased 3 ATR above the 20-bar mean; no stop hit, negative net
    C = [100.0] * 26
    assert _cl(direction="LONG", entry=103.0, stop=102.0, hit=False,
               mfe_price=0.5, C=C, atr=1.0) == "exhaustion_entry"

def test_never_onside():
    # stop hit, no reversal, never 0.25R in our favor
    fut_h = [101.5] + [101.0] * (ss.HORIZON - 1)
    fut_l = [99.9] * ss.HORIZON
    assert _cl(fut_h=fut_h, fut_l=fut_l, mfe_price=0.1) == "never_onside"

def test_bled_out_is_the_residual():
    # no stop hit, was 0.5R onside at some point, not stretched at entry
    assert _cl(hit=False, mfe_price=0.5) == "bled_out"

def test_autopsy_never_raises_on_garbage():
    assert ss._classify_loss("SHORT", 100.0, 101.0, 1.0, None, True,
                             0.1, [], [], 0, [], 0.0) in ("", "never_onside")


# ── the founding exhibit, pinned end-to-end at the grading seam ────────────────

def test_grading_seam_classifies_the_noise_stop(tmp_path, monkeypatch):
    import pandas as pd
    monkeypatch.setattr(ss, "LOG_FILE", str(tmp_path / "shadow.csv"))
    ss.log_shadow_signals([{
        "candidate_id": "EARLY_MOMENTUM", "timestamp": "2026-07-29T05:00:00Z",
        "instrument": "GBP_JPY", "direction": "SHORT",
        "entry": 217.667, "stop": 217.996, "atr": 0.34431, "adx": 20.0,
        "adx_slope": 7.8, "structure": "DOWNTREND", "extra": ""}])

    idx = pd.date_range("2026-07-29T05:00:00Z", periods=40, freq="4h")
    df = pd.DataFrame({          # stop hit on bar 1, then an 800-pip collapse
        "Open":  [217.7] * 2 + [212.0] * 38,
        "High":  [218.1] * 2 + [212.5] * 38,
        "Low":   [217.3] * 2 + [209.6] * 38,
        "Close": [217.6] * 2 + [212.0] * 38,
    }, index=idx)
    import oanda_feed
    monkeypatch.setattr(oanda_feed, "is_configured", lambda: True)
    monkeypatch.setattr(oanda_feed, "get_h4_bars", lambda pair, count=500: df)

    assert ss.grade_pending_shadow("GBP_JPY") == 1
    with open(ss.LOG_FILE) as f:
        row = list(csv.DictReader(f))[0]
    assert row["r_multiple"] == "-1.0"
    assert row["loss_species"] == "stopped_then_reversed"

def test_wins_are_not_autopsied(tmp_path, monkeypatch):
    import pandas as pd
    monkeypatch.setattr(ss, "LOG_FILE", str(tmp_path / "shadow.csv"))
    ss.log_shadow_signals([{
        "candidate_id": "MOMENTUM_JOIN", "timestamp": "2026-07-29T05:00:00Z",
        "instrument": "GBP_JPY", "direction": "SHORT",
        "entry": 217.667, "stop": 219.0, "atr": 0.34, "adx": 35.0,
        "adx_slope": 9.0, "structure": "DOWNTREND", "extra": ""}])
    idx = pd.date_range("2026-07-29T05:00:00Z", periods=40, freq="4h")
    df = pd.DataFrame({          # clean winner: never near 219, closes at 212
        "Open": [217.0] * 40, "High": [217.8] * 40,
        "Low": [211.9] * 40, "Close": [212.0] * 40,
    }, index=idx)
    import oanda_feed
    monkeypatch.setattr(oanda_feed, "is_configured", lambda: True)
    monkeypatch.setattr(oanda_feed, "get_h4_bars", lambda pair, count=500: df)
    assert ss.grade_pending_shadow("GBP_JPY") == 1
    with open(ss.LOG_FILE) as f:
        row = list(csv.DictReader(f))[0]
    assert float(row["r_multiple"]) > 0
    assert row["loss_species"] == ""


# ── header migration ───────────────────────────────────────────────────────────

_OLD_HEADER = ("candidate_id,timestamp,instrument,direction,entry,stop,atr,"
               "adx,adx_slope,structure,extra,outcome_filled,bars_elapsed,"
               "mfe_pips,mae_pips,net_30bars_pips,hit_stop,r_multiple")

def test_migration_is_additive_and_lossless(tmp_path, monkeypatch):
    monkeypatch.setattr(ss, "LOG_FILE", str(tmp_path / "shadow.csv"))
    old_row = ('EARLY_MOMENTUM,2026-07-29T05:00:00Z,GBP_JPY,SHORT,217.667,'
               '217.996,0.34431,20.0,7.8,DOWNTREND,"adx=20.0 in[18,25)",'
               'True,30,809.2,102.1,529.1,True,-1.0')
    (tmp_path / "shadow.csv").write_text(_OLD_HEADER + "\n" + old_row + "\n")

    ss.log_shadow_signals([{        # any append triggers the migration first
        "candidate_id": "MOMENTUM_JOIN", "timestamp": "2026-08-01T05:00:00Z",
        "instrument": "GBP_JPY", "direction": "SHORT",
        "entry": 212.0, "stop": 213.0, "atr": 0.4, "adx": 35.0,
        "adx_slope": 9.0, "structure": "DOWNTREND", "extra": ""}])

    with open(ss.LOG_FILE) as f:
        reader = csv.DictReader(f)
        assert list(reader.fieldnames) == ss._FIELDS
        rows = list(reader)
    assert len(rows) == 2
    old = rows[0]
    assert (old["entry"], old["mfe_pips"], old["r_multiple"]) == \
           ("217.667", "809.2", "-1.0")      # old values untouched
    assert old["loss_species"] == ""          # new column blank, not invented


# ── backfill honors the validity guard ─────────────────────────────────────────


def test_loss_species_names_every_type_the_classifier_returns():
    """LOSS_SPECIES is the frozen species set (loss_autopsy_spec); nothing
    else reads it, so pin it to what _classify_loss can actually return."""
    import ast, inspect
    src = ast.parse(inspect.getsource(ss._classify_loss))
    returned = {n.value.value for n in ast.walk(src)
                if isinstance(n, ast.Return) and isinstance(n.value, ast.Constant)
                and isinstance(n.value.value, str) and n.value.value}
    assert returned == set(ss.LOSS_SPECIES)
