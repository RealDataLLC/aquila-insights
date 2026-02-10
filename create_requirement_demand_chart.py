"""
Office Demand by Tenant Size - Grouped bar chart with total demand line
Generates a chart showing annual requirement SF broken down by tenant size category,
with a total demand line on a secondary y-axis.
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
    sys.exit(1)

import plotly.graph_objects as go
from dotenv import load_dotenv
from aquila_graphing_tools import AQUILA_COLORS, AQUILA_FONT

# Load environment variables
load_dotenv('aquila_graph.env')

# Check if we should use JSON file or environment variables
json_file = 'aquilacommercialsheets-923494a59a4b.json'
use_json = os.path.exists(json_file)

print("=" * 80)
print("OFFICE DEMAND BY TENANT SIZE")
print("=" * 80)

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
    # Helper function to strip quotes from env vars (matches office_demand_by_market pattern)
    def get_env_stripped(key):
        val = os.getenv(key)
        if val is not None:
            return val.strip('"').strip("'")
        return val

    credentials_dict = {
        "type": get_env_stripped("GOOGLE_SERVICE_ACCOUNT_TYPE"),
        "project_id": get_env_stripped("GOOGLE_PROJECT_ID"),
        "private_key_id": get_env_stripped("GOOGLE_PRIVATE_KEY_ID"),
        "private_key": get_env_stripped("GOOGLE_PRIVATE_KEY").replace('\\n', '\n') if get_env_stripped("GOOGLE_PRIVATE_KEY") else None,
        "client_email": get_env_stripped("GOOGLE_CLIENT_EMAIL"),
        "client_id": get_env_stripped("GOOGLE_CLIENT_ID"),
        "auth_uri": get_env_stripped("GOOGLE_AUTH_URI"),
        "token_uri": get_env_stripped("GOOGLE_TOKEN_URI"),
        "auth_provider_x509_cert_url": get_env_stripped("GOOGLE_AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": get_env_stripped("GOOGLE_CLIENT_X509_CERT_URL"),
        "universe_domain": get_env_stripped("GOOGLE_UNIVERSE_DOMAIN")
    }

    # Defensive: ensure "type" is present and correct, else fail with friendly error
    if credentials_dict.get("type") != "service_account":
        raise ValueError(
            f'GOOGLE_SERVICE_ACCOUNT_TYPE missing or incorrect in environment variables. '
        )
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)

client = gspread.authorize(credentials)
spreadsheet_id = '1bzpRnUrpBH6l_zX7DtTypczZf5bpYVwqPUG3tzg2vec'
sheet = client.open_by_key(spreadsheet_id)

print("  Connected successfully")

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
print("  Reading Tab 1: 'DITM & Crab Trap MASTER Report (Through 2024)' data...")
try:
    tab1 = sheet.worksheet("DITM & Crab Trap MASTER Report (Through 2024)")
except Exception as e:
    print(f"    ✗ Could not find tab by name, trying index 2: {e}")
    tab1 = sheet.get_worksheet(2)

rows = tab1.get_all_values()
df_through_2024 = pd.DataFrame(rows[1:], columns=rows[0])

print(f"    - Loaded {len(df_through_2024)} rows")
print(f"    - Columns: {len(df_through_2024.columns)}")

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
else:
    print(f"    - No USE/Use column found, keeping all {len(df_through_2024)} rows")

# ============================================================================
# STEP 3: Standardize and combine data
# ============================================================================
print("\nStep 3: Standardizing and combining data...")


def standardize_tab0(df):
    """Standardize Tab 0 (2025+) data"""
    df_std = pd.DataFrame()
    df_std['date'] = pd.to_datetime(df['DATE OF REQUIREMENT'], errors='coerce')
    df_std['sf_low'] = pd.to_numeric(df['REQUIRED SF (LOW)'], errors='coerce')
    df_std['sf_high'] = pd.to_numeric(df['REQUIRED SF (HIGH)'], errors='coerce')
    df_std['source_tab'] = '2025+'
    return df_std


def standardize_tab1(df):
    """Standardize Tab 1 (Through 2024) data"""
    df_std = pd.DataFrame()

    print("  Tab 1 column names (first 20):")
    for col in list(df.columns)[:20]:
        print(f"    - {col}")

    # Find date column with fuzzy matching
    date_col = None
    if 'DATE OF REQUIREMENT' in df.columns:
        date_col = 'DATE OF REQUIREMENT'
    else:
        # Look for columns containing both DATE and REQ
        date_candidates = [col for col in df.columns if 'DATE' in col.upper() and 'REQ' in col.upper()]
        if date_candidates:
            date_col = date_candidates[0]
        else:
            # Fall back to any DATE column
            date_cols = [col for col in df.columns if 'DATE' in col.upper()]
            if date_cols:
                date_col = date_cols[0]

    if date_col:
        print(f"  Using date column: '{date_col}'")
        df_std['date'] = pd.to_datetime(df[date_col], errors='coerce')
    else:
        print("  ✗ No date column found")
        df_std['date'] = pd.NaT

    # Find SF LOW column with fuzzy matching
    sf_low_col = None
    if 'REQUIRED SF (LOW)' in df.columns:
        sf_low_col = 'REQUIRED SF (LOW)'
    else:
        # Look for columns containing SF and LOW
        candidates = [col for col in df.columns if 'SF' in col.upper() and 'LOW' in col.upper()]
        if candidates:
            sf_low_col = candidates[0]

    if sf_low_col:
        print(f"  Using SF LOW column: '{sf_low_col}'")
        df_std['sf_low'] = pd.to_numeric(
            df[sf_low_col].astype(str).str.replace(',', '').str.replace('$', ''),
            errors='coerce'
        )
    else:
        print("  ✗ No SF LOW column found")
        df_std['sf_low'] = np.nan

    # Find SF HIGH column with fuzzy matching
    sf_high_col = None
    if 'REQUIRED SF (HIGH)' in df.columns:
        sf_high_col = 'REQUIRED SF (HIGH)'
    else:
        # Look for columns containing SF and HIGH
        candidates = [col for col in df.columns if 'SF' in col.upper() and 'HIGH' in col.upper()]
        if candidates:
            sf_high_col = candidates[0]

    if sf_high_col:
        print(f"  Using SF HIGH column: '{sf_high_col}'")
        df_std['sf_high'] = pd.to_numeric(
            df[sf_high_col].astype(str).str.replace(',', '').str.replace('$', ''),
            errors='coerce'
        )
    else:
        print("  ✗ No SF HIGH column found")
        df_std['sf_high'] = np.nan

    df_std['source_tab'] = 'Through 2024'
    return df_std


# Standardize both datasets
df_std_2025 = standardize_tab0(df_2025_plus)
df_std_2024 = standardize_tab1(df_through_2024)

# Check if Through 2024 data is empty
print(f"\n  Validation:")
print(f"    Tab 0 (2025+) standardized: {len(df_std_2025)} rows")
print(f"    Tab 1 (Through 2024) standardized: {len(df_std_2024)} rows")

if len(df_std_2024) == 0:
    print("  ⚠ WARNING: Through 2024 tab produced 0 rows after standardization!")
    print("  ⚠ Charts will only contain 2025+ data!")
else:
    # Check data quality
    valid_dates_2024 = df_std_2024['date'].notna().sum()
    valid_sf_2024 = df_std_2024['sf_low'].notna().sum()
    print(f"    Tab 1 valid dates: {valid_dates_2024} / {len(df_std_2024)}")
    print(f"    Tab 1 valid SF: {valid_sf_2024} / {len(df_std_2024)}")

    if valid_dates_2024 == 0:
        print("  ⚠ WARNING: No valid dates found in Through 2024 data!")
    if valid_sf_2024 == 0:
        print("  ⚠ WARNING: No valid SF values found in Through 2024 data!")

# Combine datasets
df_combined = pd.concat([df_std_2024, df_std_2025], ignore_index=True)

# Calculate average SF
df_combined['sf_avg'] = (df_combined['sf_low'] + df_combined['sf_high']) / 2

# Filter out records with no SF data or no date
df_combined = df_combined[df_combined['sf_avg'].notna()].copy()
df_combined = df_combined[df_combined['date'].notna()].copy()

# Filter to 2017 onwards
df_combined = df_combined[df_combined['date'] >= '2017-01-01'].copy()

# Extract year
df_combined['year'] = df_combined['date'].dt.year

# Only include complete or near-complete years (exclude current partial year if too early)
# Keep all years that have data
print(f"  Combined dataset: {len(df_combined)} rows")
print(f"  Date range: {df_combined['date'].min()} to {df_combined['date'].max()}")
print(f"  Years: {sorted(df_combined['year'].unique())}")

# ============================================================================
# STEP 4: Bin by tenant size and aggregate by year
# ============================================================================
print("\nStep 4: Binning by tenant size category...")

# Size bins matching the reference chart
bins = [0, 10000, 25000, 50000, 100000, float('inf')]
labels = ['Sub 10k SF', '10k-25k SF', '25k-50k SF', '50k-100k SF', 'Mega Requirements']

df_combined['size_category'] = pd.cut(
    df_combined['sf_avg'],
    bins=bins,
    labels=labels,
    right=False
)

# Aggregate: sum of sf_avg by year and size category
yearly_by_size = df_combined.groupby(['year', 'size_category'], observed=False).agg(
    segment_demand=('sf_avg', 'sum'),
    count=('sf_avg', 'count')
).reset_index()

# Also calculate total demand per year
yearly_total = df_combined.groupby('year').agg(
    total_demand=('sf_avg', 'sum')
).reset_index()

print(f"  Years with data: {len(yearly_total)}")
for _, row in yearly_total.iterrows():
    print(f"    {int(row['year'])}: {row['total_demand']:,.0f} SF total demand")

# ============================================================================
# STEP 5: Create the chart
# ============================================================================
print("\nStep 5: Creating Office Demand by Tenant Size chart...")

os.makedirs("charts/office", exist_ok=True)

# Define colors for each category (matching the visual style of the reference)
category_colors = {
    'Mega Requirements': AQUILA_COLORS[0],   # AQUILA Navy
    '50k-100k SF':       AQUILA_COLORS[4],   # Greenspace
    '25k-50k SF':        AQUILA_COLORS[3],   # Brass
    '10k-25k SF':        AQUILA_COLORS[2],   # Copper
    'Sub 10k SF':        AQUILA_COLORS[7],   # Pennybacker
}

# Order categories from largest to smallest for visual hierarchy
category_order = ['Mega Requirements', '50k-100k SF', '25k-50k SF', '10k-25k SF', 'Sub 10k SF']

years = sorted(yearly_by_size['year'].unique())

fig = go.Figure()

# Add grouped bars for each size category
for category in category_order:
    cat_data = yearly_by_size[yearly_by_size['size_category'] == category]
    cat_data = cat_data.set_index('year').reindex(years).reset_index()
    # Fill NaN values only in numeric columns
    cat_data['segment_demand'] = cat_data['segment_demand'].fillna(0)

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

# Add total demand line on secondary y-axis
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

# Determine date range for title
min_year = int(min(years))
max_year = int(max(years))

fig.update_layout(
    title={
        'text': f'Office Demand by Tenant Size ({min_year}\u2013{max_year})',
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

output_path = 'charts/office/requirements_demand_by_tenant_size.html'
fig.write_html(output_path)
print(f"  Chart saved to: {output_path}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"\nData: {len(df_combined)} requirements from {min_year} to {max_year}")
print(f"\nSize category breakdown:")
for category in category_order:
    cat_total = yearly_by_size[yearly_by_size['size_category'] == category]['segment_demand'].sum()
    cat_count = yearly_by_size[yearly_by_size['size_category'] == category]['count'].sum()
    print(f"  {category:25s}: {cat_total:>15,.0f} SF ({int(cat_count)} requirements)")
print(f"\n  {'TOTAL':25s}: {yearly_total['total_demand'].sum():>15,.0f} SF")
print(f"\nChart saved to: {output_path}")
print("=" * 80)
