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

  EXIT IF      The low near 1.8732 confirms as a
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

def test_digest_failed_run():
    assert dd.build_digest("... Framework error — do not trade ...") == \
        "run failed — see the log"
    assert dd.build_digest("") == "run failed — see the log"


# ── latest-view builder ────────────────────────────────────────────────────────

_DAY = ("===== 2026-09-09 00:32:26 EDT =====\n"
        "  GBP/AUD  |  x\n  DECISION     STAND ASIDE — no\n"
        "  Framework error — do not trade: OANDA\n\n"
        "===== 2026-09-09 05:32:52 EDT =====\n"
        "  GBP/AUD  |  x\n  DECISION     STAND ASIDE — no\n"
        "  GBP/JPY  |  x\n  DECISION     STAND ASIDE — no\n\n"
        "##ALERT## GBP/AUD: the market regime changed since the last run.\n"
        "===== 2026-09-09 10:30:15 EDT =====\n"
        "  GBP/AUD  |  x\n  DECISION     LONG\n"
        "  GBP/JPY  |  x\n  DECISION     STAND ASIDE — no\n")

def test_view_latest_block_verbatim_and_digest_lines():
    v = lv.build_view(_DAY, "brief_2026-09-09.log")
    assert v.startswith("LATEST RUN — 2026-09-09 10:30:15 EDT")
    assert "DECISION     LONG" in v
    assert "2026-09-09 00:32:26 EDT  error" in v
    assert "2026-09-09 05:32:52 EDT  GBP/AUD STAND ASIDE · GBP/JPY STAND ASIDE" in v
    assert "##ALERT## GBP/AUD: the market regime changed since the last run." in v
    assert v.rstrip().endswith("Full record: brief_2026-09-09.log")

def test_view_empty_log_is_graceful():
    v = lv.build_view("", "brief_x.log")
    assert "No run blocks found" in v


# ── wrapper wiring: digest strictly arg-gated ──────────────────────────────────

def test_wrapper_digest_gated_on_argument():
    with open(os.path.join(_PROJ, "scripts", "scheduled_brief.sh")) as f:
        src = f.read()
    assert '[ "${1:-}" = "digest" ]' in src
    assert 'notify "DIGEST"' in src
    assert src.count('notify "DIGEST"') == 2      # view target + day-log fallback

def test_only_brief_ny_plist_passes_digest():
    ld = os.path.join(_PROJ, "scripts", "launchd")
    for name in os.listdir(ld):
        if not name.endswith(".plist"):
            continue
        with open(os.path.join(ld, name)) as f:
            has = "<string>digest</string>" in f.read()
        assert has == ("brief-ny" in name), name
