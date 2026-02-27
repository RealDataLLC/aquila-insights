"""
Rolling 8-Quarter Office Demand by Submarket
Shows citywide average SF (black dotted) plus SW, CBD, East, NW submarkets
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
print("ROLLING 8-QUARTER OFFICE DEMAND BY SUBMARKET")
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

# Tab 1: Through 2024 data (find by name)
print("  Reading Tab 1: 'Through 2024' data...")
try:
    tab1 = sheet.worksheet("DITM & Crab Trap MASTER Report (Through 2024)")
except Exception as e:
    print(f"    ✗ Could not find tab by name, trying index 2: {e}")
    tab1 = sheet.get_worksheet(2)

rows = tab1.get_all_values()
df_through_2024 = pd.DataFrame(rows[1:], columns=rows[0])
print(f"    - Loaded {len(df_through_2024)} rows")

# Filter to office-only data
if "USE" in df_through_2024.columns:
    df_through_2024 = df_through_2024[
        df_through_2024["USE"].str.lower().str.contains("office", na=False)
    ]
    print(f"    - After filtering to office: {len(df_through_2024)} rows")
elif "Use" in df_through_2024.columns:
    df_through_2024 = df_through_2024[
        df_through_2024["Use"].str.lower().str.contains("office", na=False)
    ]
    print(f"    - After filtering to office: {len(df_through_2024)} rows")

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
    if not date_cols:
        date_cols = [col for col in df.columns if 'DATE' in col.upper() and 'REQ' in col.upper()]
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

    # Market column
    market_col = None
    if 'MARKET' in df.columns:
        market_col = 'MARKET'
    else:
        market_candidates = [col for col in df.columns if 'MARKET' in col.upper()]
        if market_candidates:
            market_col = market_candidates[0]

    if market_col:
        df_std['market'] = df[market_col].astype(str)
    else:
        df_std['market'] = ''

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

print(f"  Combined dataset: {len(df_combined)} rows from 2018+")
print(f"  Date range: {df_combined['date'].min()} to {df_combined['date'].max()}")

# ============================================================================
# STEP 4: Market mapping function
# ============================================================================
print("\nStep 4: Setting up market mapping...")

def map_markets(market_str):
    """
    Map a market string to applicable submarkets.
    Returns a list of submarkets this row applies to.
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

# ============================================================================
# STEP 5: Calculate quarterly metrics by submarket
# ============================================================================
print("\nStep 5: Calculating quarterly metrics...")

# Add quarter column
df_combined['quarter'] = df_combined['date'].dt.to_period('Q').dt.to_timestamp()

# Calculate citywide (all requirements)
print("  Calculating citywide metrics...")
citywide_quarterly = df_combined.groupby('quarter').agg({
    'sf_avg': 'mean'  # Average SF per requirement
}).reset_index()
citywide_quarterly.columns = ['quarter', 'avg_sf']
citywide_quarterly['submarket'] = 'Citywide'

print(f"    - Citywide: {len(citywide_quarterly)} quarters")

# Calculate by submarket
print("  Calculating submarket metrics...")

# Apply market mapping to each row
df_combined['applicable_markets'] = df_combined['market'].apply(map_markets)

# Explode so each row appears once per applicable market
df_expanded = df_combined.explode('applicable_markets')
df_expanded = df_expanded[df_expanded['applicable_markets'].notna()].copy()
df_expanded = df_expanded[df_expanded['applicable_markets'] != ''].copy()
df_expanded.rename(columns={'applicable_markets': 'submarket'}, inplace=True)

# Group by quarter and submarket
submarket_quarterly = df_expanded.groupby(['quarter', 'submarket'], observed=False).agg({
    'sf_avg': 'mean'  # Average SF per requirement
}).reset_index()
submarket_quarterly.columns = ['quarter', 'submarket', 'avg_sf']

print(f"    - Total submarket data points: {len(submarket_quarterly)}")
for market in ['CBD', 'SW', 'NW', 'E', 'C']:
    count = len(submarket_quarterly[submarket_quarterly['submarket'] == market])
    print(f"      {market}: {count} quarters")

# ============================================================================
# STEP 6: Apply rolling 8-quarter average
# ============================================================================
print("\nStep 6: Applying rolling 8-quarter average...")

def apply_rolling_average(df, window=8):
    """Apply rolling average to a submarket's data"""
    df = df.sort_values('quarter').copy()
    df['rolling_avg_sf'] = df['avg_sf'].rolling(window=window, min_periods=1).mean()
    return df

# Apply to citywide
citywide_rolling = apply_rolling_average(citywide_quarterly)
print(f"  Citywide rolling data: {len(citywide_rolling)} quarters")

# Apply to each submarket
rolling_data = []
for market in ['CBD', 'SW', 'NW', 'E', 'C']:
    market_data = submarket_quarterly[submarket_quarterly['submarket'] == market].copy()
    if len(market_data) > 0:
        market_rolling = apply_rolling_average(market_data)
        rolling_data.append(market_rolling)
        print(f"  {market} rolling data: {len(market_rolling)} quarters")

# Combine all submarket data
submarket_rolling = pd.concat(rolling_data, ignore_index=True)

# ============================================================================
# STEP 7: Create chart
# ============================================================================
print("\nStep 7: Creating rolling 8-quarter demand chart...")

fig = go.Figure()

# Citywide line (black dotted)
fig.add_trace(go.Scatter(
    x=citywide_rolling['quarter'],
    y=citywide_rolling['rolling_avg_sf'],
    mode='lines',
    name='Citywide',
    line=dict(color='black', width=3, dash='dot'),
    hovertemplate=(
        '<b>Citywide</b><br>'
        'Quarter: %{x|%Y Q%q}<br>'
        'Avg SF (8Q Rolling): %{y:,.0f}<br>'
        '<extra></extra>'
    )
))

# Submarket lines with Aquila colors
submarket_colors = {
    'SW': AQUILA_COLORS[1],   # Glass Blue
    'CBD': AQUILA_COLORS[2],  # Copper
    'E': AQUILA_COLORS[3],    # Brass
    'NW': AQUILA_COLORS[4],   # Greenspace
}

submarket_order = ['SW', 'CBD', 'E', 'NW']

for market in submarket_order:
    market_data = submarket_rolling[submarket_rolling['submarket'] == market]
    if len(market_data) > 0:
        fig.add_trace(go.Scatter(
            x=market_data['quarter'],
            y=market_data['rolling_avg_sf'],
            mode='lines+markers',
            name=market,
            line=dict(color=submarket_colors[market], width=2.5),
            marker=dict(size=6),
            hovertemplate=(
                f'<b>{market}</b><br>'
                'Quarter: %{x|%Y Q%q}<br>'
                'Avg SF (8Q Rolling): %{y:,.0f}<br>'
                '<extra></extra>'
            )
        ))

# Get date range for title
min_quarter = df_combined['quarter'].min()
max_quarter = df_combined['quarter'].max()

fig.update_layout(
    title={
        'text': f'Rolling 8-Quarter Office Demand by Submarket ({min_quarter.year}\u2013{max_quarter.year})',
        'font': dict(family=AQUILA_FONT, size=24, color=AQUILA_COLORS[0]),
        'x': 0.5,
        'xanchor': 'center',
    },
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(family=AQUILA_FONT, size=12, color=AQUILA_COLORS[0]),
    xaxis=dict(
        title='Quarter',
        gridcolor='#e9e9ea',
        showgrid=True,
        showline=True,
        linecolor='lightgrey',
        linewidth=2,
        tickformat='%Y Q%q'
    ),
    yaxis=dict(
        title='Average Square Feet per Requirement (8-Quarter Rolling Average)',
        gridcolor='#e9e9ea',
        showgrid=True,
        showline=True,
        linecolor='lightgrey',
        linewidth=2,
        tickformat=',',
        rangemode='tozero'
    ),
    legend=dict(
        orientation='h',
        yanchor='bottom',
        y=-0.25,
        xanchor='center',
        x=0.5,
        font=dict(size=14)
    ),
    hovermode='x unified',
    height=650,
    width=1200,
    margin=dict(t=100, b=120, l=100, r=50)
)

# Save chart
os.makedirs("charts/office", exist_ok=True)
output_file = "charts/office/requirements_rolling_8q_by_market.html"
fig.write_html(output_file)

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"\nData processed:")
print(f"  - Total requirements: {len(df_combined)}")
print(f"  - Date range: {df_combined['date'].min().date()} to {df_combined['date'].max().date()}")
print(f"  - Quarters: {len(df_combined['quarter'].unique())}")

print(f"\nRolling 8-quarter metrics:")
print(f"  - Citywide: {len(citywide_rolling)} data points")
for market in submarket_order:
    market_data = submarket_rolling[submarket_rolling['submarket'] == market]
    print(f"  - {market}: {len(market_data)} data points")

print(f"\nChart saved:")
print(f"  ✓ {output_file}")

print("\n" + "="*80)
print("✓ Complete!")
print("="*80)
