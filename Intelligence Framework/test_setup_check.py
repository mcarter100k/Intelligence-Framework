"""
test_setup_check.py

Pins the pre-trade evidence stack (docs/specs/setup_check_spec.md): full stack
renders on a mocked regime; the against-framework flag fires; stale storylines
warn; R math pinned; the soft gate logs blanks; banned-token rules hold.
No live-core behavioral changes (rest of the suite proves that).

Run: pytest test_setup_check.py
"""
import csv
import re
from datetime import datetime, timezone

import pytest

import setup_check as sc

BANNED = re.compile(r'\bADX\b|HH/HL|LH/LL|\bpivot\b|ATR ratio')


class _Entry:
    """Minimal stand-in for EntryBrief."""
    def __init__(self, **kw):
        self.h1_confirmed = kw.get("h1_confirmed", False)
        self.h1_structure = kw.get("h1_structure", "TRANSITIONAL")
        self.h1_entry_level = kw.get("h1_entry_level", 0.0)
        self.engulfing_detected = kw.get("engulfing_detected", False)
        self.near_key_level = kw.get("near_key_level", False)


def _regime(**over):
    base = {
        "instrument": "GBP_JPY", "current_price": 217.00, "atr": 1.00,
        "atr_pips": 100.0, "atr_vs_avg": 1.0,
        "regime_d1": "TRENDING_UP", "regime_h4": "TRENDING_UP",
        "adx": 28.0, "adx_h4": 27.0, "structure": "UPTREND",
        "weekly_context": "ESTABLISHED_UPTREND", "lt_trend": "UPTREND",
        "latest_sl": 216.20, "latest_sh": 218.30, "range_position": 0.5,
        "news_gate": {"active": True, "gating": False, "note": ""},
    }
    base.update(over)
    return base


def _decision(direction="LONG", grade="A"):
    return {"direction": direction, "grade": grade, "conviction": 75,
            "size_mult": 1.0, "reason": "", "source": "official_filter_path"}


def _storylines(views=None, stale=False, available=True, intervention=False):
    return {"available": available, "stale": stale,
            "age_days": 10 if stale else 0,
            "views": views or {}, "intervention_watch": intervention}


def _stack(**kw):
    args = dict(instrument="GBP_JPY", direction="LONG", target=None,
                regime=_regime(), entry=_Entry(), storylines=_storylines(),
                delta=None, decision=_decision())
    args.update(kw)
    return sc.build_stack(**args)


# ── Full render + banned tokens ────────────────────────────────────────────────

def test_full_stack_renders_six_lines_clean():
    stack = _stack()
    out = sc.render(stack)
    for label in ("1 BIAS", "2 REGIME", "3 PLAY", "4 CLOCK", "5 FUEL", "6 RISK"):
        assert label in out
    assert BANNED.search(out) is None, f"banned token in: {out}"


# ── Against-framework flag (information, never a block) ────────────────────────

def test_stand_aside_flag_fires():
    stack = _stack(decision=_decision(direction="NO TRADE", grade="C"))
    assert stack["against_framework"] is True
    assert "against its read" in stack["regime"]


def test_direction_mismatch_flags_too():
    stack = _stack(decision=_decision(direction="SHORT"))
    assert stack["against_framework"] is True


def test_aligned_direction_no_flag():
    stack = _stack(decision=_decision(direction="LONG"))
    assert stack["against_framework"] is False
    assert "AGAINST" not in stack["regime"]


# ── FUEL: storylines checked, never generated ──────────────────────────────────

def test_stale_storylines_warns():
    stack = _stack(storylines=_storylines(stale=True))
    assert stack["fuel_marker"] == "stale"
    assert "out of date" in stack["fuel"]


def test_fuel_agrees_and_conflicts():
    agree = _stack(storylines=_storylines(
        views={"GBP": "bullish", "JPY": "bearish"}))
    assert agree["fuel_marker"] == "agrees"
    conflict = _stack(storylines=_storylines(
        views={"GBP": "bearish", "JPY": "bearish"}))
    assert conflict["fuel_marker"] == "conflict"
    assert "GBP bearish" in conflict["fuel"]


def test_missing_storylines_is_blank_not_block():
    stack = _stack(storylines=_storylines(available=False))
    assert stack["fuel_marker"] == "blank"


# ── CLOCK: intervention watch (JPY only, from the storylines marker) ───────────

def test_jpy_intervention_flag():
    stack = _stack(storylines=_storylines(intervention=True))
    assert "INTERVENTION WATCH" in stack["clock"]


# ── RISK: pinned math (trade_management wired) ─────────────────────────────────

def test_risk_math_pinned():
    # LONG @ 217.00, H1 swing stop 216.50 → 50 pips; ATR 1.00 → 0.5x (no breach)
    # target 218.50 → reward 150 / risk 50 = 3.0R
    stack = _stack(target=218.50,
                   entry=_Entry(h1_confirmed=True, h1_entry_level=216.50))
    assert stack["stop_price"] == pytest.approx(216.50)
    assert stack["stop_pips"] == pytest.approx(50.0)
    assert stack["stop_atr_multiple"] == pytest.approx(0.5)
    assert stack["breach_max_stop"] is False
    assert stack["r_to_target"] == pytest.approx(3.0)
    assert "3.0 times what you risk" in stack["risk"]


def test_risk_breach_flag_pinned():
    # stop 2.0 ATR away (217.00 → 215.00 = 200 pips, ATR 1.00) → breach of 1.5x
    stack = _stack(entry=_Entry(h1_confirmed=True, h1_entry_level=215.00))
    assert stack["stop_atr_multiple"] == pytest.approx(2.0)
    assert stack["breach_max_stop"] is True
    assert "Size down" in stack["risk"]


def test_risk_no_structure_asks_for_manual_stop():
    stack = _stack(regime=_regime(latest_sl=None),
                   entry=_Entry(h1_entry_level=0.0))
    assert "define your stop by hand" in stack["risk"]


# ── Soft gate: always logs, blanks flagged, never blocked ──────────────────────

def test_soft_gate_logs_blanks(tmp_path):
    stack = _stack(storylines=_storylines(available=False))
    stack["play_marker"] = "blank"
    path = str(tmp_path / "pre_trade_journal.csv")
    sc.append_journal(stack, path=path)
    sc.append_journal(stack, path=path)          # append-only: two rows stay
    rows = list(csv.DictReader(open(path)))
    assert len(rows) == 2
    assert rows[0]["play_marker"] == "blank"
    assert rows[0]["fuel_marker"] == "blank"
    assert rows[0]["against_framework"] == "False"
    assert rows[0]["stack_id"].endswith("_GBP_JPY_LONG")


# ── storylines parser contract (inline fixture — the repo's storylines.md is
#    LIVING USER DATA and must never be asserted against by tests) ─────────────

_TEMPLATE = """# Storylines — updated: {date}

GBP: bullish — rates story
AUD: bearish — CPI crater
JPY: neutral — managed market

JPY INTERVENTION-WATCH: price in historical MoF response zone
"""


def test_template_convention_parses(tmp_path):
    from datetime import datetime, timezone
    p = tmp_path / "storylines.md"
    p.write_text(_TEMPLATE.format(
        date=datetime.now(timezone.utc).strftime("%Y-%m-%d")))
    st = sc.parse_storylines(path=str(p))
    assert st["available"] is True
    assert st["stale"] is False
    assert st["views"] == {"GBP": "bullish", "AUD": "bearish", "JPY": "neutral"}
    assert st["intervention_watch"] is True      # uncommented marker detected


def test_undated_or_freeform_file_is_treated_stale(tmp_path):
    # A file without the 'updated: YYYY-MM-DD' header (e.g. a free-form weekly
    # narrative) is available but STALE-by-convention: FUEL will warn rather
    # than silently claim fundamental support.
    p = tmp_path / "storylines.md"
    p.write_text("# storylines.md — week of 2026-08-03 (approved 2026-08-03)\n"
                 "## GBP — narrative only\n")
    st = sc.parse_storylines(path=str(p))
    assert st["available"] is True
    assert st["stale"] is True
    assert st["views"] == {}
