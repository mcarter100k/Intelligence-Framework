"""
test_us_events_context.py — US events in the brief as context only
(docs/specs/us_events_context_spec.md). The invariants in §2:

  I1  check_news_gate is identical with and without USD rows (both pairs, a
      sweep of times across a feed week, active and stale), so no decision,
      REASON or apply_filter result can change.
  I2  the frozen shadow news_window stamp (pre_release) is part of I1.
  I1b (Rev 1) a USD row can never fail the gated fetch, and USD rows never
      extend the calendar past the own rows' feed week.
  I3  (Rev 1) the US line can never trigger a notification. I3b, the title
      allow-list, is here; I3a, the real wrapper over unsanitized text, is in
      test_wrapper_behavior.py. Neither layer relies on the other.
  I4  the rendered line passes the banned-token floor.
  I5  "none" renders only from a calendar shown to carry USD rows.
"""
import csv
import json
import os
import random
import re
from datetime import datetime, timedelta, timezone

import pytest

import calendar_fetch
import decision_brief as db
from _paths import ROOT
from news_gate import check_news_gate, covered_through, us_event_context
from test_brief_display import _assert_clean

# Wed 2026-11-04 12:00 UTC; its ForexFactory week ends Sat 2026-11-07 23:59 ET.
NOW = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
HDR = ["time", "currency", "event", "actual", "forecast", "previous", "impact"]


def _write(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HDR)
        for dt, ccy, name, impact in rows:
            w.writerow([dt.strftime("%Y-%m-%d %H:%M"), ccy, name, "", "", "", impact])
    return str(path)


# ── calendar_fetch keeps USD, still requires an own-currency row ─────────────

def _feed_event(hours, country, impact="High", title="X"):
    dt = NOW + timedelta(hours=hours)
    return {"title": title, "country": country, "impact": impact,
            "date": dt.strftime("%Y-%m-%dT%H:%M:%S+00:00"), "forecast": "", "previous": ""}


def test_fetch_keeps_high_impact_usd_and_drops_low(tmp_path):
    p = tmp_path / "calendar.csv"
    feed = json.dumps([_feed_event(5, "GBP", title="UK CPI y/y"),
                       _feed_event(6, "USD", title="Non-Farm Employment Change"),
                       _feed_event(7, "USD", impact="Medium", title="Jobless Claims"),
                       _feed_event(8, "CNY", title="Caixin PMI")])
    assert calendar_fetch.fetch_calendar(calendar_path=str(p), now=NOW, fetcher=lambda: feed) is True
    rows = list(csv.DictReader(open(p)))
    assert [(r["currency"], r["event"]) for r in rows] == [
        ("GBP", "UK CPI y/y"), ("USD", "Non-Farm Employment Change")]


def test_fetch_message_counts_own_and_us_events_separately(tmp_path, capsys):
    p = tmp_path / "calendar.csv"
    feed = json.dumps([_feed_event(5, "GBP"), _feed_event(6, "AUD"), _feed_event(7, "USD")])
    calendar_fetch.fetch_calendar(calendar_path=str(p), now=NOW, fetcher=lambda: feed)
    assert "2 high-impact GBP/AUD/JPY events and 1 US events (context only)" in capsys.readouterr().out


def test_fetch_rejects_a_usd_only_feed_and_keeps_the_old_file(tmp_path, capsys):
    p = tmp_path / "calendar.csv"
    p.write_text("time,currency,event,actual,forecast,previous,impact\n"
                 "2026-11-03 09:30,GBP,Old Row,,,,High\n")
    before = p.read_text()
    feed = json.dumps([_feed_event(6, "USD", title="FOMC Statement")])
    assert calendar_fetch.fetch_calendar(calendar_path=str(p), now=NOW, fetcher=lambda: feed) is False
    assert p.read_text() == before


# ── I1b (Rev 1): a USD row never costs the gated calendar ───────────────────

_BAD_USD = [
    {"title": "Tentative", "country": "USD", "impact": "High", "date": "Tentative"},
    {"title": "No date", "country": "USD", "impact": "High"},
    {"title": "No offset", "country": "USD", "impact": "High", "date": "2026-11-04T19:00:00"},
    {"title": 123, "country": "USD", "impact": "High", "date": "2026-11-04T19:00:00+00:00"},
    {"title": "Odd forecast", "country": "USD", "impact": "High",
     "date": "2026-11-04T19:00:00+00:00", "forecast": 4.2},
]


@pytest.mark.parametrize("bad", _BAD_USD, ids=[b["title"] if isinstance(b["title"], str)
                                                else "non-text title" for b in _BAD_USD])
def test_a_malformed_usd_row_is_skipped_not_fatal(tmp_path, capsys, bad):
    own = [_feed_event(5, "GBP", title="UK CPI y/y"), _feed_event(30, "JPY", title="BoJ")]
    clean, dirty = tmp_path / "clean.csv", tmp_path / "dirty.csv"
    assert calendar_fetch.fetch_calendar(calendar_path=str(clean), now=NOW,
                                         fetcher=lambda: json.dumps(own)) is True
    assert calendar_fetch.fetch_calendar(calendar_path=str(dirty), now=NOW,
                                         fetcher=lambda: json.dumps(own + [bad])) is True
    assert dirty.read_text() == clean.read_text()      # the gated rows, byte for byte
    assert "skipped 1 US row(s)" in capsys.readouterr().out


def test_the_skip_note_carries_no_feed_markup(tmp_path, capsys):
    bad = {"title": "##ALERT## FED DECISION | GBP/JPY", "country": "USD", "impact": "High",
           "date": "Tentative \u2014 ##ALERT##"}
    assert calendar_fetch.fetch_calendar(calendar_path=str(tmp_path / "c.csv"), now=NOW,
                                         fetcher=lambda: json.dumps([_feed_event(5, "GBP"), bad])) is True
    out = capsys.readouterr().out
    assert "skipped 1 US row(s)" in out
    assert not re.search(r"[#|/\u2014]", out.split("skipped", 1)[1]), out


def test_a_malformed_own_currency_row_still_rejects_the_feed(tmp_path):
    p = tmp_path / "calendar.csv"
    p.write_text("time,currency,event,actual,forecast,previous,impact\n"
                 "2026-11-03 09:30,GBP,Old Row,,,,High\n")
    before = p.read_text()
    feed = json.dumps([_feed_event(5, "GBP"),
                       {"title": "Bad", "country": "AUD", "impact": "High", "date": "Tentative"}])
    assert calendar_fetch.fetch_calendar(calendar_path=str(p), now=NOW, fetcher=lambda: feed) is False
    assert p.read_text() == before                      # fail-closed, unchanged


def test_a_usd_row_after_the_feed_week_is_dropped(tmp_path, capsys):
    # own rows end Wed; the week ends Sat 23:59 ET = Sun 04:59 UTC. A Sat USD
    # row is kept, a Sun 06:00 UTC one (next feed week) is dropped.
    p = tmp_path / "calendar.csv"
    feed = json.dumps([_feed_event(2, "GBP"), _feed_event(80, "USD", title="Sat row"),
                       _feed_event(90, "USD", title="Next week")])
    assert calendar_fetch.fetch_calendar(calendar_path=str(p), now=NOW, fetcher=lambda: feed) is True
    rows = list(csv.DictReader(open(p)))
    assert [r["event"] for r in rows if r["currency"] == "USD"] == ["Sat row"]
    assert "after this calendar's week" in capsys.readouterr().out
    # and the gate's coverage is the own rows' week, not the next one
    own_end = covered_through(datetime.strptime(rows[0]["time"], "%Y-%m-%d %H:%M"))
    assert us_event_context(now=NOW, calendar_path=str(p))["covered_through"] == own_end


# ── I1 / I2: the gate is blind to USD rows ──────────────────────────────────

def _random_calendar(r, base):
    own = [(base + timedelta(minutes=r.randrange(-3 * 1440, 4 * 1440)),
            r.choice(["GBP", "AUD", "JPY"]), f"own {k}", r.choice(["High", "High", "Medium"]))
           for k in range(r.randrange(1, 8))]
    usd = [(base + timedelta(minutes=r.randrange(-3 * 1440, 4 * 1440)),
            "USD", f"US {k}", r.choice(["High", "Medium"])) for k in range(r.randrange(1, 8))]
    return own, usd


def _confined(own, usd):
    as_row = lambda t: {"time": t[0].strftime("%Y-%m-%d %H:%M"), "currency": t[1],
                        "event": t[2], "impact": t[3]}
    kept = calendar_fetch._confine_context_rows([as_row(t) for t in own + usd])
    names = {r["event"] for r in kept}
    return [u for u in usd if u[2] in names]


def test_gate_output_identical_with_and_without_usd_rows(tmp_path):
    r = random.Random(20261101)
    base = NOW.replace(tzinfo=None)
    compared = active = stale = gating = 0
    for k in range(60):
        own, usd = _random_calendar(r, base)
        # USD rows go through the fetch's own confinement function (spec
        # §1.1), not a test-side filter: a defect INSIDE _confine_context_rows
        # fails here. Removing its call from fetch_calendar is caught by
        # test_a_usd_row_after_the_feed_week_is_dropped instead (corrected Rev 2).
        usd = _confined(own, usd)
        a = _write(tmp_path / f"a{k}.csv", own)
        b = _write(tmp_path / f"b{k}.csv", own + usd)
        for step in range(0, 7 * 1440, 47):            # every 47 min across the week
            t = (base - timedelta(days=3) + timedelta(minutes=step)).replace(tzinfo=timezone.utc)
            for inst in ("GBP_AUD", "GBP_JPY"):
                ga = check_news_gate(inst, now=t, calendar_path=a)
                gb = check_news_gate(inst, now=t, calendar_path=b)
                assert ga == gb, (inst, t, ga, gb)
                compared += 1
                active += ga["active"]
                stale += not ga["active"]
                gating += ga["gating"]
    # the sweep exercised every branch, so equality is not vacuous
    assert compared > 10000 and active and stale and gating


# ── us_event_context statuses (I5) ──────────────────────────────────────────

def test_status_ok_lists_only_high_usd_in_the_next_24h(tmp_path):
    p = _write(tmp_path / "c.csv", [
        (datetime(2026, 11, 4, 9, 30), "GBP", "UK CPI", "High"),
        (datetime(2026, 11, 4, 19, 0), "USD", "FOMC Statement", "High"),
        (datetime(2026, 11, 4, 13, 30), "USD", "Jobless Claims", "Medium"),
        (datetime(2026, 11, 5, 11, 59), "USD", "ISM Services PMI", "High"),
        (datetime(2026, 11, 5, 12, 1), "USD", "Too Late", "High"),
        (datetime(2026, 11, 4, 11, 0), "USD", "Already Out", "High")])
    ctx = us_event_context(now=NOW, calendar_path=p)
    assert ctx["status"] == "ok"
    assert [n for _, n in ctx["events"]] == ["FOMC Statement", "ISM Services PMI"]


@pytest.mark.parametrize("rows,status", [
    ([(datetime(2026, 11, 4, 9, 30), "GBP", "UK CPI", "High")], "no_us_rows"),
    ([(datetime(2026, 10, 27, 9, 30), "GBP", "UK CPI", "High"),
      (datetime(2026, 10, 28, 9, 30), "USD", "US CPI", "High")], "stale"),
])
def test_status_no_us_rows_and_stale(tmp_path, rows, status):
    assert us_event_context(now=NOW, calendar_path=_write(tmp_path / "c.csv", rows))["status"] == status


def test_status_missing(tmp_path):
    assert us_event_context(now=NOW, calendar_path=str(tmp_path / "nope.csv"))["status"] == "missing"


# ── rendering (I4, I5) ──────────────────────────────────────────────────────

@pytest.fixture
def pacific(monkeypatch):
    monkeypatch.setenv("DISPLAY_TZ", "America/Los_Angeles")


def test_line_with_events_is_plain_and_says_information_only(tmp_path, pacific):
    p = _write(tmp_path / "c.csv", [(datetime(2026, 11, 4, 9, 30), "GBP", "UK CPI", "High"),
                                    (datetime(2026, 11, 4, 19, 0), "USD", "FOMC Statement", "High")])
    line = db._us_events_line(now=NOW, calendar_path=p)
    # Old -> new 2026-11-18 (display_timezone_spec addendum): Pacific shows as PT, 12-hour.
    assert line == ("FOMC Statement Wed 11:00 AM PT — for information; "
                    "the framework does not stand aside for US releases.")
    _assert_clean(line)


@pytest.mark.parametrize("rows,expected", [
    ([(datetime(2026, 11, 4, 9, 30), "GBP", "UK CPI", "High"),
      (datetime(2026, 11, 3, 13, 30), "USD", "Earlier", "High")], "none in the next 24 hours."),
    ([(datetime(2026, 11, 4, 9, 30), "GBP", "UK CPI", "High")],
     "not checked — the saved news calendar holds no US events (it refreshes when over a day old)."),
    ([(datetime(2026, 10, 27, 9, 30), "GBP", "UK CPI", "High")], "not checked — news calendar out of date."),
    (None, "not checked — news calendar missing."),
])
def test_line_for_each_status(tmp_path, pacific, rows, expected):
    path = _write(tmp_path / "c.csv", rows) if rows is not None else str(tmp_path / "absent.csv")
    line = db._us_events_line(now=NOW, calendar_path=path)
    assert line == expected
    _assert_clean(line)


def test_none_names_the_coverage_end_when_the_week_ends_within_24h(tmp_path, pacific):
    # Saturday 2026-11-07 12:00 UTC: the feed week ends 23:59 ET that night (< 24h away)
    sat = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    p = _write(tmp_path / "c.csv", [(datetime(2026, 11, 6, 13, 30), "USD", "NFP", "High"),
                                    (datetime(2026, 11, 6, 9, 30), "GBP", "UK GDP", "High")])
    line = db._us_events_line(now=sat, calendar_path=p)
    assert line == ("none before Sat 8:59 PM PT; later days are not in this "
                    "week's calendar yet.")


# ── grouping and "+N more" (Rev 1) ──────────────────────────────────────────

def test_every_time_slot_keeps_its_time_and_extras_are_counted(tmp_path, pacific):
    nfp, fomc = datetime(2026, 11, 4, 13, 30), datetime(2026, 11, 4, 19, 0)
    rows = [(datetime(2026, 11, 4, 9, 30), "GBP", "UK CPI", "High")]
    rows += [(nfp, "USD", n, "High") for n in ("CPI m/m", "CPI y/y", "Core CPI m/m", "Core CPI y/y")]
    rows += [(fomc, "USD", "FOMC Statement", "High")]
    rows += [(datetime(2026, 11, 4, 20 + k, 0), "USD", f"Speech {k}", "High") for k in range(4)]
    line = db._us_events_line(now=NOW, calendar_path=_write(tmp_path / "c.csv", rows))
    # Rev 1 hid the 11:00 FOMC behind "+N more"; every slot now shows its time
    assert line == ("CPI m/m, CPI y/y, Core CPI m/m +1 more Wed 5:30 AM PT · FOMC Statement "
                    "Wed 11:00 AM PT · Speech 0 Wed 12:00 PM PT · Speech 1 Wed 1:00 PM PT · "
                    "+2 later — for information; the framework does not stand aside for US releases.")
    _assert_clean(line)


def test_the_jobs_report_trio_shows_in_full(tmp_path, pacific):
    nfp = datetime(2026, 11, 4, 13, 30)
    p = _write(tmp_path / "c.csv", [(datetime(2026, 11, 4, 9, 30), "GBP", "UK CPI", "High")]
               + [(nfp, "USD", n, "High") for n in ("Average Hourly Earnings m/m",
                  "Non-Farm Employment Change", "Unemployment Rate")])
    assert db._us_events_line(now=NOW, calendar_path=p).startswith(
        "Average Hourly Earnings m/m, Non-Farm Employment Change, Unemployment Rate Wed 5:30 AM PT — ")


# ── I3b: the title allow-list (the wrapper layer is I3a, test_wrapper_behavior) ──

_TRIGGERS = ["DECISION", "ALERT", "SHADOW SIGNALS", "Framework error", "EXIT IF",
             "WATCH FOR", "STAND ASIDE", "STAND DOWN", "REASON", "MOMENTUM_JOIN"]
_CORPUS = ["FED RATE DECISION ##ALERT##", "FED DECI#SION LONG", "AL#ERT", "SHADOW SIGNALS review",
           "FOMC\nSHADOW SIGNALS", "Framework error review", "USD/JPY intervention",
           "GBP/AUD | LONG", "MOMENTUM_JOIN LONG fired", "exit if watch for", "decision long",
           "D\u0415CISION LONG", "STAND ASIDE DECISION", "reason: stand down",
           "Market closed \u2014 analysis based on last close.", "\x00ALERT\x07", "A" * 200,
           # prefix-glued (re-review 2026-11-03: these passed Rev 1's \\b rules)
           "xFramework error review", "aEXIT IF", "xWATCH FOR a 500 pip drop", "9DECISION",
           "FRAMEWORK error", "xSHADOW SIGNALS", "1STAND ASIDE", "zALERTz", "qREASONq"]


def _stand_aside_brief(us_line):
    return db.DecisionBrief(
        instrument="GBP_JPY", timestamp="test", price=210.0, atr_pips=120.0,
        decision="STAND DOWN", reason="Test reason.", conviction=0, grade="C", size_pct=0,
        market_state="Test state.", invalidation="Test watch.", regime_log="test",
        stand_down=True, override_fired=False, execution_mode="", adx_d1=0.0, adx_h4=0.0,
        weekly_context="", error=None, us_events_line=us_line).format()


def _us_block(brief):
    lines = brief.split("\n")
    i = next(k for k, l in enumerate(lines) if l.startswith("  US DATA"))
    j = next(k for k in range(i, len(lines)) if lines[k].startswith("\u2550"))
    return "\n".join(lines[i:j])


def test_no_title_can_carry_a_trigger_at_any_wrap_position(tmp_path, pacific):
    checked = 0
    for title in _CORPUS:
        for pad in range(0, 40):                   # moves the trigger across every wrap point
            raw = ("x" * pad + " " + title).strip()
            p = _write(tmp_path / "c.csv", [(datetime(2026, 11, 4, 9, 30), "GBP", "UK CPI", "High"),
                                            (datetime(2026, 11, 4, 19, 0), "USD", raw, "High")])
            block = _us_block(_stand_aside_brief(db._us_events_line(now=NOW, calendar_path=p)))
            for trig in _TRIGGERS:
                assert trig not in block, (raw, trig, block)
            assert not re.search(r"[#|_]|[A-Z]{3}/[A-Z]{3}", block), (raw, block)
            assert db._us_title(raw).isascii() and len(db._us_title(raw)) <= 63
            checked += 1
    assert checked == len(_CORPUS) * 40


def test_ordinary_titles_survive_the_allow_list():
    for t in ("FOMC Statement", "CPI m/m", "Average Hourly Earnings m/m", "ISM Services PMI",
              "Non-Farm Employment Change", "Core PCE Price Index y/y", "Fed Chair Powell Speaks",
              "S&P Global Services PMI", "Prelim UoM Consumer Sentiment", "Treasury Currency Report"):
        assert db._us_title(t) == t
    assert db._us_title("Pr\u00e9sident Speaks") == "President Speaks"     # transliterated (Rev 2)


def test_line_never_writes_to_stderr(tmp_path, capsys):
    db._us_events_line(now=NOW, calendar_path=str(tmp_path / "missing.csv"))
    db._us_events_line(now=NOW, calendar_path=_write(tmp_path / "c.csv", [
        (datetime(2026, 11, 4, 9, 30), "GBP", "UK CPI", "High"),
        (datetime(2026, 11, 4, 19, 0), "USD", "FOMC", "High")]))
    assert capsys.readouterr().err == ""


def test_brief_places_the_line_below_every_warning_note():
    b = db.DecisionBrief(
        instrument="GBP_AUD", timestamp="t", price=1.9, atr_pips=100.0, decision="STAND DOWN",
        reason="r", conviction=0, grade="C", size_pct=0, market_state="m", invalidation="w",
        regime_log="x", stand_down=True, override_fired=False, execution_mode="", adx_d1=0.0,
        adx_h4=0.0, weekly_context="", error=None, news_note="news calendar stale — event risk unchecked",
        market_open=False, market_note="Market closed — analysis based on last close.",
        price_basis="unknown",
        us_events_line="not checked — news calendar out of date.").format().split("\n")
    us = next(k for k, l in enumerate(b) if l.startswith("  US DATA"))
    for note in ("news calendar stale", "Market closed", "Price source unknown"):
        assert next(k for k, l in enumerate(b) if note in l) < us, note
    after = next(l for l in b[us + 1:] if not l.startswith(" " * 13))
    assert after.startswith("\u2550")                # last item before the header border
