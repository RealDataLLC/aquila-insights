"""
Aquila Insights - Shared utilities for branded chart generation.

Quick imports:
    from aquila import AQUILA_COLORS, AQUILA_FONT
    from aquila.brand import NAVY, COPPER, BRASS  # Named aliases
    from aquila.connectors import get_supabase_client, get_gsheets_client, fetch_fred_series
    from aquila.dateutil import parse_quarter, quarter_sort_key
    from aquila.charts import aquila_styled_line_chart
    from aquila.git import commit_and_push_all
"""

from .brand import AQUILA_COLORS, AQUILA_FONT  # noqa: F401
