"""
Census ACS (American Community Survey) API connector.
Fetches demographic data by ZCTA (zip code tabulation area) for Texas.
"""

import os
import pandas as pd
import requests


ACS_BASE = "https://api.census.gov/data/{year}/acs/acs5"

# Common ACS variable codes
POPULATION = "B01003_001E"
MEDIAN_HH_INCOME = "B19013_001E"
MEDIAN_AGE = "B01002_001E"
AVG_HOUSEHOLD_SIZE = "B25010_001E"


def fetch_acs_by_zcta(variables, year=2023, state="48"):
    """
    Fetch ACS 5-year estimates by ZCTA for a given state.

    Parameters
    ----------
    variables : list[str]
        ACS variable codes (e.g., ['B01003_001E', 'B19013_001E']).
    year : int, default 2023
        ACS release year (uses 5-year estimates).
    state : str, default "48"
        FIPS state code (48 = Texas).

    Returns
    -------
    pd.DataFrame
        DataFrame with 'zcta' column and one column per variable.
        Values are numeric (NaN for missing/negative).

    Raises
    ------
    ValueError
        If CENSUS_API_KEY is not set in environment.

    Examples
    --------
    >>> from aquila.connectors.census import fetch_acs_by_zcta, POPULATION
    >>> df = fetch_acs_by_zcta([POPULATION], year=2023)
    """
    key = os.getenv("CENSUS_API_KEY")
    if not key:
        raise ValueError("CENSUS_API_KEY must be set in aquila_graph.env")

    # Note: ZCTA queries don't support 'in state:' filter in ACS API.
    # Fetch all US ZCTAs and filter downstream in pandas.
    params = {
        "get": ",".join(["NAME"] + variables),
        "for": "zip code tabulation area:*",
        "key": key,
    }

    try:
        resp = requests.get(ACS_BASE.format(year=year), params=params)
        resp.raise_for_status()
        data = resp.json()

        headers = data[0]
        rows = data[1:]

        df = pd.DataFrame(rows, columns=headers)
        df = df.rename(columns={"zip code tabulation area": "zcta"})

        for var in variables:
            df[var] = pd.to_numeric(df[var], errors="coerce")

        # ACS uses negative values for missing/suppressed data
        for var in variables:
            df.loc[df[var] < 0, var] = pd.NA

        print(f"  [OK] Fetched {len(df)} ZCTAs from ACS {year} ({len(variables)} variables)")
        return df

    except Exception as e:
        print(f"  [ERROR] Census ACS fetch failed: {e}")
        return pd.DataFrame()
