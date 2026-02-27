#!/usr/bin/env python3
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402
"""
Update Building Performance Charts by Size

This script generates charts showing building performance metrics (occupancy rates
and rental rates) segmented by building size for both office and industrial properties.

Data Sources:
- Office: quarterly_report_data_office (Supabase)
- Industrial: quarterly_report_data_industrial (Supabase)

Filters:
- aquila_competitive_set = True
- building_status = 'Existing'

Charts Generated:
1. office_occupancy_by_size.html - Office occupancy rate by building size
2. office_rent_by_size.html - Office weighted average rent by building size
3. industrial_occupancy_by_size.html - Industrial occupancy rate by building size
4. industrial_rent_by_size.html - Industrial weighted average rent by building size

Usage:
    python3 update_building_performance_charts.py
    python3 update_building_performance_charts.py --update-readme
"""

import sys
import argparse
import re
from datetime import datetime
from dotenv import load_dotenv
from aquila_graphing_tools import initialize_supabase_connection, aquila_styled_line_chart
import pandas as pd
import numpy as np


def quarter_string_to_date(q_str):
    """
    Convert 'YYYY Qn' to a datetime representing the first day of that quarter.
    Example: '2025 Q4' -> datetime(2025, 10, 1)
    """
    match = re.match(r"(\d{4})\s*[Qq](\d)", str(q_str))
    if match:
        year = int(match.group(1))
        quarter = int(match.group(2))
        month = 3 * (quarter - 1) + 1
        return pd.Timestamp(year=year, month=month, day=1)
    return pd.NaT


def round_to_readable(value):
    """Round to nearest 5k, 10k, 25k, 50k, or 100k depending on magnitude"""
    if value < 10000:
        return round(value / 5000) * 5000
    elif value < 50000:
        return round(value / 10000) * 10000
    elif value < 100000:
        return round(value / 25000) * 25000
    else:
        return round(value / 50000) * 50000


def fetch_and_clean_data(supabase, table_name, property_type):
    """Fetch and clean data from Supabase table with pagination"""
    print(f"\nFetching {property_type} data from {table_name}...")

    all_records = []
    page = 0
    page_size = 1000  # Default Supabase page size

    while True:
        response = supabase.table(table_name) \
            .select('*') \
            .eq('aquila_competitive_set', True) \
            .eq('building_status', 'Existing') \
            .range(page * page_size, (page + 1) * page_size - 1) \
            .execute()

        batch = response.data
        all_records.extend(batch)
        print(f"  Fetched {len(batch):,} {property_type} records from page {page+1}")

        if len(batch) < page_size:
            break
        page += 1

    df = pd.DataFrame(all_records)
    print(f"  Loaded {len(df):,} {property_type} records (all pages)")

    # Identify and parse date column (handle quarter strings like '2025 Q4')
    if 'quarter' in df.columns:
        df['date'] = df['quarter'].apply(quarter_string_to_date)
    elif 'report_date' in df.columns:
        df['date'] = pd.to_datetime(df['report_date'], errors='coerce')
    else:
        # Try to find any date column
        date_columns = [col for col in df.columns if 'date' in col.lower() or 'quarter' in col.lower()]
        for col in date_columns:
            df['date'] = pd.to_datetime(df[col], errors='coerce')
            if df['date'].notna().any():
                break

    # Convert numeric columns
    df['rentable_building_area'] = pd.to_numeric(df['rentable_building_area'], errors='coerce')
    df['occupancy_pct_total'] = pd.to_numeric(df['occupancy_pct_total'], errors='coerce')

    # Property-specific rental rate column
    if property_type == 'office':
        # Use 'rental_rate' column if it exists, otherwise fall back to 'costar_rental_rate'
        if 'rental_rate' in df.columns:
            df['rental_rate'] = pd.to_numeric(df['rental_rate'], errors='coerce')
        else:
            df['rental_rate'] = pd.to_numeric(df['costar_rental_rate'], errors='coerce')
    else:  # industrial
        df['rental_rate'] = pd.to_numeric(df['survey_rental_rate'], errors='coerce')

    # Remove rows with missing critical data
    df_clean = df[
        df['date'].notna() &
        df['rentable_building_area'].notna() &
        (df['rentable_building_area'] > 0)
    ].copy()

    print(f"  Records after cleaning: {len(df_clean):,}")
    print(f"  Date range: {df_clean['date'].min()} to {df_clean['date'].max()}")

    return df_clean


def create_size_bins(df, property_type):
    """Create 5 size bins with rounded ranges"""
    quartiles = df['rentable_building_area'].quantile([0.2, 0.4, 0.6, 0.8]).values

    bins = [
        0,
        round_to_readable(quartiles[0]),
        round_to_readable(quartiles[1]),
        round_to_readable(quartiles[2]),
        round_to_readable(quartiles[3]),
        float('inf')
    ]

    labels = [
        f"0-{bins[1]/1000:.0f}k SF",
        f"{bins[1]/1000:.0f}k-{bins[2]/1000:.0f}k SF",
        f"{bins[2]/1000:.0f}k-{bins[3]/1000:.0f}k SF",
        f"{bins[3]/1000:.0f}k-{bins[4]/1000:.0f}k SF",
        f"{bins[4]/1000:.0f}k+ SF"
    ]

    print(f"\n  {property_type.capitalize()} size bins: {labels}")

    df['size_bin'] = pd.cut(
        df['rentable_building_area'],
        bins=bins,
        labels=labels,
        include_lowest=True
    )

    return df, labels


def calculate_weighted_metrics(df):
    """Calculate weighted occupancy and rent by date and size bin"""

    # Weighted occupancy rate
    occ_by_size = df.groupby(['date', 'size_bin'], observed=False).apply(
        lambda x: np.average(
            x['occupancy_pct_total'].dropna(),
            weights=x.loc[x['occupancy_pct_total'].notna(), 'rentable_building_area']
        ) if len(x['occupancy_pct_total'].dropna()) > 0 else np.nan
    ).reset_index(name='weighted_occupancy_pct')

    # Weighted average rent
    rent_by_size = df.groupby(['date', 'size_bin'], observed=False).apply(
        lambda x: np.average(
            x['rental_rate'].dropna(),
            weights=x.loc[x['rental_rate'].notna(), 'rentable_building_area']
        ) if len(x['rental_rate'].dropna()) > 0 else np.nan
    ).reset_index(name='weighted_avg_rent')

    return occ_by_size, rent_by_size


def generate_charts(occ_data, rent_data, property_type):
    """Generate and save occupancy and rent charts"""

    # Occupancy chart
    os.makedirs(f'charts/{property_type}', exist_ok=True)
    occ_filename = f'charts/{property_type}/{property_type}_occupancy_by_size.html'
    fig_occ = aquila_styled_line_chart(
        occ_data,
        x='date',
        y='weighted_occupancy_pct',
        color='size_bin',
        title=f'{property_type.capitalize()} Occupancy Rate by Building Size (Weighted by Rentable Area)'
    )
    fig_occ.update_yaxes(tickformat='.1%', title='Occupancy Rate')
    fig_occ.update_xaxes(title='Quarter')
    fig_occ.write_html(occ_filename)
    print(f"  [OK] Saved {occ_filename}")

    # Rent chart - drop NaN values before plotting
    rent_data_clean = rent_data.dropna(subset=['date', 'weighted_avg_rent'])
    rent_filename = f'charts/{property_type}/{property_type}_rent_by_size.html'
    fig_rent = aquila_styled_line_chart(
        rent_data_clean,
        x='date',
        y='weighted_avg_rent',
        color='size_bin',
        title=f'{property_type.capitalize()} Weighted Average Rent by Building Size'
    )
    fig_rent.update_yaxes(tickprefix='$', tickformat=',.2f', title='Rent ($/SF)')
    fig_rent.update_xaxes(title='Quarter')
    fig_rent.write_html(rent_filename)
    print(f"  [OK] Saved {rent_filename}")


def update_readme_dates():
    """Update README.md with today's date for building performance charts"""
    import re

    readme_path = 'README.md'
    today = datetime.now().strftime('%Y-%m-%d')

    try:
        with open(readme_path, 'r') as f:
            content = f.read()

        # Update dates for building performance charts
        patterns = [
            (r'(\[Office Occupancy by Building Size\s*\[)[^\]]+(\]\()',
             f'\\1{today}\\2'),
            (r'(\[Office Rent by Building Size\s*\[)[^\]]+(\]\()',
             f'\\1{today}\\2'),
            (r'(\[Industrial Occupancy by Building Size\s*\[)[^\]]+(\]\()',
             f'\\1{today}\\2'),
            (r'(\[Industrial Rent by Building Size\s*\[)[^\]]+(\]\()',
             f'\\1{today}\\2'),
        ]

        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content)

        with open(readme_path, 'w') as f:
            f.write(content)

        print(f"\n[OK] Updated README.md with date: {today}")
        return True

    except FileNotFoundError:
        print(f"\n[WARN] README.md not found")
        return False
    except Exception as e:
        print(f"\n[WARN] Error updating README.md: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Update building performance charts')
    parser.add_argument('--update-readme', action='store_true',
                       help='Update README.md with today\'s date')
    args = parser.parse_args()

    print("=" * 70)
    print("BUILDING PERFORMANCE CHARTS UPDATE")
    print("=" * 70)

    try:
        # Load environment and connect to Supabase
        load_dotenv('aquila_graph.env')
        supabase = initialize_supabase_connection()
        print("[OK] Connected to Supabase")

        # Process Office data
        print("\n" + "=" * 70)
        print("OFFICE CHARTS")
        print("=" * 70)
        df_office = fetch_and_clean_data(supabase, 'quarterly_report_data_office', 'office')
        df_office, office_labels = create_size_bins(df_office, 'office')
        office_occ, office_rent = calculate_weighted_metrics(df_office)
        generate_charts(office_occ, office_rent, 'office')

        # Process Industrial data
        print("\n" + "=" * 70)
        print("INDUSTRIAL CHARTS")
        print("=" * 70)
        df_industrial = fetch_and_clean_data(supabase, 'quarterly_report_data_industrial', 'industrial')
        df_industrial, industrial_labels = create_size_bins(df_industrial, 'industrial')
        industrial_occ, industrial_rent = calculate_weighted_metrics(df_industrial)
        generate_charts(industrial_occ, industrial_rent, 'industrial')

        # Update README if requested
        if args.update_readme:
            update_readme_dates()

        print("\n" + "=" * 70)
        print("SUCCESS - All building performance charts updated!")
        print("=" * 70)
        print("\nGenerated charts:")
        print("  - charts/office/office_occupancy_by_size.html")
        print("  - charts/office/office_rent_by_size.html")
        print("  - charts/industrial/industrial_occupancy_by_size.html")
        print("  - charts/industrial/industrial_rent_by_size.html")

        return 0

    except Exception as e:
        print(f"\n[ERROR] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
