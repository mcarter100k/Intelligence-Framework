"""
audit_probe.py — interpreter-level pytest probe that tests cannot patch around.

Records every non-local network name lookup and every file opened for writing
outside temp directories, attributed to the test that did it. It uses
sys.addaudithook, so a monkeypatched socket or open() cannot hide a call.

Prove it can see before trusting a clean result. Run it once on a planted
violation (see SKILL.md, "positive control").

Usage:
  AUDIT_PROJECT=/path/to/project AUDIT_OUT=/tmp/audit.json \
  PYTHONPATH=/path/to/this/scripts \
  python -m pytest -p audit_probe [pytest args]
  python audit_report.py /tmp/audit.json
"""
import json
import os
import sys
import tempfile

import pytest

_cur = {"id": "(collection/session)"}
LOOKUPS, WRITES = [], []
_TMP = tuple(os.path.realpath(p) for p in (
    tempfile.gettempdir(), "/private/var/folders", "/private/tmp",
    "/var/folders", "/tmp"))
_PROJECT = os.path.realpath(os.environ["AUDIT_PROJECT"])
_LOCAL = {"localhost", "127.0.0.1", "::1", None, ""}


def _hook(event, args):
    if event == "socket.getaddrinfo":
        host = args[0].decode() if isinstance(args[0], bytes) else args[0]
        if host not in _LOCAL:
            LOOKUPS.append((_cur["id"], str(host)))
    elif event == "open":
        path, mode = args[0], args[1]
        if isinstance(path, int) or mode is None:
            return
        if isinstance(mode, str) and not any(c in mode for c in "wax+"):
            return
        if isinstance(mode, int) and not (
                mode & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND)):
            return
        p = os.path.realpath(os.fsdecode(path))
        in_project = p.startswith(_PROJECT + os.sep)
        if in_project and "/__pycache__/" in p:
            return
        if in_project or not p.startswith(_TMP):
            WRITES.append((_cur["id"], p))


sys.addaudithook(_hook)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    _cur["id"] = item.nodeid
    yield
    _cur["id"] = "(collection/session)"


def pytest_unconfigure(config):
    with open(os.environ["AUDIT_OUT"], "w") as f:
        json.dump({"lookups": LOOKUPS, "writes": WRITES}, f)
