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
    monkeypatch.setattr(oanda_feed, "_breaker_open_until", 0.0)
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
    assert f"credentials rejected (HTTP {code})" in oanda_feed.last_error()


@pytest.mark.parametrize("failure,words", [
    (_Resp(503), "OANDA server error (HTTP 503)"),
    (_Resp(429), "rate limited (HTTP 429)"),
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
    (_Resp(401), "credentials rejected"),
    (_Resp(503), "OANDA server error"),
    (requests.Timeout("t"), "request timed out"),
])
def test_the_trader_sees_the_real_reason_not_not_enough_data(feed, failure, words):
    feed["script"] = [failure]
    r = rd.get_regime("GBP_AUD")
    assert r["error"].startswith("OANDA data unavailable for GBP/AUD: ")
    assert words in r["error"]
    assert "Not enough data" not in r["error"]


def test_genuinely_short_history_still_reads_not_enough_data(feed):
    feed["script"] = [_Resp(200, _CANDLE)]          # 1 bar < 42 required
    r = rd.get_regime("GBP_AUD")
    assert r["error"] == "Not enough data to calculate regime indicators"


# ── code-review findings (visible_failures_spec addendum) ─────────────────────

def test_f2_an_empty_response_records_its_own_cause(feed):
    """An older failure on another fetch must never be reported as the cause."""
    feed["script"] = [requests.Timeout("t")] * 3 + [_Resp(200, {"candles": []})]
    oanda_feed.get_h4_bars("GBPAUD", count=5)
    assert "H4 GBP_AUD" in oanda_feed.last_error()
    assert oanda_feed.get_daily_bars("GBPJPY", count=5) is None
    assert oanda_feed.last_error() == "no candles returned (D GBP_JPY)"


def test_f2_only_incomplete_candles_records_its_own_cause(feed):
    feed["script"] = [_Resp(200, {"candles": [{"complete": False}]})]
    oanda_feed.get_daily_bars("GBPAUD", count=5)
    assert oanda_feed.last_error() == "no complete candles returned (D GBP_AUD)"


def test_f3_the_brief_shows_the_whole_classification(feed):
    import decision_brief as db
    feed["script"] = [_Resp(401)]
    b = db.get_decision_brief("GBP_AUD")
    assert "credentials rejected (HTTP 401)" in b.reason
    assert "wrong environment" in b.reason          # not cut at 60 chars
    assert "unreachable" not in b.reason.split(":", 2)[-1].split("(")[0]


def test_f4_after_one_exhausted_outage_later_fetches_try_once(feed):
    feed["script"] = [requests.Timeout("t")]         # every call times out
    oanda_feed.get_daily_bars("GBPAUD", count=5)
    assert feed["attempts"] == 3                     # first fetch: full retries
    for _ in range(14):
        oanda_feed.get_h4_bars("GBPAUD", count=5)
    assert feed["attempts"] == 3 + 14                # the rest: one attempt each


def test_f4_the_breaker_closes_after_its_window(feed, monkeypatch):
    feed["script"] = [requests.Timeout("t")]
    oanda_feed.get_daily_bars("GBPAUD", count=5)
    monkeypatch.setattr(oanda_feed, "_breaker_open_until", 0.0)   # window over
    oanda_feed.get_daily_bars("GBPAUD", count=5)
    assert feed["attempts"] == 6                     # full retries again


def test_f4_credentials_errors_never_open_the_breaker(feed):
    feed["script"] = [_Resp(401), _Resp(503)]
    oanda_feed.get_daily_bars("GBPAUD", count=5)
    oanda_feed.get_daily_bars("GBPAUD", count=5)
    assert feed["attempts"] == 1 + 3                 # 503 still gets its retries
