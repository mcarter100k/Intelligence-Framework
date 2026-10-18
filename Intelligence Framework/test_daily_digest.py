"""
test_daily_digest.py
────────────────────
Pins docs/specs/daily_digest_spec.md: the one-line digest builder, the
latest-view builder it clicks through to, and the strictly arg-gated
wrapper wiring.

Run: pytest test_daily_digest.py
"""
import importlib.util
import os

import pytest

_PROJ = os.path.dirname(os.path.abspath(__file__))

def _load(name):
    spec = importlib.util.spec_from_file_location(
        name, os.path.join(_PROJ, "scripts", f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

dd = _load("daily_digest")
lv = _load("latest_view")


_BRIEF = """═════════
  GBP/AUD  |  Wed 09 Sep 2026  14:30 UTC
  Price: 1.8762  |  ATR: 83.3 pips
═════════

  DECISION     STAND ASIDE — conditions not right to trade

  WATCH FOR    The low near 1.8732 confirms as a
               swing low — it stays the lowest point
               for 2 more sessions and a session
               then closes above it — with the
               4-hour chart aligned, the downtrend
               is confirmed then. Revisit then.

═════════
  GBP/JPY  |  Wed 09 Sep 2026  14:30 UTC
  Price: 208.51  |  ATR: 156.5 pips
═════════

  DECISION     STAND ASIDE — conditions not right to trade

  EXIT IF      Daily price structure confirms a
               direction. Revisit then.

═════════
"""


# ── digest builder ─────────────────────────────────────────────────────────────

def test_digest_both_pairs_and_concrete_watch():
    line = dd.build_digest(_BRIEF)
    assert line == ("GBP/AUD STAND ASIDE · GBP/JPY STAND ASIDE — watch: "
                    "The low near 1.8732 confirms as a swing low — it "
                    "stays the lowest point for 2 more sessions and a "
                    "session then closes above it — with the 4-hour chart "
                    "aligned, the downtrend is confirmed then")

def test_digest_generic_watch_fallback():
    # kill the concrete-pivot marker (mind the line wrap in the fixture)
    text = _BRIEF.replace("swing low", "resolved level")
    line = dd.build_digest(text)
    assert line.startswith("GBP/AUD STAND ASIDE · GBP/JPY STAND ASIDE — watch: ")
    assert "resolved level" in line

def test_digest_long_short_decisions():
    text = _BRIEF.replace("DECISION     STAND ASIDE — conditions not right to trade",
                          "DECISION     LONG", 1)
    assert dd.build_digest(text).startswith("GBP/AUD LONG · GBP/JPY STAND ASIDE")

# ── directional decisions as the brief REALLY renders them (2026-10-18) ──────
# The test above hand-types "DECISION     LONG". The brief renders
# "LONG  ▲ — …" / "SHORT ▼ — …", and the parser wanted "—" straight after
# the word, so every directional morning digested as "?". The fixtures are
# the real 07:30 digest runs' stdout, copied from the day logs.

_FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_fixtures")


def _fixture(name):
    with open(os.path.join(_FIX, name), encoding="utf-8") as f:
        return f.read()


def test_real_2026_10_12_digest_names_the_gbpjpy_short():
    line = dd.build_digest(_fixture("brief_2026-10-12_digest_run.txt"))
    assert line.startswith("GBP/AUD STAND ASIDE · GBP/JPY SHORT — watch: "), line


def test_real_2026_10_17_digest_names_the_gbpaud_long():
    line = dd.build_digest(_fixture("brief_2026-10-17_digest_run.txt"))
    assert line.startswith("GBP/AUD LONG · GBP/JPY STAND ASIDE — watch: "), line


@pytest.mark.parametrize("decision,shown", [
    ("LONG", "LONG"), ("SHORT", "SHORT"), ("STAND DOWN", "STAND ASIDE")])
def test_the_renderers_exact_decision_line_is_parsed(decision, shown):
    """Rendered by the real DecisionBrief.format, so a glyph or spacing
    change in the brief fails here instead of silently reverting to '?'."""
    import decision_brief as db
    trade = decision != "STAND DOWN"
    text = db.DecisionBrief(
        instrument="GBP_AUD", timestamp="t", price=1.9189, atr_pips=100.9,
        decision=decision, reason="r", conviction=45 if trade else 0,
        grade="B" if trade else "C", size_pct=35 if trade else 0, market_state="m",
        invalidation="i", regime_log="l", stand_down=not trade, override_fired=False,
        execution_mode="X", adx_d1=19.0, adx_h4=33.0, weekly_context="W", error=None,
        entry_line="level 1.9189" if trade else "",
        target_line="set your own" if trade else "").format()
    rendered = {"LONG": "DECISION     LONG  ▲ — look for buy entries",
                "SHORT": "DECISION     SHORT ▼ — look for sell entries",
                "STAND DOWN": "DECISION     STAND ASIDE — conditions not right to trade"}
    assert rendered[decision] in text            # the exact string being parsed
    assert dd.build_digest(text).startswith(f"GBP/AUD {shown}")


def test_an_unrecognised_decision_word_still_shows_a_question_mark():
    text = _BRIEF.replace("DECISION     STAND ASIDE — conditions not right to trade",
                          "DECISION     MAYBE — who knows", 1)
    assert dd.build_digest(text).startswith("GBP/AUD ? · GBP/JPY STAND ASIDE")


def test_digest_failed_run():
    assert dd.build_digest("... Framework error — do not trade ...") == \
        "run failed — see the log"
    assert dd.build_digest("") == "run failed — see the log"


# ── latest-view builder: display-day grouping across files ────────────────────

def _mk_logs(tmp_path):
    d = tmp_path / "logs"
    d.mkdir()
    # display day 2026-09-09 spans two day files (file rolls on another clock)
    (d / "brief_2026-09-09.log").write_text(
        "===== 2026-09-09 05:32:52 PDT =====\n"
        "  GBP/AUD  |  x\n  DECISION     STAND ASIDE — no\n"
        "  GBP/JPY  |  x\n  DECISION     STAND ASIDE — no\n\n"
        "##ALERT## GBP/AUD: the market regime changed since the last run.\n"
        "===== 2026-09-08 23:59:00 PDT =====\n"          # OTHER display day
        "  GBP/AUD  |  x\n  DECISION     LONG\n\n")
    (d / "brief_2026-09-10.log").write_text(
        "===== 2026-09-09 21:31:03 PDT =====\n"          # same display day
        "  GBP/AUD  |  x\n  DECISION     STAND ASIDE — no\n"
        "  GBP/JPY  |  x\n  DECISION     LONG\n\n"
        "===== 2026-09-10 02:00:00 PDT =====\n"          # tomorrow
        "  GBP/AUD  |  x\n  DECISION     SHORT\n\n")
    return str(d)

def test_display_day_groups_across_two_files(tmp_path):
    blocks, sources, fb = lv.collect(_mk_logs(tmp_path), "2026-09-09")
    assert [b[0] for b in blocks] == [
        "===== 2026-09-09 05:32:52 PDT =====",
        "===== 2026-09-09 21:31:03 PDT =====",
    ]
    assert sources == ["brief_2026-09-09.log", "brief_2026-09-10.log"]
    v = lv.build_view(blocks, sources, "2026-09-09", fb)
    assert v.startswith("LATEST RUN — 2026-09-09 21:31:03 PDT")
    assert "2026-09-09 05:32:52 PDT  GBP/AUD STAND ASIDE · GBP/JPY STAND ASIDE" in v
    # other display days excluded from TODAY SO FAR
    assert "2026-09-08 23:59:00" not in v
    assert "2026-09-10 02:00:00" not in v
    # signals follow their blocks; sources named
    assert "##ALERT## GBP/AUD: the market regime changed since the last run." in v
    assert v.rstrip().endswith(
        "Full record: brief_2026-09-09.log, brief_2026-09-10.log")

def test_empty_display_day_falls_back_to_newest(tmp_path):
    blocks, sources, fb = lv.collect(_mk_logs(tmp_path), "2026-09-11")
    assert blocks == []
    v = lv.build_view(blocks, sources, "2026-09-11", fb)
    assert "No runs yet for 2026-09-11 (display day)." in v
    assert "LATEST RUN — 2026-09-10 02:00:00 PDT" in v

def test_no_files_at_all_graceful(tmp_path):
    d = tmp_path / "logs"; d.mkdir()
    blocks, sources, fb = lv.collect(str(d), "2026-09-09")
    v = lv.build_view(blocks, sources, "2026-09-09", fb)
    assert "No run blocks found for 2026-09-09" in v


# ── digest wiring: only the NY plist passes "digest". The wrapper's gating on
#    that argument is EXECUTED in test_wrapper_behavior.py. ──────────────────

def test_only_brief_ny_plist_passes_digest():
    ld = os.path.join(_PROJ, "scripts", "launchd")
    for name in os.listdir(ld):
        if not name.endswith(".plist"):
            continue
        with open(os.path.join(ld, name)) as f:
            has = "<string>digest</string>" in f.read()
        assert has == ("brief-ny" in name), name
