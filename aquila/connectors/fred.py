"""
FRED (Federal Reserve Economic Data) API connector.
Consolidates the 2 duplicated fetch implementations.
"""

import os
import pandas as pd
import requests


def fetch_fred_series(series_id, series_name=None):
    """
    Fetch a FRED time series and return as a DataFrame.

    Parameters
    ----------
    series_id : str
        FRED series identifier (e.g., 'AUST448BPPRIV').
    series_name : str, optional
        Name for the value column. Defaults to series_id.

    Returns
    -------
    pd.DataFrame
        DataFrame with 'date' and series_name columns. Empty if fetch fails.

    Raises
    ------
    ValueError
        If FRED_API_KEY is not set in environment.

    Examples
    --------
    >>> from aquila.connectors import fetch_fred_series
    >>> df = fetch_fred_series('AUST448BPPRIV', 'Austin Housing Starts')
    """
    fred_api_key = os.getenv('FRED_API_KEY')
    if not fred_api_key:
        raise ValueError("FRED_API_KEY must be set in aquila_graph.env")

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": fred_api_key,
        "file_type": "json",
    }

    column_name = series_name if series_name else series_id

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        observations = data.get("observations", [])

        if not observations:
            print(f"    Warning: No data returned for series {series_id}")
            return pd.DataFrame()

        df = pd.DataFrame(observations)
        df['date'] = pd.to_datetime(df['date'])

        # Convert value to numeric, handling '.' as NaN
        df['value'] = pd.to_numeric(df['value'], errors='coerce')

        # Rename value column to series name
        df = df[['date', 'value']].rename(columns={'value': column_name})

        # Drop NaN values
        df = df.dropna()

        print(f"    [OK] Fetched {len(df)} observations for {series_id} ({column_name})")
        return df

    except Exception as e:
        print(f"    [ERROR] Failed to fetch {series_id}: {e}")
        return pd.DataFrame()
