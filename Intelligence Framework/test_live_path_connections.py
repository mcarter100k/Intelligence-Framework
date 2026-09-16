"""
test_live_path_connections.py — connection-shaped tests for the live core
(docs/specs/level_source_repair_spec.md, guards A and B).

WHY THIS FILE EXISTS. Every defect in the 2026-09-16 finding was a
CONNECTION bug, not a component bug: a reader whose writer had been
quarantined, a pair argument that was never threaded, a function whose
signature lied about being pair-specific. Every one of those modules had
passing component tests throughout. The suite was component-shaped and
the defects lived between components, so they survived 98 days.

HONEST LIMIT OF GUARD B — stated here so this test is never mistaken for
the control it resembles. The quarantine-boundary test below would NOT
have caught the primary defect. `entry_confirmation` read
`last_run.json`: a bare filename at the repo root, containing no
`shadow/` substring anywhere. The artifact was WRITTEN by a quarantined
module but did not LIVE in a quarantined path, so no path-based check
could see it.

The control that would have caught it is orphan detection — every file
artifact a live module reads must have a live writer — which requires
the read/write map that Step 2's integration inventory produces. The
spec recommends promoting that rule into a test once Step 2 reports.
Guard B closes a real hole; it is a narrower one than the finding
exposed.
"""
import ast
import os
import re
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import artifact_freshness as af

# The PROTECTED live core, per AGENTS.md. Kept in sync by
# test_live_core_list_is_accurate below.
LIVE_CORE = [
    "decision_brief.py", "run_outcome_check.py", "regime_detection.py",
    "official_decision.py", "no_trade_filter.py",
    "regime_classifier_logger.py", "trade_outcome_logger.py",
    "shadow_signals.py", "session_memory.py", "entry_confirmation.py",
    "levels_context.py", "intraday_context.py", "oanda_feed.py",
    "news_gate.py", "calendar_fetch.py", "setup_check.py",
    "session_guard.py", "risk_config.py", "display_time.py",
]

# Artifacts a live module only ever WRITES — nothing on the live path
# reads them back, so a freshness cadence would watch a one-way street.
# Adding to this list is a classification decision, not a drive-by edit.
WRITE_ONLY_OK = {
    "pre_trade_journal.csv",   # setup_check appends; no live reader
    "trade_signal_log.csv",    # trade_outcome_logger appends; no live reader
}

_ARTIFACT_LITERAL = re.compile(
    r'["\']([A-Za-z0-9_./-]+\.(?:csv|json|md|log|env))["\']')

# A quarantine-zone reference that actually RESOLVES somewhere: the zone
# followed by a real path segment. Deliberately does not match a bare
# "shadow/" in prose — live modules legitimately explain the boundary
# ("imports NOTHING from shadow/", "PROMOTED out of shadow/"), and
# run_outcome_check prints a warning naming legacy_validators/ to steer
# the reader AWAY from it. Flagging those would pressure authors to delete
# exactly the documentation that keeps the boundary legible.
_QUARANTINE_PATH = re.compile(
    r"(?:shadow|legacy_validators)/[A-Za-z0-9_-][A-Za-z0-9_./-]*")


def _source(module: str) -> str:
    with open(os.path.join(_ROOT, module), encoding="utf-8") as f:
        return f.read()


def _quarantine_offenders(src: str, name: str) -> list:
    """Quarantine-path references in EXECUTABLE code (docstrings excluded)."""
    tree = ast.parse(src, filename=name)
    skip = {id(d) for d in _docstring_nodes(tree)}
    out = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and id(node) not in skip
                and _QUARANTINE_PATH.search(node.value)):
            out.append(f"{name}:{node.lineno}: {node.value.strip()[:80]}")
    return out


def _docstring_nodes(tree: ast.AST):
    """The Constant nodes that are docstrings — prose, never executed."""
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef,
                                 ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", None)
        if (body and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)):
            yield body[0].value


def test_live_core_list_is_accurate():
    """Every named module exists. A rename that misses this list would
    otherwise silently shrink the surface the guards below cover."""
    missing = [m for m in LIVE_CORE
               if not os.path.exists(os.path.join(_ROOT, m))]
    assert not missing, f"LIVE_CORE names modules that do not exist: {missing}"
    assert len(LIVE_CORE) == len(set(LIVE_CORE))


def test_no_live_module_touches_quarantine():
    """GUARD B: no live-core module may name a path under shadow/ or
    legacy_validators/ in EXECUTABLE code — file artifacts included, not
    just imports. Their priors are not evidence (AGENTS.md).

    Scans string constants via AST, excluding docstrings: comments and
    docstrings never execute, and live modules legitimately cite
    `shadow/market_brain.py` when explaining why a boundary exists. A
    guard that forced those explanations to be deleted would make the
    boundary less legible, not better enforced.
    """
    offenders = []
    for module in LIVE_CORE:
        offenders += _quarantine_offenders(_source(module), module)
    assert not offenders, (
        "live-core module references a quarantined path:\n  "
        + "\n  ".join(offenders))


def test_no_live_module_imports_quarantined_name():
    """The import-shaped half of GUARD B, checked separately so a failure
    names which kind of breach occurred."""
    offenders = []
    bad = re.compile(
        r"^\s*(?:from|import)\s+(?:shadow|legacy_validators)\b", re.M)
    for module in LIVE_CORE:
        for m in bad.finditer(_source(module)):
            offenders.append(f"{module}: {m.group(0).strip()}")
    assert not offenders, (
        "live-core module imports from a quarantine zone:\n  "
        + "\n  ".join(offenders))


def test_every_live_artifact_is_inventoried():
    """GUARD A: every artifact a live-core module names must be accounted
    for — a watched cadence, an explicit no-cadence entry, or a declared
    write-only file. A new artifact cannot enter the live path silently.

    This is the pin for the primary defect's failure mode: last_run.json
    was read by entry_confirmation and inventoried nowhere.
    """
    inventoried = ({rel for rel, _ in af.CADENCES}
                   | {rel for rel, _ in af.READ_SIDE_NO_CADENCE}
                   | WRITE_ONLY_OK)
    unaccounted = {}
    for module in LIVE_CORE:
        for lit in set(_ARTIFACT_LITERAL.findall(_source(module))):
            if os.path.basename(lit) not in inventoried:
                unaccounted.setdefault(lit, []).append(module)
    assert not unaccounted, (
        "live-core artifacts missing from the freshness inventory "
        "(add a cadence, a READ_SIDE_NO_CADENCE reason, or WRITE_ONLY_OK): "
        + str({k: sorted(v) for k, v in unaccounted.items()}))


def test_entry_confirmation_no_longer_reads_last_run_json():
    """Regression pin for DEFECT 1: the orphaned read is gone, and the
    module asks the live level module directly instead."""
    src = _source("entry_confirmation.py")
    code = "\n".join(ln.split("#", 1)[0] for ln in src.splitlines())
    assert "last_run.json" not in code
    assert "get_key_levels(oanda_pair)" in code


def test_no_cadence_entries_never_render_stale(tmp_path):
    """A no-cadence artifact is reported for visibility and can never
    produce a STALE line — otherwise the wrapper would turn normal
    operation (no trades this week) into a health failure."""
    lines = af.read_side_lines(proj=str(tmp_path))     # nothing exists
    assert lines and all(ln.startswith("watched: ") for ln in lines)
    assert not any(ln.startswith("STALE:") for ln in lines)
    assert len(lines) == len(af.READ_SIDE_NO_CADENCE)


def test_guard_b_actually_fires_on_a_real_breach():
    """A guard never shown to fire is not a guard. Synthetic breaches must
    be caught; the prose forms live modules really contain must not be."""
    caught = _quarantine_offenders(
        'import os\n'
        'P = "shadow/last_run.json"\n'
        'Q = open("legacy_validators/validate_adx_threshold.py")\n',
        "fake_breach.py")
    assert len(caught) == 2, caught

    allowed = _quarantine_offenders(
        '"""Lean by design — imports NOTHING from shadow/."""\n'
        'MSG = "Do NOT use the v1 validators in legacy_validators/ — '
        'their output is INVALIDATED."\n'
        'def f():\n'
        '    """PROMOTED out of shadow/ 2026-09-09 per the spec."""\n'
        '    return 1\n',
        "fake_prose.py")
    assert allowed == [], allowed


def test_read_side_inventory_pinned():
    """The read-side boundary is a reviewed decision, like the cadence
    table it sits beside."""
    assert [rel for rel, _ in af.READ_SIDE_NO_CADENCE] == [
        "trades.csv", ".env",
    ]
