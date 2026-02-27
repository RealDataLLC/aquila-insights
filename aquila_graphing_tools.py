"""
Backward-compatibility shim.

All shared logic now lives in the `aquila` package:
    aquila/brand.py       - AQUILA_COLORS, AQUILA_FONT, named aliases
    aquila/connectors/    - Supabase, Google Sheets, FRED API
    aquila/charts.py      - aquila_styled_line_chart
    aquila/dateutil.py    - parse_quarter, quarter_sort_key
    aquila/git.py         - commit_and_push_all

This file re-exports the same public API so existing scripts continue to work
without any import changes.
"""

# ── Brand constants ───────────────────────────────────────────────────────────
from aquila.brand import AQUILA_COLORS, AQUILA_FONT  # noqa: F401

# ── Supabase ──────────────────────────────────────────────────────────────────
from aquila.connectors.supabase import get_supabase_client  # noqa: F401


def initialize_supabase_connection():
    """Backward-compat wrapper. Prefer `from aquila.connectors import get_supabase_client`."""
    return get_supabase_client(use_service_role=True)


# ── Charts ────────────────────────────────────────────────────────────────────
from aquila.charts import aquila_styled_line_chart  # noqa: F401

# ── Git ───────────────────────────────────────────────────────────────────────
from aquila.git import commit_and_push_all  # noqa: F401
