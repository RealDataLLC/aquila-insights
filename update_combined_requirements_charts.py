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
print(f"    - Loaded {len(df_2025_plus)} rows, {len(df_2025_plus.columns)} columns")

# Tab 1: Through 2024 data (use get_all_values for better performance with large sheets)
print("  Reading Tab 1: 'Through 2024' data...")
tab1 = sheet.get_worksheet(2)  # Index 2, not 1
rows = tab1.get_all_values()
df_through_2024 = pd.DataFrame(rows[1:], columns=rows[0])  # Skip header row for data

# Filter to office-only data
if "USE" in df_through_2024.columns:
    df_through_2024 = df_through_2024[df_through_2024["USE"].str.lower().str.contains("office", na=False)]

print(f"    - Loaded {len(df_through_2024)} rows, {len(df_through_2024.columns)} columns")

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
        print(f"    ✓ {key}: '{tab0_col}' (exact match)")
    else:
        # Look for similar column names
        similar = [col for col in df_through_2024.columns
                  if any(word in col.upper() for word in tab0_col.upper().split())]
        if similar:
            column_mapping[key] = similar[0]
            print(f"    ≈ {key}: '{similar[0]}' (similar to '{tab0_col}')")
        else:
            print(f"    ✗ {key}: no match found for '{tab0_col}'")

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
os.makedirs("charts", exist_ok=True)

# Chart styling constants
COLORS = {
    'background': '#FFFFFF',
    'text': '#2C3E50',
    'blue': '#00008B',
    'orange': '#DAA520',
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
print("    ✓ Saved charts/office/requirements_sf_total.html")

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
        title="Count",
        overlaying='y',
        side='right',
        titlefont=dict(family=AQUILA_FONT, size=12, color=COLORS['text']),
        tickfont=dict(family=AQUILA_FONT, size=12, color=COLORS['text'])
    ),
    legend=dict(orientation="h", y=-0.2),
    margin=dict(t=100, b=50, l=50, r=50)
)
fig2.write_html("charts/office/requirements_sf_avg.html")
print("    ✓ Saved charts/office/requirements_sf_avg.html")

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
print("    ✓ Saved charts/office/requirements_sf_avg_by_industry.html")

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
print("    ✓ Saved charts/office/requirements_by_size_range.html")

# ============================================================================
# STEP 6: Fetch Supabase absorption data
# ============================================================================
print("\nStep 6: Fetching absorption data from Supabase...")

try:
    supabase = initialize_supabase_connection()
    print("  ✓ Connected to Supabase")

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
    print(f"  ✗ Error fetching Supabase data: {e}")
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
    print("    ✓ Saved charts/office/requirements_vs_absorption_office.html")

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
print(f"  ✓ charts/office/requirements_sf_total.html")
print(f"  ✓ charts/office/requirements_sf_avg.html")
print(f"  ✓ charts/office/requirements_sf_avg_by_industry.html")
print(f"  ✓ charts/office/requirements_by_size_range.html")
if absorption_quarterly is not None:
    print(f"  ✓ charts/office/requirements_vs_absorption_office.html")

print("\n" + "="*80)
print("✓ Complete!")
print("="*80)
