"""
Skyline (restb.ai) API connector for lease comparable data.

Base URL: https://api.withskyline.com/external/v1
Auth: Bearer token via SKYLINE_API_KEY environment variable.
"""

import os
import requests


_BASE_URL = "https://api.withskyline.com/external/v1"


def _get_headers():
    api_key = os.getenv("SKYLINE_API_KEY")
    if not api_key:
        raise ValueError("SKYLINE_API_KEY must be set in aquila_graph.env")
    return {"Authorization": f"Bearer {api_key}"}


def fetch_all_leases(lease_type=None, start_date=None, end_date=None):
    """
    Fetch all lease comparables from the Skyline API, paginating automatically.

    Parameters
    ----------
    lease_type : str, optional
        Filter by lease type (New, Renewal, Expansion, Sublease, Unknown).
    start_date : str, optional
        ISO date string -- only leases executed on or after this date.
    end_date : str, optional
        ISO date string -- only leases executed on or before this date.

    Returns
    -------
    list[dict]
        List of lease objects with nested tenant/property/broker data.
    """
    headers = _get_headers()
    params = {
        "pageSize": 100,
        "sortBy": "executionDate",
        "sortOrder": "desc",
    }
    if lease_type:
        params["leaseType"] = lease_type
    if start_date:
        params["executionDate_gte"] = start_date
    if end_date:
        params["executionDate_lte"] = end_date

    all_leases = []
    page = 1

    while True:
        params["page"] = page
        try:
            resp = requests.get(f"{_BASE_URL}/leases", headers=headers, params=params)
            resp.raise_for_status()
            body = resp.json()
        except Exception as e:
            print(f"    [ERROR] Skyline API page {page}: {e}")
            break

        data = body.get("data", [])
        pagination = body.get("pagination", {})
        all_leases.extend(data)

        total = pagination.get("total", 0)
        print(f"    [OK] Skyline page {page}: {len(data)} leases (total: {total})")

        if not pagination.get("hasNextPage", False):
            break
        page += 1

    print(f"    [OK] Fetched {len(all_leases)} total leases from Skyline")
    return all_leases
