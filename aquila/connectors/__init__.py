"""
Data source connectors for Aquila Insights.
Auto-loads aquila_graph.env at import time.

Usage:
    from aquila.connectors import get_supabase_client, get_gsheets_client, fetch_fred_series
"""

import os
from dotenv import load_dotenv

# Auto-load credentials on first import
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ENV_PATH = os.path.join(_REPO_ROOT, "aquila_graph.env")
load_dotenv(_ENV_PATH)

# Re-export connectors for convenience
from .supabase import get_supabase_client  # noqa: E402
from .gsheets import get_gsheets_client    # noqa: E402
from .fred import fetch_fred_series        # noqa: E402
