"""
test_trade_logger.py — Gate 1 (controlled inputs; never sufficient alone).

Pins the repaired trade journal (docs/specs/trade_logger_repair_spec.md):
two-row append-only convention, pinned schema, stack_id linkage with
most-recent-match default, instrument-correct pip math, derived open list.

Run: pytest test_trade_logger.py
"""
import csv

import pytest

import trade_logger as tl


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    path = tmp_path / "trades.csv"
    monkeypatch.setattr(tl, "TRADES_FILE", str(path))
    return path


def _feed(monkeypatch, answers):
    it = iter(answers)
    monkeypatch.setattr("builtins.input", lambda *_a: next(it))


def test_schema_pinned():
    assert tl.FIELDS == [
        "row_type", "position_id", "timestamp_utc", "instrument", "direction",
        "open_price", "stop", "target", "close_price", "size", "pips",
        "outcome", "balance_open", "balance_close", "return_pct",
        "stack_id", "rationale",
    ]


def test_full_open_close_flow_two_rows(ledger, monkeypatch):
    # OPEN: instrument, direction, entry, stop, target, size, balance,
    #       stack (- = none), rationale
    _feed(monkeypatch, ["GBP_JPY", "SHORT", "217.450", "218.100", "216.200",
                        "0.10", "", "-", "carry unwind idea"])
    tl.log_open()
    # CLOSE: position id (default offered), exit price, balance
    _feed(monkeypatch, ["", "216.450", ""])
    tl.log_close()

    rows = list(csv.DictReader(open(ledger)))
    assert [r["row_type"] for r in rows] == ["OPEN", "CLOSE"]
    o, c = rows
    assert o["position_id"] == c["position_id"] == "GBPJPY-001"
    assert o["open_price"] == "217.45" and o["stop"] == "218.1"
    # SHORT 217.450 → 216.450 with JPY pip 0.01 = +100.0 pips, WIN
    assert c["pips"] == "100.0"
    assert c["outcome"] == "WIN"
    # two-row ledger: the OPEN row was never edited (no close fields on it)
    assert o["close_price"] == "" and o["pips"] == ""
    # position no longer open
    assert tl.open_positions() == []


def test_stack_id_default_offers_most_recent_match(ledger, tmp_path, monkeypatch):
    stack = tmp_path / "pre_trade_journal.csv"
    with open(stack, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["stack_id", "instrument", "direction"])
        w.writeheader()
        w.writerow({"stack_id": "S1_GBP_JPY_LONG", "instrument": "GBP_JPY",
                    "direction": "LONG"})
        w.writerow({"stack_id": "S2_GBP_JPY_LONG", "instrument": "GBP_JPY",
                    "direction": "LONG"})
        w.writerow({"stack_id": "S3_GBP_AUD_LONG", "instrument": "GBP_AUD",
                    "direction": "LONG"})
    monkeypatch.setattr(tl, "_STACK_FILE", str(stack))

    # most recent MATCHING (instrument+direction) = S2, not S3
    assert tl.latest_matching_stack("GBP_JPY", "LONG") == "S2_GBP_JPY_LONG"
    assert tl.latest_matching_stack("GBP_JPY", "SHORT") is None

    # pressing Enter at the stack prompt accepts the offered default
    _feed(monkeypatch, ["GBP_JPY", "LONG", "217.000", "216.500", "",
                        "0.0", "", "", "paper test"])
    tl.log_open()
    row = list(csv.DictReader(open(ledger)))[0]
    assert row["stack_id"] == "S2_GBP_JPY_LONG"


def test_position_ids_increment_per_instrument(ledger, monkeypatch):
    monkeypatch.setattr(tl, "_STACK_FILE", "/nonexistent")
    _feed(monkeypatch, ["GBP_AUD", "LONG", "1.9100", "1.9000", "", "0.0",
                        "", "-", ""])
    tl.log_open()
    _feed(monkeypatch, ["GBP_AUD", "SHORT", "1.9200", "1.9300", "", "0.0",
                        "", "-", ""])
    tl.log_open()
    rows = list(csv.DictReader(open(ledger)))
    assert [r["position_id"] for r in rows] == ["GBPAUD-001", "GBPAUD-002"]
    assert len(tl.open_positions()) == 2


def test_no_receiver_remnants():
    src = open(tl.__file__).read()
    for token in ("trade_receiver", "main.py", "pending_trades",
                  "commission", "swap"):
        assert token not in src, f"remnant found: {token}"
