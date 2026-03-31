"""
Data source connectors for Aquila Insights.
Auto-loads aquila_graph.env at import time.

Usage:
    from aquila.connectors import get_supabase_client, get_gsheets_client, fetch_fred_series
"""

import os
from dotenv import load_dotenv


def _find_env_file():
    """Walk up from this file to find aquila_graph.env (handles git worktrees)."""
    current = os.path.dirname(os.path.abspath(__file__))
    for _ in range(8):
        candidate = os.path.join(current, "aquila_graph.env")
        if os.path.exists(candidate):
            return candidate
        current = os.path.dirname(current)
    # Fallback: original behaviour (relative to package root)
    pkg_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(pkg_root, "aquila_graph.env")


_ENV_PATH = _find_env_file()
load_dotenv(_ENV_PATH)

# Re-export connectors for convenience
from .supabase import get_supabase_client  # noqa: E402
from .gsheets import get_gsheets_client    # noqa: E402
from .fred import fetch_fred_series        # noqa: E402
from .skyline import fetch_all_leases     # noqa: E402
from .census import (                      # noqa: E402
    fetch_acs_by_zcta, fetch_tracts_acs, fetch_acs_multiyear,
    fetch_acs_msa, fetch_lodes_wac, fetch_qcew, fetch_tiger_centroids,
    POPULATION, MEDIAN_HH_INCOME, MEDIAN_AGE, AVG_HOUSEHOLD_SIZE,
    AUSTIN_COUNTIES, AUSTIN_COUNTY_PREFIXES, LODES_OFFICE_COLS,
    TIGER_TRACTS, TIGER_BLOCK_GROUPS,
)
