"""
alert_state.py — what is worth telling the owner (docs/specs/alert_importance_spec.md).

  python3 scripts/alert_state.py decisions "<DSTATE>"
      N5. DSTATE is the brief wrapper's per-pair state, e.g.
      "GBP_AUD=LONG/open;GBP_JPY=STAND ASIDE/closed". Prints one line naming
      every open pair whose decision CHANGED since its last open-market
      record (a new LONG/SHORT, a reversal, or a withdrawal back to stand
      aside), or nothing. Closed pairs and error briefs are neither reported
      nor recorded.

  python3 scripts/alert_state.py gates
      N4. Reads each candidate's graded independent episodes
      (shadow_signals.get_shadow_tally) and whether the market is open
      (regime_detection._market_status, the function behind the brief's
      closed banner). Prints one line per candidate that first reached a
      review gate (20 futility, 30 flag, 60 decision) and has not been
      announced, only when the market is open; otherwise nothing.

State: logs/alert_state.json = {"decisions": {pair: decision},
"gates": {candidate: last announced gate}}, read and written under
ledger_io.locked. Exit 0 with the answer on stdout; exit 3 with the reason on
stderr if anything fails, so the caller can fall back loudly instead of
silently dropping a notification.
"""
from __future__ import annotations

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

STATE_FILE = os.path.join(_ROOT, "logs", "alert_state.json")
DIRECTIONAL = ("LONG", "SHORT")
KNOWN = DIRECTIONAL + ("STAND ASIDE",)
CANDIDATES = ("EARLY_MOMENTUM", "EARLY_MOMENTUM_v2", "THRUST_PULLBACK", "MOMENTUM_JOIN")
GATES = {20: "the futility checkpoint is due (docs/specs/futility_rule_spec.md)",
         30: "the review flag is due",
         60: "the decision review is due"}


def parse_dstate(dstate: str) -> list:
    """[(pair, decision, is_open)] from "GBP_AUD=LONG/open;GBP_JPY=..."."""
    out = []
    for part in filter(None, (dstate or "").split(";")):
        pair, _, rest = part.partition("=")
        decision, _, status = rest.rpartition("/")
        out.append((pair.strip(), decision.strip(), status.strip() == "open"))
    return out


def decision_changes(dstate: str, record: dict) -> tuple:
    """(messages, new record). Pure; the record is not mutated."""
    record = dict(record)
    msgs = []
    for pair, decision, is_open in parse_dstate(dstate):
        if not is_open or decision not in KNOWN:
            continue                                  # closed or error: no report, no record
        name = pair.replace("_", "/")
        prior = record.get(pair)
        if decision in DIRECTIONAL:
            if prior == decision:
                pass
            elif prior in DIRECTIONAL:
                msgs.append(f"{name} {decision} (was {prior})")
            else:
                msgs.append(f"{name} {decision}")
        elif prior in DIRECTIONAL:
            msgs.append(f"{name} back to stand aside — the {prior} idea is withdrawn")
        record[pair] = decision
    return msgs, record


def gate_announcements(episodes: dict, market_open: bool, announced: dict) -> tuple:
    """(messages, new announced). A gate reached while closed stays
    unannounced, so the next open run reports it."""
    announced = dict(announced)
    msgs = []
    if not market_open:
        return msgs, announced
    for cand in sorted(episodes):
        n = episodes[cand]
        reached = max((g for g in GATES if n >= g), default=0)
        if reached > announced.get(cand, 0):
            msgs.append(f"{cand} reached {reached} graded episodes: {GATES[reached]}")
            announced[cand] = reached
    return msgs, announced


def _load() -> dict:
    if not os.path.exists(STATE_FILE):
        return {"decisions": {}, "gates": {}}
    with open(STATE_FILE) as f:
        d = json.load(f)
    return {"decisions": d.get("decisions", {}), "gates": d.get("gates", {})}


def _save(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=1, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, STATE_FILE)


def _live_inputs() -> tuple:
    from regime_detection import _market_status
    from shadow_signals import get_shadow_tally
    return ({c: int(get_shadow_tally(c)["episodes"]) for c in CANDIDATES},
            bool(_market_status()["open"]))


def main(argv) -> int:
    from ledger_io import locked
    try:
        if len(argv) == 3 and argv[1] == "decisions":
            with locked(STATE_FILE):
                state = _load()
                msgs, state["decisions"] = decision_changes(argv[2], state["decisions"])
                _save(state)
            if msgs:
                print(" · ".join(msgs))
            return 0
        if len(argv) == 2 and argv[1] == "gates":
            episodes, market_open = _live_inputs()
            with locked(STATE_FILE):
                state = _load()
                msgs, state["gates"] = gate_announcements(episodes, market_open, state["gates"])
                _save(state)
            for m in msgs:
                print(m)
            return 0
        print(__doc__, file=sys.stderr)
        return 3
    except Exception as e:                            # caller falls back loudly
        print(f"alert_state failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv))
