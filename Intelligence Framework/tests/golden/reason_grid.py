"""
reason_grid.py: the W5 input grid for docs/specs/range_volatile_wording_v3_spec.md
§4 as amended by v4 §2, plus the approval's build-time addition
(atr_compression). It is generated from `main` BEFORE the wording build and
committed on its own.

Every combination below is rendered through decision_brief._render_reason,
the exact pipeline the brief prints. Impossible combinations are kept on
purpose: rendering must not crash on any of them.

A cell is a TARGET when its REASON begins with TARGET_PREFIX (main: "Range
breaking down"). The golden file stores:
  - the cell count;
  - sha256 of the sorted target keys, plus their count;
  - sha256 over the sorted (key, sha256(reason)) pairs of every NON-target
    cell.
After the build, a cell is a target iff it renders one of the new sentences.
The target-key hash must still match (the same cells changed), and the
non-target hash must still match (nothing else changed).

Storage change from the spec, old → new (v4 §2 said "the target-cell keys
are stored as a plain list"): a hash of the sorted list plus its count. It is
equally exact and keeps about 1 MB of keys out of the repo.

Run: python3 tests/golden/reason_grid.py > tests/golden/reason_grid_main.json
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

REGIMES  = ("TRENDING_UP", "TRENDING_DOWN", "RANGING", "VOLATILE")
SUBTYPES = ("", "TRANSITION_ZONE", "UNCONFIRMED_TREND", "EXHAUSTION", "STRUCTURE_DISAGREES")
DECISIONS = ("LONG", "SHORT", "STAND DOWN")
STAND_RSN = ("", "RANGING D1 + VOLATILE H4 — range breaking down, wait",
             "news: high-impact release in 45 minutes")
FILTER_BLOCK = ("", "blocked")
ATR_VS_AVG = (0.5, 1.0, 2.0)
H4_CHANGE = (None, 4, 190, -190)
SPIKE_MULT = {"GBP_AUD": 1.2, "GBP_JPY": 1.5}      # regime_detection.PAIRS
NEWS = {False: {}, True: {"gating": True, "active": True, "event": "UK CPI y/y",
                          "currency": "GBP", "minutes_until": 45,
                          "event_time_utc": "2026-11-04 07:00", "note": "",
                          "pre_release": True}}
FIXED = {"adx": 14.5, "adx_h4": 33.0, "structure": "TRANSITIONAL",
         "structure_h4": "TRANSITIONAL", "weekly_context": "ESTABLISHED_UPTREND",
         "execution_mode": "STAND_DOWN", "filter_reason": ""}
TARGET_PREFIX = "Range breaking down"


def _conflict_type(d1, h4, conflict):
    if not conflict:
        return ""
    if d1 == "RANGING" and h4 == "VOLATILE":
        return "RANGING_D1_VOLATILE_H4"
    if d1 == "TRENDING_UP" and h4 == "TRENDING_DOWN":
        return "D1_BULLISH_H4_BEARISH"
    if d1 == "TRENDING_DOWN" and h4 == "TRENDING_UP":
        return "D1_BEARISH_H4_BULLISH"
    return "OTHER"


def cells():
    """Yield (key, regime, decision_str) for every grid cell."""
    for (d1, d1s, h4, h4s, dec, conflict, gating, fblock, ratio, chg, rsn, inst,
         comp) in itertools.product(REGIMES, SUBTYPES, REGIMES, SUBTYPES, DECISIONS,
                                    (False, True), (False, True), FILTER_BLOCK,
                                    ATR_VS_AVG, H4_CHANGE, STAND_RSN,
                                    tuple(SPIKE_MULT), (False, True)):
        regime = dict(FIXED, regime_d1=d1, regime_d1_subtype=d1s, regime_h4=h4,
                      regime_h4_subtype=h4s, timeframe_conflict=conflict,
                      conflict_type=_conflict_type(d1, h4, conflict),
                      news_gate=NEWS[gating], filter_block=fblock, atr_vs_avg=ratio,
                      h4_change_pips_10=chg, stand_down_reason=rsn,
                      atr_spike_multiplier=SPIKE_MULT[inst], atr_compression=comp)
        key = "|".join(map(str, (d1, d1s, h4, h4s, dec, int(conflict), int(gating), fblock,
                                 ratio, chg, STAND_RSN.index(rsn), inst, int(comp))))
        yield key, regime, dec


def summarize(is_target):
    """Render every cell. `is_target(reason)` marks target cells."""
    import decision_brief as db
    targets, rows, n = [], [], 0
    for key, regime, dec in cells():
        reason = db._render_reason(regime, {"reason": ""}, dec, False)
        n += 1
        if is_target(reason):
            targets.append(key)
        else:
            rows.append(key + "\t" + hashlib.sha256(reason.encode()).hexdigest())
    targets.sort()
    rows.sort()
    return {
        "cells": n,
        "targets": len(targets),
        "target_keys_sha256": hashlib.sha256("\n".join(targets).encode()).hexdigest(),
        "non_target_sha256": hashlib.sha256("\n".join(rows).encode()).hexdigest(),
    }, targets, rows


if __name__ == "__main__":
    summary, targets, _ = summarize(lambda r: r.startswith(TARGET_PREFIX))
    summary["has_conflict_path"] = any(k.split("|")[5] == "1" for k in targets)
    summary["has_stand_down_path"] = any(k.split("|")[5] == "0" for k in targets)
    print(json.dumps(summary, indent=2))
