#!/usr/bin/env python3
"""
Generate quarterly transaction SF chart from Transaction Request Form data.

Reads Excel data, cleans the 'Total SF / Total Acreage if Land' column,
aggregates by quarter based on 'When was the lease executed?', and creates
a line chart showing total SF per quarter.
"""

import pandas as pd
import numpy as np
import re
import plotly.graph_objects as go
from aquila_graphing_tools import AQUILA_COLORS, AQUILA_FONT

# Constants
SQFT_PER_ACRE = 43560
INPUT_FILE = 'data/TransactionRequestForm_Data_16668082_1769632373.xlsx'
OUTPUT_FILE = 'charts/office/transaction_sf_by_quarter.html'


def clean_sf_value(val):
    """
    Clean and extract square footage from various input formats.

    Handles:
    - Plain numbers: 3950, 9000
    - Numbers with commas: '5,188', '43,187'
    - Numbers with SF/RSF suffix: '5,133 SF', '11,788 RSF'
    - Lowercase sf: '120,440sf', '300sf'
    - Acres: '2.87 acres', '7.3 acres', '13.834 Acres'
    - Complex totals with = or 'total': extracts final number
    - Multiple suites: sums them
    - Acre + SF combos: prefers SF value
    - Invalid values: returns None

    Returns
    -------
    float or None
        Square footage as float, or None if unparseable
    """
    if pd.isna(val):
        return None

    # Convert to string for processing
    val_str = str(val).strip()

    # Skip clearly invalid values
    invalid_patterns = ['united states', 'n/a', 'fdasdf', '-', '']
    if val_str.lower() in invalid_patterns or val_str == '-':
        return None

    # If it's already a number (int/float), check if it might be acres
    if isinstance(val, (int, float)):
        # Small decimals are likely acres (e.g., 2.87, 7.3)
        # But some legitimate SF values can be small (like 180.91)
        # Use a heuristic: if < 100, treat as acres; otherwise SF
        if val < 100:
            return val * SQFT_PER_ACRE
        return float(val)

    # Strategy 1: Look for explicit "total" or "=" with final number
    # e.g., "13,443 SF (expansion) & 29,621 SF (extension) = 43,064 SF"
    # e.g., "(Shah Smith = 5,360 SF) and Gonzales Shah Smith (540 SF) for a total of 5,900 SF"
    total_patterns = [
        # Check for "total" patterns first (more specific)
        r'(?:for\s+a\s+)?total\s+(?:of\s+)?([\d,]+)\s*(?:SF|sf)?',  # total of 5,900 SF or for a total of 5,900 SF
        r'\(([\d,]+)\s*(?:SF|sf)?\s*total(?:\s+now)?\)',  # (10,064 SF total now)
        # "=" pattern last (catch-all for equations like "... = 43,064 SF")
        r'=\s*([\d,]+)\s*(?:SF|sf)?\s*$',  # = 43,064 SF (only at end of string)
    ]
    for pattern in total_patterns:
        match = re.search(pattern, val_str, re.IGNORECASE)
        if match:
            num_str = match.group(1).replace(',', '')
            try:
                return float(num_str)
            except ValueError:
                pass

    # Strategy 2: If there's both SF and acres mentioned, prefer SF
    # e.g., "38.669 ac or 1,684,410sf"
    # e.g., "5,084 SF / 1.22ac"
    # e.g., "17.32 Acres (189,280 SF)"
    # e.g., "435714 SF on 32.67 Acres"
    sf_in_combo = re.search(r'([\d,]+)\s*(?:SF|sf)\b', val_str)
    if sf_in_combo and ('acre' in val_str.lower() or ' ac' in val_str.lower()):
        num_str = sf_in_combo.group(1).replace(',', '')
        try:
            return float(num_str)
        except ValueError:
            pass

    # Strategy 3: Multiple suites - sum all SF values
    # e.g., "Suite 238 (894 SF) & Suite 234 (1,750 SF)"
    # e.g., "Suite H1 -2,934 SF and Suite H45 - 1,137 SF"
    # e.g., "6,857 SF ( Suite 100) & 3,469 SF (Suite 110)"
    suite_sf_matches = re.findall(r'([\d,]+)\s*(?:SF|RSF|sf)\b', val_str)
    if len(suite_sf_matches) > 1 and ('suite' in val_str.lower() or '&' in val_str or ' and ' in val_str.lower()):
        try:
            total = sum(float(m.replace(',', '')) for m in suite_sf_matches)
            return total
        except ValueError:
            pass

    # Strategy 4: Expansion + extension or similar additions
    # e.g., "18,000 Expansion + 18,000 extension"
    if '+' in val_str and ('expansion' in val_str.lower() or 'extension' in val_str.lower()):
        numbers = re.findall(r'([\d,]+)', val_str)
        try:
            total = sum(float(n.replace(',', '')) for n in numbers if float(n.replace(',', '')) > 100)
            if total > 0:
                return total
        except ValueError:
            pass

    # Strategy 5: Simple SF/RSF value
    # e.g., "5,133 SF", "11,788 RSF", "120,440sf", "4,834-sf"
    sf_match = re.search(r'^[^\d]*([\d,]+)\s*(?:-?\s*)?(?:SF|RSF|sf)\s*$', val_str)
    if not sf_match:
        # Also try with trailing characters
        sf_match = re.search(r'^[^\d]*([\d,]+)\s*(?:-?\s*)?(?:SF|RSF|sf)\b', val_str)
    if sf_match:
        num_str = sf_match.group(1).replace(',', '')
        try:
            return float(num_str)
        except ValueError:
            pass

    # Strategy 6: Acres conversion
    # e.g., "2.87 acres", "7.3 acres", "13.834 Acres", "83 Acres"
    # e.g., "17.4 Acres - Tract 1 & 0.517 Acres Tract 2"
    # e.g., "+/-3.10 acres of improved property"
    # e.g., "Approximately 31.217 acres"
    acres_matches = re.findall(r'([\d,.]+)\s*(?:acres?|ac)\b', val_str, re.IGNORECASE)
    if acres_matches:
        try:
            total_acres = sum(float(a.replace(',', '')) for a in acres_matches)
            return total_acres * SQFT_PER_ACRE
        except ValueError:
            pass

    # Strategy 7: Plain number with commas
    # e.g., "5,188", "43,187", "32,000"
    plain_match = re.match(r'^[\s]*([\d,]+)[\s]*$', val_str)
    if plain_match:
        num_str = plain_match.group(1).replace(',', '')
        try:
            return float(num_str)
        except ValueError:
            pass

    # Strategy 8: Number with spaces in wrong places
    # e.g., "7, 298 SF and 2,521 SF (9,791 SF)" - look for parenthetical total
    paren_total = re.search(r'\(([\d,]+)\s*(?:SF|sf)?\)(?:\s*$|\s*total)', val_str)
    if paren_total:
        num_str = paren_total.group(1).replace(',', '')
        try:
            return float(num_str)
        except ValueError:
            pass

    # Strategy 9: Suite breakdown with total at start
    # e.g., "13,650 - 10,500 SF in Suite 100 and 3,150 SF in Suite 150"
    # e.g., "12,699 SF - 8,829 SF in Suite 500 and 3,870 SF in Suite 650"
    leading_total = re.match(r'^([\d,]+)\s*(?:SF)?\s*[-–]', val_str)
    if leading_total and ('suite' in val_str.lower() or ' in ' in val_str.lower()):
        num_str = leading_total.group(1).replace(',', '')
        try:
            return float(num_str)
        except ValueError:
            pass

    # Strategy 10: RSF in buildings
    # e.g., "34, 403 RSF in Building I and 11,411 RSF in Building III"
    rsf_matches = re.findall(r'([\d,\s]+)\s*RSF', val_str)
    if rsf_matches:
        try:
            # Remove spaces from numbers like "34, 403"
            total = sum(float(m.replace(',', '').replace(' ', '')) for m in rsf_matches)
            return total
        except ValueError:
            pass

    # Strategy 11: Just get the first large number as last resort
    # Skip very complex entries that we can't reliably parse
    all_numbers = re.findall(r'[\d,]+', val_str)
    if all_numbers:
        try:
            # Get the largest number that's > 100 (likely SF, not acres)
            candidates = [float(n.replace(',', '')) for n in all_numbers]
            large_candidates = [c for c in candidates if c > 100]
            if large_candidates:
                return max(large_candidates)
        except ValueError:
            pass

    # Unable to parse
    return None


def get_quarter(date):
    """Convert a date to quarter string like '2024 Q4'."""
    if pd.isna(date):
        return None
    quarter = (date.month - 1) // 3 + 1
    return f"{date.year} Q{quarter}"


def main():
    """Main function to process data and generate chart."""
    print("Loading data...")
    df = pd.read_excel(INPUT_FILE)
    print(f"Loaded {len(df)} rows")

    # Filter out land transactions
    land_col = 'Is this Land?'
    initial_count = len(df)
    # Keep rows where Is this Land? is "No" or is null/empty
    # Exclude rows where it's "Yes" or contains "Land"
    df = df[
        (df[land_col].isna()) |
        (df[land_col] == 'No') |
        (~df[land_col].astype(str).str.contains('Land|Yes', case=False, na=False))
    ]
    excluded_count = initial_count - len(df)
    print(f"Filtered out {excluded_count} land transactions, {len(df)} rows remaining")

    # Clean the SF column
    print("\nCleaning Total SF column...")
    sf_col = 'Total SF / Total Acreage if Land '
    date_col = 'When was the lease executed?'

    df['cleaned_sf'] = df[sf_col].apply(clean_sf_value)

    # Stats on cleaning
    total_rows = len(df)
    non_null_original = df[sf_col].notna().sum()
    cleaned_non_null = df['cleaned_sf'].notna().sum()

    print(f"  Original non-null values: {non_null_original}")
    print(f"  Successfully cleaned: {cleaned_non_null}")
    print(f"  Could not parse: {non_null_original - cleaned_non_null}")

    # Show some examples of what couldn't be parsed
    failed_to_parse = df[(df[sf_col].notna()) & (df['cleaned_sf'].isna())][sf_col].unique()
    if len(failed_to_parse) > 0:
        print(f"\n  Examples that could not be parsed:")
        for val in failed_to_parse[:10]:
            print(f"    - {repr(val)}")

    # Parse dates and extract quarters
    print("\nExtracting quarters from dates...")
    df['quarter'] = pd.to_datetime(df[date_col], errors='coerce').apply(get_quarter)

    # Filter to rows with both valid quarter and SF
    platform_col = 'Platform'
    df_valid = df[(df['quarter'].notna()) & (df['cleaned_sf'].notna())].copy()
    print(f"Rows with valid quarter and SF: {len(df_valid)}")

    # Aggregate by quarter and platform
    print("\nAggregating by quarter and platform...")
    quarterly = df_valid.groupby(['quarter', platform_col]).agg({
        'cleaned_sf': 'sum'
    }).reset_index()
    quarterly.columns = ['Quarter', 'Platform', 'Total SF']

    # Sort by quarter
    quarterly['sort_key'] = quarterly['Quarter'].apply(
        lambda x: (int(x.split()[0]), int(x.split()[1][1])) if pd.notna(x) else (0, 0)
    )
    quarterly = quarterly.sort_values('sort_key').drop('sort_key', axis=1)

    # Get unique quarters in order for x-axis
    quarters_ordered = quarterly['Quarter'].unique().tolist()

    # Get unique platforms
    platforms = quarterly['Platform'].unique().tolist()

    print(f"\nQuarterly totals by platform:")
    for quarter in quarters_ordered:
        q_data = quarterly[quarterly['Quarter'] == quarter]
        total = q_data['Total SF'].sum()
        print(f"  {quarter}: {total:,.0f} SF total")
        for _, row in q_data.iterrows():
            print(f"    - {row['Platform']}: {row['Total SF']:,.0f} SF")

    # Create the stacked bar chart
    print("\nGenerating stacked bar chart...")

    fig = go.Figure()

    # Add a bar trace for each platform
    for i, platform in enumerate(platforms):
        platform_data = quarterly[quarterly['Platform'] == platform]
        # Create a series with all quarters, filling missing with 0
        sf_by_quarter = []
        for q in quarters_ordered:
            match = platform_data[platform_data['Quarter'] == q]
            if len(match) > 0:
                sf_by_quarter.append(match['Total SF'].values[0])
            else:
                sf_by_quarter.append(0)

        fig.add_trace(go.Bar(
            x=quarters_ordered,
            y=sf_by_quarter,
            name=platform,
            marker_color=AQUILA_COLORS[i % len(AQUILA_COLORS)],
            hovertemplate='%{x}<br>' + platform + '<br>%{y:,.0f} SF<extra></extra>'
        ))

    fig.update_layout(
        title=dict(
            text='Transaction Volume by Quarter and Platform (Total SF)',
            font=dict(family=AQUILA_FONT, size=20, color='#172344')
        ),
        barmode='stack',
        height=650,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, color='#172344'),
        xaxis=dict(
            title='Quarter',
            showline=True,
            linecolor='#e9e9ea',
            linewidth=0.5,
            mirror=False,
            showgrid=False,
            zeroline=False,
            tickangle=45,
        ),
        yaxis=dict(
            title='Total Square Footage',
            showline=True,
            linecolor='#e9e9ea',
            linewidth=0.5,
            mirror=False,
            showgrid=True,
            gridcolor='#e9e9ea',
            zeroline=True,
            tickformat=',',
        ),
        legend=dict(
            orientation='h',
            yanchor='top',
            y=-0.15,
            xanchor='center',
            x=0.5,
            font=dict(size=10)
        ),
        margin=dict(b=180),
        hovermode='x unified'
    )

    # Save chart
    fig.write_html(OUTPUT_FILE)
    print(f"\nChart saved to: {OUTPUT_FILE}")

    return quarterly


if __name__ == '__main__':
    main()
