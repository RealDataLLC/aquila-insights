"""
Supabase PostgreSQL connector.
Consolidates the 4 different implementations across the codebase.

Most tables (market_tables_office, market_tables_industrial, quarterly_report_data_*)
require the service role key (SUPABASE_KEY), not the anon key (SUPABASE_PUBLIC_KEY).
"""

import os


def get_supabase_client(use_service_role=True):
    """
    Create and return an authenticated Supabase client.

    Parameters
    ----------
    use_service_role : bool, default True
        If True, uses SUPABASE_KEY (service role) for full table access.
        If False, uses SUPABASE_PUBLIC_KEY (anon key) which is subject to RLS.

    Returns
    -------
    supabase.Client
        Authenticated Supabase client.

    Raises
    ------
    ValueError
        If required environment variables are missing.

    Examples
    --------
    >>> from aquila.connectors import get_supabase_client
    >>> supabase = get_supabase_client()
    >>> response = supabase.table('market_tables_office').select('*').execute()
    """
    from supabase import create_client

    url = os.getenv("SUPABASE_URL")

    if use_service_role:
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

    else:
        key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        #

    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY must be set in aquila_graph.env"
        )

    #print(f"Using Supabase Key: {key}")

    return create_client(url, key)
