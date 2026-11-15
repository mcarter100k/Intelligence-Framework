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
from _paths import ROOT
import ast
import os
import re
import sys

from _paths import ROOT as _ROOT
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import artifact_freshness as af

# The PROTECTED live core: exactly AGENTS.md's protected list, enforced by
# test_live_core_is_exactly_the_agents_md_protected_list below.
LIVE_CORE = [
    "decision_brief.py", "run_outcome_check.py", "regime_detection.py",
    "official_decision.py", "no_trade_filter.py",
    "regime_classifier_logger.py", "trade_outcome_logger.py",
    "shadow_signals.py", "session_memory.py", "entry_confirmation.py",
    "levels_context.py", "intraday_context.py", "oanda_feed.py",
    "news_gate.py", "calendar_fetch.py", "setup_check.py",
    "session_guard.py", "risk_config.py", "display_time.py",
    "exclusions.py",          # added 2026-09-16, exclusion_registry_spec.md
    "ledger_io.py",           # protected 2026-09-30; missing here until 2026-10-18
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
# ("imports NOTHING from shadow/", "PROMOTED out of shadow/"). Flagging
# those would pressure authors to delete
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


def _agents_protected_block():
    """The module names in AGENTS.md's PROTECTED code block."""
    text = open(os.path.join(_ROOT, "AGENTS.md"), encoding="utf-8").read()
    block = text.split("## PROTECTED", 1)[1].split("```", 2)[1]
    return set(re.findall(r"\b[a-z_]+\.py\b", block))


def test_live_core_is_exactly_the_agents_md_protected_list():
    """LIVE_CORE is what the guards scan; AGENTS.md is what review protects.
    They drifted once: ledger_io.py was protected but never scanned."""
    assert set(LIVE_CORE) == _agents_protected_block()


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
        "trades.csv", ".env", "excluded_rows.csv", "trade_log.csv",
        "trade_signal_log.csv",     # 2026-11-15, alert_importance_spec N7
    ]


# ══════════════════════════════════════════════════════════════════════════════
# PART 2 — orphan detection (docs/specs/evidence_loop_repair_spec.md)
#
# ROOT CAUSE this test exists for: the 2026-07-29 quarantine was audited
# ONE-DIRECTIONALLY — what shadow/ imports was checked; what imports shadow's
# functions, and what consumes artifacts shadow writes, was not. Three severed
# connections followed from that single omission (log_regime 2026-09-09,
# last_run.json and trade_signal_log 2026-09-16). This runs the audit in the
# other direction, automatically.
#
# Built with the four things the Step 2 inventory proved are required. The
# first two are not hypothetical: both produced real false positives during
# that pass, and either would have condemned working code.
#   1. alias-resolved imports   — `import apply_filter as _apply_filter`
#   2. indirect dispatch        — values in a list/dict, called through a loop
#   3. __main__ entry points    — reachable with no importer
#   4. an allowlist with a REASON per entry
# ══════════════════════════════════════════════════════════════════════════════

SUPPORT_FILES = [
    "scripts/artifact_freshness.py", "scripts/health_state.py",
    "scripts/latest_view.py", "scripts/daily_digest.py",
    "trade_logger.py", "trade_management.py",
]

# Orphans that are CORRECT. A bare name is not allowed here — every entry
# carries the reason it is legitimately unreferenced. Plain dead code is
# deleted, not allowlisted (2026-09-29 audit).
ORPHAN_ALLOWLIST = {
    "get_size_note": "risk_config display helper; unused pending the "
                     "circuit-breaker enforcement spec",
    "format_grade_block": "risk_config display helper; same pending spec",
    "print_risk_rules": "risk_config display helper; same pending spec",
    "calculate_lot_size": "test-only; unused pending the breaker wiring",
    "can_trade": "test-only; unused pending the circuit-breaker gate spec",
    "append_exclusion": "authoring path, used by tests and by the "
                        "one-off seeding of an authorized exclusion. "
                        "Deliberately NOT called by any grader — a grader "
                        "that could write its own exclusions is the whole "
                        "failure mode this registry exists to prevent.",
}

ARTIFACT_ALLOWLIST = {
    "storylines.md": "CORRECTLY writer-less — a human writes it in the "
                     "Sunday session; its 216h freshness cadence is the "
                     "control. Never 'fix' this one.",
}


def _alias_map(tree):
    """local name -> original name, for `import x as y` in either form."""
    out = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for a in node.names:
                if a.asname:
                    out[a.asname] = a.name
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.asname:
                    out[a.asname] = a.name.split(".")[-1]
    return out


def _referenced_names(files):
    """Every name CALLED or referenced AS A VALUE across `files`.

    Referencing as a value is what makes indirect dispatch visible:
    `_CANDIDATES = [check_thrust_pullback, ...]` never calls the name, and a
    call-only scan reports the frozen candidates as dead.
    """
    seen = set()
    for rel in files:
        path = os.path.join(_ROOT, rel)
        if not os.path.exists(path):
            continue
        try:
            tree = ast.parse(_source(rel), filename=rel)
        except SyntaxError:
            continue
        alias = _alias_map(tree)
        for node in ast.walk(tree):
            nm = None
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                nm = node.id
            elif isinstance(node, ast.Attribute):
                nm = node.attr
            if nm:
                seen.add(nm)
                if nm in alias:
                    seen.add(alias[nm])
    return seen


def _live_corpus():
    return LIVE_CORE + [f for f in SUPPORT_FILES
                        if os.path.exists(os.path.join(_ROOT, f))]


def _public_functions(module):
    tree = ast.parse(_source(module), filename=module)
    return [n.name for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
            and not n.name.startswith("_")]


def test_no_unallowlisted_function_orphans():
    """A live-core function with no live producer/consumer, not allowlisted
    with a reason, is a severed connection — fail until it is wired or
    consciously listed."""
    referenced = _referenced_names(_live_corpus())
    orphans = []
    for module in LIVE_CORE:
        for fn in _public_functions(module):
            if fn in referenced or fn in ORPHAN_ALLOWLIST:
                continue
            orphans.append(f"{module}:{fn}()")
    assert not orphans, (
        "live-core functions with no live caller and no allowlist reason "
        "(wire them, or add an entry to ORPHAN_ALLOWLIST saying why the "
        "orphan is correct):\n  " + "\n  ".join(orphans))


def test_every_allowlist_entry_carries_a_reason():
    """A bare name in the allowlist is how a guard rots into a rubber stamp."""
    for table in (ORPHAN_ALLOWLIST, ARTIFACT_ALLOWLIST):
        for name, reason in table.items():
            assert isinstance(reason, str) and len(reason.strip()) >= 20, (
                f"allowlist entry {name!r} needs a real written reason")


def test_alias_resolution_is_live_not_orphan():
    """REGRESSION PIN — false positive #1 from the Step 2 pass.

    regime_detection imports apply_filter under an alias. A call-only,
    alias-blind scan reports it as dead, and apply_filter is one of the two
    suite floors. (get_filter_summary, once pinned here too, was removed
    2026-10-18: its only output was a key nothing read.)
    """
    referenced = _referenced_names(_live_corpus())
    assert "apply_filter" in referenced


def test_indirect_dispatch_is_live_not_orphan():
    """REGRESSION PIN — false positive #2 from the Step 2 pass.

    shadow_signals.py:218 holds the three FROZEN candidates in _CANDIDATES
    and dispatches `for fn in _CANDIDATES`. A call-only scan reports the
    evidence ledger as having stopped accruing.
    """
    referenced = _referenced_names(_live_corpus())
    for fn in ("check_early_momentum_v2", "check_thrust_pullback",
               "check_momentum_join"):
        assert fn in referenced, f"{fn} is dispatched via _CANDIDATES"


def test_cli_entry_points_are_reachable():
    """A __main__ block makes a module reachable with no importer."""
    for module in ("setup_check.py", "decision_brief.py",
                   "run_outcome_check.py"):
        src_ = _source(module)
        assert ('__name__ == "__main__"' in src_
                or "__name__ == '__main__'" in src_), module


def test_orphan_detector_catches_a_synthetic_orphan():
    """The guard must be shown to fire."""
    referenced = _referenced_names(_live_corpus())
    assert "a_function_nobody_calls_xyzzy" not in referenced


def test_every_live_read_artifact_has_a_live_writer():
    """The artifact half — D1's actual shape. A live module reading a file
    nothing live writes is the defect that cost 98 days."""
    inventoried = ({rel for rel, _ in af.CADENCES}
                   | {rel for rel, _ in af.READ_SIDE_NO_CADENCE}
                   | WRITE_ONLY_OK | set(ARTIFACT_ALLOWLIST))
    unknown = set()
    for module in LIVE_CORE:
        for lit in set(_ARTIFACT_LITERAL.findall(_source(module))):
            if os.path.basename(lit) not in inventoried:
                unknown.add(lit)
    assert not unknown, (
        "live-core artifact with no inventory entry and no allowlist "
        f"reason: {sorted(unknown)}")


def test_trade_signal_ledger_is_now_watched(tmp_path):
    """The Step 2 finding, pinned: neither ledger was watched, which is how
    trade_signal_log.csv sat at 2 lines since 2026-06-28 while
    run_outcome_check graded it nightly."""
    # Old -> new 2026-11-15 (alert_importance_spec N7): watched by a cadence
    # until then; now by agreement_lines(), which fails when a regime-log
    # trade call has no trade row (positive control in test_artifact_freshness).
    watched = {rel for rel, _ in af.CADENCES}
    assert "trade_signal_log.csv" not in watched
    assert "trade_signal_log.csv" in {rel for rel, _ in af.READ_SIDE_NO_CADENCE}
    import time
    t = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 3600))
    (tmp_path / "regime_classification_log.csv").write_text(
        f"timestamp,instrument,stand_down,logic_version\n{t},GBP_JPY,False,p5-2026-09-30\n")
    (tmp_path / "trade_signal_log.csv").write_text("signal_id,timestamp,instrument\n")
    assert af.agreement_lines(proj=str(tmp_path))[0].startswith("STALE: trade_signal_log.csv")
    # trade_log.csv is inventoried WITHOUT a cadence: it is frozen
    # historical evidence (April-era snapshot schema, superseded by
    # trades.csv, ruled untouched by trade_logger_repair_spec.md:23-28).
    # A cadence would render STALE forever — 3987h at first check — making
    # every scheduled run a health FAILURE. Accounted for, never alarming.
    no_cadence = {rel for rel, _ in af.READ_SIDE_NO_CADENCE}
    assert "trade_log.csv" in no_cadence
    assert "trade_log.csv" not in watched


def test_log_signal_is_wired_into_the_live_path():
    """PART 1 pin: the orphaned writer now has a live caller."""
    src_ = _source("decision_brief.py")
    code = "\n".join(ln.split("#", 1)[0] for ln in src_.splitlines())
    assert "log_signal" in code, "decision_brief must call log_signal"
    referenced = _referenced_names(_live_corpus())
    assert "log_signal" in referenced
