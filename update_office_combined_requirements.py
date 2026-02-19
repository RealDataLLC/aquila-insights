"""
Combined Requirements Data Charts - Combines 2025+ and Through 2024 data
Generates updated requirements charts and new requirements vs absorption chart
"""
import pandas as pd
import numpy as np
import sys
import os

# Add retry logic for imports
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure gspread and oauth2client are installed")
    sys.exit(1)

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from dotenv import load_dotenv
from aquila_graphing_tools import initialize_supabase_connection, AQUILA_COLORS, AQUILA_FONT

# Load environment variables
load_dotenv('aquila_graph.env')

# Check if we should use JSON file or environment variables
json_file = 'aquilacommercialsheets-923494a59a4b.json'
use_json = os.path.exists(json_file)

print("="*80)
print("COMBINED REQUIREMENTS DATA ANALYSIS")
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
    # Helper function to strip quotes from env vars
    def get_env_stripped(key):
        val = os.getenv(key)
        if val:
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
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)

client = gspread.authorize(credentials)
spreadsheet_id = '1bzpRnUrpBH6l_zX7DtTypczZf5bpYVwqPUG3tzg2vec'
sheet = client.open_by_key(spreadsheet_id)

print("  [OK] Connected successfully")

# ============================================================================
# STEP 2: Read both tabs
# ============================================================================
print("\nStep 2: Reading data from both tabs...")

# Tab 0: 2025+ data
print("  Reading Tab 0: '2025 +' data...")
tab0 = sheet.get_worksheet(0)
df_2025_plus = pd.DataFrame(tab0.get_all_records())
print(f"    - Loaded {len(df_2025_plus)} rows, {len(df_2025_plus.columns)} columns")

# Tab 1: Through 2024 data (find by name)
print("  Reading Tab 1: 'DITM & Crab Trap MASTER Report (Through 2024)' data...")
try:
    tab1 = sheet.worksheet("DITM & Crab Trap MASTER Report (Through 2024)")
except Exception as e:
    print(f"    [ERROR] Could not find tab by name, trying index 2: {e}")
    tab1 = sheet.get_worksheet(2)

rows = tab1.get_all_values()
df_through_2024 = pd.DataFrame(rows[1:], columns=rows[0])  # Skip header row for data

print(f"    - Loaded {len(df_through_2024)} rows, {len(df_through_2024.columns)} columns")

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
# STEP 3: Map columns between tabs
# ============================================================================
print("\nStep 3: Mapping columns between tabs...")

# Key columns we need for analysis:
# - Date column
# - Company/tenant name
# - Square footage (low, high, avg)
# - Industry
# - Market
# - Status

# Column mapping: {tab1_column: tab0_column}
column_mapping = {}

# Analyze Tab 1 columns
print("\n  Tab 1 columns:")
for col in df_through_2024.columns[:20]:  # Show first 20
    print(f"    - {col}")

# Common columns that should exist in both
key_columns_tab0 = {
    'date': 'DATE OF REQUIREMENT',
    'company': 'COMPANY',
    'sf_low': 'REQUIRED SF (LOW)',
    'sf_high': 'REQUIRED SF (HIGH)',
    'industry': 'INDUSTRY',
    'market': 'MARKET',
    'status': 'STATUS',
    'use_market': 'USE MARKET'
}

# Try to find matching columns in Tab 1
print("\n  Attempting column mapping...")
for key, tab0_col in key_columns_tab0.items():
    # Look for exact match first
    if tab0_col in df_through_2024.columns:
        column_mapping[key] = tab0_col
        print(f"    [OK] {key}: '{tab0_col}' (exact match)")
    else:
        # Look for similar column names
        similar = [col for col in df_through_2024.columns
                  if any(word in col.upper() for word in tab0_col.upper().split())]
        if similar:
            column_mapping[key] = similar[0]
            print(f"    ~ {key}: '{similar[0]}' (similar to '{tab0_col}')")
        else:
            print(f"    [ERROR] {key}: no match found for '{tab0_col}'")

# ============================================================================
# STEP 4: Standardize and combine data
# ============================================================================
print("\nStep 4: Standardizing and combining data...")

def standardize_tab0(df):
    """Standardize Tab 0 (2025+) data"""
    df_std = pd.DataFrame()
    df_std['date'] = pd.to_datetime(df['DATE OF REQUIREMENT'], errors='coerce')
    df_std['company'] = df.get('COMPANY', '')
    df_std['sf_low'] = pd.to_numeric(df['REQUIRED SF (LOW)'], errors='coerce')
    df_std['sf_high'] = pd.to_numeric(df['REQUIRED SF (HIGH)'], errors='coerce')
    df_std['industry'] = df.get('INDUSTRY', '')
    df_std['market'] = df.get('MARKET', '')
    df_std['use_market'] = df.get('USE MARKET', '')
    df_std['status'] = df.get('STATUS', 'Active')
    df_std['source_tab'] = '2025+'
    return df_std

def standardize_tab1(df, mapping):
    """Standardize Tab 1 (Through 2024) data using column mapping"""
    df_std = pd.DataFrame()

    # Date - try multiple possible date columns
    date_col = mapping.get('date')
    if date_col and date_col in df.columns:
        df_std['date'] = pd.to_datetime(df[date_col], errors='coerce')
    else:
        # Try to find any date column
        date_candidates = [col for col in df.columns if 'DATE' in col.upper()]
        if date_candidates:
            df_std['date'] = pd.to_datetime(df[date_candidates[0]], errors='coerce')
        else:
            df_std['date'] = pd.NaT

    # Other columns
    df_std['company'] = df.get(mapping.get('company', 'COMPANY'), '')

    # SF columns - handle both numeric and string values
    sf_low_col = mapping.get('sf_low', 'REQUIRED SF (LOW)')
    sf_high_col = mapping.get('sf_high', 'REQUIRED SF (HIGH)')

    if sf_low_col in df.columns:
        df_std['sf_low'] = pd.to_numeric(
            df[sf_low_col].astype(str).str.replace(',', '').str.replace('$', ''),
            errors='coerce'
        )
    else:
        df_std['sf_low'] = np.nan

    if sf_high_col in df.columns:
        df_std['sf_high'] = pd.to_numeric(
            df[sf_high_col].astype(str).str.replace(',', '').str.replace('$', ''),
            errors='coerce'
        )
    else:
        df_std['sf_high'] = np.nan

    df_std['industry'] = df.get(mapping.get('industry', 'INDUSTRY'), '')
    df_std['market'] = df.get(mapping.get('market', 'MARKET'), '')
    df_std['use_market'] = df.get(mapping.get('use_market', 'USE MARKET'), '')
    df_std['status'] = df.get(mapping.get('status', 'STATUS'), 'Active')
    df_std['source_tab'] = 'Through 2024'

    return df_std

# Standardize both datasets
df_std_2025 = standardize_tab0(df_2025_plus)
df_std_2024 = standardize_tab1(df_through_2024, column_mapping)

print(f"  Tab 0 (2025+): {len(df_std_2025)} rows")
print(f"    Date range: {df_std_2025['date'].min()} to {df_std_2025['date'].max()}")
print(f"    Valid SF records: {df_std_2025['sf_low'].notna().sum()}")

print(f"  Tab 1 (Through 2024): {len(df_std_2024)} rows")
print(f"    Date range: {df_std_2024['date'].min()} to {df_std_2024['date'].max()}")
print(f"    Valid SF records: {df_std_2024['sf_low'].notna().sum()}")

# Combine datasets
df_combined = pd.concat([df_std_2024, df_std_2025], ignore_index=True)

# Calculate average SF
df_combined['sf_avg'] = (df_combined['sf_low'] + df_combined['sf_high']) / 2

# Filter out records with no SF data
df_combined = df_combined[df_combined['sf_avg'].notna()].copy()

# Filter to 2018 onwards for requirements analysis
df_combined = df_combined[df_combined['date'] >= '2018-01-01'].copy()

print(f"\n  Combined dataset: {len(df_combined)} rows")
print(f"    Date range: {df_combined['date'].min()} to {df_combined['date'].max()}")
print(f"    Total SF (avg): {df_combined['sf_avg'].sum():,.0f}")

# ============================================================================
# STEP 5: Generate updated requirements charts
# ============================================================================
print("\nStep 5: Generating updated requirements charts...")

# Create charts directory
os.makedirs("charts/office", exist_ok=True)

# Chart styling constants
COLORS = {
    'background': '#FFFFFF',
    'text': '#172344',  # AQUILA Navy
    'blue': '#00008B',
    'orange': '#DAA520',
    'gridcolor': '#e9e9ea',
    'light_gray': '#F8F9F9'
}

# 5a. Monthly aggregation
print("  Aggregating data by month...")
monthly_data = df_combined.groupby(pd.Grouper(key='date', freq='ME')).agg({
    'sf_low': ['sum', 'count'],
    'sf_high': 'sum',
    'sf_avg': ['mean', 'median']
}).reset_index()

monthly_data.columns = [
    'date', 'sf_low_sum', 'count', 'sf_high_sum', 'sf_avg_mean', 'sf_avg_median'
]

print(f"    - Monthly data points: {len(monthly_data)}")

# 5b. Chart 1: Total SF Requirements (Low/High lines)
print("  Creating Chart 1: Total SF Requirements...")
fig1 = px.line(
    monthly_data,
    x='date',
    y=['sf_low_sum', 'sf_high_sum'],
    title='Monthly Total Square Footage Requirements (Combined Historical Data)',
    labels={
        'value': 'Square Footage',
        'date': 'Date',
        'sf_low_sum': 'Low Requirement (sqft)',
        'sf_high_sum': 'High Requirement (sqft)'
    },
    color_discrete_sequence=[COLORS['orange'], COLORS['blue']]
)

# Manually update the legend names
for i, trace_name in enumerate(['Low Requirement (sqft)', 'High Requirement (sqft)']):
    fig1.data[i].name = trace_name

fig1.update_layout(
    plot_bgcolor=COLORS['background'],
    paper_bgcolor=COLORS['background'],
    font=dict(family=AQUILA_FONT, size=12, color=AQUILA_COLORS[0]),
    title={'font': dict(family=AQUILA_FONT, size=24, color=AQUILA_COLORS[0])},
    xaxis=dict(
        gridcolor=COLORS['light_gray'],
        showgrid=True,
        showline=True,
        linecolor='lightgrey'
    ),
    yaxis=dict(
        gridcolor=COLORS['light_gray'],
        showline=True,
        linecolor='lightgrey'
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.2,
        xanchor="center",
        x=0.5
    ),
    margin=dict(t=100, b=50, l=50, r=50),
    height=550  # Increased height
)
fig1.write_html("charts/office/requirements_sf_total.html")
print("    [OK] Saved charts/office/requirements_sf_total.html")

# 5c. Chart 2: Average SF with Count (dual-axis)
print("  Creating Chart 2: Average SF Metrics...")
fig2 = go.Figure()

fig2.add_trace(go.Scatter(
    x=monthly_data['date'],
    y=monthly_data['sf_avg_mean'],
    mode='lines+markers',
    name='Avg SF (Mean)',
    line=dict(color=COLORS['orange'])
))
fig2.add_trace(go.Scatter(
    x=monthly_data['date'],
    y=monthly_data['sf_avg_median'],
    mode='lines+markers',
    name='Avg SF (Median)',
    line=dict(color=COLORS['blue'])
))

fig2.add_trace(go.Bar(
    x=monthly_data['date'],
    y=monthly_data['count'],
    name='Record Count',
    yaxis='y2',
    marker_color=COLORS['text'],
    opacity=0.3
))

fig2.update_layout(
    title={
        'text': 'Monthly Average Square Footage Metrics (Combined Historical Data)',
        'font': dict(family=AQUILA_FONT, size=24, color=AQUILA_COLORS[0])
    },
    plot_bgcolor=COLORS['background'],
    paper_bgcolor=COLORS['background'],
    font=dict(family=AQUILA_FONT, size=12, color=AQUILA_COLORS[0]),
    xaxis=dict(
        title='Date',
        gridcolor=COLORS['light_gray'],
        showgrid=True,
        showline=True,
        linecolor='lightgrey'
    ),
    yaxis=dict(
        title="Square Footage",
        gridcolor=COLORS['light_gray'],
        showline=True,
        linecolor='lightgrey'
    ),
    yaxis2=dict(
        title=dict(text="Count", font=dict(family=AQUILA_FONT, size=12, color=COLORS['text'])),
        overlaying='y',
        side='right',
        tickfont=dict(family=AQUILA_FONT, size=12, color=COLORS['text'])
    ),
    legend=dict(orientation="h", y=-0.2),
    margin=dict(t=100, b=50, l=50, r=50)
)
fig2.write_html("charts/office/requirements_sf_avg.html")
print("    [OK] Saved charts/office/requirements_sf_avg.html")

# 5d. Chart 3: Demand by Industry (donut chart)
print("  Creating Chart 3: Demand by Industry...")
industry_data = (
    df_combined.dropna(subset=['sf_avg'])
    .groupby('industry')['sf_avg']
    .sum()
    .reset_index()
)
industry_data = industry_data[industry_data['sf_avg'] > 0]
industry_data = industry_data[industry_data['industry'].astype(str).str.strip() != '']

# Note how far back the data goes
if 'date' in df_combined.columns:
    min_date = df_combined['date'].min()
    max_date = df_combined['date'].max()
    date_range_note = f"(Data from {min_date:%b %Y} to {max_date:%b %Y})"
else:
    date_range_note = ""

# Top 7 + Other
industry_data_sorted = industry_data.sort_values(by='sf_avg', ascending=False)
top_n = 7
largest = industry_data_sorted.iloc[:top_n]
other = industry_data_sorted.iloc[top_n:]

if not other.empty:
    other_row = pd.DataFrame([{
        'industry': 'Other',
        'sf_avg': other['sf_avg'].sum()
    }])
    pie_data = pd.concat([largest, other_row], ignore_index=True)
else:
    pie_data = largest

# Extend color palette
industry_colors = (AQUILA_COLORS * ((len(pie_data) // len(AQUILA_COLORS)) + 1))[:len(pie_data)]

fig3 = go.Figure(
    data=[
        go.Pie(
            labels=pie_data['industry'],
            values=pie_data['sf_avg'],
            textinfo='label+percent',
            insidetextorientation='radial',
            hole=0.55,
            marker=dict(
                line=dict(color=COLORS['background'], width=2),
                colors=industry_colors
            )
        )
    ]
)
fig3.update_layout(
    title={
        'text': f'Tenant Demand by Industry (Combined Historical Data) {date_range_note}',
        'font': dict(family=AQUILA_FONT, size=24, color=AQUILA_COLORS[0])
    },
    plot_bgcolor=COLORS['background'],
    paper_bgcolor=COLORS['background'],
    font=dict(family=AQUILA_FONT, size=12, color=AQUILA_COLORS[0]),
    showlegend=False,
    width=1000,  # Increased from 820
    height=650,
    margin=dict(t=100, b=80, l=50, r=50)
)
fig3.write_html("charts/office/requirements_sf_avg_by_industry.html")
print("    [OK] Saved charts/office/requirements_sf_avg_by_industry.html")

# 5e. Chart 4: Requirements by Size Range
print("  Creating Chart 4: Requirements by Size Range...")
bins = [0, 14000, 40000, 100000, float('inf')]
labels = ['0-14k', '15k-39k', '40k-99k', '100k+']

df_combined['size_range'] = pd.cut(df_combined['sf_avg'], bins=bins, labels=labels, right=False)

size_group = df_combined.groupby('size_range', observed=False).agg(
    total_sf=('sf_avg', 'sum'),
    count=('sf_avg', 'count')
).reset_index()

size_group['size_range'] = pd.Categorical(size_group['size_range'], categories=labels, ordered=True)
size_group = size_group.sort_values('size_range').reset_index(drop=True)

fig4 = go.Figure(
    data=[
        go.Bar(
            y=size_group['size_range'],
            x=size_group['total_sf'],
            orientation='h',
            marker_color=AQUILA_COLORS[:len(size_group)],
            text=size_group['count'],
            texttemplate='%{text} reqs',
            textposition='inside',
            textfont=dict(family=AQUILA_FONT, size=14),
            hovertemplate=(
                'Size Range: %{y}<br>'
                'Total SF: %{x:,.0f}<br>'
                'Count: %{text}<extra></extra>'
            ),
        )
    ]
)
fig4.update_layout(
    title={
        'text': 'Total Cumulative SF Requested by Size Range (Combined Historical Data)',
        'font': dict(family=AQUILA_FONT, size=22, color=AQUILA_COLORS[0])
    },
    xaxis=dict(
        title='Total Cumulative Requested SF',
        showgrid=True,
        showline=True,
        linecolor='lightgrey',
        linewidth=2
    ),
    yaxis=dict(
        title='Requirement Size Range (SF)',
        showline=True,
        linecolor='lightgrey',
        linewidth=2
    ),
    font=dict(family=AQUILA_FONT, size=12, color=AQUILA_COLORS[0]),
    plot_bgcolor=COLORS['background'],
    paper_bgcolor=COLORS['background'],
    width=820,
    height=500,
    margin=dict(t=80, b=80, l=120, r=50)
)
fig4.write_html("charts/office/requirements_by_size_range.html")
print("    [OK] Saved charts/office/requirements_by_size_range.html")

# ============================================================================
# STEP 6: Fetch Supabase absorption data
# ============================================================================
print("\nStep 6: Fetching absorption data from Supabase...")

try:
    supabase = initialize_supabase_connection()
    print("  [OK] Connected to Supabase")

    # Query office market data for absorption
    print("  Querying market_tables_office...")
    all_records = []
    page = 0
    page_size = 1000

    while True:
        response = supabase.table('market_tables_office') \
            .select('quarter, total_net_absorption') \
            .gte('quarter', '2018 Q1') \
            .range(page * page_size, (page + 1) * page_size - 1) \
            .execute()

        batch = response.data
        all_records.extend(batch)

        if len(batch) < page_size:
            break
        page += 1

    df_absorption = pd.DataFrame(all_records)
    print(f"    - Loaded {len(df_absorption)} records")

    # Parse 'quarter' column like "2018 Q1" robustly
    def parse_quarter(qstr):
        import re
        m = re.match(r'(\d{4})\s*[Qq](\d)', str(qstr))
        if m:
            year = int(m.group(1))
            q = int(m.group(2))
            # pandas period to timestamp defaults to START of quarter
            return pd.Timestamp(f"{year}-{(q-1)*3+1:02d}-01")
        else:
            raise ValueError(f"Unknown quarter format: {qstr}")

    df_absorption['quarter'] = df_absorption['quarter'].apply(parse_quarter)
    df_absorption['total_net_absorption'] = pd.to_numeric(df_absorption['total_net_absorption'], errors='coerce')

    # Aggregate by quarter
    absorption_quarterly = df_absorption.groupby('quarter')['total_net_absorption'].sum().reset_index()
    absorption_quarterly.columns = ['quarter', 'absorption_sf']

    print(f"    - Quarterly data points: {len(absorption_quarterly)}")
    print(f"    - Date range: {absorption_quarterly['quarter'].min()} to {absorption_quarterly['quarter'].max()}")

except Exception as e:
    print(f"  [ERROR] Error fetching Supabase data: {e}")
    print("  Continuing without absorption comparison chart...")
    absorption_quarterly = None

# ============================================================================
# STEP 7: Create Requirements vs Absorption comparison chart
# ============================================================================
if absorption_quarterly is not None:
    print("\nStep 7: Creating Requirements vs Absorption comparison chart...")

    # Aggregate requirements data by quarter
    df_combined['quarter'] = df_combined['date'].dt.to_period('Q').dt.to_timestamp()
    requirements_quarterly = df_combined.groupby('quarter').agg({
        'sf_avg': 'sum',
        'sf_low': 'sum',
        'sf_high': 'sum'
    }).reset_index()
    requirements_quarterly.columns = ['quarter', 'requirements_sf_avg', 'requirements_sf_low', 'requirements_sf_high']

    print(f"  Requirements quarterly data: {len(requirements_quarterly)} points")

    # Merge requirements and absorption
    comparison_df = pd.merge(
        requirements_quarterly,
        absorption_quarterly,
        on='quarter',
        how='outer'
    ).sort_values('quarter')

    print(f"  Combined comparison data: {len(comparison_df)} quarters")

    # Create comparison chart
    fig5 = go.Figure()

    # Requirements (average SF)
    fig5.add_trace(go.Scatter(
        x=comparison_df['quarter'],
        y=comparison_df['requirements_sf_avg'],
        mode='lines+markers',
        name='Requirements (Avg SF)',
        line=dict(color=AQUILA_COLORS[1], width=2.5),  # Gold
        marker=dict(size=8)
    ))

    # Absorption
    fig5.add_trace(go.Scatter(
        x=comparison_df['quarter'],
        y=comparison_df['absorption_sf'],
        mode='lines+markers',
        name='Absorption (Total SF)',
        line=dict(color=AQUILA_COLORS[0], width=2.5),  # Navy
        marker=dict(size=8)
    ))

    fig5.update_layout(
        title={
            'text': 'Office Requirements vs Absorption (Quarterly, 2018+)',
            'font': dict(family=AQUILA_FONT, size=24, color=AQUILA_COLORS[0])
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
            linewidth=2
        ),
        yaxis=dict(
            title='Square Feet',
            gridcolor='#e9e9ea',
            showgrid=True,
            showline=True,
            linecolor='lightgrey',
            linewidth=2,
            tickformat=','
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
            font=dict(size=14)
        ),
        hovermode='x unified',
        height=600,
        margin=dict(t=100, b=100, l=80, r=50)
    )

    fig5.write_html("charts/office/requirements_vs_absorption_office.html")
    print("    [OK] Saved charts/office/requirements_vs_absorption_office.html")

# ============================================================================
# CHART 6: Rolling 12-Month Requirements with YoY Comparison
# ============================================================================
print("\n6. Generating Rolling 12-Month Requirements YoY chart...")

# Calculate rolling 12-month metrics
# Set index to date for rolling calculations
monthly_data_indexed = monthly_data.set_index('date').sort_index()

# Calculate rolling 12-month sum for average SF
# For average SF, we want the rolling mean (not sum)
rolling_data = pd.DataFrame()
rolling_data['current_avg_sf'] = monthly_data_indexed['sf_avg_mean'].rolling(window=12, min_periods=1).mean()
rolling_data['current_count'] = monthly_data_indexed['count'].rolling(window=12, min_periods=1).sum()

# Shift data by 12 months to get prior year
rolling_data['prior_avg_sf'] = rolling_data['current_avg_sf'].shift(12)
rolling_data['prior_count'] = rolling_data['current_count'].shift(12)

# Reset index for plotting
rolling_data = rolling_data.reset_index()

# Only show data where we have at least 12 months of history
rolling_data = rolling_data[rolling_data['date'] >= '2019-01-31'].copy()

print(f"  Rolling 12-month data: {len(rolling_data)} points")
print(f"  Date range: {rolling_data['date'].min()} to {rolling_data['date'].max()}")

# Create dual-axis chart
fig6 = go.Figure()

# Current year - Average SF (line, left axis)
fig6.add_trace(go.Scatter(
    x=rolling_data['date'],
    y=rolling_data['current_avg_sf'],
    mode='lines',
    name='Current Year Avg SF (12M Rolling)',
    line=dict(color=AQUILA_COLORS[0], width=2.5),  # Navy
    yaxis='y'
))

# Prior year - Average SF (line, left axis)
fig6.add_trace(go.Scatter(
    x=rolling_data['date'],
    y=rolling_data['prior_avg_sf'],
    mode='lines',
    name='Prior Year Avg SF (12M Rolling)',
    line=dict(color=AQUILA_COLORS[1], width=2.5, dash='dash'),  # Gold, dashed
    yaxis='y'
))

# Current year - Count (bar, right axis)
fig6.add_trace(go.Bar(
    x=rolling_data['date'],
    y=rolling_data['current_count'],
    name='Current Year Count (12M Rolling)',
    marker_color=AQUILA_COLORS[0],  # Navy
    opacity=0.3,
    yaxis='y2'
))

# Prior year - Count (bar, right axis)
fig6.add_trace(go.Bar(
    x=rolling_data['date'],
    y=rolling_data['prior_count'],
    name='Prior Year Count (12M Rolling)',
    marker_color=AQUILA_COLORS[1],  # Gold
    opacity=0.3,
    yaxis='y2'
))

fig6.update_layout(
    title={
        'text': 'Rolling 12-Month Requirements: Year-over-Year Comparison',
        'font': dict(family=AQUILA_FONT, size=24, color=AQUILA_COLORS[0])
    },
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(family=AQUILA_FONT, size=12, color=AQUILA_COLORS[0]),
    xaxis=dict(
        title='Date',
        gridcolor='#e9e9ea',
        showgrid=True,
        showline=True,
        linecolor='lightgrey',
        linewidth=2
    ),
    yaxis=dict(
        title='Average Square Feet (12M Rolling Mean)',
        gridcolor='#e9e9ea',
        showgrid=True,
        showline=True,
        linecolor='lightgrey',
        linewidth=2,
        tickformat=','
    ),
    yaxis2=dict(
        title='Count of Requirements (12M Rolling Sum)',
        overlaying='y',
        side='right',
        showgrid=False,
        showline=True,
        linecolor='lightgrey',
        linewidth=2
    ),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.3,
        xanchor="center",
        x=0.5,
        font=dict(size=12)
    ),
    hovermode='x unified',
    height=650,
    margin=dict(t=100, b=120, l=80, r=80),
    barmode='overlay'
)

fig6.write_html('charts/office/requirements_yoy_rolling_12m.html')
print('  [OK] Saved charts/office/requirements_yoy_rolling_12m.html')

# ============================================================================
# PROJECTION FUNCTIONS FOR 2026
# ============================================================================
def calculate_2026_annual_projection(df_combined):
    """
    Calculate projected 2026 full-year demand annualized from YTD pace.

    Method: Take YTD 2026 actual demand, compare to same period in 2025,
    then scale by 2025 full-year total to project 2026 full year.

    Returns:
        dict with 'projected_total', 'ytd_actual', 'projection_factor',
                  'projected_by_size', 'as_of_date'
    """
    from datetime import datetime

    today = datetime.now()
    current_year = today.year
    day_of_year = today.timetuple().tm_yday

    size_categories = ['Sub 10k SF', '10k-25k SF', '25k-50k SF', '50k-100k SF', 'Mega Requirements']

    # Filter by year
    df_2025 = df_combined[df_combined['date'].dt.year == 2025].copy()
    df_2026 = df_combined[df_combined['date'].dt.year == current_year].copy()

    # Apply size bins
    bins = [0, 10000, 25000, 50000, 100000, float('inf')]
    for df in [df_2025, df_2026]:
        df['size_category_temp'] = pd.cut(
            df['sf_avg'], bins=bins, labels=size_categories, right=False
        )

    total_2025 = df_2025['sf_avg'].sum()
    ytd_2026 = df_2026['sf_avg'].sum()

    # Compare YTD 2026 to same calendar period in 2025
    comparison_date_2025 = datetime(2025, 1, 1) + pd.Timedelta(days=day_of_year - 1)
    df_2025_ytd = df_2025[df_2025['date'] <= comparison_date_2025]
    ytd_2025 = df_2025_ytd['sf_avg'].sum()

    # Projection factor: full-year 2025 / YTD-equivalent 2025
    if ytd_2025 > 0:
        projection_factor = total_2025 / ytd_2025
    else:
        projection_factor = 365.0 / day_of_year

    projected_total_2026 = ytd_2026 * projection_factor

    # Distribute projected total by 2025 annual size mix
    annual_2025_by_size = df_2025.groupby('size_category_temp', observed=False)['sf_avg'].sum()
    actual_2026_by_size = df_2026.groupby('size_category_temp', observed=False)['sf_avg'].sum()

    projected_by_size = {}
    for size_cat in size_categories:
        size_val_2025 = annual_2025_by_size.get(size_cat, 0)
        size_pct = size_val_2025 / total_2025 if total_2025 > 0 else 1.0 / len(size_categories)
        projected_by_size[size_cat] = projected_total_2026 * size_pct

    return {
        'projected_total': projected_total_2026,
        'ytd_actual': ytd_2026,
        'projection_factor': projection_factor,
        'projected_by_size': projected_by_size,
        'actual_by_size': {cat: actual_2026_by_size.get(cat, 0) for cat in size_categories},
        'as_of_date': today,
        'comparison_date': comparison_date_2025,
    }

# ============================================================================
# CHART 7: Office Demand by Tenant Size (Annual Grouped Bar + Total Line)
# ============================================================================
print("\n7. Generating Office Demand by Tenant Size chart (Annual)...")

from datetime import datetime

# Calculate 2026 annual projection
projection_data = calculate_2026_annual_projection(df_combined)
print(f"  2026 Annual Projection calculated:")
print(f"    - Projection factor: {projection_data['projection_factor']:.2f}x")
print(f"    - Projected full-year 2026: {projection_data['projected_total']:,.0f} SF")
print(f"    - YTD 2026 actual: {projection_data['ytd_actual']:,.0f} SF")
print(f"    - As of: {projection_data['as_of_date']:%Y-%m-%d}")

# Filter to records with valid dates
df_demand = df_combined[df_combined['date'].notna()].copy()
df_demand['year'] = df_demand['date'].dt.year

# Size bins (5 categories)
demand_bins = [0, 10000, 25000, 50000, 100000, float('inf')]
demand_labels = ['Sub 10k SF', '10k-25k SF', '25k-50k SF', '50k-100k SF', 'Mega Requirements']

df_demand['size_category'] = pd.cut(
    df_demand['sf_avg'],
    bins=demand_bins,
    labels=demand_labels,
    right=False
)

# Aggregate: sum of sf_avg by year and size category (exclude current year — use projection instead)
current_year = datetime.now().year
df_historical = df_demand[df_demand['year'] < current_year].copy()

annual_by_size = df_historical.groupby(['year', 'size_category'], observed=False).agg(
    segment_demand=('sf_avg', 'sum'),
    count=('sf_avg', 'count')
).reset_index()

annual_total = df_historical.groupby('year').agg(
    total_demand=('sf_avg', 'sum')
).reset_index()

# Add projected 2026 as a separate year row
category_order = ['Mega Requirements', '50k-100k SF', '25k-50k SF', '10k-25k SF', 'Sub 10k SF']

for size_cat in demand_labels:
    proj_row = pd.DataFrame([{
        'year': current_year,
        'size_category': size_cat,
        'segment_demand': projection_data['projected_by_size'][size_cat],
        'count': 0,
        'is_projected': True
    }])
    annual_by_size = pd.concat([annual_by_size, proj_row], ignore_index=True)

proj_total_row = pd.DataFrame([{
    'year': current_year,
    'total_demand': projection_data['projected_total'],
    'is_projected': True
}])
annual_total = pd.concat([annual_total, proj_total_row], ignore_index=True)

# Mark historical as actual
if 'is_projected' not in annual_by_size.columns:
    annual_by_size['is_projected'] = False
annual_by_size['is_projected'] = annual_by_size['is_projected'].fillna(False).astype(bool)

if 'is_projected' not in annual_total.columns:
    annual_total['is_projected'] = False
annual_total['is_projected'] = annual_total['is_projected'].fillna(False).astype(bool)

years = sorted(annual_by_size['year'].unique())

# Colors for each size category
category_colors = {
    'Mega Requirements': AQUILA_COLORS[0],   # AQUILA Navy
    '50k-100k SF':       AQUILA_COLORS[4],   # Greenspace
    '25k-50k SF':        AQUILA_COLORS[3],   # Brass
    '10k-25k SF':        AQUILA_COLORS[2],   # Copper
    'Sub 10k SF':        AQUILA_COLORS[7],   # Pennybacker
}

fig7 = go.Figure()

# Grouped bars — actual years (solid) and projected year (hatched/lighter)
for category in category_order:
    cat_data = annual_by_size[annual_by_size['size_category'] == category].copy()
    cat_data = cat_data.set_index('year').reindex(years).reset_index()
    cat_data['segment_demand'] = cat_data['segment_demand'].fillna(0)
    cat_data['count'] = cat_data['count'].fillna(0)
    cat_data['is_projected'] = cat_data['is_projected'].fillna(False).astype(bool)
    cat_data['year_label'] = cat_data['year'].astype(str)

    actual_rows = cat_data[~cat_data['is_projected']]
    proj_rows = cat_data[cat_data['is_projected']]

    if len(actual_rows) > 0:
        fig7.add_trace(go.Bar(
            x=actual_rows['year_label'],
            y=actual_rows['segment_demand'],
            name=category,
            marker_color=category_colors[category],
            legendgroup=category,
            showlegend=True,
            hovertemplate=(
                f'<b>{category}</b><br>'
                'Year: %{x}<br>'
                'Demand: %{y:,.0f} SF<br>'
                '<b>(Actual)</b><extra></extra>'
            ),
        ))

    if len(proj_rows) > 0:
        fig7.add_trace(go.Bar(
            x=proj_rows['year_label'],
            y=proj_rows['segment_demand'],
            name=f'{category} (Projected)',
            marker_color=category_colors[category],
            marker_line=dict(width=2, color=category_colors[category]),
            marker_pattern_shape="/",
            opacity=0.45,
            legendgroup=category,
            showlegend=False,
            hovertemplate=(
                f'<b>{category}</b><br>'
                'Year: %{x}<br>'
                'Demand: %{y:,.0f} SF<br>'
                '<b>(Projected)</b><extra></extra>'
            ),
        ))

# Total demand line on secondary y-axis
total_data = annual_total.set_index('year').reindex(years).reset_index()
total_data['total_demand'] = total_data['total_demand'].fillna(0)
total_data['is_projected'] = total_data['is_projected'].fillna(False).astype(bool)
total_data['year_label'] = total_data['year'].astype(str)

actual_total_line = total_data[~total_data['is_projected']]
proj_total_line = total_data[total_data['is_projected']]

if len(actual_total_line) > 0:
    fig7.add_trace(go.Scatter(
        x=actual_total_line['year_label'],
        y=actual_total_line['total_demand'],
        mode='lines+markers',
        name='Total Demand',
        line=dict(color=AQUILA_COLORS[0], width=3),
        marker=dict(size=10, color=AQUILA_COLORS[0], symbol='circle'),
        yaxis='y2',
        legendgroup='total',
        showlegend=True,
        hovertemplate=(
            '<b>Total Demand</b><br>'
            'Year: %{x}<br>'
            'Total: %{y:,.0f} SF<br>'
            '<b>(Actual)</b><extra></extra>'
        ),
    ))

if len(proj_total_line) > 0:
    # Connect last actual to projected
    if len(actual_total_line) > 0:
        last_actual = actual_total_line.iloc[-1]
        first_proj = proj_total_line.iloc[0]
        connect_df = pd.DataFrame([
            {'year_label': last_actual['year_label'], 'total_demand': last_actual['total_demand']},
            {'year_label': first_proj['year_label'], 'total_demand': first_proj['total_demand']}
        ])
        fig7.add_trace(go.Scatter(
            x=connect_df['year_label'],
            y=connect_df['total_demand'],
            mode='lines',
            line=dict(color=AQUILA_COLORS[0], width=3, dash='dash'),
            yaxis='y2',
            legendgroup='total',
            showlegend=False,
            hoverinfo='skip'
        ))

    fig7.add_trace(go.Scatter(
        x=proj_total_line['year_label'],
        y=proj_total_line['total_demand'],
        mode='markers',
        name='Total Demand (Projected)',
        marker=dict(size=12, color=AQUILA_COLORS[0], symbol='circle-open', line=dict(width=2.5)),
        yaxis='y2',
        legendgroup='total',
        showlegend=True,
        hovertemplate=(
            '<b>Total Demand</b><br>'
            'Year: %{x}<br>'
            'Total: %{y:,.0f} SF<br>'
            f'<b>(Annualized — as of {projection_data["as_of_date"]:%b %d, %Y})</b><extra></extra>'
        ),
    ))

min_year = years[0]
max_year = years[-1]

# Annotation explaining the projection
fig7.add_annotation(
    text=(
        f"Note: {current_year} bar is annualized from YTD demand "
        f"(as of {projection_data['as_of_date']:%b %d, %Y}) "
        f"using {projection_data['projection_factor']:.1f}x pace factor vs. {current_year - 1}"
    ),
    xref="paper", yref="paper",
    x=0.5, y=1.08,
    showarrow=False,
    font=dict(size=11, color=AQUILA_COLORS[0]),
    xanchor='center',
    yanchor='bottom'
)

fig7.update_layout(
    title={
        'text': f'Office Demand by Tenant Size (Annual: {min_year}\u2013{max_year} with {current_year} Annualized Projection)',
        'font': dict(family=AQUILA_FONT, size=24, color=AQUILA_COLORS[0]),
        'x': 0.5,
        'xanchor': 'center',
    },
    barmode='group',
    bargroupgap=0,
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(family=AQUILA_FONT, size=12, color=AQUILA_COLORS[0]),
    xaxis=dict(
        title='',
        showgrid=False,
        showline=True,
        linecolor='lightgrey',
        linewidth=1,
        tickfont=dict(size=12),
        tickangle=0,
    ),
    yaxis=dict(
        title=dict(text='Segment Demand (SF)', font=dict(size=14)),
        showgrid=True,
        gridcolor='#e9e9ea',
        showline=True,
        linecolor='lightgrey',
        linewidth=1,
        tickformat=',',
        rangemode='tozero',
    ),
    yaxis2=dict(
        title=dict(text='Total Demand (SF)', font=dict(size=14)),
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
        y=-0.2,
        xanchor='center',
        x=0.5,
        font=dict(size=12),
        traceorder='normal',
    ),
    height=650,
    width=1400,
    margin=dict(t=80, b=140, l=80, r=80),
    hovermode='x unified',
)

fig7.write_html('charts/office/requirements_demand_by_tenant_size.html')
print('  [OK] Saved charts/office/requirements_demand_by_tenant_size.html')

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"\nCombined dataset:")
print(f"  - Total records: {len(df_combined)}")
print(f"  - Date range: {df_combined['date'].min().date()} to {df_combined['date'].max().date()}")
print(f"  - Tab 0 (2025+) records: {len(df_std_2025)}")
print(f"  - Tab 1 (Through 2024) records: {len(df_std_2024)}")
print(f"  - Total requirements SF (avg): {df_combined['sf_avg'].sum():,.0f}")

print(f"\nCharts generated:")
print(f"  [OK] charts/office/requirements_sf_total.html")
print(f"  [OK] charts/office/requirements_sf_avg.html")
print(f"  [OK] charts/office/requirements_sf_avg_by_industry.html")
print(f"  [OK] charts/office/requirements_by_size_range.html")
if absorption_quarterly is not None:
    print(f"  [OK] charts/office/requirements_vs_absorption_office.html")
print(f"  [OK] charts/office/requirements_yoy_rolling_12m.html")
print(f"  [OK] charts/office/requirements_demand_by_tenant_size.html")

print("\n" + "="*80)
print("[OK] Complete!")
print("="*80)
