#!/usr/bin/env python3
"""
Update FRED Economic Indicators Charts
Regenerates 7 economic indicator charts from Federal Reserve Economic Data

Usage:
    python3 update_fred_economic_indicators.py
    python3 update_fred_economic_indicators.py --update-readme
"""

import os
import requests
import pandas as pd
import numpy as np
from dotenv import load_dotenv
from aquila_graphing_tools import aquila_styled_line_chart
from datetime import datetime
import sys
import re

# Load environment
load_dotenv('aquila_graph.env')

def fetch_fred_series(series_id, series_name=None):
    """
    Fetch FRED data and return as DataFrame with date and value columns.

    Parameters
    ----------
    series_id : str
        FRED series identifier
    series_name : str, optional
        Name for the value column (defaults to series_id)

    Returns
    -------
    pd.DataFrame
        DataFrame with 'date' and series_name columns
    """
    url = "https://api.stlouisfed.org/fred/series/observations"
    fred_api_key = os.getenv('FRED_API_KEY')

    params = {
        "series_id": series_id,
        "api_key": fred_api_key,
        "file_type": "json"
    }

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
        column_name = series_name if series_name else series_id
        df = df[['date', 'value']].rename(columns={'value': column_name})

        # Drop NaN values
        df = df.dropna()

        print(f"    ✓ Fetched {len(df)} observations for {series_id} ({column_name})")
        return df

    except Exception as e:
        print(f"    Error fetching series {series_id}: {str(e)}")
        return pd.DataFrame()


def generate_office_employment_chart():
    """Generate Austin Employment - Office Sectors chart"""
    print("\n[1/8] Generating: Austin Employment - Office Sectors...")

    # Fetch employment data for office sectors
    df_prof = fetch_fred_series('AUST448PBSV', 'Professional & Business Services')
    df_fire = fetch_fred_series('AUST448FIRE', 'Financial Activities')
    df_govt = fetch_fred_series('AUST448GOVT', 'Government')
    df_info = fetch_fred_series('AUST448INFO', 'Information (Tech)')

    # Merge all series on date
    df_office = df_prof.merge(df_fire, on='date', how='outer') \
                       .merge(df_govt, on='date', how='outer') \
                       .merge(df_info, on='date', how='outer')

    # Convert to long format for plotting
    df_office_long = df_office.melt(id_vars=['date'],
                                     var_name='Sector',
                                     value_name='Employment (thousands)')

    # Create chart
    fig = aquila_styled_line_chart(
        df_office_long,
        x='date',
        y='Employment (thousands)',
        color='Sector',
        title='Austin Employment - Office Sectors',
        height=800
    )

    fig.update_yaxes(rangemode='tozero')

    # Save chart
    os.makedirs("charts", exist_ok=True)
    fig.write_html('charts/austin_employment_office_sectors.html')
    print("    ✓ Saved: charts/austin_employment_office_sectors.html")


def generate_industrial_employment_chart():
    """Generate Austin Employment - Industrial Sector chart"""
    print("\n[2/8] Generating: Austin Employment - Industrial Sector...")

    # Fetch industrial employment data
    df_industrial = fetch_fred_series('AUST448TRAD', 'Trade, Transportation & Utilities')

    # Create chart
    fig = aquila_styled_line_chart(
        df_industrial,
        x='date',
        y='Trade, Transportation & Utilities',
        title='Austin Employment - Industrial Sector',
        height=800
    )

    fig.update_yaxes(rangemode='tozero', title='Employment (thousands)')

    # Save chart
    os.makedirs("charts", exist_ok=True)
    fig.write_html('charts/austin_employment_industrial.html')
    print("    ✓ Saved: charts/austin_employment_industrial.html")


def generate_retail_employment_chart():
    """Generate Austin Employment - Retail Sector chart"""
    print("\n[3/8] Generating: Austin Employment - Retail Sector...")

    # Fetch retail employment data
    df_retail = fetch_fred_series('AUST448LEIH', 'Leisure & Hospitality')

    # Create chart
    fig = aquila_styled_line_chart(
        df_retail,
        x='date',
        y='Leisure & Hospitality',
        title='Austin Employment - Retail Sector',
        height=800
    )

    fig.update_yaxes(rangemode='tozero', title='Employment (thousands)')

    # Save chart
    os.makedirs("charts", exist_ok=True)
    fig.write_html('charts/austin_employment_retail.html')
    print("    ✓ Saved: charts/austin_employment_retail.html")


def generate_tech_comparison_chart():
    """Generate Austin vs National Tech Employment Growth chart"""
    print("\n[4/8] Generating: Austin vs National Tech Employment Growth...")

    # Fetch tech employment data
    df_austin_tech = fetch_fred_series('AUST448INFO', 'Austin Tech')
    df_national_tech = fetch_fred_series('USINFO', 'National Tech')

    # Merge on date
    df_tech = df_austin_tech.merge(df_national_tech, on='date', how='inner')

    # Index both series to 100 at earliest common date
    if len(df_tech) > 0:
        base_austin = df_tech['Austin Tech'].iloc[0]
        base_national = df_tech['National Tech'].iloc[0]

        df_tech['Austin Tech (Index)'] = (df_tech['Austin Tech'] / base_austin) * 100
        df_tech['National Tech (Index)'] = (df_tech['National Tech'] / base_national) * 100

        # Convert to long format
        df_tech_long = df_tech[['date', 'Austin Tech (Index)', 'National Tech (Index)']].melt(
            id_vars=['date'],
            var_name='Region',
            value_name='Employment Index (Base 100)'
        )

        # Create chart
        fig = aquila_styled_line_chart(
            df_tech_long,
            x='date',
            y='Employment Index (Base 100)',
            color='Region',
            title='Austin vs National Tech Employment Growth',
            height=800
        )

        fig.update_yaxes(rangemode='tozero')

        # Save chart
        os.makedirs("charts", exist_ok=True)
        fig.write_html('charts/austin_vs_national_tech_employment.html')
        print("    ✓ Saved: charts/austin_vs_national_tech_employment.html")
    else:
        print("    Warning: No overlapping data for tech employment comparison")


def generate_wage_comparison_chart():
    """Generate Austin vs National Wage Growth chart"""
    print("\n[5/7] Generating: Austin vs National Wage Growth...")

    # Fetch wage data
    df_austin_wage = fetch_fred_series('AUST448AVGW', 'Austin Weekly Wage')
    df_national_wage = fetch_fred_series('CES0500000003', 'National Hourly Wage')

    # Convert national hourly to weekly (×40 hours)
    df_national_wage['National Weekly Wage'] = df_national_wage['National Hourly Wage'] * 40
    df_national_wage = df_national_wage[['date', 'National Weekly Wage']]

    # Merge on date
    df_wage = df_austin_wage.merge(df_national_wage, on='date', how='inner')

    # Index both series to 100 at earliest common date
    if len(df_wage) > 0:
        base_austin = df_wage['Austin Weekly Wage'].iloc[0]
        base_national = df_wage['National Weekly Wage'].iloc[0]

        df_wage['Austin Wage (Index)'] = (df_wage['Austin Weekly Wage'] / base_austin) * 100
        df_wage['National Wage (Index)'] = (df_wage['National Weekly Wage'] / base_national) * 100

        # Convert to long format
        df_wage_long = df_wage[['date', 'Austin Wage (Index)', 'National Wage (Index)']].melt(
            id_vars=['date'],
            var_name='Region',
            value_name='Wage Index (Base 100)'
        )

        # Create chart
        fig = aquila_styled_line_chart(
            df_wage_long,
            x='date',
            y='Wage Index (Base 100)',
            color='Region',
            title='Austin vs National Wage Growth',
            height=800
        )

        fig.update_yaxes(rangemode='tozero')

        # Save chart
        os.makedirs("charts", exist_ok=True)
        fig.write_html('charts/austin_vs_national_wage_growth.html')
        print("    ✓ Saved: charts/austin_vs_national_wage_growth.html")
    else:
        print("    Warning: No overlapping data for wage comparison")


def generate_interest_rates_chart():
    """Generate Interest Rates - Treasury & Mortgage chart"""
    print("\n[6/7] Generating: Interest Rates - Treasury & Mortgage...")

    # Fetch interest rate data
    df_treasury = fetch_fred_series('DGS10', '10-Year Treasury')
    df_mortgage = fetch_fred_series('MORTGAGE30US', '30-Year Mortgage')

    # Merge on date
    df_rates = df_treasury.merge(df_mortgage, on='date', how='outer')

    # Convert to long format
    df_rates_long = df_rates.melt(
        id_vars=['date'],
        var_name='Rate Type',
        value_name='Interest Rate (%)'
    )

    # Create chart
    fig = aquila_styled_line_chart(
        df_rates_long,
        x='date',
        y='Interest Rate (%)',
        color='Rate Type',
        title='Interest Rates - Treasury & Mortgage',
        height=800
    )

    fig.update_yaxes(rangemode='tozero')

    # Save chart
    os.makedirs("charts", exist_ok=True)
    fig.write_html('charts/interest_rates_treasury_mortgage.html')
    print("    ✓ Saved: charts/interest_rates_treasury_mortgage.html")


def generate_inflation_chart():
    """Generate Inflation - Core CPI vs Rent CPI chart"""
    print("\n[7/7] Generating: Inflation - Core CPI vs Rent CPI...")

    # Fetch inflation data
    df_core_cpi = fetch_fred_series('CPILFESL', 'Core CPI')
    df_rent_cpi = fetch_fred_series('CUUR0000SEHC', 'Rent CPI')

    # Merge on date
    df_inflation = df_core_cpi.merge(df_rent_cpi, on='date', how='inner')

    # Index both series to 100 at earliest common date
    if len(df_inflation) > 0:
        base_core = df_inflation['Core CPI'].iloc[0]
        base_rent = df_inflation['Rent CPI'].iloc[0]

        df_inflation['Core CPI (Index)'] = (df_inflation['Core CPI'] / base_core) * 100
        df_inflation['Rent CPI (Index)'] = (df_inflation['Rent CPI'] / base_rent) * 100

        # Convert to long format
        df_inflation_long = df_inflation[['date', 'Core CPI (Index)', 'Rent CPI (Index)']].melt(
            id_vars=['date'],
            var_name='Inflation Type',
            value_name='CPI Index (Base 100)'
        )

        # Create chart
        fig = aquila_styled_line_chart(
            df_inflation_long,
            x='date',
            y='CPI Index (Base 100)',
            color='Inflation Type',
            title='Inflation - Core CPI vs Rent CPI',
            height=800
        )

        fig.update_yaxes(rangemode='tozero')

        # Save chart
        os.makedirs("charts", exist_ok=True)
        fig.write_html('charts/inflation_core_vs_rent_cpi.html')
        print("    ✓ Saved: charts/inflation_core_vs_rent_cpi.html")
    else:
        print("    Warning: No overlapping data for inflation comparison")


def update_readme_dates():
    """Update README.md with today's date for all 7 FRED economic indicator charts"""
    print("\nUpdating README.md dates...")

    today = datetime.now().strftime('%Y-%m-%d')

    # Read README
    with open('README.md', 'r') as f:
        content = f.read()

    # Define regex patterns for all 7 charts
    patterns = [
        (r'(\[Austin Employment - Office Sectors\s*\[)[^\]]+(\]\()', f'\\1{today}\\2'),
        (r'(\[Austin Employment - Industrial Sector\s*\[)[^\]]+(\]\()', f'\\1{today}\\2'),
        (r'(\[Austin Employment - Retail Sector\s*\[)[^\]]+(\]\()', f'\\1{today}\\2'),
        (r'(\[Austin vs National Tech Employment Growth\s*\[)[^\]]+(\]\()', f'\\1{today}\\2'),
        (r'(\[Austin vs National Wage Growth\s*\[)[^\]]+(\]\()', f'\\1{today}\\2'),
        (r'(\[Interest Rates - Treasury & Mortgage\s*\[)[^\]]+(\]\()', f'\\1{today}\\2'),
        (r'(\[Inflation - Core CPI vs Rent CPI\s*\[)[^\]]+(\]\()', f'\\1{today}\\2'),
    ]

    updated_count = 0
    for pattern, replacement in patterns:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            updated_count += 1

    # Write back if any updates made
    if updated_count > 0:
        with open('README.md', 'w') as f:
            f.write(content)

        print(f"  ✓ Updated {updated_count} chart dates to {today} in README.md")
    else:
        print("  ⚠ Could not find chart links in README.md")


def main():
    """Main execution"""
    print("=" * 70)
    print("UPDATING FRED ECONOMIC INDICATORS CHARTS")
    print("=" * 70)

    try:
        # Get API key
        fred_api_key = os.getenv("FRED_API_KEY")
        if not fred_api_key:
            raise ValueError("FRED_API_KEY not found in aquila_graph.env")

        print(f"✓ API key loaded")

        # Generate all 7 charts
        generate_office_employment_chart()
        generate_industrial_employment_chart()
        generate_retail_employment_chart()
        generate_tech_comparison_chart()
        generate_wage_comparison_chart()
        generate_interest_rates_chart()
        generate_inflation_chart()

        print("\n" + "=" * 70)
        print("✓ SUCCESS: All 7 FRED economic indicator charts updated")
        print("=" * 70)

        # Update README if requested
        if '--update-readme' in sys.argv:
            update_readme_dates()

        print("\nGenerated charts:")
        print("  • austin_employment_office_sectors.html")
        print("  • austin_employment_industrial.html")
        print("  • austin_employment_retail.html")
        print("  • austin_vs_national_tech_employment.html")
        print("  • austin_vs_national_wage_growth.html")
        print("  • interest_rates_treasury_mortgage.html")
        print("  • inflation_core_vs_rent_cpi.html")
        print("\nNext steps:")
        print("  1. Review charts in browser")
        print("  2. Commit: git add charts/ README.md && git commit -m 'Update FRED economic indicator charts'")
        print("  3. Push to GitHub")
        print("")

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
