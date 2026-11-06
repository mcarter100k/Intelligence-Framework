"""
Standing display-claim test (docs/specs/display_claims_spec.md §4).

Every sentence the brief renders makes a claim about the market or about the
evidence. This test renders states through the real builders (REASON, MARKET
STATE, EXIT IF / WATCH FOR, THE FULL PICTURE) and the SESSION-note functions,
and checks each registered claim against the state that produced it.

  * States are assembled around the real classifier, conflict, composite,
    weekly, apply_filter and official-decision functions (the round-2
    reviewer's builder). test_builder_matches_get_regime pins that assembly to
    the real get_regime on synthetic bars.
  * A claim that is false today is a strict xfail (it must flip when its fix
    lands) AND may not spread: its false-cell count is capped at the baseline.
  * Every claim's trigger must fire somewhere in the grid, so a reworded
    trigger cannot pass by matching nothing.
  * The claim-word check: any rendered "historically", "statistical", "no …
    edge", "reliable", "BoJ", "coil", "typically", "strongest" or "fade" must
    be registered with its finding. Research stated as fact cannot regrow
    unnoticed.

Default tier: a fixed-seed sample of the grid (every suite run).
Full tier:    pytest -m display_sweep tests/test_display_claims.py
              (the whole ~218k-cell grid, deselected by default; re-run it
              whenever display logic changes and log its counts).
"""
import collections
import itertools
import random
import re
from unittest import mock

import pytest

import decision_brief as db
import news_gate
import regime_detection as rd
import session_memory as sm
from no_trade_filter import apply_filter
from official_decision import get_official_decision

# ── State builder (mirrors get_regime's assembly around the real functions) ──

_GATE = {"gating": False, "active": True}


def _weekly(lt, st):
    c = [100.0] * 24
    a = {"UP": 90.0, "DOWN": 110.0, "R": 100.0}[lt]
    b = {"UP": 90.0, "DOWN": 110.0, "R": 100.0}[st]
    for i in (1, 2, 3):
        c[i] = a
    for i in (17, 18, 19):
        c[i] = b
    return rd._compute_weekly_context(c, c, c)


WEEKLY = {(lt, st): _weekly(lt, st) for lt in ("UP", "DOWN", "R") for st in ("UP", "DOWN", "R")}


def build(inst, adx, atr, st, slope, adx4, atr4, st4, slope4, wk, rp=0.1, gate=_GATE):
    """The regime dict get_regime would return for these classifier inputs
    (the fields the renderers read)."""
    pair = rd.PAIRS[inst]
    d1, d1s = rd._classify_ex(adx, atr, slope, pair=pair, instrument=inst, structure=st)
    h4, h4s = rd._classify_ex(adx4, atr4, slope4, instrument=inst, pair=pair, structure=st4)
    conflict, ctype = rd._detect_conflict(d1, h4)
    res = rd.get_composite_regime(d1, h4)
    comp = pair.atr_compression_min > 0 and atr < pair.atr_compression_min
    exh = adx >= rd._ADX_EXHAUSTION_THRESHOLD or (inst == "GBP_JPY" and adx >= rd._ADX_JPY_EXHAUSTION)
    fin = {"instrument": inst, "adx": adx, "confidence": res["confidence"],
           "adx_exhaustion": exh, "range_position": rp,
           "regime_d1_subtype": d1s, "regime_h4_subtype": h4s,
           "regime_d1": d1, "regime_h4": h4, "adx_h4": adx4, "atr_vs_avg": atr,
           "atr_compression": comp, "atr_compression_note": "c" if comp else "",
           "timeframe_conflict": conflict, "conflict_type": ctype, "structure": st,
           "weekly_context": wk["weekly_context"], "lt_trend": wk["lt_trend"],
           "st_trend": wk["st_trend"], "execution_mode": res["execution_mode"],
           "size_mult": res["size_mult"], "resolution_note": res["note"],
           "news_gate": gate}
    fr = apply_filter(dict(fin))
    full = dict(fin, stand_down=not fr.allowed,
                stand_down_reason="" if fr.allowed else fr.reason,
                filter_allowed=fr.allowed, filter_mode=fr.execution_mode,
                filter_size_mult=fr.size_mult, filter_reason=fr.reason,
                filter_block=fr.block, override_fired=fr.override_fired,
                pair=pair.display_name, structure_h4=st4,
                atr_spike_multiplier=pair.atr_spike_multiplier, current_price=1.0)
    return full, fr


# ── The grid ────────────────────────────────────────────────────────────────

D1ADX = [5, 17.6, 18, 21, 24.9, 25, 28, 31.9, 32, 34.9, 35, 45]
D1ATR = [0.5, 0.79, 0.8, 0.95, 1.05, 1.19, 1.2, 1.35, 1.49, 1.5, 1.8, 2.0]
ST = ["UPTREND", "DOWNTREND", "TRANSITIONAL"]
H4ADX = [10, 18, 22, 25, 30, 35, 50]
H4ATR = [0.7, 1.0, 1.3, 1.6]
SIGN = {"UPTREND": 1.0, "DOWNTREND": -1.0, "TRANSITIONAL": 0.3}   # live: slope follows structure
AXES = [("GBP_AUD", "GBP_JPY"), D1ADX, D1ATR, ST, H4ADX, H4ATR, ST, sorted(WEEKLY)]
TOTAL = 1
for _a in AXES:
    TOTAL *= len(_a)
SAMPLE_N, SAMPLE_SEED = 20000, 20261105


def _cell(index):
    out = []
    for axis in reversed(AXES):
        index, k = divmod(index, len(axis))
        out.append(axis[k])
    return tuple(reversed(out))


def _render(cell):
    inst, adx, atr, st, adx4, atr4, st4, wkey = cell
    wk = WEEKLY[wkey]
    full, fr = build(inst, adx, atr, st, SIGN[st], adx4, atr4, st4, SIGN[st4], wk)
    od = get_official_decision(full)
    dec = od["direction"] if od["direction"] in ("LONG", "SHORT") else "STAND DOWN"
    inv = db._plain(db._build_invalidation(full, dec))
    texts = {"REASON": db._render_reason(full, {}, dec, fr.override_fired),
             "MARKET STATE": db._build_market_state(full),
             "EXIT IF / WATCH FOR": inv,
             "FULL PICTURE": db._build_narrative(full, dec, None, inv, None, 0.0001)}
    return {"cell": cell, "state": full, "fr": fr, "dec": dec, "texts": texts, "wk": wk}


def _sweep(indices):
    return [_render(_cell(i)) for i in indices]


@pytest.fixture(scope="module")
def grid():
    idx = sorted(random.Random(SAMPLE_SEED).sample(range(TOTAL), SAMPLE_N))
    return _sweep(idx)


# ── SESSION notes: pure functions over a threshold grid ─────────────────────

ADX_VALUES = [10.0, 17.6, 17.96, 18.2, 22.0, 24.6, 24.96, 25.2, 28.0, 33.0]
ATR_VALUES = [0.70, 0.76, 0.79, 0.82, 0.86, 1.0, 1.15, 1.22, 1.45, 1.55, 2.1]


def _adx_trend(d):
    return "STABLE" if abs(d) < 0.5 else ("RISING" if d > 0 else "FALLING")


def _atr_trend(d):
    return "STABLE" if abs(d) < 0.05 else ("EXPANDING" if d > 0 else "CONTRACTING")


def _session_notes():
    out = []
    for inst in ("GBP_AUD", "GBP_JPY"):
        for now, prior in itertools.product(ADX_VALUES, ADX_VALUES):
            d = now - prior
            out.append(("adx", inst, now, prior, sm._adx_note(now, prior, d, _adx_trend(d), inst)))
        for now, prior in itertools.product(ATR_VALUES, ATR_VALUES):
            d = now - prior
            out.append(("atr", inst, now, prior, sm._atr_note(now, prior, d, _atr_trend(d), inst)))
    return out


SESSION = _session_notes()


# ── Claims about a rendered cell ────────────────────────────────────────────

def _dir_of(label):
    return 1 if label in ("TRENDING_UP", "UPTREND") else (-1 if label in ("TRENDING_DOWN", "DOWNTREND") else 0)


def _weekly_sign(wk):
    lt = wk["lt_trend"]
    return 1 if lt == "UPTREND" else (-1 if lt == "DOWNTREND" else 0)


def _c3(r, grid):
    """Inventory 3: the override REASON says 'transition' only on a transition-zone daily."""
    if not (r["fr"].override_fired and r["dec"] != "STAND DOWN" and "transition" in r["texts"]["REASON"]):
        return None
    return r["state"]["regime_d1_subtype"] == "TRANSITION_ZONE"


def _c4(r, grid):
    """Inventory 4: 'on all timeframes' only when weekly, daily and 4-hour all trend that way."""
    hits = [t for t in r["texts"].values() if "on all timeframes" in t]
    if not hits:
        return None
    want = 1 if any("uptrend on all" in t for t in hits) else -1
    s = r["state"]
    return (_dir_of(s["regime_d1"]) == want and _dir_of(s["regime_h4"]) == want
            and _weekly_sign(r["wk"]) == want)


def _spike_override_trades(grid):
    return sum(1 for r in grid if r["fr"].override_fired and r["dec"] != "STAND DOWN"
               and r["state"]["atr_vs_avg"] >= r["state"]["atr_spike_multiplier"])


def _c6(r, grid):
    """Inventory 6: 'regardless of trend strength' is false if the override trades any spike."""
    if "regardless of trend strength" not in r["texts"]["REASON"]:
        return None
    return grid["_spike_override_trades"] == 0


def _p10(r, grid):
    """Inventory 9 (true today): 'All three timeframes line up' on a trade → daily and 4-hour agree."""
    if r["dec"] == "STAND DOWN" or "All three timeframes line up" not in r["texts"]["FULL PICTURE"]:
        return None
    return r["state"]["regime_d1"] == r["state"]["regime_h4"]


def _p9(r, grid):
    """Inventory 9 (true today): 'pieces don't line up' never while weekly, daily and 4-hour agree."""
    if r["dec"] != "STAND DOWN" or "pieces don't line up" not in r["texts"]["FULL PICTURE"]:
        return None
    s = r["state"]
    d = _dir_of(s["regime_d1"])
    return not (d != 0 and s["regime_h4"] == s["regime_d1"] and _weekly_sign(r["wk"]) == d)


CELL_CLAIMS = {"3_override_transition": _c3, "4_all_timeframes": _c4,
               "6_spike_regardless": _c6, "P10_all_three_line_up": _p10,
               "P9_pieces_dont_line_up": _p9}

# ── Claims about SESSION notes ──────────────────────────────────────────────

_PAIR_NUMS = re.compile(r"\(([\d.]+)x? → ([\d.]+)x?\)")


def _s5a(kind, inst, now, prior, text):
    """5a: _adx_note cannot see the regime, so it may never call the market trending."""
    if kind != "adx" or "stable and trending" not in text:
        return None
    return False


def _s5b(kind, inst, now, prior, text):
    """5b: a threshold-crossing note shows two numbers on opposite sides of the threshold."""
    if "just crossed" not in text and "dropped below" not in text:
        return None
    m = _PAIR_NUMS.search(text)
    if not m:
        return False
    a, b = float(m.group(1)), float(m.group(2))
    thresh = rd._ADX_TRANSITION_HIGH if kind == "adx" else rd.PAIRS[inst].atr_spike_multiplier
    return a != b and ((a < thresh) != (b < thresh))


def _s5c(kind, inst, now, prior, text):
    """5c: a downward crossing of GBP/JPY's compression level says so."""
    comp = rd.PAIRS[inst].atr_compression_min
    if kind != "atr" or comp <= 0 or not (now < comp <= prior) or _atr_trend(now - prior) == "STABLE":
        return None
    return "entered" in text or "dropped below" in text


def _s5d(kind, inst, now, prior, text):
    """5d: 'approaching' only while the value is still on the near side of the level."""
    if kind != "atr" or "approaching pre-intervention" not in text:
        return None
    return now >= rd.PAIRS[inst].atr_compression_min


SESSION_CLAIMS = {"5a_stable_and_trending": _s5a, "5b_crossing_numbers": _s5b,
                  "5c_compression_entry_reachable": _s5c, "5d_approaching_while_below": _s5d}

# ── The claim-word class (item 7) ───────────────────────────────────────────

CLAIM_WORDS = re.compile(r"historically|statistical|\bno (?:clean |directional |clean directional )?edge\b"
                         r"|reliable|\bBoJ\b|\bcoil\b|typically|strongest|\bfade\b", re.I)

# Registered claim-word phrases: (distinguishing substring, finding, status).
# Known false today; each is reworded by display_claims_spec.md §2 item 7.
REGISTERED = {
    "no statistical edge":                ("7a", "R1 demoted, R4 no band at N>=15, R12 inconclusive: untested"),
    "both signals historically fail here": ("7b", "R3 descriptive (11 events); R6 REFUTED"),
    "historically precedes a fake move":   ("7c", "R7 REFUTED (backwards)"),
    "too high for reliable signals":       ("7d", "no study; a hard rule (N6)"),
    "too high for a reliable read":        ("7e", "no study; a hard rule (N6)"),
    "structural disagreement, no edge":    ("7f", "design rule D3, never measured"),
    "No edge; standing aside":             ("7f", "design rule D3, never measured"),
    "no clean directional edge":           ("7g", "design rule, never measured"),
    "no edge on either TF":                ("7h", "design rule, never measured"),
    "no edge yet":                         ("7i", "same as 7a"),
    "pre-intervention coil":               ("7b/7j", "R3 descriptive; no BoJ link studied"),
    "BoJ risk elevated":                   ("7j", "no study"),
    "fade, don't follow":                  ("7k", "advises a trade the framework never takes"),
}
KNOWN_FALSE_PHRASES = set(REGISTERED)   # all of today's registered phrases are known false


def _claim_word_hits(texts):
    """(surface, fragment, registered key or None) for every claim word rendered."""
    out = []
    for surface, text in texts:
        for m in CLAIM_WORDS.finditer(text):
            key = next((k for k in REGISTERED if k.lower() in text.lower()
                        and text.lower().find(k.lower()) <= m.start() < text.lower().find(k.lower()) + len(k)
                        ), None)
            frag = text[max(0, m.start() - 60): m.end() + 40]
            out.append((surface, frag, key))
    return out


def _all_texts(grid):
    for r in grid:
        for surface, t in r["texts"].items():
            yield surface, t
    for kind, inst, now, prior, text in SESSION:
        yield "SESSION", text


# ── Evaluation ──────────────────────────────────────────────────────────────

def _evaluate(rows):
    grid = {"_spike_override_trades": _spike_override_trades(rows)}
    fired = collections.Counter()
    false = collections.Counter()
    examples = {}
    for r in rows:
        for cid, fn in CELL_CLAIMS.items():
            ok = fn(r, grid)
            if ok is None:
                continue
            fired[cid] += 1
            if not ok:
                false[cid] += 1
                examples.setdefault(cid, (r["cell"], r["texts"]))
    for note in SESSION:
        for cid, fn in SESSION_CLAIMS.items():
            ok = fn(*note)
            if ok is None:
                continue
            fired[cid] += 1
            if not ok:
                false[cid] += 1
                examples.setdefault(cid, note)
    words = collections.Counter()
    unregistered = []
    for surface, frag, key in _claim_word_hits(_all_texts(rows)):
        fired["7_claim_words"] += 1
        if key is None:
            unregistered.append((surface, frag))
        else:
            words[key] += 1
    return fired, false, examples, words, unregistered


@pytest.fixture(scope="module")
def evaluated(grid):
    return _evaluate(grid)


# Baselines measured on main 4828ab2 (2026-11-05): false cells per claim, and
# renders per registered claim-word phrase. The full tier reproduces the
# round-2 inventory exactly (override 'transition' 2,304 of 3,672; 'on all
# timeframes' 216,300 of 217,728). A fix sets its counts to 0 and removes the
# claim from KNOWN_FALSE / the phrase from REGISTERED; strict xfail makes that
# removal compulsory.
BASELINE = {
    "default": {"3_override_transition": 64, "4_all_timeframes": 6625, "6_spike_regardless": 5383,
                "P10_all_three_line_up": 0, "P9_pieces_dont_line_up": 0},
    "full": {"3_override_transition": 2304, "4_all_timeframes": 216300, "6_spike_regardless": 175824,
             "P10_all_three_line_up": 0, "P9_pieces_dont_line_up": 0},
}
for _tier in BASELINE.values():   # SESSION notes are the same grid in both tiers
    _tier.update({"5a_stable_and_trending": 8, "5b_crossing_numbers": 20,
                  "5c_compression_entry_reachable": 23, "5d_approaching_while_below": 25})
WORD_BASELINE = {
    "default": {"too high for reliable signals": 6938, "too high for a reliable read": 1689,
                "no statistical edge": 2445, "No edge; standing aside": 266,
                "pre-intervention coil": 1682, "both signals historically fail here": 1657,
                "historically precedes a fake move": 1657, "fade, don't follow": 2032,
                "no edge yet": 16},
    "full": {"too high for reliable signals": 226368, "too high for a reliable read": 54432,
             "no statistical edge": 78912, "No edge; standing aside": 8568,
             "pre-intervention coil": 54457, "both signals historically fail here": 54432,
             "historically precedes a fake move": 54432, "fade, don't follow": 66096,
             "no edge yet": 16},
}
KNOWN_FALSE = {"3_override_transition", "4_all_timeframes", "6_spike_regardless",
               "5a_stable_and_trending", "5b_crossing_numbers",
               "5c_compression_entry_reachable", "5d_approaching_while_below"}
ALL_CLAIMS = list(CELL_CLAIMS) + list(SESSION_CLAIMS)
# Registered phrases the sample never renders (no grid cell produces them);
# they stay registered so a future rendering is recognised, not unregistered.
NOT_RENDERED_IN_GRID = {"structural disagreement, no edge", "no clean directional edge",
                        "no edge on either TF", "BoJ risk elevated"}


def _xfail_if_known(cid):
    if cid in KNOWN_FALSE:
        return pytest.param(cid, marks=pytest.mark.xfail(
            strict=True, raises=AssertionError,
            reason="known false (display_claims_spec.md §2); fix pending team review"))
    return cid


def _phrase_param(key):
    return pytest.param(key, marks=pytest.mark.xfail(
        strict=True, raises=AssertionError,
        reason=f"item {REGISTERED[key][0]}: {REGISTERED[key][1]}; reworded by display_claims_spec.md"))


# ── Default tier ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("cid", ALL_CLAIMS + ["7_claim_words"])
def test_every_claim_trigger_fires(evaluated, cid):
    """Non-vacuity: a trigger that matches nothing proves nothing."""
    fired = evaluated[0]
    assert fired[cid] > 0, f"claim {cid} never rendered in the grid: reworded trigger or broken builder"


@pytest.mark.parametrize("cid", [_xfail_if_known(c) for c in ALL_CLAIMS])
def test_claim_holds_in_every_cell(evaluated, cid):
    fired, false, examples = evaluated[0], evaluated[1], evaluated[2]
    assert false[cid] == 0, (f"{cid}: false in {false[cid]} of {fired[cid]} cells; "
                             f"e.g. {str(examples.get(cid))[:400]}")


def test_known_false_claims_do_not_spread(evaluated):
    fired, false, _, words, _ = evaluated
    grown = {c: (false[c], BASELINE["default"][c]) for c in ALL_CLAIMS
             if false[c] > BASELINE["default"][c]}
    assert not grown, f"false-cell counts above baseline (now, baseline): {grown}"
    grown_w = {k: (words[k], WORD_BASELINE["default"].get(k, 0)) for k in words
               if words[k] > WORD_BASELINE["default"].get(k, 0)}
    assert not grown_w, f"claim-word phrases rendering more than baseline: {grown_w}"


def test_no_unregistered_claim_word(evaluated):
    """Item 7's guard: research stated as fact cannot appear without a registered finding."""
    unregistered = evaluated[4]
    assert not unregistered, ("unregistered claim words rendered (register with a finding, or "
                              f"reword): {unregistered[:10]}")


@pytest.mark.parametrize("key", [_phrase_param(k) for k in sorted(REGISTERED)
                                 if k not in NOT_RENDERED_IN_GRID])
def test_registered_research_claim_no_longer_rendered(evaluated, key):
    words = evaluated[3]
    assert words[key] == 0, f"{key!r} rendered {words[key]} times"


# ── Builder parity with the real get_regime ─────────────────────────────────

def _walk(seed, n, freq, start, drift, vol):
    import pandas as pd
    rnd = random.Random(seed)
    c, closes = 1.90, []
    for _ in range(n):
        c += drift + rnd.gauss(0, vol)
        closes.append(c)
    return pd.DataFrame(
        {"Open": closes, "Close": closes, "High": [x + vol for x in closes],
         "Low": [x - vol for x in closes], "Volume": [1000] * n},
        index=pd.date_range(start, periods=n, freq=freq, tz="UTC"))


PARITY_FIELDS = ("regime_d1", "regime_h4", "regime_d1_subtype", "regime_h4_subtype",
                 "timeframe_conflict", "conflict_type", "execution_mode", "size_mult",
                 "stand_down", "stand_down_reason", "atr_compression", "adx_exhaustion",
                 "filter_allowed", "filter_block", "override_fired")


def test_builder_matches_get_regime():
    """The builder mirrors get_regime's assembly. Drive the real get_regime on
    synthetic bars, record each classifier call's inputs, rebuild from them,
    and compare every field the renderers read, plus the official decision."""
    seen = set()
    compared = 0
    real = rd._classify_ex
    for inst in ("GBP_AUD", "GBP_JPY"):
        for seed in range(24):
            calls = []

            def rec(adx, atr_ratio, slope, instrument=None, pair=None, structure=None):
                calls.append((adx, atr_ratio, slope, structure))
                return real(adx, atr_ratio, slope, instrument=instrument, pair=pair, structure=structure)

            d_drift = (0.004, -0.004, 0.0, 0.0015)[seed % 4]
            d_vol = (0.002, 0.006, 0.0008)[seed % 3]
            d1 = _walk(seed, 220, "B", "2025-01-01", d_drift, d_vol)
            wk = _walk(500 + seed, 110, "W", "2023-01-01", d_drift * 3, 0.004)
            h4 = _walk(100 + seed, 200, "4h", "2025-09-01", (0.0009, -0.0009, 0.0)[seed % 3], 0.0012)
            with mock.patch.object(rd, "_classify_ex", rec), \
                 mock.patch.object(rd, "_oanda_ok", return_value=True), \
                 mock.patch.object(rd, "_oanda_live_price", return_value=None), \
                 mock.patch.object(news_gate, "check_news_gate", return_value=dict(_GATE)), \
                 mock.patch("regime_detection._oanda_daily_bars", lambda *a, count=220, **k: d1.tail(count).copy()), \
                 mock.patch("regime_detection._oanda_h4_bars", lambda *a, count=120, **k: h4.tail(count).copy()), \
                 mock.patch("regime_detection._oanda_weekly_bars", lambda *a, count=110, **k: wk.tail(count).copy()):
                reg = rd.get_regime(inst)
            assert not reg.get("error"), reg.get("error")
            assert len(calls) == 2, f"expected one daily and one 4-hour classification, got {len(calls)}"
            (adx, atr, slope, st), (adx4, atr4, slope4, st4) = calls
            weekly = {k: reg[k] for k in ("lt_trend", "st_trend", "weekly_context")}
            full, _ = build(inst, adx, atr, st, slope, adx4, atr4, st4, slope4, weekly,
                            rp=reg["range_position"])
            diff = {f: (reg[f], full[f]) for f in PARITY_FIELDS if reg[f] != full[f]}
            assert not diff, f"builder diverges from get_regime ({inst}, seed {seed}): {diff}"
            off_real, off_built = get_official_decision(reg), get_official_decision(full)
            assert (off_real["direction"], off_real["grade"]) == (off_built["direction"], off_built["grade"])
            seen.add((reg["regime_d1"], reg["regime_h4"], reg["stand_down"]))
            compared += 1
    assert compared == 48
    assert len(seen) >= 3, f"parity compared too few distinct states to mean anything: {seen}"


# ── Full tier (deselected by default) ───────────────────────────────────────

@pytest.mark.display_sweep
def test_full_sweep():
    """The whole grid. Run when display logic changes; log the counts."""
    fired, false, examples, words, unregistered = _evaluate(_sweep(range(TOTAL)))
    print({c: (fired[c], false[c]) for c in ALL_CLAIMS + ["7_claim_words"]}, dict(words))
    assert all(fired[c] > 0 for c in ALL_CLAIMS), fired
    assert not unregistered, unregistered[:10]
    grown = {c: (false[c], BASELINE["full"][c]) for c in ALL_CLAIMS if false[c] > BASELINE["full"][c]}
    assert not grown, grown
    grown_w = {k: (words[k], WORD_BASELINE["full"].get(k, 0)) for k in words
               if words[k] > WORD_BASELINE["full"].get(k, 0)}
    assert not grown_w, grown_w
