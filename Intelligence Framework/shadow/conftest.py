"""
conftest.py for the quarantined shadow stack.

Puts both this shadow/ directory and the project root on sys.path so the
quarantined modules (which import each other by bare name AND import live-core
modules from the root) resolve when their tests run. The live suite does not
import anything here.
"""
import os
import sys

_here = os.path.dirname(os.path.abspath(__file__))
for _p in (_here, os.path.dirname(_here)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
