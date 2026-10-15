"""Does a FRESH Claude Code session invoke our skills on its own?

Each prompt runs in its own headless session (`claude -p`, stream-json) from
a scratch directory, with every tool that can change anything disallowed.
A run "triggered" a skill if the stream contains a Skill tool_use whose
input names it. Results go to results.json and a printed table.
Usage: python run_trigger_eval.py <claude-binary> <runs-per-prompt>
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

CLAUDE, RUNS = sys.argv[1], int(sys.argv[2])
HERE = os.path.dirname(os.path.abspath(__file__))
CWD = os.path.join(HERE, "cwd")
os.makedirs(CWD, exist_ok=True)

EVALS = [
    ("evidence-validation", "I just finished fixing the file-locking bug in my ledger code. Write me a short status report saying it's done and verified."),
    ("evidence-validation", "did we fully validate the backup feature? are you sure it actually works?"),
    ("evidence-validation", "The tests pass now so the header migration is fixed, right? Confirm it's safe to merge."),
    ("trading-foundation", "I'm thinking about trading GBP/AUD breakouts after a tight consolidation box on the H4 chart. Is that an edge?"),
    ("trading-foundation", "Help me set up a weekly review process for my FX trades and my trade journal."),
    ("trading-foundation", "My backtest of this EUR/JPY setup shows a 62% win rate over 45 trades. Is that good enough to go live?"),
    ("trading-foundation", "I need to add a thrust filter to the M15 engulfing check in entry_confirmation.py. Write the patch."),
    ("trading-foundation", "Refactor the grading loop in shadow_signals.py so it writes the ledger in one pass."),
    ("trading-foundation", "The regime logger is missing a column. Add it and update the header."),
    (None, "Write a Python function that reverses a singly linked list."),
    (None, "What's the capital of Australia?"),
    (None, "Explain what a moving average is in one short paragraph."),
]
DENY = "Bash,Edit,Write,NotebookEdit,WebFetch,WebSearch,Agent,Workflow"


def run(prompt):
    try:
        p = subprocess.run(
            [CLAUDE, "-p", prompt, "--output-format", "stream-json", "--verbose",
             "--max-turns", "4", "--disallowedTools", DENY],
            cwd=CWD, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=240)
        out = p.stdout
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
    invoked, loaded_ok = [], None
    for line in out.splitlines():
        try:
            ev = json.loads(line)
        except Exception:
            continue
        if ev.get("type") == "system" and ev.get("subtype") == "init":
            loaded_ok = all(s in (ev.get("skills") or []) for s in ("evidence-validation", "trading-foundation"))
        if ev.get("type") == "assistant":
            for block in ev.get("message", {}).get("content", []):
                if block.get("type") == "tool_use" and block.get("name") == "Skill":
                    invoked.append(str(block.get("input", {}).get("skill", "")))
    return {"invoked": invoked, "skills_listed_at_start": loaded_ok}


jobs = [(exp, pr) for exp, pr in EVALS for _ in range(RUNS)]
with ThreadPoolExecutor(max_workers=3) as ex:
    outs = list(ex.map(lambda j: run(j[1]), jobs))
results = [{"expected": e, "prompt": p, **o} for (e, p), o in zip(jobs, outs)]
json.dump(results, open(os.path.join(HERE, "results.json"), "w"), indent=2)
for r in results:
    ours = [s for s in r["invoked"] if s in ("evidence-validation", "trading-foundation")]
    ok = (r["expected"] in ours) if r["expected"] else not ours
    print(f"{'PASS' if ok else 'FAIL'}  expected={str(r['expected']):20s} invoked={r['invoked']!s:40s} "
          f"listed={r['skills_listed_at_start']}  | {r['prompt'][:60]}")
