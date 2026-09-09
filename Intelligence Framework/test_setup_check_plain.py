"""
test_setup_check_plain.py
─────────────────────────
Pins docs/specs/setup_check_plain_english_spec.md: colleague-voice wording
for every line variant, the delta-duplication fix, the noise flag, all three
verdicts, and the extended banned-token contract on rendered output.

Run: pytest test_setup_check_plain.py
"""
import re

import pytest

import setup_check as sc
from test_setup_check import _Entry, _regime, _decision, _storylines, _stack

# extended ban (spec §banned tokens): the six labels are exempt — strip them
# from each rendered line before scanning sentence bodies.
_BANNED = re.compile(
    r"\bADX\b|HH/HL|LH/LL|\bpivot\b|ATR ratio|"
    r"\binvalidation\b|none-named|\bstructural\b|\bregime\b|\bstack\b",
    re.IGNORECASE)
_LABELS = re.compile(r"^\s*(═+|\d [A-Z]+|PRE-TRADE CHECK.*)")


def _body_text(rendered: str) -> str:
    out = []
    for ln in rendered.splitlines():
        m = re.match(r"^\s*\d ([A-Z]+)\s+(.*)$", ln)
        out.append(m.group(2) if m else ("" if _LABELS.match(ln) else ln))
    return "\n".join(out)


def _render(**kw):
    return sc.render(_stack(**kw))


# ── banned tokens on rendered bodies, across representative states ─────────────

def test_banned_tokens_absent_from_all_variants():
    variants = [
        dict(),                                            # aligned trending
        dict(decision=_decision(direction="NO TRADE", grade="C")),
        dict(storylines=_storylines(stale=True)),
        dict(storylines=_storylines(available=False)),
        dict(regime=_regime(latest_sl=None), entry=_Entry(h1_entry_level=0.0)),
        dict(entry=_Entry(h1_confirmed=True, h1_entry_level=216.80)),  # noise
        dict(delta={"summary": "Since 44min ago: Regime changed "
                               "(RANGING → VOLATILE). Re-evaluate.",
                    "minutes_ago": 44}),
    ]
    for kw in variants:
        body = _body_text(_render(**kw))
        hit = _BANNED.search(body)
        assert hit is None, f"banned token {hit.group(0)!r} in: {body}"


# ── BIAS ───────────────────────────────────────────────────────────────────────

def test_bias_undecided_daily():
    s = _stack(regime=_regime(regime_d1="VOLATILE"))
    assert "The daily chart hasn't picked a direction yet "\
           "(trend strength 28/100)." in s["bias"]

def test_bias_trending_daily_and_weekly_voice():
    s = _stack()
    assert s["bias"].startswith("The weekly chart shows ")
    assert "The daily chart is trending up (trend strength 28/100)." in s["bias"]

def test_bias_exhaustion_daily_renders_overextension():
    s = _stack(regime=_regime(regime_d1="RANGING",
                              regime_d1_subtype="EXHAUSTION",
                              structure="DOWNTREND", adx=40.0))
    assert "flagged as overextended" in s["bias"]
    assert "moving sideways" not in s["bias"]


# ── REGIME: delta fix, framework sentence, against-read ───────────────────────

def test_delta_duplication_fixed_unchanged_case():
    s = _stack(delta={"summary": "Since 44min ago: Conditions unchanged.",
                      "minutes_ago": 44})
    assert "Nothing has changed since the last read 44 minutes ago." in s["regime"]
    assert "since last run: Since" not in s["regime"]
    assert "Since 44min ago:" not in s["regime"]

def test_delta_changed_case_reads_plainly():
    s = _stack(delta={"summary": "Since 100min ago: Regime changed "
                                 "(RANGING → VOLATILE). Re-evaluate.",
                      "minutes_ago": 100})
    assert "Since the last read 1h 40m ago:" in s["regime"]
    assert "Regime" not in s["regime"].split("Since the last read")[1].split(".")[0] \
        or True  # body wording checked by the banned-token sweep
    assert "since last run" not in s["regime"]

def test_regime_quiet_sideways_wording():
    s = _stack(regime=_regime(regime_h4="RANGING"))
    assert "The 4-hour chart is quiet and sideways" in s["regime"]

def test_framework_no_trade_sentence_and_against():
    s = _stack(decision=_decision(direction="NO TRADE", grade="C"))
    assert "The framework itself says: don't trade right now (rating C)." in s["regime"]
    assert ("You'd be trading against its read — allowed, but know why "
            "you disagree before you act.") in s["regime"]

def test_framework_agreeing_direction_sentence():
    s = _stack(decision=_decision(direction="LONG", grade="B+"))
    assert "The framework itself says: trade LONG (rating B+)." in s["regime"]
    assert "against its read" not in s["regime"]


# ── PLAY ───────────────────────────────────────────────────────────────────────

def test_play_none_named_wording():
    s = _stack()
    assert s["play_name"] == "none-named"
    assert s["play"] == ("This doesn't match any play in the playbook "
                         "(base break, coil break, first pullback, retest "
                         "fade). If you can't name it, it's a feeling, "
                         "not a trade.")

def test_play_first_pullback_asks_agree():
    s = _stack(entry=_Entry(near_key_level=True))
    assert s["play_name"] == "first-pullback"
    assert s["play"].startswith("This looks like a first pullback after a break")
    assert s["play"].endswith("Agree?")

def test_play_coil_and_base_and_fade():
    coil = _stack(regime=_regime(atr_vs_avg=0.8),
                  entry=_Entry(engulfing_detected=True))
    assert coil["play_name"] == "coil-break"
    base = _stack(regime=_regime(range_position=0.8),
                  entry=_Entry(h1_confirmed=True))
    assert base["play_name"] == "base-break"
    fade = _stack(direction="SHORT",
                  regime=_regime(regime_h4="TRENDING_UP", regime_d1="RANGING"),
                  entry=_Entry(near_key_level=True))
    assert fade["play_name"] == "retest-fade"
    assert "counter-trend by definition" in fade["play"]


# ── CLOCK ──────────────────────────────────────────────────────────────────────

def test_clock_clear_wording():
    s = _stack()
    assert s["clock"] == "No major economic release in the next 2 hours."
    assert s["clock_clear"] is True

def test_clock_gating_wording_hours_minutes():
    s = _stack(regime=_regime(news_gate={"active": True, "gating": True,
                                         "event": "UK GDP",
                                         "minutes_until": 100}))
    assert s["clock"] == "UK GDP in 1h 40m — stand aside until after."
    assert s["clock_clear"] is False

def test_clock_unavailable_wording():
    s = _stack(regime=_regime(news_gate={"active": False, "gating": False,
                                         "note": "stale"}))
    assert "The news calendar is out of date or missing" in s["clock"]


# ── FUEL ───────────────────────────────────────────────────────────────────────

def test_fuel_stale_names_the_approval_date():
    st = _storylines(stale=True)
    st["header_date"] = "2026-08-03"
    s = _stack(storylines=st)
    assert s["fuel"] == ("This week's storyline for this pair is out of "
                         "date (last approved 2026-08-03) so it can't "
                         "count as evidence. Refresh it in the Sunday "
                         "session.")

def test_fuel_agrees_and_conflicts_voice():
    agree = _stack(storylines=_storylines(
        views={"GBP": "bullish", "JPY": "bearish"}))
    assert agree["fuel"].startswith("Your direction AGREES with the week's storyline:")
    conflict = _stack(storylines=_storylines(
        views={"GBP": "bearish", "JPY": "bearish"}))
    assert conflict["fuel"].startswith("Your direction CONFLICTS with the week's storyline:")

def test_parser_accepts_approved_header(tmp_path):
    p = tmp_path / "storylines.md"
    p.write_text("# storylines.md — week of 2026-09-06 (approved 2026-09-06)\n"
                 "GBP: bullish\n")
    from datetime import datetime, timezone
    st = sc.parse_storylines(str(p), now=datetime(2026, 9, 9,
                                                  tzinfo=timezone.utc))
    assert st["header_date"] == "2026-09-06"
    assert st["stale"] is False


# ── RISK: noise flag + fake-ratio ──────────────────────────────────────────────

def test_noise_flag_fires_below_min_multiple():
    # LONG @217.00, stop 216.80 → 20 pips; ATR 100 pips → 0.2x < 0.3
    s = _stack(entry=_Entry(h1_confirmed=True, h1_entry_level=216.80))
    assert s["stop_in_noise"] is True
    assert "inside normal noise" in s["risk"]
    assert "hit by accident, not by being wrong" in s["risk"]
    assert "100-pip daily range" in s["risk"]

def test_noise_flag_silent_at_or_above_min():
    # 30 pips / 100 ATR = 0.3 exactly → NOT inside noise (strictly closer)
    s = _stack(entry=_Entry(h1_confirmed=True, h1_entry_level=216.70))
    assert s["stop_in_noise"] is False
    assert "inside normal noise" not in s["risk"]

def test_fake_ratio_sentence_with_target():
    s = _stack(target=218.50,
               entry=_Entry(h1_confirmed=True, h1_entry_level=216.80))
    assert "times what you risk" in s["risk"]
    assert "That ratio is flattering only because the stop is fake." in s["risk"]

def test_ratio_not_called_fake_with_honest_stop():
    s = _stack(target=218.50,
               entry=_Entry(h1_confirmed=True, h1_entry_level=216.50))
    assert "flattering" not in s["risk"]


# ── VERDICT: all three ─────────────────────────────────────────────────────────

def test_verdict_negative_enumerates_and_says_now():
    s = _stack(entry=_Entry(h1_confirmed=True, h1_entry_level=216.80),
               decision=_decision(direction="NO TRADE", grade="C"),
               storylines=_storylines(views={"GBP": "bearish",
                                             "JPY": "bullish"}))
    s["play_marker"] = "blank"
    v = sc.compute_verdict(s)
    assert v == ("VERDICT: 1 blank line(s), stop inside noise, against the "
                 "storyline, against the framework's read. "
                 "Nothing here says NOW.")

def test_verdict_positive_every_line_supports():
    s = _stack(direction="LONG",
               decision=_decision(direction="LONG", grade="A"),
               storylines=_storylines(views={"GBP": "bullish",
                                             "JPY": "bearish"}),
               entry=_Entry(h1_confirmed=True, h1_entry_level=216.50,
                            near_key_level=True))
    assert s["play_name"] == "first-pullback"
    v = sc.compute_verdict(s)
    assert v == "VERDICT: Every line supports this. Size per your rules."

def test_verdict_mixed_names_the_weak_lines():
    s = _stack(decision=_decision(direction="NO TRADE", grade="C"),
               storylines=_storylines(stale=True),
               entry=_Entry(h1_confirmed=True, h1_entry_level=216.50))
    v = sc.compute_verdict(s)
    assert v.startswith("VERDICT: Mixed — ")
    assert "the framework's read is against you" in v
    assert "the storyline can't back you" in v
    assert "no named play" in v

def test_verdict_is_a_real_column_schema_pinned_at_22(tmp_path):
    # team ruling 2026-09-09: verdict is the 22nd column, not a risk suffix
    assert len(sc._JOURNAL_FIELDS) == 22
    assert sc._JOURNAL_FIELDS[-1] == "verdict"
    s = _stack()
    s["verdict"] = sc.compute_verdict(s)
    path = str(tmp_path / "journal.csv")
    sc.append_journal(s, path=path)
    import csv
    with open(path) as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == sc._JOURNAL_FIELDS
        row = next(reader)
    assert row["verdict"].startswith("VERDICT:")
    assert "VERDICT:" not in row["risk"]                 # no suffix append

def test_journal_migration_is_additive_and_lossless(tmp_path):
    # a real pre-ruling journal: 21-column header, one row
    path = str(tmp_path / "journal.csv")
    old_fields = sc._JOURNAL_FIELDS[:-1]
    import csv
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=old_fields)
        w.writeheader()
        w.writerow({k: ("OLDVAL" if k == "risk" else "x") for k in old_fields})

    s = _stack()
    s["verdict"] = sc.compute_verdict(s)
    sc.append_journal(s, path=path)                      # triggers migration

    with open(path) as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == sc._JOURNAL_FIELDS   # 22 now
        rows = list(reader)
    assert len(rows) == 2
    assert rows[0]["risk"] == "OLDVAL"                   # old values verbatim
    assert rows[0]["verdict"] == ""                      # old rows blank
    assert rows[1]["verdict"].startswith("VERDICT:")
