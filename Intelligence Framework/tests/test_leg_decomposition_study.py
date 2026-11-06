"""Pins studies/leg_decomposition_study.py to
docs/specs/leg_decomposition_study_spec.md: the cross identity, the
identity check (passes on consistent data, fails on misalignment), weekly
grouping, R², the exact F(2, d2) tail, the lag test (finds a planted lead,
not a fake one), the stress quintile, and the risk-verdict boundaries.
Synthetic data only; no files, no network."""
import math
import os
import random
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "studies"))
import leg_decomposition_study as S  # noqa: E402

UTC = timezone.utc


def _legs(n=400, seed=1):
    rng = random.Random(seed)
    gu, au, uj = [1.5], [0.75], [110.0]
    for _ in range(n):
        gu.append(gu[-1] * math.exp(rng.gauss(0, 0.006)))
        au.append(au[-1] * math.exp(rng.gauss(0, 0.007)))
        uj.append(uj[-1] * math.exp(rng.gauss(0, 0.006)))
    dates = [datetime(2010, 1, 4, 22, tzinfo=UTC) + timedelta(days=k) for k in range(n + 1)]
    closes = {"GBP_USD": dict(zip(dates, gu)), "AUD_USD": dict(zip(dates, au)), "USD_JPY": dict(zip(dates, uj))}
    closes["GBP_AUD"] = {t: closes["GBP_USD"][t] / closes["AUD_USD"][t] for t in dates}
    closes["GBP_JPY"] = {t: closes["GBP_USD"][t] * closes["USD_JPY"][t] for t in dates}
    return closes, dates


def test_identity_holds_exactly_on_synthetic_crosses():
    closes, dates = _legs()
    r = S.daily_returns(closes, S.MAIN, dates)
    for pair in S.CROSSES:
        ic = S.identity_check(r[pair], S.reconstruct(pair, r))
        assert ic["pass"] and ic["corr"] > 0.999999 and ic["median_bp"] < 1e-6
        assert abs(ic["shifted_corr"]) < 0.3                    # control of the control


def test_identity_check_fails_on_misaligned_legs():
    closes, dates = _legs()
    r = S.daily_returns(closes, S.MAIN, dates)
    shifted = {k: (np.roll(v, 1) if k == "GBP_USD" else v) for k, v in r.items()}
    assert not S.identity_check(r["GBP_AUD"], S.reconstruct("GBP_AUD", shifted))["pass"]


def test_identity_check_fails_on_sign_error():
    closes, dates = _legs()
    r = S.daily_returns(closes, S.MAIN, dates)
    wrong = r["GBP_USD"] + r["AUD_USD"]
    assert not S.identity_check(r["GBP_AUD"], wrong)["pass"]


def test_weekly_groups_by_iso_week_and_drops_short_weeks():
    dates = [datetime(2010, 1, 4, 22, tzinfo=UTC) + timedelta(days=k) for k in range(12)]
    # session days: Tue 01-05 ... ; ISO weeks split them
    r = {"X": np.ones(12)}
    wr, rv, excl = S.weekly(r, dates, min_days=3)
    sizes = {}
    for t in dates:
        w = S.C.session_day(t).isocalendar()[:2]
        sizes[w] = sizes.get(w, 0) + 1
    assert sorted(wr["X"].tolist()) == sorted(float(v) for v in sizes.values() if v >= 3)
    assert excl == sum(1 for v in sizes.values() if v < 3)
    assert np.allclose(rv["X"] ** 2, wr["X"])                  # ones: sum of squares = sum


def test_ols_r2_known():
    x = np.arange(10, dtype=float)
    _, resid, r2 = S.ols(2 * x + 1, x)
    assert abs(r2 - 1) < 1e-12 and np.allclose(resid, 0)


def test_f2_tail_exact():
    assert abs(S.f2_sf(0.0, 50) - 1.0) < 1e-12
    assert abs(S.f2_sf(3.0, 1e9) - math.exp(-3.0)) < 1e-6   # limit: chi2(2)/2 tail
    scipy_stats = pytest.importorskip("scipy.stats")
    for f, d2 in ((0.7, 30), (4.2, 120), (9.5, 2000)):
        assert abs(S.f2_sf(f, d2) - scipy_stats.f.sf(f, 2, d2)) < 1e-10


def test_lag_test_finds_planted_lead_and_not_a_fake_one():
    rng = np.random.default_rng(5)
    x1, x2 = rng.normal(size=600), rng.normal(size=600)
    y_lead = np.concatenate([[0.0], 0.6 * x1[:-1]]) + rng.normal(scale=0.5, size=600)
    assert S.lag_test(y_lead, x1, x2)[3] < 1e-10
    y_none = rng.normal(size=600)
    assert S.lag_test(y_none, x1, x2)[3] > S.ALPHA_LAG


def test_stress_mask_top_quintile():
    m = S.stress_mask(np.arange(100, dtype=float))
    assert m.sum() == 20 and m[80] and not m[79]               # inclusive 80th pct = 79.2


def test_risk_verdict_boundaries():
    assert S.risk_verdict(0.70, 50).startswith("JUSTIFIED")
    assert S.risk_verdict(0.30, 50).startswith("OVER-CONSERVATIVE")
    assert "1.33" in S.risk_verdict(0.5, 50)
    assert S.risk_verdict(0.9, 19).startswith("INSUFFICIENT")


def test_corr_ci_and_alpha():
    x = np.arange(50, dtype=float)
    r, lo, hi, n = S.corr_ci(x, x * 2)
    assert r > 0.9999 and n == 50 and lo <= r <= hi
    assert abs(S.ALPHA_LAG - 0.008512) < 1e-6
