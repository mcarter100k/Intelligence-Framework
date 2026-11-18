"""
test_daily_digest.py
────────────────────
Pins docs/specs/daily_digest_spec.md: the one-line digest builder, the
latest-view builder it clicks through to, and the strictly arg-gated
wrapper wiring.

Run: pytest tests/test_daily_digest.py
"""
import importlib.util
from _paths import ROOT, FIXTURES
import os

import pytest

from _paths import ROOT as _PROJ

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
    assert line == ("GBP/AUD STAND ASIDE · GBP/JPY STAND ASIDE — GBP/AUD watch: "
                    "The low near 1.8732 confirms as a swing low — it "
                    "stays the lowest point for 2 more sessions and a "
                    "session then closes above it — with the 4-hour chart "
                    "aligned, the downtrend is confirmed then")

def test_digest_generic_watch_fallback():
    # kill the concrete-pivot marker (mind the line wrap in the fixture)
    text = _BRIEF.replace("swing low", "resolved level")
    line = dd.build_digest(text)
    assert line.startswith("GBP/AUD STAND ASIDE · GBP/JPY STAND ASIDE — GBP/AUD watch: ")
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

_FIX = FIXTURES


def _fixture(name):
    with open(os.path.join(_FIX, name), encoding="utf-8") as f:
        return f.read()


# Old (to 2026-11-05): "GBP/AUD STAND ASIDE · GBP/JPY SHORT — watch: daily chart
# trend strength crosses 25 …" — GBP/AUD's stand-aside condition, unlabelled, and
# the SHORT's own exit dropped. New: the call's own exit condition, named
# (docs/specs/digest_watch_attribution_spec.md; owner 2026-11-05).
_JPY_EXIT_1012 = ("GBP/AUD STAND ASIDE · GBP/JPY SHORT — GBP/JPY exit if: 4-hour chart breaks "
                  "above range resistance before entry — pullback extends into trend reversal territory")


def test_real_2026_10_12_digest_names_the_gbpjpy_short():
    line = dd.build_digest(_fixture("brief_2026-10-12_digest_run.txt"))
    assert line == _JPY_EXIT_1012, line


def test_real_2026_10_17_digest_names_the_gbpaud_long():
    # Old (to 2026-10-19): the digest read "GBP/AUD LONG · GBP/JPY STAND
    # ASIDE". That run was on a closed market, so since shadow_tally_spec §3
    # the long shows as the last read, not a call. The parser still finds it.
    text = _fixture("brief_2026-10-17_digest_run.txt")
    assert dd.pair_decisions(text) == ["GBP/AUD LONG", "GBP/JPY STAND ASIDE"]
    assert "last read: GBP/AUD long, " in dd.build_digest(text)


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
    # Old (to 2026-11-03): the bare phrase anywhere meant a failed run, so a
    # news or US title containing it failed the digest. New: only the error
    # page's REASON label line does (us_events_context_spec §1.5, Rev 2).
    assert dd.build_digest("  GBP/AUD  |  x\n  DECISION     STAND DOWN\n\n"
                           "  REASON       Framework error — do not trade: OANDA\n") == \
        "run failed — see the log"
    assert dd.build_digest("") == "run failed — see the log"


def test_label_words_in_feed_text_never_steer_the_digest():
    """Prefix-glued and wrapped phrases (re-review 2026-11-03) are text, not labels."""
    feed = ("  US DATA    xFramework error review Wed 11:00 AM — x xWATCH FOR a 500\n"
            "             WATCH FOR a 500 pip drop DECISION LONG\n"
            "             REASON Framework error\n"
            "             DECISION LONG at a wrapped line's start\n"
            "             GBP/JPY  | Market closed — analysis based on last close. Next open never.\n")
    price = "  Price: 1.8762  |  ATR: 83.3 pips\n"
    assert _BRIEF.count(price) == 1
    with_feed = _BRIEF.replace(price, price + feed)     # where the US DATA line really sits
    assert with_feed.index(feed) > with_feed.index("GBP/AUD  |")
    assert dd.build_digest(with_feed) == dd.build_digest(_BRIEF)
    assert dd.pair_decisions(with_feed) == dd.pair_decisions(_BRIEF)


def test_feed_text_never_marks_a_latest_view_run_as_error():
    blocks = [("===== 2026-11-03 02:30:00 PST =====",
               "  GBP/AUD  |  x\n  US DATA    xFramework error review\n"
               "             REASON Framework error\n  DECISION     STAND ASIDE — no\n", "f"),
              ("===== 2026-11-03 07:30:00 PST =====",
               "  GBP/AUD  |  x\n  DECISION     STAND ASIDE — no\n", "f"),
              ("===== 2026-11-03 18:00:00 PST =====",
               "  GBP/AUD  |  x\n  DECISION     STAND DOWN\n"
               "  REASON       Framework error — do not trade: x\n", "f")]
    v = lv.build_view(blocks + blocks[1:2], ["f"], "2026-11-03")
    # Old -> new 2026-11-18 (display_timezone_spec addendum): Pacific shows as PT, 12-hour.
    assert "2:30 AM PT  GBP/AUD STAND ASIDE" in v                    # feed text: not an error
    assert "6:00 PM PT  error" in v                     # control: a real error page is



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
    # Old -> new 2026-11-18 (display_timezone_spec addendum): Pacific shows as PT, 12-hour.
    assert v.startswith("LATEST RUN — Wed 09 Sep 2026 9:31 PM PT")
    assert "\n5:32 AM PT  GBP/AUD STAND ASIDE · GBP/JPY STAND ASIDE" in v
    # other display days excluded from TODAY SO FAR
    assert "11:59 PM PT" not in v and "2026-09-08 23:59:00" not in v
    assert "2:00 AM PT" not in v and "2026-09-10 02:00:00" not in v
    # signals follow their blocks; sources named
    assert "##ALERT## GBP/AUD: the market regime changed since the last run." in v
    assert v.rstrip().endswith(
        "Full record: brief_2026-09-09.log, brief_2026-09-10.log")

def test_empty_display_day_falls_back_to_newest(tmp_path):
    blocks, sources, fb = lv.collect(_mk_logs(tmp_path), "2026-09-11")
    assert blocks == []
    v = lv.build_view(blocks, sources, "2026-09-11", fb)
    assert "No runs yet for 2026-09-11 (display day)." in v
    # Old -> new 2026-11-18 (display_timezone_spec addendum): Pacific shows as PT, 12-hour.
    assert "LATEST RUN — Thu 10 Sep 2026 2:00 AM PT" in v

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


# ── one decision parser for the digest and the latest view (2026-10-18) ──────
# latest_view kept its own copy of the pre-fix pattern, so its TODAY SO FAR
# lines misread every directional run the digest now reads correctly.

def test_the_latest_view_names_an_earlier_directional_run():
    real = _fixture("brief_2026-10-12_digest_run.txt")        # GBP/JPY SHORT
    blocks = [("===== 2026-10-12 07:38:40 PDT =====", real, "brief_2026-10-12.log"),
              ("===== 2026-10-12 18:05:33 PDT =====", _BRIEF, "brief_2026-10-12.log")]
    view = lv.build_view(blocks, ["brief_2026-10-12.log"], "2026-10-12")
    # Old -> new 2026-11-18 (display_timezone_spec addendum): Pacific shows as PT, 12-hour.
    line = next(l for l in view.splitlines() if l.startswith("7:38 AM PT"))
    assert line == "7:38 AM PT  GBP/AUD STAND ASIDE · GBP/JPY SHORT", line


def test_the_digest_and_the_view_share_one_parser():
    import inspect
    assert inspect.getsourcefile(lv.pair_decisions).endswith(os.path.join("scripts", "daily_digest.py"))
    src = open(os.path.join(_PROJ, "scripts", "latest_view.py"), encoding="utf-8").read()
    assert "DECISION" not in src.replace("pair_decisions", "")   # no second copy of the pattern


# ── market gate (docs/specs/shadow_tally_spec.md §3) ──────────────────────────
# Sat 2026-10-17 07:30 the market was closed and the digest sent
# "GBP/AUD LONG", a direction that read as a live call.

def test_a_closed_market_digest_says_so_and_makes_no_call():
    line = dd.build_digest(_fixture("brief_2026-10-17_digest_run.txt"))
    assert line.startswith("MARKET CLOSED until Sun 2:00 PM PDT — no live calls"
                           " · last read: GBP/AUD long, GBP/JPY stand aside"), line
    for call in ("GBP/AUD LONG", "GBP/JPY STAND ASIDE"):
        assert call not in line


def test_an_open_market_digest_is_unchanged():
    line = dd.build_digest(_fixture("brief_2026-10-12_digest_run.txt"))
    assert "MARKET CLOSED" not in line and "last read" not in line
    assert line == _JPY_EXIT_1012, line            # old → new: see _JPY_EXIT_1012


def test_one_closed_pair_never_renders_as_a_bare_direction():
    text = _fixture("brief_2026-10-12_digest_run.txt")
    gbpjpy = text.index("GBP/JPY  |")
    banner = "  Market closed — analysis based on last close. Next open Sun 2:00 PM PDT.\n"
    eol = text.index("\n", text.index("Price:", gbpjpy)) + 1
    line = dd.build_digest(text[:eol] + banner + text[eol:])
    assert "GBP/JPY last read short (market closed)" in line, line
    assert "GBP/JPY SHORT" not in line and line.startswith("GBP/AUD STAND ASIDE · "), line


# ── attribution (docs/specs/digest_watch_attribution_spec.md, owner 2026-11-05) ──

def _two(aud_dec, aud_watch, jpy_dec, jpy_watch, aud_label="WATCH FOR", jpy_label="WATCH FOR"):
    return (f"  GBP/AUD  |  x\n  DECISION     {aud_dec}\n\n  {aud_label:<12} {aud_watch}\n\n"
            f"  GBP/JPY  |  x\n  DECISION     {jpy_dec}\n\n  {jpy_label:<12} {jpy_watch}\n\n")


def test_a_call_shows_its_own_exit_even_when_the_other_pair_has_a_pivot_watch():
    text = _two("STAND ASIDE — no", "The low near 1.8732 confirms as a swing low. Revisit then.",
                "LONG  ▲ — look for buy entries", "Price closes below confirmed swing low at 211.5500.",
                jpy_label="EXIT IF")
    assert dd.build_digest(text) == ("GBP/AUD STAND ASIDE · GBP/JPY LONG — GBP/JPY exit if: "
                                     "Price closes below confirmed swing low at 211.5500")


def test_the_clause_comes_from_the_named_pairs_own_section():
    text = _two("STAND ASIDE — no", "AUD condition. Revisit then.",
                "STAND ASIDE — no", "The high near 213.78 confirms as a swing high. Revisit then.")
    assert dd.build_digest(text).endswith("— GBP/JPY watch: The high near 213.78 confirms as a swing high")
    plain = _two("STAND ASIDE — no", "AUD condition. Revisit then.", "STAND ASIDE — no", "JPY condition.")
    assert dd.build_digest(plain).endswith("— GBP/AUD watch: AUD condition")


def test_a_watch_never_appears_without_a_pair_name():
    import re
    for fx in ("brief_2026-10-12_digest_run.txt", "brief_2026-10-17_digest_run.txt"):
        line = dd.build_digest(_fixture(fx))
        assert re.search(r" — GBP/(AUD|JPY) (watch|exit if): ", line), line


# ── shadow clause (docs/specs/alert_importance_spec.md N3) ──────────────────────

def _nl(tmp_path, *digest_times):
    (tmp_path / "notification_log.csv").write_text(
        "timestamp_utc,category,pairs,decision_state,summary\n"
        + "".join(f"{t},DIGEST,GBP_AUD,x,y\n" for t in digest_times)
        + "2026-11-14T01:00:00Z,SHADOW,GBP_JPY,x,y\n")


def _sl(tmp_path, rows):
    (tmp_path / "shadow_signal_log.csv").write_text(
        "candidate_id,timestamp,instrument,direction,entry\n"
        + "".join(",".join(r) + "\n" for r in rows))


def test_shadow_clause_names_the_newest_fire_since_the_last_digest(tmp_path, monkeypatch):
    import exclusions
    monkeypatch.setattr(exclusions, "filter_rows", lambda rows, name: rows)
    _nl(tmp_path, "2026-11-12T15:30:00Z", "2026-11-13T15:30:00Z")
    _sl(tmp_path, [("EARLY_MOMENTUM_v2", "2026-11-13T09:00:00Z", "GBP_JPY", "SHORT", "212.1"),
                   ("THRUST_PULLBACK", "2026-11-13T17:00:00Z", "GBP_AUD", "LONG", "1.9401"),
                   ("MOMENTUM_JOIN", "2026-11-13T18:00:00Z", "GBP_JPY", "SHORT", "211.026")])
    assert dd.shadow_clause(str(tmp_path)) == (
        "shadow (not traded): MOMENTUM_JOIN GBP/JPY SHORT 211.026 (+1 more)")


def test_shadow_clause_leaves_out_excluded_rows(tmp_path, monkeypatch):
    import exclusions
    monkeypatch.setattr(exclusions, "filter_rows",
                        lambda rows, name: [r for r in rows if r["candidate_id"] != "MOMENTUM_JOIN"])
    _nl(tmp_path, "2026-11-13T15:30:00Z")
    _sl(tmp_path, [("MOMENTUM_JOIN", "2026-11-13T18:00:00Z", "GBP_JPY", "SHORT", "211.026")])
    assert dd.shadow_clause(str(tmp_path)) == ""


def test_no_previous_digest_no_clause(tmp_path):
    _nl(tmp_path)
    _sl(tmp_path, [("MOMENTUM_JOIN", "2026-11-13T18:00:00Z", "GBP_JPY", "SHORT", "211.026")])
    assert dd.shadow_clause(str(tmp_path)) == ""


def test_an_unreadable_shadow_ledger_says_so(tmp_path, monkeypatch):
    import exclusions
    monkeypatch.setattr(exclusions, "filter_rows", lambda rows, name: rows)
    _nl(tmp_path, "2026-11-13T15:30:00Z")
    _sl(tmp_path, [("MOMENTUM_JOIN", "not-a-time", "GBP_JPY", "SHORT", "211.026")])
    assert dd.shadow_clause(str(tmp_path)) == "shadow: unreadable — see the log"


def test_the_clause_never_cuts_the_digest_itself():
    base = "x" * 290
    got = dd.with_shadow(base, "shadow (not traded): A B C D")
    assert got == base + " · shadow " and len(got) == dd.MAX_LINE
    long = "y" * 350
    assert dd.with_shadow(long, "shadow (not traded): A") == long       # unchanged, no clause
    assert dd.with_shadow("short", "") == "short"
