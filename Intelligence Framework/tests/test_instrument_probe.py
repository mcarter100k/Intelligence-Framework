"""
test_instrument_probe.py — the read-only account probe (studies/instrument_probe.py).

Canned responses only (conftest blocks the network). Pins: availability is
reported per target, the account id never appears unmasked, financing is
read when present, and an HTTP failure raises instead of printing a report.
"""
import os
import sys

import pytest

from _paths import ROOT
sys.path.insert(0, os.path.join(ROOT, "studies"))
import instrument_probe as ip  # noqa: E402

ACCT = "101-004-1234567-001"


class _Resp:
    def __init__(self, payload, status=200):
        self._p, self.status_code = payload, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._p


def _fake_get(fail_on=None):
    def get(url, headers=None, params=None, timeout=None):
        if fail_on and fail_on in url:
            return _Resp({}, 403)
        if url.endswith("/instruments"):
            return _Resp({"instruments": [
                {"name": "GBP_JPY", "type": "CURRENCY",
                 "financing": {"longRate": "0.0150", "shortRate": "-0.0350"}},
                {"name": "GBP_AUD", "type": "CURRENCY"},
                {"name": "USD_JPY", "type": "CURRENCY"},
                {"name": "XAU_USD", "type": "METAL"},
            ]})
        if "/candles" in url:
            t = "2005-01-03T22:00:00Z" if "from" in (params or {}) else "2026-10-30T21:00:00Z"
            return _Resp({"candles": [{"time": t}]})
        raise AssertionError(url)
    return get


@pytest.fixture
def creds(monkeypatch):
    monkeypatch.setenv("OANDA_API_KEY", "secret-key-xyz")
    monkeypatch.setenv("OANDA_ACCOUNT_ID", ACCT)
    monkeypatch.setenv("OANDA_ENVIRONMENT", "practice")


def test_reports_availability_history_and_financing(creds, monkeypatch, capsys):
    monkeypatch.setattr(ip.requests, "get", _fake_get())
    assert ip.main() == 0
    out = capsys.readouterr().out
    assert "USD_JPY      offered (CURRENCY): daily history 2005-01-03 → 2026-10-30" in out
    assert "USB10Y_USD   NOT OFFERED" in out
    assert "XAU_USD      offered (METAL)" in out
    assert "GBP_JPY: longRate 0.0150 shortRate -0.0350" in out
    assert "GBP_AUD: no financing field returned" in out
    assert "Instruments offered by type: CURRENCY 3, METAL 1" in out


def test_never_prints_the_account_id_or_key(creds, monkeypatch, capsys):
    monkeypatch.setattr(ip.requests, "get", _fake_get())
    ip.main()
    out = capsys.readouterr().out
    assert ACCT not in out and "secret-key-xyz" not in out
    assert ip.masked(ACCT) in out and ip.masked(ACCT).endswith("-001")


def test_http_failure_raises_not_a_report(creds, monkeypatch, capsys):
    monkeypatch.setattr(ip.requests, "get", _fake_get(fail_on="/instruments"))
    with pytest.raises(RuntimeError, match="HTTP 403"):
        ip.main()
    assert "INSTRUMENT PROBE" not in capsys.readouterr().out
