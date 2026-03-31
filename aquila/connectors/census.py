"""
Census Bureau data connector.

Covers:
  - ACS 5-Year and 1-Year estimates (ZCTA, tract, MSA level)
  - Census LODES / LEHD Workplace Area Characteristics (block level)
  - BLS QCEW (Quarterly Census of Employment and Wages)
"""

import io
import os
import time
import gzip

import pandas as pd
import requests


ACS_BASE = "https://api.census.gov/data/{year}/acs/{dataset}"
LODES_BASE = "https://lehd.ces.census.gov/data/lodes/LODES8/{state}/wac/{state}_wac_{segment}_{jobtype}_{year}.csv.gz"
QCEW_BASE = "https://data.bls.gov/cew/data/api/{year}/{quarter}/area/{area_fips}.csv"
TIGER_TRACTS = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
    "tigerWMS_ACS2023/MapServer/8/query"
)
# Note: Census Blocks are not in this ACS2023 service. Use Block Groups (layer 10)
# and aggregate LODES 15-digit block GEOIDs to 12-digit block group GEOIDs.
TIGER_BLOCK_GROUPS = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/"
    "tigerWMS_ACS2023/MapServer/10/query"
)

# Common ACS variable codes
POPULATION = "B01003_001E"
MEDIAN_HH_INCOME = "B19013_001E"
MEDIAN_AGE = "B01002_001E"
AVG_HOUSEHOLD_SIZE = "B25010_001E"

# Austin MSA 4-county FIPS (Travis, Williamson, Hays, Bastrop)
AUSTIN_COUNTIES = ["453", "491", "209", "021"]
AUSTIN_COUNTY_PREFIXES = ["48453", "48491", "48209", "48021"]

# LODES office-using industry columns (CNS codes = NAICS sectors)
LODES_OFFICE_COLS = {
    "CNS09": "Information (NAICS 51)",
    "CNS10": "Finance & Insurance (NAICS 52)",
    "CNS12": "Professional Services (NAICS 54)",
    "CNS13": "Management (NAICS 55)",
}


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
        resp = requests.get(ACS_BASE.format(year=year, dataset="acs5"), params=params)
        resp.raise_for_status()
        data = resp.json()

        headers = data[0]
        rows = data[1:]

        df = pd.DataFrame(rows, columns=headers)
        df = df.rename(columns={"zip code tabulation area": "zcta"})

        for var in variables:
            df[var] = pd.to_numeric(df[var], errors="coerce")
            # ACS uses negative values for missing/suppressed data
            df.loc[df[var] < 0, var] = pd.NA

        print(f"  [OK] Fetched {len(df)} ZCTAs from ACS {year} ({len(variables)} variables)")
        return df

    except Exception as e:
        print(f"  [ERROR] Census ACS fetch failed: {e}")
        return pd.DataFrame()


def _fetch_acs_raw(year, variables, geography, dataset="acs5"):
    """
    Internal: fetch one ACS call, return raw DataFrame with geography columns.

    geography may be:
      - A plain 'for' string: "metropolitan statistical area/...:12420"
      - A 'for' string with in-filter: "tract:*&in=state:48 county:453"
        (the '&in=' is detected and split into a separate 'in' param)
    """
    key = os.getenv("CENSUS_API_KEY")
    if not key:
        raise ValueError("CENSUS_API_KEY must be set in aquila_graph.env")
    url = ACS_BASE.format(year=year, dataset=dataset)

    # Split compound geography into for= and in= components
    params = {"get": ",".join(["NAME"] + variables), "key": key}
    if "&in=" in geography:
        for_part, in_part = geography.split("&in=", 1)
        params["for"] = for_part
        params["in"] = in_part
    else:
        params["for"] = geography

    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    df = pd.DataFrame(data[1:], columns=data[0])
    for var in variables:
        if var in df.columns:
            df[var] = pd.to_numeric(df[var], errors="coerce")
            df.loc[df[var] < 0, var] = pd.NA
    return df


def fetch_tracts_acs(year, variables, county_fips_list=None, state="48", dataset="acs5", name_map=None):
    """
    Fetch ACS tract-level data for one or more counties.

    Parameters
    ----------
    year : int
    variables : list[str]
    county_fips_list : list[str], default AUSTIN_COUNTIES
        3-digit county FIPS codes within the state.
    state : str, default "48" (Texas)
    dataset : str, "acs5" or "acs1"
    name_map : dict, optional
        Rename variable codes to readable names.

    Returns
    -------
    pd.DataFrame
        Includes 'GEOID' (11-digit state+county+tract), 'state', 'county', 'tract'.
    """
    if county_fips_list is None:
        county_fips_list = AUSTIN_COUNTIES
    frames = []
    for county in county_fips_list:
        # Census API requires: for=tract:*  in=state:48 county:453
        geo = f"tract:*&in=state:{state} county:{county}"
        try:
            df = _fetch_acs_raw(year, variables, geo, dataset)
            if not df.empty:
                df["GEOID"] = df["state"] + df["county"] + df["tract"]
                frames.append(df)
        except Exception as e:
            print(f"  [WARN] Tract ACS fetch skipped county {county} ({e})")
        time.sleep(0.3)
    if not frames:
        return pd.DataFrame()
    result = pd.concat(frames, ignore_index=True)
    if name_map:
        result = result.rename(columns=name_map)
    print(f"  [OK] Fetched {len(result)} tracts from ACS {dataset} {year} ({len(county_fips_list)} counties)")
    return result


def fetch_acs_multiyear(years, variables, geography, dataset="acs5", name_map=None):
    """
    Fetch ACS data for multiple years, returning a long DataFrame with a 'year' column.

    Skips years that return 404 (data not yet available).
    """
    frames = []
    for year in years:
        try:
            df = _fetch_acs_raw(year, variables, geography, dataset)
            if not df.empty:
                df["year"] = year
                frames.append(df)
                print(f"  [OK] ACS {dataset} {year}: {len(df)} rows")
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                print(f"  [SKIP] ACS {dataset} {year} not yet available")
            else:
                print(f"  [ERROR] ACS {dataset} {year}: {e}")
        except Exception as e:
            print(f"  [ERROR] ACS {dataset} {year}: {e}")
        time.sleep(0.3)
    if not frames:
        return pd.DataFrame()
    result = pd.concat(frames, ignore_index=True)
    if name_map:
        result = result.rename(columns=name_map)
    return result


def fetch_acs_msa(year, variables, msa_fips_list, dataset="acs1", name_map=None):
    """
    Fetch ACS data for a list of MSAs (CBSAs).

    Parameters
    ----------
    msa_fips_list : list[str]
        CBSA FIPS codes, e.g. ['12420', '19100', '26420'].
    dataset : str, default "acs1"
        ACS 1-Year is available at MSA level; ACS 5-Year is not for all MSAs.

    Returns
    -------
    pd.DataFrame with 'msa_fips' and 'NAME' columns plus requested variables.
    """
    frames = []
    for msa in msa_fips_list:
        geo = f"metropolitan statistical area/micropolitan statistical area:{msa}"
        try:
            df = _fetch_acs_raw(year, variables, geo, dataset)
            if not df.empty:
                df["msa_fips"] = msa
                frames.append(df)
        except Exception as e:
            print(f"  [WARN] MSA {msa} ACS {year} skipped: {e}")
        time.sleep(0.3)
    if not frames:
        return pd.DataFrame()
    result = pd.concat(frames, ignore_index=True)
    if name_map:
        result = result.rename(columns=name_map)
    return result


def fetch_lodes_wac(year, state="tx", segment="S000", jobtype="JT00", county_prefixes=None):
    """
    Download Census LODES Workplace Area Characteristics for a state, filtered to specified counties.

    Returns office-relevant columns plus total jobs (C000).
    No API key required — direct public CSV download.

    Parameters
    ----------
    year : int
    state : str, default "tx"
    segment : str, default "S000" (all workers)
    jobtype : str, default "JT00" (all job types)
    county_prefixes : list[str], default AUSTIN_COUNTY_PREFIXES
        5-digit state+county FIPS strings to filter blocks.

    Returns
    -------
    pd.DataFrame with 'w_geocode', 'C000', 'CNS09', 'CNS10', 'CNS12', 'CNS13'.
    """
    if county_prefixes is None:
        county_prefixes = AUSTIN_COUNTY_PREFIXES
    url = LODES_BASE.format(state=state, segment=segment, jobtype=jobtype, year=year)
    keep_cols = ["w_geocode", "C000"] + list(LODES_OFFICE_COLS.keys())
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        df = pd.read_csv(io.BytesIO(gzip.decompress(resp.content)), dtype={"w_geocode": str})
        df["w_geocode"] = df["w_geocode"].str.zfill(15)
        # Filter to Austin-area counties
        mask = df["w_geocode"].str[:5].isin(county_prefixes)
        df = df.loc[mask, [c for c in keep_cols if c in df.columns]].copy()
        for col in keep_cols[1:]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        df["office_jobs"] = df[[c for c in LODES_OFFICE_COLS if c in df.columns]].sum(axis=1)
        print(f"  [OK] LODES WAC {year}: {len(df)} Austin-area blocks, {df['office_jobs'].sum():,} office jobs")
        return df
    except Exception as e:
        print(f"  [ERROR] LODES WAC {year} download failed: {e}")
        return pd.DataFrame()


def fetch_qcew(area_fips, year, quarter="a"):
    """
    Download BLS QCEW data for a given area and year.

    No API key required.

    Parameters
    ----------
    area_fips : str
        County FIPS (e.g. '48453' for Travis) or MSA code ('C1240' for Austin MSA).
    year : int
    quarter : str, default "a" (annual average)
        "a" = annual, "1"/"2"/"3"/"4" = quarterly.

    Returns
    -------
    pd.DataFrame with columns including 'industry_code', 'own_code',
    'annual_avg_estabs', 'annual_avg_emplvl', 'total_annual_wages'.
    """
    url = QCEW_BASE.format(year=year, quarter=quarter, area_fips=area_fips)
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        df.columns = [c.strip() for c in df.columns]
        # Normalize numeric columns
        for col in ["annual_avg_estabs", "annual_avg_emplvl", "total_annual_wages",
                    "annual_avg_estabs_count", "annual_avg_emp_count"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")
        print(f"  [OK] QCEW {area_fips} {year} {quarter}: {len(df)} rows")
        return df
    except Exception as e:
        print(f"  [ERROR] QCEW {area_fips} {year}: {e}")
        return pd.DataFrame()


def fetch_tiger_centroids(layer_url, county_fips_list=None, state="48"):
    """
    Fetch Census TIGER centroid coordinates for tracts or blocks via ArcGIS REST API.

    Parameters
    ----------
    layer_url : str
        TIGERweb MapServer layer URL (use TIGER_TRACTS or TIGER_BLOCKS constants).
    county_fips_list : list[str]
    state : str, default "48"

    Returns
    -------
    pd.DataFrame with 'GEOID', 'CENTLAT', 'CENTLON' columns.
    """
    if county_fips_list is None:
        county_fips_list = AUSTIN_COUNTIES
    counties_str = "','".join(county_fips_list)
    where = f"STATE='{state}' AND COUNTY IN ('{counties_str}')"
    params = {
        "where": where,
        "outFields": "GEOID,CENTLAT,CENTLON",
        "returnGeometry": "false",
        "resultRecordCount": 10000,
        "f": "json",
    }
    frames = []
    offset = 0
    while True:
        params["resultOffset"] = offset
        try:
            resp = requests.get(layer_url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            features = data.get("features", [])
            if not features:
                break
            rows = [f["attributes"] for f in features]
            frames.extend(rows)
            if len(features) < params["resultRecordCount"]:
                break
            offset += len(features)
        except Exception as e:
            print(f"  [ERROR] TIGER fetch failed at offset {offset}: {e}")
            break
    if not frames:
        return pd.DataFrame()
    df = pd.DataFrame(frames)
    df["CENTLAT"] = pd.to_numeric(df["CENTLAT"], errors="coerce")
    df["CENTLON"] = pd.to_numeric(df["CENTLON"], errors="coerce")
    print(f"  [OK] TIGER: {len(df)} centroids fetched")
    return df
