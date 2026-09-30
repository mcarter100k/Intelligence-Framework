"""
test_unresolved_direction.py
────────────────────────────
Pins docs/specs/unresolved_direction_polish_spec.md: the TRANSITION_ZONE
subtype and wording, the H4 unconfirmed render, the choppy ban, the DATA
BASIS label (evidence key unchanged), and the regime ledger's additive
subtype column.

Run: pytest test_unresolved_direction.py
"""
import csv

import decision_brief as db
import regime_classifier_logger as rcl
import regime_detection as rd
from test_unconfirmed_trend import _regime


# ── wording: transition zone, both timeframes ──────────────────────────────────

def test_h4_transition_zone_wording():
    ms = db._build_market_state(_regime(regime_h4="VOLATILE",
                                        regime_h4_subtype="TRANSITION_ZONE",
                                        adx_h4=20.0))
    assert ("4-hour chart: no clear direction yet (trend strength 20/100, "
            "transition zone)") in ms

def test_narrative_transition_zone_daily():
    n = db._build_narrative(_regime(adx=20.0,
                                    regime_d1_subtype="TRANSITION_ZONE"),
                            "STAND DOWN")
    assert ("The daily chart has no clear direction yet (trend strength "
            "20/100, transition zone)") in n


# ── H4 unconfirmed render, honest units ────────────────────────────────────────

def test_h4_unconfirmed_renders_hours_not_sessions():
    r = _regime(regime_h4="VOLATILE", regime_h4_subtype="UNCONFIRMED_TREND",
                adx_h4=27.0, h4_change_pips_10=-120.0)
    ms = db._build_market_state(r)
    assert ("4-hour chart: falling — down 120 pips over the last 40 hours "
            "— but the confirmation rule isn't met yet "
            "(trend strength 27/100)") in ms
    n = db._build_narrative(r, "STAND DOWN")
    assert ("The 4-hour chart has been falling — down 120 pips over the "
            "last 40 hours. The engine is waiting for the latest low to "
            "confirm before calling it a trend.") in n

def test_h4_unconfirmed_without_fact_falls_back():
    r = _regime(regime_h4="VOLATILE", regime_h4_subtype="UNCONFIRMED_TREND",
                adx_h4=27.0)
    assert "40 hours" not in db._build_market_state(r)


# ── choppy ban ─────────────────────────────────────────────────────────────────

def test_choppy_gone_from_volatile_vocabulary():
    assert "choppy" not in db._DIR_WORDS["VOLATILE"]

def test_choppy_absent_across_variants():
    variants = [
        _regime(),                                          # unconfirmed d1
        _regime(regime_d1_subtype="TRANSITION_ZONE", adx=20.0),
        _regime(regime_d1_subtype="", d1_change_pips_10=None),  # plain VOLATILE
        _regime(regime_h4="VOLATILE", regime_h4_subtype=""),
    ]
    for r in variants:
        for text in (db._build_market_state(r),
                     db._build_narrative(r, "STAND DOWN")):
            assert "choppy" not in text, text


# ── DATA BASIS: label changes, evidence key does not ───────────────────────────

def test_data_basis_label_for_volatile_bucket(monkeypatch):
    seen = {}
    def fake_acc(instrument=None):
        seen["called"] = True
        return {"VOLATILE": {"n": 3, "accuracy": 0.0, "correct": 0,
                             "flagged": False, "actionable": False}}
    monkeypatch.setattr(db, "get_regime_accuracy", fake_acc)
    out = db._build_regime_log("VOLATILE", "GBP_AUD")
    assert out.startswith("daily unresolved-direction bucket (transition "
                          "zone + unconfirmed trends): 3 outcomes logged")
    assert seen["called"]                       # key VOLATILE still queried

def test_data_basis_other_regimes_unchanged(monkeypatch):
    monkeypatch.setattr(db, "get_regime_accuracy",
                        lambda instrument=None: {"TRENDING_UP": {
                            "n": 3, "accuracy": 1.0, "correct": 3,
                            "flagged": False, "actionable": False}})
    assert db._build_regime_log("TRENDING_UP", "GBP_AUD").startswith(
        "D1 TRENDING_UP: 3 outcomes logged")


# ── regime ledger: 26-column pin, migration, populated subtype ─────────────────

def test_ledger_schema_pinned_at_27():
    # 26 -> 27 on 2026-09-30: price_basis appended (data_at_source_spec P1).
    assert len(rcl.FIELDNAMES) == 27
    assert rcl.FIELDNAMES[-2:] == ["subtype", "price_basis"]

def test_subtype_tag_format():
    assert rcl._subtype_tag({"regime_d1_subtype": "UNCONFIRMED_TREND",
                             "regime_h4_subtype": "TRANSITION_ZONE"}) == \
        "d1=UNCONFIRMED_TREND;h4=TRANSITION_ZONE"
    assert rcl._subtype_tag({"regime_d1_subtype": "",
                             "regime_h4_subtype": "EXHAUSTION"}) == \
        "h4=EXHAUSTION"
    assert rcl._subtype_tag({}) == ""

def test_migration_additive_and_lossless(tmp_path, monkeypatch):
    monkeypatch.setattr(rcl, "LOG_FILE", str(tmp_path / "regime.csv"))
    old_fields = rcl.FIELDNAMES[:-2]        # before subtype AND price_basis
    with open(rcl.LOG_FILE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=old_fields)
        w.writeheader()
        w.writerow({k: ("KEEP" if k == "outcome_detail" else "x")
                    for k in old_fields})
    rcl._write_row({k: "" for k in rcl.FIELDNAMES})   # append migrates first
    with open(rcl.LOG_FILE) as f:
        reader = csv.DictReader(f)
        assert list(reader.fieldnames) == rcl.FIELDNAMES
        rows = list(reader)
    assert rows[0]["outcome_detail"] == "KEEP"        # old values verbatim
    assert rows[0]["subtype"] == ""                   # old rows blank
    assert rows[0]["price_basis"] == ""               # blank = pre-2026-09-30 prior close

def test_new_classification_populates_subtype(tmp_path, monkeypatch):
    monkeypatch.setattr(rcl, "LOG_FILE", str(tmp_path / "regime.csv"))
    regime = {"regime": "VOLATILE", "regime_d1": "VOLATILE",
              "regime_h4": "RANGING",
              "regime_d1_subtype": "UNCONFIRMED_TREND",
              "regime_h4_subtype": "", "current_price": 1.88,
              "adx": 25.0, "adx_h4": 17.0, "atr_vs_avg": 1.0,
              "structure": "TRANSITIONAL", "weekly_context": "X",
              "execution_mode": "STAND_DOWN", "confidence": "NONE",
              "size_mult": 0.0, "timeframe_conflict": False,
              "stand_down": True, "atr_pips": 83.0}
    rcl.log_regime(regime, "GBP_AUD")
    with open(rcl.LOG_FILE) as f:
        row = next(csv.DictReader(f))
    assert row["subtype"] == "d1=UNCONFIRMED_TREND"
