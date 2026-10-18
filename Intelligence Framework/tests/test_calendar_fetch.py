"""
test_calendar_fetch.py

Pins the calendar auto-fetcher (docs/specs/calendar_autofetch_spec.md):
happy path writes the news_gate schema; malformed feed preserves the old
file; empty feed is rejected; network failure exits 0 with a loud note.

Run: pytest tests/test_calendar_fetch.py
"""
import csv
import json
from datetime import datetime, timedelta, timezone

import pytest

import calendar_fetch
from calendar_fetch import fetch_calendar

NOW = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
_OLD_CONTENT = ("time,currency,event,actual,forecast,previous,impact\n"
                "2026-04-01 01:30,GBP,Old Manual Row,,51.4,51.4,High\n")


def _feed(events):
    return json.dumps(events)


def _event(hours_ahead, country="GBP", impact="High", title="UK CPI y/y"):
    dt = (NOW + timedelta(hours=hours_ahead)).astimezone(timezone.utc)
    return {"title": title, "country": country,
            "date": dt.strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "impact": impact, "forecast": "2.9%", "previous": "3.0%"}


def _old_file(tmp_path):
    p = tmp_path / "calendar.csv"
    p.write_text(_OLD_CONTENT)
    return p


def test_happy_path_writes_news_gate_schema(tmp_path):
    p = _old_file(tmp_path)
    feed = _feed([
        _event(20, "GBP"),
        _event(40, "AUD", title="RBA Rate Statement"),
        _event(60, "JPY", title="BOJ Policy Rate"),
        _event(30, "USD", title="FOMC"),          # filtered: not our currency
        _event(25, "GBP", impact="Low"),          # filtered: not high impact
        _event(24 * 20, "GBP"),                   # filtered: outside 8-day window
    ])
    ok = fetch_calendar(calendar_path=str(p), now=NOW, fetcher=lambda: feed)
    assert ok is True
    rows = list(csv.DictReader(open(p)))
    assert [r["currency"] for r in rows] == ["GBP", "AUD", "JPY"]   # sorted by time
    assert rows[0]["event"] == "UK CPI y/y"
    assert rows[0]["impact"] == "High"
    assert rows[0]["actual"] == ""                                   # feed has no actuals
    # schema is exactly what news_gate reads
    assert list(rows[0].keys()) == ["time", "currency", "event", "actual",
                                    "forecast", "previous", "impact"]
    # and news_gate itself accepts the file
    from news_gate import check_news_gate
    r = check_news_gate("GBP_AUD", now=NOW, calendar_path=str(p))
    assert r["active"] is True


def test_malformed_feed_preserves_old_file(tmp_path, capsys):
    p = _old_file(tmp_path)
    ok = fetch_calendar(calendar_path=str(p), now=NOW,
                        fetcher=lambda: "<html>not json</html>")
    assert ok is False
    assert p.read_text() == _OLD_CONTENT                 # untouched
    assert "REJECTED" in capsys.readouterr().out


def test_bad_event_shape_preserves_old_file(tmp_path, capsys):
    p = _old_file(tmp_path)
    feed = _feed([{"title": "X", "country": "GBP", "date": "not-a-date",
                   "impact": "High"}])
    ok = fetch_calendar(calendar_path=str(p), now=NOW, fetcher=lambda: feed)
    assert ok is False
    assert p.read_text() == _OLD_CONTENT
    assert "malformed" in capsys.readouterr().out.lower()


def test_empty_feed_rejected(tmp_path, capsys):
    p = _old_file(tmp_path)
    ok = fetch_calendar(calendar_path=str(p), now=NOW, fetcher=lambda: "[]")
    assert ok is False
    assert p.read_text() == _OLD_CONTENT
    assert "0 high-impact" in capsys.readouterr().out


def test_network_failure_exit0_and_loud_note(tmp_path, capsys, monkeypatch):
    p = _old_file(tmp_path)

    def _boom(*a, **k):
        raise ConnectionError("dns down")

    monkeypatch.setattr(calendar_fetch, "_fetch_raw", _boom)
    monkeypatch.setattr(calendar_fetch, "_CALENDAR_FILE", str(p))
    rc = calendar_fetch.main()
    assert rc == 0                                        # exit-0 discipline
    assert p.read_text() == _OLD_CONTENT
    out = capsys.readouterr().out
    assert "CALENDAR FETCH FAILED" in out
    assert "stale-calendar note" in out
