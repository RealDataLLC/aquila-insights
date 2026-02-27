"""
Chart generators organized by domain.
Adds repo root to sys.path so generators can import from aquila/ and aquila_graphing_tools.
"""
import sys
import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
