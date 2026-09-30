"""
test_oanda_errors.py — an OANDA failure says what happened, and transient
failures retry (docs/specs/visible_failures_spec.md D7).

Before: a revoked key (401), an OANDA outage (503) and a timeout all
returned None after ONE attempt, and the trader read "Not enough data to
calculate regime indicators" for all three.
"""
import pytest
import requests

import oanda_feed
import regime_detection as rd


class _Resp:
    def __init__(self, code, payload=None):
        self.status_code = code
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            e = requests.HTTPError(f"{self.status_code} error")
            e.response = self
            raise e

    def json(self):
        return self._payload


_CANDLE = {"candles": [{"complete": True, "time": "2026-09-28T21:00:00Z",
                        "volume": 1,
                        "mid": {"o": "1.9", "h": "1.91", "l": "1.89", "c": "1.9"}}]}


@pytest.fixture
def feed(monkeypatch):
    """Scripted responses; counts attempts; no real sleeping."""
    monkeypatch.setenv("OANDA_API_KEY", "k")
    monkeypatch.setenv("OANDA_ACCOUNT_ID", "a")
    monkeypatch.setattr(oanda_feed.time, "sleep", lambda s: None)
    state = {"script": [], "attempts": 0}

    def fake_get(*a, **k):
        state["attempts"] += 1
        step = state["script"].pop(0) if state["script"] else state["last"]
        state["last"] = step
        if isinstance(step, Exception):
            raise step
        return step

    monkeypatch.setattr(oanda_feed.requests, "get", fake_get)
    return state


@pytest.mark.parametrize("code", [401, 403])
def test_rejected_credentials_are_named_and_never_retried(feed, code):
    feed["script"] = [_Resp(code)]
    assert oanda_feed.get_daily_bars("GBPAUD", count=5) is None
    assert feed["attempts"] == 1
    assert f"HTTP {code}: OANDA rejected the credentials" in oanda_feed.last_error()


@pytest.mark.parametrize("failure,words", [
    (_Resp(503), "HTTP 503: OANDA server error"),
    (_Resp(429), "HTTP 429: rate limited"),
    (requests.Timeout("t"), "request timed out"),
    (requests.ConnectionError("c"), "connection failed"),
])
def test_transient_failures_retry_twice_then_say_why(feed, failure, words):
    feed["script"] = [failure]
    assert oanda_feed.get_daily_bars("GBPAUD", count=5) is None
    assert feed["attempts"] == 3
    assert words in oanda_feed.last_error()
    assert "3 attempts" in oanda_feed.last_error()


def test_a_transient_failure_then_success_returns_data_and_clears_the_error(feed):
    feed["script"] = [_Resp(503), _Resp(200, _CANDLE)]
    df = oanda_feed.get_daily_bars("GBPAUD", count=5)
    assert df is not None and len(df) == 1
    assert feed["attempts"] == 2
    assert oanda_feed.last_error() is None


def test_missing_credentials_are_named(monkeypatch):
    monkeypatch.delenv("OANDA_API_KEY", raising=False)
    assert oanda_feed.get_daily_bars("GBPAUD", count=5) is None
    assert oanda_feed.last_error().startswith("credentials missing")


@pytest.mark.parametrize("failure,words", [
    (_Resp(401), "rejected the credentials"),
    (_Resp(503), "OANDA server error"),
    (requests.Timeout("t"), "request timed out"),
])
def test_the_trader_sees_the_real_reason_not_not_enough_data(feed, failure, words):
    feed["script"] = [failure]
    r = rd.get_regime("GBP_AUD")
    assert r["error"].startswith("OANDA unreachable for GBP/AUD: ")
    assert words in r["error"]
    assert "Not enough data" not in r["error"]


def test_genuinely_short_history_still_reads_not_enough_data(feed):
    feed["script"] = [_Resp(200, _CANDLE)]          # 1 bar < 42 required
    r = rd.get_regime("GBP_AUD")
    assert r["error"] == "Not enough data to calculate regime indicators"
