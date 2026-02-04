"""
Office Demand by Tenant Size - By Market
Generates market-specific charts broken out by CBD, SW, NW, E, C
"""
import pandas as pd
import numpy as np
import sys
import os

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure gspread and oauth2client are installed")
    sys.exit(1)

import plotly.graph_objects as go
from datetime import datetime
from dotenv import load_dotenv
from aquila_graphing_tools import AQUILA_COLORS, AQUILA_FONT

# Load environment variables
load_dotenv('aquila_graph.env')

# Check if we should use JSON file or environment variables
json_file = 'aquilacommercialsheets-923494a59a4b.json'
use_json = os.path.exists(json_file)

print("="*80)
print("OFFICE DEMAND BY TENANT SIZE - BY MARKET")
print("="*80)

# ============================================================================
# STEP 1: Connect to Google Sheets
# ============================================================================
print("\nStep 1: Connecting to Google Sheets...")

scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

if use_json:
    print("  Using JSON credentials file")
    credentials = ServiceAccountCredentials.from_json_keyfile_name(json_file, scope)
else:
    print("  Using environment variables for credentials")
    credentials_dict = {
        "type": os.getenv("GOOGLE_SERVICE_ACCOUNT_TYPE"),
        "project_id": os.getenv("GOOGLE_PROJECT_ID"),
        "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("GOOGLE_PRIVATE_KEY").replace('\\n', '\n') if os.getenv("GOOGLE_PRIVATE_KEY") else None,
        "client_email": os.getenv("GOOGLE_CLIENT_EMAIL"),
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "auth_uri": os.getenv("GOOGLE_AUTH_URI"),
        "token_uri": os.getenv("GOOGLE_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv("GOOGLE_AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.getenv("GOOGLE_CLIENT_X509_CERT_URL"),
        "universe_domain": os.getenv("GOOGLE_UNIVERSE_DOMAIN")
    }
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)

client = gspread.authorize(credentials)
spreadsheet_id = '1bzpRnUrpBH6l_zX7DtTypczZf5bpYVwqPUG3tzg2vec'
sheet = client.open_by_key(spreadsheet_id)

print("  ✓ Connected successfully")

# ============================================================================
# STEP 2: Read both tabs
# ============================================================================
print("\nStep 2: Reading data from both tabs...")

# Tab 0: 2025+ data
print("  Reading Tab 0: '2025 +' data...")
tab0 = sheet.get_worksheet(0)
df_2025_plus = pd.DataFrame(tab0.get_all_records())
print(f"    - Loaded {len(df_2025_plus)} rows")

# Tab 1: Through 2024 data (index 2)
print("  Reading Tab 1: 'Through 2024' data...")
tab1 = sheet.get_worksheet(2)
rows = tab1.get_all_values()
df_through_2024 = pd.DataFrame(rows[1:], columns=rows[0])

# Filter to office-only data
if "USE" in df_through_2024.columns:
    df_through_2024 = df_through_2024[df_through_2024["USE"].str.lower().str.contains("office", na=False)]

print(f"    - Loaded {len(df_through_2024)} rows")

# ============================================================================
# STEP 3: Standardize data
# ============================================================================
print("\nStep 3: Standardizing data...")

def standardize_tab0(df):
    """Standardize Tab 0 (2025+) data"""
    df_std = pd.DataFrame()
    df_std['date'] = pd.to_datetime(df['DATE OF REQUIREMENT'], errors='coerce')
    df_std['sf_low'] = pd.to_numeric(df['REQUIRED SF (LOW)'], errors='coerce')
    df_std['sf_high'] = pd.to_numeric(df['REQUIRED SF (HIGH)'], errors='coerce')
    df_std['market'] = df.get('MARKET', '').astype(str)
    df_std['source_tab'] = '2025+'
    return df_std

def standardize_tab1(df):
    """Standardize Tab 1 (Through 2024) data"""
    df_std = pd.DataFrame()

    # Date
    date_cols = [col for col in df.columns if 'DATE' in col.upper() and 'REQUIREMENT' in col.upper()]
    if date_cols:
        df_std['date'] = pd.to_datetime(df[date_cols[0]], errors='coerce')
    else:
        df_std['date'] = pd.NaT

    # SF columns
    sf_low_col = next((col for col in df.columns if 'SF' in col.upper() and 'LOW' in col.upper()), None)
    sf_high_col = next((col for col in df.columns if 'SF' in col.upper() and 'HIGH' in col.upper()), None)

    if sf_low_col:
        df_std['sf_low'] = pd.to_numeric(
            df[sf_low_col].astype(str).str.replace(',', '').str.replace('$', ''),
            errors='coerce'
        )
    else:
        df_std['sf_low'] = np.nan

    if sf_high_col:
        df_std['sf_high'] = pd.to_numeric(
            df[sf_high_col].astype(str).str.replace(',', '').str.replace('$', ''),
            errors='coerce'
        )
    else:
        df_std['sf_high'] = np.nan

    df_std['market'] = df.get('MARKET', '').astype(str)
    df_std['source_tab'] = 'Through 2024'

    return df_std

# Standardize both datasets
df_std_2025 = standardize_tab0(df_2025_plus)
df_std_2024 = standardize_tab1(df_through_2024)

# Combine datasets
df_combined = pd.concat([df_std_2024, df_std_2025], ignore_index=True)

# Calculate average SF
df_combined['sf_avg'] = (df_combined['sf_low'] + df_combined['sf_high']) / 2

# Filter out records with no SF data
df_combined = df_combined[df_combined['sf_avg'].notna()].copy()

# Filter to 2018 onwards
df_combined = df_combined[df_combined['date'] >= '2018-01-01'].copy()

print(f"  Combined dataset: {len(df_combined)} rows")
print(f"  Date range: {df_combined['date'].min()} to {df_combined['date'].max()}")

# ============================================================================
# STEP 4: Market mapping function
# ============================================================================
print("\nStep 4: Setting up market mapping...")

def map_markets(market_str):
    """
    Map a market string to applicable submarkets.
    Returns a list of submarkets this row applies to.

    Rules:
    - Far NW, FNW, Domain, Cedar Park → NW
    - Urban Core → CBD and C
    - Citywide, Flexible, Market Wide, Austin MSA, Austin Metro → all markets
    - NC → C
    - Bee Caves → SW
    - CBD, SW, NW, E, C → themselves
    """
    if pd.isna(market_str) or market_str == '':
        return []

    market_upper = str(market_str).upper().strip()
    applicable_markets = []

    # Split by comma to handle multiple markets
    market_parts = [m.strip() for m in market_upper.split(',')]

    for part in market_parts:
        # Citywide/flexible - applies to all markets
        if any(keyword in part for keyword in ['CITYWIDE', 'FLEXIBLE', 'MARKET WIDE', 'AUSTIN MSA', 'AUSTIN METRO']):
            return ['CBD', 'SW', 'NW', 'E', 'C']

        # Urban Core → CBD and C
        if 'URBAN CORE' in part:
            applicable_markets.extend(['CBD', 'C'])

        # Far NW, FNW, Domain, Cedar Park → NW
        elif any(keyword in part for keyword in ['FAR NW', 'FNW', 'DOMAIN', 'CEDAR PARK']):
            applicable_markets.append('NW')

        # NC → C
        elif part == 'NC':
            applicable_markets.append('C')

        # Bee Caves → SW
        elif 'BEE CAVES' in part:
            applicable_markets.append('SW')

        # Direct matches
        elif 'CBD' in part:
            applicable_markets.append('CBD')
        elif part in ['SW', 'S']:
            applicable_markets.append('SW')
        elif part in ['NW', 'N']:
            applicable_markets.append('NW')
        elif part == 'E':
            applicable_markets.append('E')
        elif part == 'C':
            applicable_markets.append('C')

    # Remove duplicates while preserving order
    return list(dict.fromkeys(applicable_markets))

# Test the mapping function
print("  Testing market mapping:")
test_cases = [
    "CBD, SW, NW, E",
    "Citywide",
    "Urban Core",
    "Far NW",
    "NC",
    "Bee Caves",
    "CBD"
]
for test in test_cases:
    result = map_markets(test)
    print(f"    '{test}' → {result}")

# ============================================================================
# STEP 5: Expand data by market
# ============================================================================
print("\nStep 5: Expanding data by applicable markets...")

# Apply market mapping to each row
df_combined['applicable_markets'] = df_combined['market'].apply(map_markets)

# Explode so each row appears once per applicable market
df_expanded = df_combined.explode('applicable_markets')

# Filter to rows that have at least one applicable market
df_expanded = df_expanded[df_expanded['applicable_markets'].notna()].copy()
df_expanded = df_expanded[df_expanded['applicable_markets'] != ''].copy()

# Rename for clarity
df_expanded.rename(columns={'applicable_markets': 'submarket'}, inplace=True)

print(f"  Expanded to {len(df_expanded)} market-specific records")
print(f"  Breakdown by submarket:")
for market in ['CBD', 'SW', 'NW', 'E', 'C']:
    count = len(df_expanded[df_expanded['submarket'] == market])
    total_sf = df_expanded[df_expanded['submarket'] == market]['sf_avg'].sum()
    print(f"    {market}: {count} records, {total_sf:,.0f} SF")

# ============================================================================
# STEP 6: Generate market-specific charts
# ============================================================================
print("\nStep 6: Generating market-specific charts...")

# Create output directory
os.makedirs('charts/office', exist_ok=True)

# Size bins (5 categories)
demand_bins = [0, 10000, 25000, 50000, 100000, float('inf')]
demand_labels = ['Sub 10k SF', '10k-25k SF', '25k-50k SF', '50k-100k SF', 'Mega Requirements']

df_expanded['size_category'] = pd.cut(
    df_expanded['sf_avg'],
    bins=demand_bins,
    labels=demand_labels,
    right=False
)

# Add year column
df_expanded['year'] = df_expanded['date'].dt.year

# Colors for each size category (replace Signal with Pennybacker)
category_colors = {
    'Mega Requirements': AQUILA_COLORS[0],   # AQUILA Navy
    '50k-100k SF':       AQUILA_COLORS[4],   # Greenspace
    '25k-50k SF':        AQUILA_COLORS[3],   # Brass
    '10k-25k SF':        AQUILA_COLORS[2],   # Copper
    'Sub 10k SF':        AQUILA_COLORS[7],   # Pennybacker (was Signal)
}

category_order = ['Mega Requirements', '50k-100k SF', '25k-50k SF', '10k-25k SF', 'Sub 10k SF']

# Market display names
market_names = {
    'CBD': 'CBD',
    'SW': 'Southwest',
    'NW': 'Northwest',
    'E': 'East',
    'C': 'Central'
}

# Generate a chart for each market
for market_code in ['CBD', 'SW', 'NW', 'E', 'C']:
    print(f"\n  Generating chart for {market_names[market_code]}...")

    # Filter to this market
    df_market = df_expanded[df_expanded['submarket'] == market_code].copy()

    if len(df_market) == 0:
        print(f"    ⚠ No data for {market_code}, skipping")
        continue

    # Aggregate by year and size category
    yearly_by_size = df_market.groupby(['year', 'size_category'], observed=False).agg(
        segment_demand=('sf_avg', 'sum'),
        count=('sf_avg', 'count')
    ).reset_index()

    # Total demand per year
    yearly_total = df_market.groupby('year').agg(
        total_demand=('sf_avg', 'sum')
    ).reset_index()

    years = sorted(yearly_by_size['year'].unique())

    if len(years) == 0:
        print(f"    ⚠ No year data for {market_code}, skipping")
        continue

    # Create figure
    fig = go.Figure()

    # Grouped bars for each size category
    for category in category_order:
        cat_data = yearly_by_size[yearly_by_size['size_category'] == category]
        cat_data = cat_data[['year', 'segment_demand', 'count']].set_index('year').reindex(years).reset_index()
        # Fill NaN values only in numeric columns
        cat_data['segment_demand'] = cat_data['segment_demand'].fillna(0)
        cat_data['count'] = cat_data['count'].fillna(0)

        fig.add_trace(go.Bar(
            x=cat_data['year'].astype(str),
            y=cat_data['segment_demand'],
            name=category,
            marker_color=category_colors[category],
            hovertemplate=(
                f'<b>{category}</b><br>'
                'Year: %{x}<br>'
                'Demand: %{y:,.0f} SF<br>'
                '<extra></extra>'
            ),
        ))

    # Total demand line on secondary y-axis
    total_data = yearly_total.set_index('year').reindex(years).reset_index()
    total_data['total_demand'] = total_data['total_demand'].fillna(0)

    fig.add_trace(go.Scatter(
        x=total_data['year'].astype(str),
        y=total_data['total_demand'],
        mode='lines+markers',
        name='Total Demand',
        line=dict(color=AQUILA_COLORS[0], width=3, dash='dash'),
        marker=dict(size=10, color=AQUILA_COLORS[0], symbol='line-ew-open', line=dict(width=3)),
        yaxis='y2',
        hovertemplate=(
            '<b>Total Demand</b><br>'
            'Year: %{x}<br>'
            'Total: %{y:,.0f} SF<br>'
            '<extra></extra>'
        ),
    ))

    min_year = int(min(years))
    max_year = int(max(years))

    fig.update_layout(
        title={
            'text': f'Office Demand by Tenant Size - {market_names[market_code]} ({min_year}–{max_year})',
            'font': dict(family=AQUILA_FONT, size=24, color=AQUILA_COLORS[0]),
            'x': 0.5,
            'xanchor': 'center',
        },
        barmode='group',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, size=12, color=AQUILA_COLORS[0]),
        xaxis=dict(
            title='',
            showgrid=False,
            showline=True,
            linecolor='lightgrey',
            linewidth=1,
            tickfont=dict(size=13),
        ),
        yaxis=dict(
            title='Segment Demand (SF)',
            titlefont=dict(size=14),
            showgrid=True,
            gridcolor='#e9e9ea',
            showline=True,
            linecolor='lightgrey',
            linewidth=1,
            tickformat=',',
            rangemode='tozero',
        ),
        yaxis2=dict(
            title='Total Demand (SF)',
            titlefont=dict(size=14),
            overlaying='y',
            side='right',
            showgrid=False,
            showline=True,
            linecolor='lightgrey',
            linewidth=1,
            tickformat=',',
            rangemode='tozero',
        ),
        legend=dict(
            orientation='h',
            yanchor='top',
            y=-0.1,
            xanchor='center',
            x=0.5,
            font=dict(size=12),
            traceorder='normal',
        ),
        height=650,
        width=1000,
        margin=dict(t=80, b=120, l=80, r=80),
        hovermode='x unified',
    )

    # Save chart
    filename = f'charts/office/requirements_demand_by_tenant_size_{market_code.lower()}.html'
    fig.write_html(filename)
    print(f"    ✓ Saved {filename}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"\nMarket-specific charts generated:")
for market_code in ['CBD', 'SW', 'NW', 'E', 'C']:
    filename = f'charts/office/requirements_demand_by_tenant_size_{market_code.lower()}.html'
    if os.path.exists(filename):
        print(f"  ✓ {filename}")

print("\n" + "="*80)
print("✓ Complete!")
print("="*80)
