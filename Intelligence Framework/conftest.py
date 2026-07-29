"""
conftest.py — pytest bootstrap for the Intelligence Framework.

Ensures the repo root is importable regardless of the directory pytest is
invoked from, so `import regime_detection` etc. resolve without installation.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
