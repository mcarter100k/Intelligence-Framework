"""
test_owner_clock.py
───────────────────
Pins the owner directive of 2026-11-18 (docs/specs/display_timezone_spec.md,
addendum): every time the owner reads is a 12-hour clock with AM/PM and the
"PT" label, never 24-hour. Log records, filenames and data timestamps are
exempt.

The clock sweep renders each surface that shows a time over every hour of a
day. The shown time must change with its input (24 hours, 24 different
renders), and none may be a 24-hour clock. The pattern is tested both ways
first, so a pass means the surfaces are clean, not that the pattern is blind.

Run: pytest tests/test_owner_clock.py
"""
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from _paths import ROOT
from display_time import to_display

for _d in ("scripts", "studies"):                 # latest_view, artifact_freshness, the replay
    if os.path.join(ROOT, _d) not in sys.path:
        sys.path.insert(0, os.path.join(ROOT, _d))

LA = ZoneInfo("America/Los_Angeles")
STYLES = ("full", "time", "day_time", "day_date")

# A clock not followed by AM/PM: "07:30", "18:00 PT", "12:30:06 PST".
CLOCK_24 = re.compile(r"(?<![\d:])(?:[01]?\d|2[0-3]):[0-5]\d(?::[0-5]\d)?(?![\d:])(?!\s?[AP]M\b)")
CLOCK_12 = re.compile(r"\b(?:1[0-2]|[1-9]):[0-5]\d [AP]M PT\b")


def clock_24(text):
    return CLOCK_24.findall(text)


@pytest.fixture(autouse=True)
def _default_zone(monkeypatch):
    monkeypatch.delenv("DISPLAY_TZ", raising=False)


# ── the pattern can see ──────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "07:30", "18:00 PT", "Sun 11-15 18:00 PT", "===== heartbeat 2026-11-15 12:30:06 PST =====",
    "newest 2026-11-19 00:30", "first: GBP_AUD 2026-11-17T15:30Z", "at 9:05 then", "23:59"])
def test_pattern_catches_a_24_hour_clock(text):
    assert clock_24(text), text


@pytest.mark.parametrize("text", [
    "3:45 AM PT", "6:00 PM PT", "11:30 PM PT", "12:00 AM PT", "Thu 12 Nov 6:00 AM PT",
    "in 15h 00m", "$3,870.32", "0.10 ATR", "2026-11-18", "1339 passed"])
def test_pattern_passes_a_12_hour_clock_and_non_clocks(text):
    assert not clock_24(text), text


# ── the helper, every hour of a winter and a summer day ─────────────────────

@pytest.mark.parametrize("day", [(2026, 1, 15), (2026, 7, 15)])
def test_helper_every_hour_every_style(day):
    times = []
    for h in range(24):
        dt = datetime(*day, h, 7, tzinfo=LA)
        for style in STYLES:
            s = to_display(dt, style=style)
            assert not clock_24(s), s
            assert CLOCK_12.search(s) and s.endswith(("AM PT", "PM PT")), s
        times.append(to_display(dt, style="time"))
    assert len(set(times)) == 24                     # the shown time follows the input
    assert times[0] == "12:07 AM PT"
    assert times[1] == "1:07 AM PT"
    assert times[12] == "12:07 PM PT"
    assert times[13] == "1:07 PM PT"
    assert times[23] == "11:07 PM PT"


def test_day_date_style_pinned():
    assert to_display(datetime(2026, 11, 12, 14, 0, tzinfo=timezone.utc),
                      style="day_date") == "Thu 12 Nov 6:00 AM PT"


def test_another_zone_keeps_its_abbreviation_by_date(monkeypatch):
    monkeypatch.setenv("DISPLAY_TZ", "America/New_York")
    assert to_display(datetime(2026, 1, 15, 17, 7, tzinfo=timezone.utc),
                      style="time") == "12:07 PM EST"
    assert to_display(datetime(2026, 7, 15, 17, 7, tzinfo=timezone.utc),
                      style="time") == "1:07 PM EDT"


# ── the clock sweep: every surface that shows a time ────────────────────────

def _hours(day=(2026, 11, 4)):
    base = datetime(*day, tzinfo=LA)
    return [(base + timedelta(hours=h)).astimezone(timezone.utc) for h in range(24)]


def _swept(render):
    shown = [render(t) for t in _hours()]
    for s in shown:
        assert not clock_24(s), s
        assert CLOCK_12.search(s), s
    assert len(set(shown)) == 24, shown              # changes with its input
    return shown


def test_sweep_news_gate_stand_aside_reason():
    from no_trade_filter import apply_filter

    def render(t):
        regime = {"regime_d1": "TRENDING_UP", "regime_h4": "TRENDING_UP",
                  "adx_h4": 28.0, "atr_vs_avg": 1.0, "atr_compression": False,
                  "timeframe_conflict": False, "conflict_type": "",
                  "structure": "UPTREND", "weekly_context": "ESTABLISHED_UPTREND",
                  "lt_trend": "UPTREND", "st_trend": "UPTREND",
                  "execution_mode": "CONTINUATION", "size_mult": 1.0,
                  "confidence": "HIGH",
                  "news_gate": {"active": True, "gating": True, "event": "UK GDP",
                                "currency": "GBP", "minutes_until": 90,
                                "event_time_utc": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                "note": ""}}
        return apply_filter(regime).reason
    _swept(render)


def test_sweep_setup_check_clock_line():
    from test_setup_check import _stack, _regime
    _swept(lambda t: _stack(regime=_regime(news_gate={
        "active": True, "gating": True, "event": "UK GDP", "minutes_until": 100,
        "event_time_utc": t.strftime("%Y-%m-%dT%H:%M:%SZ")}))["clock"])


def test_sweep_brief_us_events_line(tmp_path):
    import csv
    import decision_brief as db
    now = datetime(2026, 11, 4, 7, 0, tzinfo=timezone.utc)    # Tue 11:00 PM PT

    def render(t):
        path = tmp_path / "calendar.csv"
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["time", "currency", "event", "actual", "forecast", "previous", "impact"])
            w.writerow([(now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M"), "GBP", "own", "", "", "", "High"])
            w.writerow([t.strftime("%Y-%m-%d %H:%M"), "USD", "CPI m/m", "", "", "", "High"])
        return db._us_events_line(now=now, calendar_path=str(path))
    _swept(render)


def test_market_closed_note():
    from regime_detection import _market_status
    note = _market_status(_now=datetime(2026, 11, 14, 23, 0, tzinfo=timezone.utc))["note"]
    assert note.endswith("Next open Sun 2:00 PM PT.") and not clock_24(note), note


def test_sweep_freshness_stale_line(tmp_path):
    import artifact_freshness as af

    def render(t):
        epoch = t.timestamp()
        with open(tmp_path / "regime_classification_log.csv", "w") as f:
            f.write("timestamp,instrument,stand_down,logic_version\n"
                    f"{t:%Y-%m-%dT%H:%M:%SZ},GBP_JPY,False,p5-2026-09-30\n")
        with open(tmp_path / "trade_signal_log.csv", "w") as f:
            f.write("signal_id,timestamp,instrument\n")
        line = af.agreement_lines(now=epoch + 3600, proj=str(tmp_path))[0]
        assert line.startswith("STALE:"), line
        return line
    _swept(render)


def test_sweep_latest_view():
    import latest_view as v

    def render(t):
        loc = t.astimezone(LA)
        hdr = f"===== {loc:%Y-%m-%d %H:%M:%S} {loc:%Z} ====="
        view = v.build_view([(hdr, f"{hdr}\nbody\n", "brief_x.log")], ["brief_x.log"],
                            f"{loc:%Y-%m-%d}")
        assert "=====" not in view, view                 # the log header is not repeated
        return view
    shown = _swept(render)
    assert shown[13].startswith("LATEST RUN — Wed 04 Nov 2026 1:00 PM PT\n"), shown[13]


def test_latest_view_today_so_far_lines():
    import latest_view as v
    blocks = [("===== 2026-11-17 02:33:55 PST =====",
               "===== 2026-11-17 02:33:55 PST =====\nx\n", "b.log"),
              ("===== 2026-11-17 13:30:05 PST =====",
               "===== 2026-11-17 13:30:05 PST =====\ny\n", "b.log")]
    view = v.build_view(blocks, ["b.log"], "2026-11-17")
    assert "\n2:33 AM PT  " in view and not clock_24(view), view


def test_sweep_gold_alert_replay_renderer():
    import ccd1_arrival_lastweek as R
    shown = _swept(R.pt)
    assert shown[18] == "Wed 04 Nov 6:00 PM PT"


# ── the heartbeat, end to end through the real wrapper ──────────────────────

def test_heartbeat_reads_12_hour_pacific(tmp_path):
    from test_wrapper_behavior import _heartbeat_project, _run, _log, _notes
    proj = _heartbeat_project(tmp_path)
    (proj / "calendar.csv").write_text(
        "time,currency,event,actual,forecast,previous,impact\n"
        "2026-11-19 00:30,USD,X,,,,High\n")
    _run(tmp_path, proj, "weekly_heartbeat.sh")
    log = _log(proj, "heartbeat")
    header = log.splitlines()[0]
    assert re.fullmatch(r"===== heartbeat \w{3} \d{2} \w{3} \d{4} "
                        r"(?:1[0-2]|[1-9]):[0-5]\d [AP]M PT =====", header), header
    assert "newest Wed 18 Nov 2026 4:30 PM PT" in log, log
    assert not clock_24(log), clock_24(log)
    assert not clock_24(_notes(tmp_path))
