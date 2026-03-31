"""
Spatial utilities for Aquila Insights.

Maps Census geographic units (tracts, blocks) to Aquila office submarkets
using the KMZ polygon boundaries already in the repo.

Usage:
    from aquila.geo import build_tract_submarket_map, build_block_submarket_map

    tract_map = build_tract_submarket_map()   # {GEOID_11: submarket_name}
    block_map = build_block_submarket_map()   # {GEOID_15: submarket_name}
"""

import os
import sys

import pandas as pd
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from aquila.connectors.census import (
    fetch_tiger_centroids,
    TIGER_TRACTS,
    TIGER_BLOCK_GROUPS,
    AUSTIN_COUNTIES,
)

# -- Locate KMZ relative to repo root ----------------------------------------
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_KMZ = os.path.join(_REPO_ROOT, "data", "Final AQUILA Submarket Map.kmz")

# -- Module-level caches so each map is built only once per process -----------
_tract_cache: dict[str, str] = {}
_block_cache: dict[str, str] = {}


def _load_submarket_polygons(kmz_path=None):
    """
    Parse KMZ and group KML polygon names into Aquila submarkets.

    Returns dict of {submarket_name: Shapely MultiPolygon}.
    Reuses parse_kmz() and SUBMARKET_GROUPS from reports/map_builder.py.
    """
    # Import here to avoid circular imports and unnecessary load at module init
    reports_dir = os.path.join(_REPO_ROOT, "reports")
    if reports_dir not in sys.path:
        sys.path.insert(0, reports_dir)
    from map_builder import parse_kmz, SUBMARKET_GROUPS

    raw_polygons = parse_kmz(kmz_path or _DEFAULT_KMZ)

    submarket_polys = {}
    for submarket, poly_names in SUBMARKET_GROUPS.items():
        parts = []
        for name in poly_names:
            coords = raw_polygons.get(name)
            if coords and len(coords) >= 3:
                parts.append(Polygon(coords))
        if parts:
            submarket_polys[submarket] = unary_union(parts)
    return submarket_polys


def _assign_submarket(centroids_df, submarket_polys):
    """
    Point-in-polygon test for each centroid row.

    centroids_df must have 'GEOID', 'CENTLAT', 'CENTLON' columns.
    Returns dict {GEOID: submarket_name}.
    """
    mapping = {}
    for _, row in centroids_df.iterrows():
        geoid = str(row["GEOID"])
        lat = row["CENTLAT"]
        lon = row["CENTLON"]
        if pd.isna(lat) or pd.isna(lon):
            continue
        pt = Point(lon, lat)  # shapely uses (x=lon, y=lat)
        for submarket, poly in submarket_polys.items():
            if poly.contains(pt):
                mapping[geoid] = submarket
                break
    return mapping


def build_tract_submarket_map(kmz_path=None):
    """
    Build a mapping of Census tract GEOID (11-digit) → Aquila office submarket.

    Tracts outside all submarket polygons are excluded from the dict.
    Result is cached in memory after the first call.

    Returns
    -------
    dict[str, str]
        e.g. {'48453000100': 'CBD', '48453010200': 'Northwest', ...}
    """
    global _tract_cache
    if _tract_cache:
        return _tract_cache

    print("  Building tract→submarket spatial map...")
    submarket_polys = _load_submarket_polygons(kmz_path)
    centroids = fetch_tiger_centroids(TIGER_TRACTS, AUSTIN_COUNTIES)
    if centroids.empty:
        print("  [WARN] No tract centroids retrieved — submarket map will be empty")
        return {}

    _tract_cache = _assign_submarket(centroids, submarket_polys)
    matched = len(_tract_cache)
    total = len(centroids)
    print(f"  [OK] Tract map: {matched}/{total} tracts assigned to a submarket")
    return _tract_cache


def build_block_group_submarket_map(kmz_path=None):
    """
    Build a mapping of Census block group GEOID (12-digit) → Aquila office submarket.

    The TIGER ACS2023 service does not include individual Census Blocks, so we use
    Block Groups as the spatial unit. LODES 15-digit block GEOIDs are aggregated to
    12-digit block group GEOIDs (first 12 chars) before joining.

    Block groups outside all submarket polygons are excluded from the dict.
    Result is cached in memory after the first call.

    Returns
    -------
    dict[str, str]
        e.g. {'480530001001': 'CBD', ...}
    """
    global _block_cache
    if _block_cache:
        return _block_cache

    print("  Building block group→submarket spatial map...")
    submarket_polys = _load_submarket_polygons(kmz_path)
    centroids = fetch_tiger_centroids(TIGER_BLOCK_GROUPS, AUSTIN_COUNTIES)
    if centroids.empty:
        print("  [WARN] No block group centroids retrieved — block map will be empty")
        return {}

    _block_cache = _assign_submarket(centroids, submarket_polys)
    matched = len(_block_cache)
    total = len(centroids)
    print(f"  [OK] Block group map: {matched}/{total} block groups assigned to a submarket")
    return _block_cache


# Keep old name as alias for backward compatibility
build_block_submarket_map = build_block_group_submarket_map


