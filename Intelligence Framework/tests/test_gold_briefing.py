"""
test_gold_briefing.py
─────────────────────
The gold BRIEFING (docs/specs/configuration_detector_spec.md §14, §14.1,
§14.2): the market gate, the next-briefing time, every line of the render
(price and staleness, levels, releases, clock, volatility, history, fixed
sentences), the language rules (§8, §16, the display floor), a render sweep
that each changing line follows its input, and, through the real wrapper
under /bin/bash, whether it reaches the owner (AGENTS rule 12): open or
closed, muted or not, a good run or a failed one.

Run: pytest tests/test_gold_briefing.py
"""
import os
import re
import sys
import textwrap
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from _paths import ROOT
from test_brief_display import BANNED, BANNED_RAW
from test_gold_levels import synthetic
from test_owner_clock import CLOCK_24

import gold_briefing as B
import gold_levels as G

PT = ZoneInfo("America/Los_Angeles")
UTC = timezone.utc


def pt(*a):
    return datetime(*a, tzinfo=PT).astimezone(UTC)


@pytest.fixture(autouse=True)
def _zone(monkeypatch):
    monkeypatch.delenv("DISPLAY_TZ", raising=False)


@pytest.fixture(scope="module")
def bars():
    return synthetic(hours=2600)


@pytest.fixture(scope="module")
def base(bars):
    """A render moment 1h 45m after the last synthetic hour opened."""
    last = bars["H1"]["t"][-1]
    now = last + timedelta(minutes=105)
    lv = G.levels_now(bars, now)
    return {"now": now, "levels": lv, "price": bars["H1"]["C"][-1]}


def cal(*rows):
    return [(t, cur, ev, imp) for t, cur, ev, imp in rows], ""


def render(bars, base, **kw):
    args = dict(now=base["now"], bars=bars, price=base["price"], price_time=base["now"] - timedelta(minutes=5),
                cal=cal((base["now"] + timedelta(days=3), "USD", "far", "High")), history_rows=[],
                levels=base["levels"])
    args.update(kw)
    return B.render(**args)


# ── the gate and the next briefing ──────────────────────────────────────────

@pytest.mark.parametrize("when,open_", [
    (pt(2026, 11, 19, 3, 45), True),     # Thursday
    (pt(2026, 11, 23, 3, 45), True),     # Monday
    (pt(2026, 11, 21, 3, 45), False),    # Saturday
    (pt(2026, 11, 22, 3, 45), False),    # Sunday morning, before the 2 PM PT open
    (pt(2026, 11, 22, 15, 5), True),     # Sunday after the open
    (pt(2026, 11, 20, 14, 30), False),   # Friday after the close
    (pt(2026, 11, 19, 14, 30), False),   # gold's daily break, 5-6 PM New York
    (pt(2026, 11, 19, 13, 59), True),
    (pt(2026, 11, 19, 15, 0), True),
    (pt(2026, 12, 25, 3, 45), False),    # Christmas
])
def test_market_gate(when, open_):
    assert B.market_open(when) is open_


@pytest.mark.parametrize("now,expect", [
    (pt(2026, 11, 19, 3, 45), pt(2026, 11, 20, 3, 45)),
    (pt(2026, 11, 20, 3, 45), pt(2026, 11, 23, 3, 45)),      # Friday -> Monday
    (pt(2026, 12, 24, 3, 45), pt(2026, 12, 28, 3, 45)),      # over Christmas and the weekend
])
def test_next_briefing(now, expect):
    assert B.next_briefing(now) == expect


# ── the render ──────────────────────────────────────────────────────────────

def test_fixed_and_window_sentences_always_present(bars, base):
    text, _ = render(bars, base)
    for s in B.FIXED_SENTENCES + B.WINDOW_SENTENCES:
        assert s in text


def test_price_line_and_staleness(bars, base):
    now = base["now"]
    fresh, s1 = render(bars, base, price_time=now - timedelta(minutes=30))
    stale, s2 = render(bars, base, price_time=now - timedelta(minutes=31))
    assert "may not be trading" not in fresh and "(stale)" not in s1
    assert "That price is 0h 31m old: gold may not be trading." in stale and "(stale)" in s2
    assert f"Price: {B.money(base['price'])}, the close of the 15-minute bar ending" in fresh


def test_nearest_levels_both_sides_and_none(bars, base):
    atr = base["levels"][0]
    lv = [("D1", "D150", 3100.0), ("PDAY", "PDL60", 2990.0), ("H4", "H4600", 3150.0),
          ("PWEEK", "PWL(2026, 30)", 2900.0), ("RANGE", "RH3060.00000", 3060.0)]
    text, summary = render(bars, base, price=3000.0, levels=(atr, lv))
    assert f"  Above: $3,060.00, the hourly range's high (the range on the hourly chart now), $60.00 = {60 / atr:.2f} ATR away." in text
    assert "  Below: $2,990.00, the prior session's low (the session that opened" in text
    assert f"above $3,060.00 +$60.00 ({60 / atr:.2f} ATR) · below $2,990.00 -$10.00 ({10 / atr:.2f} ATR)" in summary
    none_text, none_sum = render(bars, base, price=3500.0, levels=(atr, lv))
    assert "  Above: none among the qualifying levels." in none_text and "above none" in none_sum


@pytest.mark.parametrize("kind,lid,words", [
    ("D1", "D150", "a daily swing (the daily swing of the session that opened"),
    ("H4", "H4600", "a 4-hour swing (the 4-hour swing of the bar that opened"),
    ("PDAY", "PDH60", "the prior session's high (the session that opened"),
    ("PWEEK", "PWH(2026, 46)", "the prior week's high (the trading week of Mon 09 Nov)"),
    ("RANGE", "RL2900.00000", "the hourly range's low (the range on the hourly chart now)"),
])
def test_every_level_type_reads_in_plain_words(bars, base, kind, lid, words):
    text, _ = render(bars, base, price=1.0, levels=(50.0, [(kind, lid, 2900.0)]))
    assert words in text, text
    assert not re.search(r"\b(?:D1|H4|PDH|PDL|PWH|PWL|RH|RL)\d", text)


def test_releases_window_marks_and_bounds(bars, base):
    d = base["now"].astimezone(PT).date() + timedelta(days=1)
    now = datetime(d.year, d.month, d.day, 3, 45, tzinfo=PT).astimezone(UTC)     # the scheduled time
    assert B.market_open(now)
    until = B.next_briefing(now)
    n = now.astimezone(PT)
    inside = datetime(n.year, n.month, n.day, 5, 30, tzinfo=PT).astimezone(UTC)
    if inside <= now:
        inside += timedelta(days=1)
    assert now < inside < until                                    # a 5:30 AM PT release in the window
    rows = cal((now + timedelta(minutes=10), "USD", "Early", "High"),
               (inside, "USD", "CPI m/m", "High"),
               (now + timedelta(minutes=20), "USD", "Low one", "Low"),
               (now + timedelta(minutes=30), "EUR", "Euro one", "High"),
               (until, "USD", "At the next briefing", "High"),
               (until + timedelta(days=2), "USD", "Later", "High"))
    text, summary = render(bars, base, now=now, price_time=now - timedelta(minutes=5), cal=rows)
    assert "Early" in text and "Low one" not in text and "Euro one" not in text
    assert "At the next briefing" not in text                      # the window is [now, next)
    marked = [l for l in text.splitlines() if "inside gold's 4–8 AM PT window" in l]
    assert len(marked) == 1 and "CPI m/m" in marked[0]
    assert "last entry" not in text
    assert summary.endswith(f"2 US releases before the next briefing, first {B.to_display(now + timedelta(minutes=10), 'time')}")


def test_calendar_that_ends_early_is_said_never_zero(bars, base):
    now = base["now"]
    text, summary = render(bars, base, cal=cal((now - timedelta(hours=30), "USD", "Old", "High")))
    assert "  none in the stored calendar." in text
    assert "The stored calendar's last entry is" in text and "anything after it is not known yet" in text
    assert "0 US releases before the next briefing; the calendar ends" in summary and "later ones not known" in summary


def test_missing_calendar_is_unknown(bars, base, tmp_path):
    rows, problem = B.read_calendar(str(tmp_path / "absent.csv"))
    assert rows is None and "could not be read" in problem
    text, summary = render(bars, base, cal=(rows, problem))
    assert "US releases: unknown, because the news calendar could not be read" in text
    assert "US releases unknown" in summary and "0 US" not in summary


def test_history_not_live_until_a_row_exists(bars, base, tmp_path):
    path = tmp_path / "notification_log.csv"
    path.write_text("timestamp_utc,category,pairs,decision_state,summary\n"
                    "2026-11-01T00:00:00Z,DIGEST,,,d\n2026-11-01T00:00:00Z,BREAKING,,,x\n")
    assert B.alert_rows(str(path)) == []
    text, _ = render(bars, base, history_rows=B.alert_rows(str(path)))
    assert "Alert history, last 7 days: " + B.HISTORY_NOT_LIVE in text
    for cat in ("ARRIVAL", "LEVEL BREAK"):
        path.write_text("timestamp_utc,category,pairs,decision_state,summary\n"
                        f"2026-11-19T12:00:00Z,{cat},XAU_USD,,x\n")
        rows = B.alert_rows(str(path))
        assert len(rows) == 1
        marked, _ = render(bars, base, history_rows=rows)
        assert B.HISTORY_NOT_BUILT in marked and B.HISTORY_NOT_LIVE not in marked
    assert B.alert_rows(str(tmp_path / "absent.csv")) == []


def test_volatility_line_pinned():
    long_ = synthetic(hours=7700, seed=3)["D"]
    assert len(long_["t"]) > 265
    line = B.volatility(long_, long_["t"][-1] + timedelta(hours=30))
    assert re.fullmatch(r"Volatility: the 14-day average daily range is \d+\.\d\d% of price, above \d+% of the last "
                        r"250 days; the (low|middle|high) third by R50's cut points \(1\.206% and 1\.480%\)\.", line), line


def test_volatility_needs_enough_history(bars):
    short = {k: v[-100:] for k, v in bars["D"].items()}
    assert "not enough daily history" in B.volatility(short, bars["H1"]["t"][-1])


# ── language (§8, §16, the display floor) ───────────────────────────────────

WORDS = re.compile(r"\b(?:long|short|buy|sell|go long|go short|entry|target|probability|chance|likely to "
                   r"(?:hold|break)|buy area|sell area|zone of interest|opportunity|setup|look for|bounce|"
                   r"reject|rejection|fade|support|resistance)\b", re.I)


def _texts(bars, base):
    now = base["now"]
    out = []
    for h in range(0, 24, 3):
        t = now + timedelta(hours=h)
        out += list(render(bars, base, now=t, price_time=t - timedelta(minutes=50 * (h % 2))))
    out += list(render(bars, base, history_rows=[{"category": "ARRIVAL"}]))
    out += list(render(bars, base, cal=(None, "the news calendar is empty")))
    return out


def test_no_banned_words_jargon_or_identifiers(bars, base):
    for text in _texts(bars, base):
        body = text.replace("is likely available, not which way it goes", "")   # §16's own sentence, verbatim
        assert not WORDS.search(body), WORDS.search(body).group()
        assert not BANNED.search(text), BANNED.search(text).group()
        assert not BANNED_RAW.search(text), BANNED_RAW.search(text).group()


def test_no_24_hour_clock(bars, base):
    for text in _texts(bars, base):
        assert not CLOCK_24.findall(text), CLOCK_24.findall(text)


# ── render sweep: each changing line follows its input ──────────────────────

def _line(text, start):
    return [l for l in text.splitlines() if l.startswith(start)]


def test_sweep_each_line_follows_its_input(bars, base):
    now = base["now"]
    hours = [render(bars, base, now=now + timedelta(hours=h), price_time=now + timedelta(hours=h, minutes=-5))
             for h in range(24)]
    assert len({_line(t, "GOLD BRIEFING")[0] for t, _ in hours}) == 24
    assert len({_line(t, "Price:")[0] for t, _ in hours}) == 24
    assert len({_line(t, "Clock:")[0] for t, _ in hours}) > 3
    prices = [render(bars, base, price=base["price"] + d) for d in (-3, -1, 1, 3)]
    for start in ("Price:", "  Above:", "  Below:"):
        assert len({_line(t, start)[0] for t, _ in prices}) == 4, start
    assert len({s for _, s in prices}) == 4
    atr, lv = base["levels"]
    scaled = [render(bars, base, levels=(atr * f, lv)) for f in (0.8, 1.0, 1.2)]
    assert len({_line(t, "ATR here")[0] for t, _ in scaled}) == 3
    evs = [render(bars, base, cal=cal((now + timedelta(hours=h), "USD", f"Ev{h}", "High"))) for h in (1, 2, 3)]
    assert len({t for t, _ in evs}) == 3 and len({s for _, s in evs}) == 3


# ── main: failures are failures ─────────────────────────────────────────────

def test_main_closed_market_exits_3(capsys):
    assert B.main([], now=pt(2026, 11, 21, 3, 45)) == 3
    assert "gold market closed" in capsys.readouterr().out


def test_main_failed_fetch_exits_2(monkeypatch, capsys):
    import oanda_feed as F
    monkeypatch.setattr(F, "get_daily_bars", lambda *a, **k: None)
    monkeypatch.setattr(F, "last_error", lambda: "timeout")
    assert B.main([], now=pt(2026, 11, 19, 3, 45)) == 2
    assert capsys.readouterr().out.startswith("BRIEFING FAILED: no D bars for gold (timeout)")


def test_main_render_crash_exits_2(monkeypatch, capsys, bars):
    import oanda_feed as F
    import pandas as pd

    def frame(s):
        return pd.DataFrame({"Open": s["C"], "High": s["H"], "Low": s["L"], "Close": s["C"]},
                            index=pd.DatetimeIndex(s["t"]))
    for name, key in (("get_daily_bars", "D"), ("get_h4_bars", "H4"), ("get_hourly_bars", "H1"),
                      ("get_m15_bars", "H1")):
        monkeypatch.setattr(F, name, lambda *a, _k=key, **k: frame(bars[_k]))
    monkeypatch.setattr(B, "render", lambda *a, **k: 1 / 0)
    assert B.main([], now=pt(2026, 11, 19, 3, 45)) == 2
    assert capsys.readouterr().out.startswith("BRIEFING FAILED: ZeroDivisionError")


def test_main_renders_and_writes_the_summary(monkeypatch, capsys, bars, tmp_path):
    import oanda_feed as F
    import pandas as pd

    def frame(s):
        return pd.DataFrame({"Open": s["C"], "High": s["H"], "Low": s["L"], "Close": s["C"]},
                            index=pd.DatetimeIndex(s["t"]))
    for name, key in (("get_daily_bars", "D"), ("get_h4_bars", "H4"), ("get_hourly_bars", "H1"),
                      ("get_m15_bars", "H1")):
        monkeypatch.setattr(F, name, lambda *a, _k=key, **k: frame(bars[_k]))
    now = bars["H1"]["t"][-1] + timedelta(minutes=105)
    out = tmp_path / "s.txt"
    assert B.main(["--summary-out", str(out)], now=now) == 0
    text = capsys.readouterr().out
    assert text.startswith("GOLD BRIEFING — ") and B.FIXED_SENTENCES[1] in text
    assert out.read_text().startswith("Gold $")


# ── should it reach the owner (AGENTS rule 12), through the real wrapper ────

def _stub(proj, rc, out, summary=""):
    body = f"""
        import sys
        args = sys.argv[1:]
        if {summary!r} and "--summary-out" in args:
            open(args[args.index("--summary-out") + 1], "w").write({summary!r} + "\\n")
        print({out!r})
        sys.exit({rc})
    """
    (proj / "gold_briefing.py").write_text(textwrap.dedent(body))


@pytest.mark.parametrize("muted", [False, True])
def test_a_good_briefing_reaches_the_owner_muted_or_not(tmp_path, muted):
    from test_wrapper_behavior import _project, _run, _log, _notes
    proj = _project(tmp_path)
    if muted:
        (proj / "ALERTS_MUTED").write_text("")
    _stub(proj, 0, "GOLD BRIEFING — text", "Gold $3,550.22 at 3:45 AM PT · above none")
    _run(tmp_path, proj, "scheduled_briefing.sh")
    notes = _notes(tmp_path)
    assert "Gold $3,550.22 at 3:45 AM PT" in notes and "BRIEFING" in notes
    log = _log(proj, "briefing")
    assert "GOLD BRIEFING — text" in log and "exit 0" in log
    assert ("SENT WHILE MUTED (exempt category) BRIEFING" in log) is muted
    ledger = (proj / "notification_log.csv").read_text()
    assert ",BRIEFING,XAU_USD," in ledger


def test_a_closed_market_sends_nothing(tmp_path):
    from test_wrapper_behavior import _project, _run, _log, _notes
    proj = _project(tmp_path)
    _stub(proj, 3, "gold market closed at Sat: no BRIEFING")
    _run(tmp_path, proj, "scheduled_briefing.sh")
    assert _notes(tmp_path) == ""
    assert "gold market closed" in _log(proj, "briefing")


@pytest.mark.parametrize("rc,out,why", [
    (2, "BRIEFING FAILED: no D bars for gold (timeout)", "BRIEFING FAILED: no D bars for gold (timeout)"),
    (1, "Traceback (most recent call last):\nZeroDivisionError: boom", "BRIEFING FAILED: exit 1: ZeroDivisionError: boom"),
])
def test_a_failed_briefing_reaches_the_owner_as_a_failure(tmp_path, rc, out, why):
    from test_wrapper_behavior import _project, _run, _notes
    proj = _project(tmp_path)
    (proj / "ALERTS_MUTED").write_text("")
    _stub(proj, rc, out)
    _run(tmp_path, proj, "scheduled_briefing.sh")
    assert why in _notes(tmp_path)


# ── the mute exemption: exactly five, by first word ─────────────────────────

@pytest.mark.parametrize("sub,sent", [
    ("BRIEFING", True), ("ARRIVAL", True), ("RELEASE", True), ("BREAK", True), ("LEVEL BREAK", True),
    ("ALERT", False), ("DIGEST", False), ("HEARTBEAT", False), ("DECISION", False), ("RECOVERED", False),
    ("REVIEW", False), ("BREAKING", False), ("XBRIEFING", False), ("SHADOW", False),
])
def test_mute_exemption_exactly_five(tmp_path, sub, sent):
    import subprocess
    from test_wrapper_behavior import _project, _notes
    proj = _project(tmp_path)
    (proj / "ALERTS_MUTED").write_text("")
    script = f'PROJ="{proj}"; . "{proj}/scripts/notify.sh"; notify "{sub}" "msg" "logs/x.log"'
    env = {"HOME": str(tmp_path / "home"), "PATH": f"{tmp_path / 'bin'}:/usr/bin:/bin"}
    (tmp_path / "home").mkdir(exist_ok=True)
    subprocess.run(["/bin/bash", "-c", script], env=env, check=True, timeout=60)
    assert ("msg" in _notes(tmp_path)) is sent
    log = (proj / "logs" / "x.log").read_text()
    assert ("MUTED (not sent" in log) is (not sent)
