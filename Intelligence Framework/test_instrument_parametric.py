"""
test_instrument_parametric.py

Locks in Phase 1.3: signal builders compute on the TRADED instrument, never a
hardcoded GBP/AUD. Guards against the GBP/JPY contamination where 73% of the
bias was measured on AUD data.

Run: pytest test_instrument_parametric.py
"""
import pandas as pd
import pytest


# ── cross_market: GBP/AUD-specific model must not contaminate other pairs ───────

def test_cross_market_not_modelled_for_non_aud():
    from cross_market import get_cross_market
    for inst in ("GBP_JPY", "EUR_USD", "GBP_USD"):
        x = get_cross_market(inst)
        assert x["overall_bias"] == "NEUTRAL", inst
        assert x.get("not_modelled") is True, inst
        assert x["error"] is None, inst  # intentional neutral, not a failure


def test_cross_market_default_is_gbp_aud():
    # Default arg preserves the original GBP/AUD behaviour (modelled path).
    from cross_market import get_cross_market
    # non-AUD short-circuits before any network; GBP_AUD would hit the network,
    # so we only assert the non-modelled branch here and the signature default.
    import inspect
    assert inspect.signature(get_cross_market).parameters["instrument"].default == "GBP_AUD"


# ── currency_strength: differential follows the requested pair ──────────────────

def _mock_bars(returns_by_instrument):
    """Return a get_daily_bars stub yielding a 3-row frame per instrument with a
    controlled prev→last close (so 1-day return is deterministic)."""
    def _stub(pair="GBPAUD", count=3, **kw):
        prev, last = returns_by_instrument.get(pair, (1.0, 1.0))
        return pd.DataFrame({"Close": [prev, prev, last]})
    return _stub


@pytest.fixture
def strong_gbp_weak_aud(monkeypatch):
    # GBP up vs USD, AUD down vs USD, JPY ~flat vs USD → GBP/AUD diff >> GBP/JPY diff
    bars = {
        "GBP_USD": (1.0000, 1.0100),  # +1.0% GBP
        "AUD_USD": (1.0000, 0.9900),  # -1.0% AUD
        "USD_JPY": (1.0000, 1.0000),  # flat
        "EUR_USD": (1.0000, 1.0000),
        "USD_CHF": (1.0000, 1.0000),
        "USD_CAD": (1.0000, 1.0000),
        "NZD_USD": (1.0000, 1.0000),
    }
    monkeypatch.setattr("oanda_feed.is_configured", lambda: True)
    monkeypatch.setattr("oanda_feed.get_daily_bars", _mock_bars(bars))


def test_currency_strength_differential_follows_pair(strong_gbp_weak_aud):
    from currency_strength import get_currency_strength

    aud = get_currency_strength(["GBP", "AUD"])
    jpy = get_currency_strength(["GBP", "JPY"])

    # Each differential equals base_score - quote_score for THAT pair
    assert aud["differential"] == pytest.approx(round(aud["GBP"] - aud["AUD"], 1))
    assert jpy["base"] == "GBP" and jpy["quote"] == "JPY"
    assert jpy["differential"] == pytest.approx(round(jpy["base_score"] - jpy["quote_score"], 1))

    # With GBP strong / AUD weak / JPY flat, GBP/AUD diff must exceed GBP/JPY diff
    assert aud["differential"] > jpy["differential"]


# ── liquidity_context: live price fetched for the requested instrument ──────────

def test_liquidity_fetches_live_price_for_instrument(monkeypatch):
    import liquidity_context as lc

    captured = {}

    def _fake_live_price(pair="GBPAUD", **kw):
        captured["pair"] = pair
        return 217.55

    def _fake_daily(pair="GBPAUD", count=30, **kw):
        # synthetic JPY-scale history
        base = 217.0
        closes = [base + i * 0.05 for i in range(30)]
        return pd.DataFrame({
            "Open": closes, "High": [c + 0.1 for c in closes],
            "Low": [c - 0.1 for c in closes], "Close": closes,
        })

    monkeypatch.setattr(lc, "is_configured", lambda: True)
    monkeypatch.setattr(lc, "get_live_price", _fake_live_price)
    monkeypatch.setattr(lc, "get_daily_bars", _fake_daily)

    result = lc.get_liquidity_context("GBP_JPY")
    assert captured["pair"] == "GBP_JPY"          # fetched for the right pair
    assert result["current_price"] == pytest.approx(217.55, abs=0.01)
    assert result["error"] is None
