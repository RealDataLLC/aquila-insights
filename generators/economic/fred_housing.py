#!/usr/bin/env python3
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402
"""
Update FRED API Charts
Regenerates economic indicator charts from Federal Reserve Economic Data

Usage:
    python3 update_fred_charts.py
    python3 update_fred_charts.py --update-readme
"""

import os
import requests
import pandas as pd
from dotenv import load_dotenv
from aquila_graphing_tools import aquila_styled_line_chart
from aquila.charts import write_chart_html
from datetime import datetime
import sys

# Load environment
load_dotenv('aquila_graph.env')

def fetch_fred_series(series_id, api_key):
    """
    Fetches a FRED series by series_id and returns observations as DataFrame

    Args:
        series_id: FRED series ID (e.g., 'AUST448BPPRIV')
        api_key: FRED API key

    Returns:
        DataFrame with FRED data
    """
    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    fred_data = response.json()
    observations = fred_data.get("observations", [])
    df = pd.DataFrame(observations)

    return df

def generate_housing_starts_chart(fred_api_key):
    """Generate Austin Housing Starts chart"""
    print("\n[1/1] Generating: Austin Housing Starts...")

    # Fetch data
    series_id = "AUST448BPPRIV"  # Austin Private Housing Units Authorized by Building Permits
    print(f"  Fetching FRED series: {series_id}")

    df = fetch_fred_series(series_id, fred_api_key)
    print(f"  [OK] Loaded {len(df)} observations")

    # Convert types
    df["units"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"])

    # Remove null values
    df = df.dropna(subset=["units"])

    print(f"  [OK] Date range: {df['date'].min()} to {df['date'].max()}")

    # Create chart
    fig = aquila_styled_line_chart(
        df,
        x="date",
        y="units",
        title="Austin Housing Starts (Private Units Authorized by Building Permits)",
        height=600
    )

    fig.update_yaxes(
        rangemode="tozero",
        autorange=True,
        title="Units"
    )

    fig.update_xaxes(title="Date")

    # Save
    os.makedirs("charts", exist_ok=True)
    write_chart_html(fig, "charts/economic-indicators/austin_housing_starts.html")
    print("  [OK] Saved: charts/austin_housing_starts.html")

def update_readme_dates():
    """Update README.md with today's date for FRED charts"""
    print("\nUpdating README.md dates...")

    today = datetime.now().strftime('%Y-%m-%d')

    # Read README
    with open('README.md', 'r') as f:
        content = f.read()

    # Update date for housing starts chart
    import re
    pattern = r'Austin Housing Starts \(Monthly\) \[\d{4}-\d{2}-\d{2}\]'
    replacement = f'Austin Housing Starts (Monthly) [{today}]'

    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)

        # Write back
        with open('README.md', 'w') as f:
            f.write(content)

        print(f"  [OK] Updated README.md date to {today}")
    else:
        print("  [WARN] Could not find chart link in README.md")

def main():
    """Main execution"""
    print("=" * 70)
    print("UPDATING FRED API CHARTS")
    print("=" * 70)

    try:
        # Get API key
        fred_api_key = os.getenv("FRED_API_KEY")
        if not fred_api_key:
            raise ValueError("FRED_API_KEY not found in aquila_graph.env")

        print(f"[OK] API key loaded")

        # Generate charts
        generate_housing_starts_chart(fred_api_key)

        print("\n" + "=" * 70)
        print("[OK] SUCCESS: All FRED charts updated")
        print("=" * 70)

        # Update README if requested
        if '--update-readme' in sys.argv:
            update_readme_dates()

        print("\nGenerated charts:")
        print("  • austin_housing_starts.html")
        print("\nNext steps:")
        print("  1. Review chart in browser")
        print("  2. Commit: git add charts/ README.md && git commit -m 'Update FRED housing starts chart'")
        print("  3. Push to GitHub")
        print("")

    except Exception as e:
        print(f"\n[ERROR] ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
