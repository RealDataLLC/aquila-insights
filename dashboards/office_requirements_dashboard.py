"""
Austin Office Requirements Dashboard
Interactive dashboard for exploring office requirement trends with YoY comparison

Features:
- Filter by submarket (CBD, SW, NW, E, C)
- Filter by industry
- Filter by size category (Sub 10k, 10k-25k, 25k-50k, 50k-100k, Mega)
- Custom date range selection with DatePickerRange (controls graph range only, not data filtering)
- Real-time metric cards (Total SF, Count, Avg SF, YoY Growth)
- SF range line chart with YoY comparison and 3-month rolling average on average SF
- Requirement count bar chart with YoY comparison
- Interactive data table with sortable columns
- Export filtered data to CSV (includes rolling averages)

Note: Data is NOT filtered by date - the date range only controls what's displayed
on the charts. This ensures prior year data is always available for comparison.
"""

import base64
import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
from dash import dcc, html, Input, Output, State, dash_table, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dotenv import load_dotenv
from flask import session

try:
    from supabase import create_client as _supabase_create_client
    _SUPABASE_PKG = True
except ImportError:
    _SUPABASE_PKG = False
    print("WARNING: supabase package not installed. Auth will be disabled.")

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure gspread and oauth2client are installed")
    print("Run: pip install -r requirements.txt")
    sys.exit(1)

from aquila_graphing_tools import AQUILA_COLORS, AQUILA_FONT

# Load environment variables from parent directory
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'aquila_graph.env')
load_dotenv(env_path)

# ============================================================================
# LOGO
# ============================================================================

def _load_logo_b64():
    logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'Aquila_Logo2.png')
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            return 'data:image/png;base64,' + base64.b64encode(f.read()).decode()
    return None

LOGO_B64 = _load_logo_b64()

# ============================================================================
# SUPABASE AUTH CLIENT
# ============================================================================

_SUPABASE_URL = os.getenv('SUPABASE_URL')
_SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY')
_supabase_auth = None
if _SUPABASE_PKG and _SUPABASE_URL and _SUPABASE_ANON_KEY:
    _supabase_auth = _supabase_create_client(_SUPABASE_URL, _SUPABASE_ANON_KEY)
    print("Supabase auth client initialized")
else:
    print("WARNING: Supabase auth not configured (SUPABASE_URL/SUPABASE_ANON_KEY missing)")

# ============================================================================
# DATA LOADING FUNCTIONS
# ============================================================================

def map_markets(market_str):
    """
    Map market strings to applicable markets.
    Handles multi-market requirements and special cases.

    Returns list of applicable markets (CBD, SW, NW, E, C)
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


def load_requirements_data():
    """
    Load and combine office requirements data from Google Sheets.

    Returns cleaned DataFrame with columns:
    - date: datetime
    - sf_low: float
    - sf_high: float
    - sf_avg: float
    - industry: str
    - market: str (original market string)
    - applicable_markets: list (processed markets)
    """
    print("\n" + "="*80)
    print("LOADING OFFICE REQUIREMENTS DATA")
    print("="*80)

    # ============================================================================
    # STEP 1: Connect to Google Sheets
    # ============================================================================
    print("\nConnecting to Google Sheets...")

    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]

    # Check if JSON file exists in parent directory
    json_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'aquilacommercialsheets-923494a59a4b.json')
    use_json = os.path.exists(json_file)

    if use_json:
        print("  Using JSON credentials file")
        credentials = ServiceAccountCredentials.from_json_keyfile_name(json_file, scope)
    else:
        print("  Using environment variables for credentials")

        # Check if env vars are loaded
        test_val = os.getenv("GOOGLE_CLIENT_EMAIL")
        if not test_val:
            print(f"  WARNING: GOOGLE_CLIENT_EMAIL not found in environment")
            print(f"  Attempted to load from: {env_path}")
            print(f"  File exists: {os.path.exists(env_path)}")
            raise ValueError("Google credentials not found in environment. Please check aquila_graph.env file.")

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

    print("  Connected successfully")

    # ============================================================================
    # STEP 2: Read both tabs
    # ============================================================================
    print("\nReading data from both tabs...")

    # Tab 0: 2025+ data
    print("  Reading Tab 0: '2025 +' data...")
    tab0 = sheet.get_worksheet(0)
    df_2025_plus = pd.DataFrame(tab0.get_all_records())
    print(f"    - Loaded {len(df_2025_plus)} rows")

    # Tab 1: Through 2024 data
    print("  Reading Tab 1: 'DITM & Crab Trap MASTER Report (Through 2024)' data...")
    try:
        tab1 = sheet.worksheet("DITM & Crab Trap MASTER Report (Through 2024)")
    except Exception as e:
        print(f"    Could not find tab by name, trying index 2: {e}")
        tab1 = sheet.get_worksheet(2)

    rows = tab1.get_all_values()
    df_through_2024 = pd.DataFrame(rows[1:], columns=rows[0])

    # Filter to office-only
    if "USE" in df_through_2024.columns:
        df_through_2024 = df_through_2024[
            df_through_2024["USE"].str.lower().str.contains("office", na=False)
        ]
    elif "Use" in df_through_2024.columns:
        df_through_2024 = df_through_2024[
            df_through_2024["Use"].str.lower().str.contains("office", na=False)
        ]

    print(f"    - Loaded {len(df_through_2024)} office rows")

    # ============================================================================
    # STEP 3: Standardize columns
    # ============================================================================
    print("\nStandardizing columns...")

    # Tab 0 - standardize
    df_2025 = pd.DataFrame({
        'date': pd.to_datetime(df_2025_plus['DATE OF REQUIREMENT'], errors='coerce'),
        'sf_low': pd.to_numeric(df_2025_plus['REQUIRED SF (LOW)'].astype(str).str.replace(',', '').str.replace('$', ''), errors='coerce'),
        'sf_high': pd.to_numeric(df_2025_plus['REQUIRED SF (HIGH)'].astype(str).str.replace(',', '').str.replace('$', ''), errors='coerce'),
        'industry': df_2025_plus.get('INDUSTRY', ''),
        'market': df_2025_plus.get('MARKET', ''),
        'source_tab': '2025+'
    })

    # Tab 1 - standardize (more defensive)
    def standardize_tab1(df):
        """Standardize Tab 1 data with defensive column detection"""
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
        market_col = 'MARKET' if 'MARKET' in df.columns else next((col for col in df.columns if 'MARKET' in col.upper()), None)
        if market_col:
            df_std['market'] = df[market_col].astype(str)
        else:
            df_std['market'] = ''

        # Industry column
        industry_col = 'INDUSTRY' if 'INDUSTRY' in df.columns else next((col for col in df.columns if 'INDUSTRY' in col.upper()), None)
        if industry_col:
            df_std['industry'] = df[industry_col].astype(str)
        else:
            df_std['industry'] = ''

        df_std['source_tab'] = 'Through 2024'
        return df_std

    df_2024 = standardize_tab1(df_through_2024)

    # Combine
    df = pd.concat([df_2024, df_2025], ignore_index=True)

    print(f"  Combined dataset: {len(df)} rows")

    # ============================================================================
    # STEP 4: Clean and process
    # ============================================================================
    print("\nCleaning and processing data...")

    # Filter to 2018+
    df = df[df['date'] >= '2018-01-01']
    print(f"  After filtering to 2018+: {len(df)} rows")

    # Calculate sf_avg
    df['sf_avg'] = (df['sf_low'] + df['sf_high']) / 2

    # Remove rows with no valid SF
    df = df.dropna(subset=['sf_avg'])
    print(f"  After removing invalid SF: {len(df)} rows")

    # Calculate size category using office-specific bins
    demand_bins = [0, 10000, 25000, 50000, 100000, float('inf')]
    demand_labels = ['Sub 10k SF', '10k-25k SF', '25k-50k SF', '50k-100k SF', 'Mega Requirements']
    df['size_category'] = pd.cut(df['sf_avg'], bins=demand_bins, labels=demand_labels, right=False)

    # Apply market mapping
    df['applicable_markets'] = df['market'].apply(map_markets)

    # Keep un-exploded copy for Citywide demand aggregation (avoids double-counting)
    df_raw = df.copy()

    # Explode to one row per applicable market
    df = df.explode('applicable_markets')
    df = df.dropna(subset=['applicable_markets'])

    print(f"  After market mapping & exploding: {len(df)} rows")
    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"  Total SF (avg): {df['sf_avg'].sum():,.0f}")

    print("\nData loaded successfully")
    return df_raw, df


def aggregate_annual_demand(df_raw, df_exploded, submarket, sizes):
    """
    Aggregate demand into rolling 12-month windows by size category.

    Uses df_raw (un-exploded) for Citywide to avoid double-counting requirements
    that map to multiple submarkets. Uses df_exploded filtered by applicable_markets
    for specific submarkets.
    """
    today = pd.Timestamp.today()
    last_full_month_end = pd.Timestamp(today.year, today.month, 1) - pd.Timedelta(days=1)

    if submarket == 'Citywide':
        df = df_raw.copy()
    else:
        df = df_exploded[df_exploded['applicable_markets'] == submarket].copy()

    if sizes and 'All' not in sizes:
        df = df[df['size_category'].isin(sizes)]

    if len(df) == 0:
        return pd.DataFrame(), pd.DataFrame(), []

    windows = []
    window_end = last_full_month_end
    data_min_date = df['date'].min().replace(day=1)

    while window_end >= data_min_date:
        window_start = (window_end - pd.DateOffset(months=11)).replace(day=1)
        windows.append({
            'label': f"{window_start.strftime('%b %Y')}\u2013{window_end.strftime('%b %Y')}",
            'start': window_start,
            'end':   window_end,
        })
        window_end = window_start - pd.Timedelta(days=1)

    windows = list(reversed(windows))   # chronological order (oldest first)
    windows = [w for w in windows if w['start'].year >= 2018]   # drop orphaned pre-2018 windows
    window_labels_list = [w['label'] for w in windows]

    bin_edges = [w['start'] for w in windows] + [windows[-1]['end'] + pd.Timedelta(days=1)]
    df['window_label'] = pd.cut(df['date'], bins=bin_edges, labels=window_labels_list, right=False)
    df_windowed = df[df['window_label'].notna()].copy()
    df_windowed['window_label'] = df_windowed['window_label'].astype(str)

    window_by_size = (
        df_windowed.groupby(['window_label', 'size_category'], observed=True)['sf_avg']
        .sum().reset_index(name='segment_demand')
    )
    window_total = (
        df_windowed.groupby('window_label', observed=True)['sf_avg']
        .sum().reset_index(name='total_demand')
    )
    return window_by_size, window_total, window_labels_list


def aggregate_monthly(df, submarkets, industries, sizes, start_date, end_date):
    """
    Aggregate data by month for current and prior year periods.
    Returns data with month names for YoY comparison on same x-axis ticks.

    IMPORTANT: Does NOT filter the data - filters are only applied to determine
    which data to aggregate. All historical data is included in aggregations
    to ensure prior year data is always available.

    Parameters
    ----------
    df : DataFrame
        Full requirements dataset
    submarkets : list
        Selected submarkets (e.g., ['CBD', 'SW'])
    industries : list
        Selected industries or ['All']
    sizes : list
        Selected size categories or ['All']
    start_date : datetime
        Start date for current period (for graph range only)
    end_date : datetime
        End date for current period (for graph range only)

    Returns
    -------
    monthly_current : DataFrame
        Current period monthly aggregations with month_name and rolling averages
    monthly_prior : DataFrame
        Prior year monthly aggregations with month_name and rolling averages
    """
    # Calculate prior year date range
    date_range = (end_date - start_date).days
    prior_end = start_date - pd.DateOffset(days=1)
    prior_start = prior_end - pd.DateOffset(days=date_range)

    # Filter by submarkets, industries, sizes ONLY (not by date yet)
    df_filtered = df[df['applicable_markets'].isin(submarkets)].copy()

    # Filter by industries (if not "All")
    if industries != ['All'] and len(industries) > 0:
        df_filtered = df_filtered[df_filtered['industry'].isin(industries)]

    # Filter by size (if not "All")
    if sizes != ['All'] and len(sizes) > 0:
        df_filtered = df_filtered[df_filtered['size_category'].isin(sizes)]

    # Aggregate ALL data (no date filtering) to calculate rolling averages properly
    monthly_all = df_filtered.groupby(pd.Grouper(key='date', freq='ME')).agg({
        'sf_low': 'sum',
        'sf_high': 'sum',
        'sf_avg': ['sum', 'count']  # Sum for total SF, count for # requirements
    }).reset_index()

    # Flatten multi-index columns
    monthly_all.columns = ['date', 'sf_low', 'sf_high', 'sf_avg_total', 'count']

    # Calculate sf_avg (average SF across all requirements in the month)
    monthly_all['sf_avg'] = (monthly_all['sf_low'] + monthly_all['sf_high']) / 2

    # Calculate 3-month rolling average on average SF
    monthly_all['sf_avg_3m_rolling'] = monthly_all['sf_avg'].rolling(window=3, min_periods=1).mean()

    # Split into current and prior periods (for display only)
    monthly_current = monthly_all[
        (monthly_all['date'] >= start_date) &
        (monthly_all['date'] <= end_date)
    ].copy()

    monthly_prior = monthly_all[
        (monthly_all['date'] >= prior_start) &
        (monthly_all['date'] <= prior_end)
    ].copy()

    # Add month name for x-axis (e.g., "Sep 2025")
    monthly_current['month_name'] = monthly_current['date'].dt.strftime('%b %Y')
    monthly_current['sort_order'] = monthly_current['date']

    # Add month name matching current year (for alignment)
    monthly_prior['month_name'] = (monthly_prior['date'] + pd.DateOffset(months=12)).dt.strftime('%b %Y')
    monthly_prior['sort_order'] = monthly_prior['date'] + pd.DateOffset(months=12)

    return monthly_current, monthly_prior


def calculate_metrics(monthly_current, monthly_prior):
    """
    Calculate metric card values from aggregated data

    Parameters
    ----------
    monthly_current : DataFrame
        Current period monthly aggregations
    monthly_prior : DataFrame
        Prior year monthly aggregations

    Returns
    -------
    dict
        Dictionary with metric values and percentage changes
    """
    total_sf_current = monthly_current['sf_low'].sum() + monthly_current['sf_high'].sum()
    total_sf_prior = monthly_prior['sf_low'].sum() + monthly_prior['sf_high'].sum()
    sf_pct_change = ((total_sf_current - total_sf_prior) / total_sf_prior * 100) if total_sf_prior > 0 else 0

    count_current = monthly_current['count'].sum()
    count_prior = monthly_prior['count'].sum()
    count_pct_change = ((count_current - count_prior) / count_prior * 100) if count_prior > 0 else 0

    avg_sf_current = total_sf_current / count_current if count_current > 0 else 0
    avg_sf_prior = total_sf_prior / count_prior if count_prior > 0 else 0
    avg_sf_pct_change = ((avg_sf_current - avg_sf_prior) / avg_sf_prior * 100) if avg_sf_prior > 0 else 0

    return {
        'total_sf_current': total_sf_current,
        'total_sf_prior': total_sf_prior,
        'sf_pct_change': sf_pct_change,
        'count_current': int(count_current),
        'count_prior': int(count_prior),
        'count_pct_change': count_pct_change,
        'avg_sf_current': avg_sf_current,
        'avg_sf_prior': avg_sf_prior,
        'avg_sf_pct_change': avg_sf_pct_change
    }


# ============================================================================
# LOAD DATA ON STARTUP
# ============================================================================
print("Loading requirements data...")
df_global_raw, df_global = load_requirements_data()

# Get unique industries for filter
all_industries = sorted(df_global['industry'].dropna().unique().tolist())
industry_options = [{'label': 'All', 'value': 'All'}] + [{'label': ind, 'value': ind} for ind in all_industries if ind != '']

print(f"Found {len(all_industries)} unique industries")

# ============================================================================
# DASH APP LAYOUT
# ============================================================================

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "Aquila Insights Dashboard"
app.server.secret_key = os.getenv('FLASK_SECRET_KEY', 'aquila-dashboard-2026-change-me')


@app.server.route('/logout')
def _logout():
    from flask import redirect
    session.clear()
    return redirect('/')

# Calculate default dates for DatePickerRange
max_date = df_global['date'].max()
max_complete_month = max_date
default_start = max_complete_month - pd.DateOffset(months=12)

# ============================================================================
# AUTH LAYOUT
# ============================================================================

_VERCEL_URL = os.getenv('APP_URL', 'https://aquila-insights.vercel.app').rstrip('/')

login_form_div = html.Div([
    html.H4("Austin Office Requirements", style={'textAlign': 'center', 'color': AQUILA_COLORS[0], 'fontFamily': AQUILA_FONT, 'marginBottom': '4px'}),
    html.P("Sign in with your aquilacommercial.com email", style={'textAlign': 'center', 'color': '#888', 'fontFamily': AQUILA_FONT, 'fontSize': '13px', 'marginBottom': '24px'}),
    html.Label("Email", style={'fontFamily': AQUILA_FONT, 'fontWeight': 'bold', 'fontSize': '14px'}),
    dbc.Input(id='login-email', type='email', placeholder='you@aquilacommercial.com', className='mb-3'),
    html.Div(id='login-error', style={'color': '#BF4040', 'fontSize': '13px', 'fontFamily': AQUILA_FONT, 'marginBottom': '8px'}),
    html.Div(id='login-success', style={'color': '#556B30', 'fontSize': '13px', 'fontFamily': AQUILA_FONT, 'marginBottom': '8px'}),
    dbc.Button("Send Magic Link", id='login-btn', n_clicks=0,
               style={'width': '100%', 'backgroundColor': AQUILA_COLORS[0], 'border': 'none', 'fontFamily': AQUILA_FONT}),
    html.P("We'll email you a secure sign-in link — no password needed.",
           style={'textAlign': 'center', 'color': '#aaa', 'fontFamily': AQUILA_FONT, 'fontSize': '12px', 'marginTop': '16px'})
], id='login-form-div')

auth_layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            dbc.Card(
                dbc.CardBody([login_form_div]),
                style={'maxWidth': '420px', 'margin': 'auto', 'marginTop': '80px',
                       'boxShadow': '0 4px 20px rgba(0,0,0,0.12)', 'border': 'none'}
            )
        ], width=12)
    ])
], fluid=True, style={'minHeight': '100vh', 'backgroundColor': '#f5f7fa'})

# ============================================================================
# MAIN LAYOUT (existing dashboard, now with logo header)
# ============================================================================

main_layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H2("Austin Office Requirements", style={'color': AQUILA_COLORS[0], 'fontFamily': AQUILA_FONT, 'margin': 0}),
            html.P("Interactive dashboard with year-over-year comparison", style={'color': '#666', 'fontFamily': AQUILA_FONT, 'margin': 0})
        ], style={'display': 'flex', 'flexDirection': 'column', 'justifyContent': 'center'}),
        dbc.Col(
            html.A("Sign Out", href='/logout',
                   style={'color': AQUILA_COLORS[0], 'fontFamily': AQUILA_FONT, 'fontSize': '13px',
                          'border': f'1px solid {AQUILA_COLORS[0]}', 'padding': '5px 14px',
                          'borderRadius': '4px', 'textDecoration': 'none'}),
            width='auto', style={'display': 'flex', 'alignItems': 'center', 'marginLeft': 'auto'}
        )
    ], style={'marginTop': '20px', 'marginBottom': '4px', 'paddingBottom': '12px',
              'borderBottom': f'2px solid {AQUILA_COLORS[0]}'}, align='center'),

    dbc.Row([
        # Left sidebar - Filters
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Filters", style={'backgroundColor': AQUILA_COLORS[0], 'color': 'white', 'fontFamily': AQUILA_FONT}),
                dbc.CardBody([
                    # Submarket filter
                    html.Label("Submarket:", style={'fontWeight': 'bold', 'fontFamily': AQUILA_FONT, 'marginTop': '10px'}),
                    dcc.Dropdown(
                        id='submarket-filter',
                        options=[
                            {'label': 'All', 'value': 'All'},
                            {'label': 'CBD', 'value': 'CBD'},
                            {'label': 'SW - Southwest', 'value': 'SW'},
                            {'label': 'NW - Northwest', 'value': 'NW'},
                            {'label': 'E - East', 'value': 'E'},
                            {'label': 'C - Central', 'value': 'C'}
                        ],
                        value=['All'],
                        multi=True,
                        style={'fontFamily': AQUILA_FONT}
                    ),

                    # Industry filter
                    html.Label("Industry:", style={'fontWeight': 'bold', 'fontFamily': AQUILA_FONT, 'marginTop': '20px'}),
                    dcc.Dropdown(
                        id='industry-filter',
                        options=industry_options,
                        value=['All'],
                        multi=True,
                        style={'fontFamily': AQUILA_FONT}
                    ),

                    # Size filter
                    html.Label("Size Range:", style={'fontWeight': 'bold', 'fontFamily': AQUILA_FONT, 'marginTop': '20px'}),
                    dcc.Dropdown(
                        id='size-filter',
                        options=[
                            {'label': 'All', 'value': 'All'},
                            {'label': 'Sub 10k SF', 'value': 'Sub 10k SF'},
                            {'label': '10k-25k SF', 'value': '10k-25k SF'},
                            {'label': '25k-50k SF', 'value': '25k-50k SF'},
                            {'label': '50k-100k SF', 'value': '50k-100k SF'},
                            {'label': 'Mega Requirements', 'value': 'Mega Requirements'}
                        ],
                        value=['All'],
                        multi=True,
                        style={'fontFamily': AQUILA_FONT}
                    ),

                    # Date Range Picker
                    html.Label("Date Range:", style={'fontWeight': 'bold', 'fontFamily': AQUILA_FONT, 'marginTop': '20px'}),
                    dcc.DatePickerRange(
                        id='date-range',
                        min_date_allowed=pd.to_datetime('2018-01-01'),
                        max_date_allowed=max_complete_month,
                        start_date=default_start,
                        end_date=max_complete_month,
                        display_format='MMM YYYY',
                        style={'fontFamily': AQUILA_FONT}
                    ),

                    # Export button
                    html.Div([
                        html.Button('Export to CSV', id='export-btn', className='btn btn-primary',
                                    style={'width': '100%', 'marginTop': '30px', 'backgroundColor': AQUILA_COLORS[0], 'borderColor': AQUILA_COLORS[0], 'fontFamily': AQUILA_FONT}),
                        dcc.Download(id='download-csv')
                    ])
                ])
            ])
        ], width=3),

        # Right area - Metric Cards + Charts
        dbc.Col([
            dcc.Loading(
                id="loading-charts",
                type="default",
                children=[
                    # Metric Cards Row
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Total SF (Current)", className="card-subtitle", style={'fontFamily': AQUILA_FONT, 'color': AQUILA_COLORS[0]}),
                                    html.H3(id='metric-total-sf', style={'fontFamily': AQUILA_FONT, 'color': AQUILA_COLORS[0]}),
                                    html.P(id='metric-total-sf-change', style={'fontFamily': AQUILA_FONT, 'fontSize': '14px'})
                                ])
                            ], style={'marginBottom': '20px'})
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Requirements Count", className="card-subtitle", style={'fontFamily': AQUILA_FONT, 'color': AQUILA_COLORS[0]}),
                                    html.H3(id='metric-count', style={'fontFamily': AQUILA_FONT, 'color': AQUILA_COLORS[0]}),
                                    html.P(id='metric-count-change', style={'fontFamily': AQUILA_FONT, 'fontSize': '14px'})
                                ])
                            ], style={'marginBottom': '20px'})
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Avg SF per Req", className="card-subtitle", style={'fontFamily': AQUILA_FONT, 'color': AQUILA_COLORS[0]}),
                                    html.H3(id='metric-avg-sf', style={'fontFamily': AQUILA_FONT, 'color': AQUILA_COLORS[0]}),
                                    html.P(id='metric-avg-sf-change', style={'fontFamily': AQUILA_FONT, 'fontSize': '14px'})
                                ])
                            ], style={'marginBottom': '20px'})
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("YoY Growth", className="card-subtitle", style={'fontFamily': AQUILA_FONT, 'color': AQUILA_COLORS[0]}),
                                    html.H3(id='metric-yoy-growth', style={'fontFamily': AQUILA_FONT, 'color': AQUILA_COLORS[0]}),
                                    html.P(id='metric-yoy-icon', style={'fontFamily': AQUILA_FONT, 'fontSize': '20px'})
                                ])
                            ], style={'marginBottom': '20px'})
                        ], width=3)
                    ], style={'marginBottom': '20px'}),

                    # SF Range Chart
                    dcc.Graph(id='sf-range-chart', config={'displayModeBar': False}, style={'marginBottom': '30px'}),

                    # Count Chart
                    dcc.Graph(id='count-chart', config={'displayModeBar': False}, style={'marginBottom': '30px'}),

                    # Data Table
                    dash_table.DataTable(
                        id='data-table',
                        page_size=20,
                        sort_action='native',
                        style_table={'overflowX': 'auto', 'marginTop': '30px'},
                        style_cell={'fontFamily': AQUILA_FONT, 'textAlign': 'left', 'padding': '10px'},
                        style_header={'backgroundColor': AQUILA_COLORS[0], 'color': 'white', 'fontWeight': 'bold'},
                        style_data_conditional=[
                            {
                                'if': {'column_id': 'pct_change_sf'},
                                'backgroundColor': 'rgba(0, 255, 0, 0.2)'
                            }
                        ]
                    )
                ]
            ),

            # ----------------------------------------------------------------
            # Annual Demand by Tenant Size (Rolling 12-Month Windows)
            # ----------------------------------------------------------------
            html.Hr(style={'marginTop': '30px', 'marginBottom': '20px'}),
            html.H5(
                "Annual Demand by Tenant Size (Rolling 12-Month Windows)",
                style={'color': AQUILA_COLORS[0], 'fontFamily': AQUILA_FONT, 'marginBottom': '12px'}
            ),
            dbc.Row([
                dbc.Col([
                    html.Label("Submarket:", style={'fontWeight': 'bold', 'fontFamily': AQUILA_FONT}),
                    dcc.Dropdown(
                        id='demand-submarket-filter',
                        options=[
                            {'label': 'Citywide', 'value': 'Citywide'},
                            {'label': 'CBD', 'value': 'CBD'},
                            {'label': 'SW - Southwest', 'value': 'SW'},
                            {'label': 'NW - Northwest', 'value': 'NW'},
                            {'label': 'E - East', 'value': 'E'},
                            {'label': 'C - Central', 'value': 'C'},
                        ],
                        value='Citywide',
                        multi=False,
                        style={'fontFamily': AQUILA_FONT}
                    ),
                ], width=4),
                dbc.Col([
                    html.Label("Size:", style={'fontWeight': 'bold', 'fontFamily': AQUILA_FONT}),
                    dcc.Dropdown(
                        id='demand-size-filter',
                        options=[
                            {'label': 'All', 'value': 'All'},
                            {'label': 'Sub 10k SF', 'value': 'Sub 10k SF'},
                            {'label': '10k-25k SF', 'value': '10k-25k SF'},
                            {'label': '25k-50k SF', 'value': '25k-50k SF'},
                            {'label': '50k-100k SF', 'value': '50k-100k SF'},
                            {'label': 'Mega Requirements', 'value': 'Mega Requirements'},
                        ],
                        value=['All'],
                        multi=True,
                        style={'fontFamily': AQUILA_FONT}
                    ),
                ], width=8),
            ], style={'marginBottom': '16px'}),
            dcc.Loading(
                id='loading-demand-chart',
                type='default',
                children=[dcc.Graph(id='demand-chart', config={'displayModeBar': False})]
            ),
        ], width=9)
    ], style={'marginTop': '20px'})
], fluid=True)

# Root layout: fixed top-left logo bar + Location shell + dynamic page-content
app.layout = html.Div([
    html.Div(
        html.Img(src=LOGO_B64, style={'height': '40px', 'padding': '8px 16px'}) if LOGO_B64 else html.Span(),
        style={
            'position': 'fixed', 'top': 0, 'left': 0, 'zIndex': 1000,
            'backgroundColor': 'white',
            'boxShadow': '0 1px 4px rgba(0,0,0,0.08)',
        }
    ),
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content', style={'paddingTop': '58px'})
])


# ============================================================================
# CALLBACKS - AUTH
# ============================================================================

@app.callback(Output('page-content', 'children'), Input('url', 'pathname'))
def display_page(pathname):
    return main_layout if session.get('authenticated') else auth_layout


@app.callback(
    [Output('login-error', 'children'), Output('login-success', 'children')],
    Input('login-btn', 'n_clicks'),
    State('login-email', 'value'),
    prevent_initial_call=True
)
def handle_login(n_clicks, email):
    if not email:
        return "Please enter your email.", ""
    if not email.strip().lower().endswith('@aquilacommercial.com'):
        return "Access restricted to @aquilacommercial.com addresses.", ""
    if not _supabase_auth:
        return "Auth service unavailable. Check SUPABASE_URL and SUPABASE_ANON_KEY.", ""
    try:
        _supabase_auth.auth.sign_in_with_otp({
            "email": email.strip(),
            "options": {"email_redirect_to": f"{_VERCEL_URL}/auth/callback"}
        })
        return "", "Magic link sent! Check your inbox."
    except Exception as e:
        return f"Error sending link: {str(e)}", ""


# Flask routes to handle the magic link callback
@app.server.route('/auth/callback')
def auth_callback():
    """Supabase redirects here after magic link click with tokens in URL fragment.
    Returns a minimal page with JS that extracts the token and calls /auth/set-session."""
    return '''<!DOCTYPE html>
<html><head><title>Signing in...</title>
<style>body{font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;background:#f5f7fa}
.msg{text-align:center;color:#172344}</style></head>
<body><div class="msg"><p>Signing in...</p></div>
<script>
var hash = window.location.hash.substring(1);
var params = new URLSearchParams(hash);
var token = params.get('access_token');
var refresh = params.get('refresh_token');
if (token) {
  fetch('/auth/set-session', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({access_token: token, refresh_token: refresh})
  }).then(function(r){ return r.json(); }).then(function(d){
    window.location.href = d.ok ? '/' : '/?auth_error=' + encodeURIComponent(d.error || 'unknown');
  }).catch(function(){ window.location.href = '/?auth_error=network'; });
} else {
  window.location.href = '/?auth_error=no_token';
}
</script></body></html>'''


@app.server.route('/auth/set-session', methods=['POST'])
def auth_set_session():
    """Verifies the Supabase access token, checks email domain, sets Flask session."""
    from flask import request, jsonify
    data = request.get_json() or {}
    access_token = data.get('access_token')
    if not access_token or not _supabase_auth:
        return jsonify({'ok': False, 'error': 'missing_token'})
    try:
        user_response = _supabase_auth.auth.get_user(access_token)
        email = user_response.user.email
        if not email or not email.lower().endswith('@aquilacommercial.com'):
            return jsonify({'ok': False, 'error': 'unauthorized_domain'})
        session['authenticated'] = True
        session['user_email'] = email
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


# ============================================================================
# CALLBACKS - DASHBOARD
# ============================================================================

@app.callback(
    [Output('sf-range-chart', 'figure'),
     Output('count-chart', 'figure'),
     Output('metric-total-sf', 'children'),
     Output('metric-total-sf-change', 'children'),
     Output('metric-count', 'children'),
     Output('metric-count-change', 'children'),
     Output('metric-avg-sf', 'children'),
     Output('metric-avg-sf-change', 'children'),
     Output('metric-yoy-growth', 'children'),
     Output('metric-yoy-icon', 'children'),
     Output('data-table', 'data'),
     Output('data-table', 'columns')],
    [Input('submarket-filter', 'value'),
     Input('industry-filter', 'value'),
     Input('size-filter', 'value'),
     Input('date-range', 'start_date'),
     Input('date-range', 'end_date')]
)
def update_charts(submarkets, industries, sizes, start_date, end_date):
    """Update charts, metrics, and table based on filter selections"""

    # Handle "All" selection for submarkets
    if 'All' in submarkets:
        submarkets = ['CBD', 'SW', 'NW', 'E', 'C']

    # Handle "All" selection for sizes
    if 'All' in sizes:
        sizes = ['All']

    # Convert date strings to datetime
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # Aggregate data
    monthly_current, monthly_prior = aggregate_monthly(df_global, submarkets, industries, sizes, start_date, end_date)

    # Calculate metrics
    metrics = calculate_metrics(monthly_current, monthly_prior)

    # Merge current and prior by month_name for YoY comparison
    df_plot = monthly_current.merge(
        monthly_prior,
        on='month_name',
        how='outer',
        suffixes=('_current', '_prior')
    ).sort_values('sort_order_current')

    # FIX: Remove orphaned rows that can't be properly sorted
    # (These are months that exist in prior year but not current year)
    df_plot = df_plot[df_plot['sort_order_current'].notna()]

    # Fill NaN with 0 for plotting
    df_plot = df_plot.fillna(0)

    # Use month_name for x-axis
    df_plot['x_label'] = df_plot['month_name']

    # ========================================================================
    # SF Range Chart
    # ========================================================================
    sf_fig = go.Figure()

    # Current period lines
    sf_fig.add_trace(go.Scatter(
        x=df_plot['x_label'],
        y=df_plot['sf_low_current'],
        mode='lines+markers',
        name='SF Low (Current)',
        line=dict(color=AQUILA_COLORS[0], width=3),
        marker=dict(size=8, color=AQUILA_COLORS[0]),
        hovertemplate='%{x}<br>SF Low (Current): %{y:,.0f}<extra></extra>'
    ))

    sf_fig.add_trace(go.Scatter(
        x=df_plot['x_label'],
        y=df_plot['sf_high_current'],
        mode='lines+markers',
        name='SF High (Current)',
        line=dict(color=AQUILA_COLORS[1], width=3),
        marker=dict(size=8, color=AQUILA_COLORS[1]),
        hovertemplate='%{x}<br>SF High (Current): %{y:,.0f}<extra></extra>'
    ))

    # Prior year lines (dashed)
    sf_fig.add_trace(go.Scatter(
        x=df_plot['x_label'],
        y=df_plot['sf_low_prior'],
        mode='lines+markers',
        name='SF Low (Prior Year)',
        line=dict(color=AQUILA_COLORS[0], width=2, dash='dash'),
        marker=dict(size=6, color=AQUILA_COLORS[0], symbol='circle-open'),
        opacity=0.6,
        hovertemplate='%{x}<br>SF Low (Prior Year): %{y:,.0f}<extra></extra>'
    ))

    sf_fig.add_trace(go.Scatter(
        x=df_plot['x_label'],
        y=df_plot['sf_high_prior'],
        mode='lines+markers',
        name='SF High (Prior Year)',
        line=dict(color=AQUILA_COLORS[1], width=2, dash='dash'),
        marker=dict(size=6, color=AQUILA_COLORS[1], symbol='circle-open'),
        opacity=0.6,
        hovertemplate='%{x}<br>SF High (Prior Year): %{y:,.0f}<extra></extra>'
    ))

    # 3-month rolling average - current period (dotted)
    sf_fig.add_trace(go.Scatter(
        x=df_plot['x_label'],
        y=df_plot['sf_avg_3m_rolling_current'],
        mode='lines',
        name='SF Avg 3M Rolling (Current)',
        line=dict(color=AQUILA_COLORS[2], width=2, dash='dot'),  # Copper color
        opacity=0.7,
        hovertemplate='%{x}<br>SF Avg 3M Rolling (Current): %{y:,.0f}<extra></extra>'
    ))

    # 3-month rolling average - prior period (dashdot)
    sf_fig.add_trace(go.Scatter(
        x=df_plot['x_label'],
        y=df_plot['sf_avg_3m_rolling_prior'],
        mode='lines',
        name='SF Avg 3M Rolling (Prior Year)',
        line=dict(color=AQUILA_COLORS[3], width=2, dash='dashdot'),  # Brass color
        opacity=0.5,
        hovertemplate='%{x}<br>SF Avg 3M Rolling (Prior Year): %{y:,.0f}<extra></extra>'
    ))

    sf_fig.update_layout(
        title=dict(
            text='SF Range (Low/High) with Year-over-Year Comparison & 3-Month Rolling Average',
            font=dict(family=AQUILA_FONT, size=18, color=AQUILA_COLORS[0])
        ),
        xaxis=dict(
            title='Month',
            gridcolor='#E8E8E8',
            tickfont=dict(family=AQUILA_FONT, color=AQUILA_COLORS[0])
        ),
        yaxis=dict(
            title='Square Feet',
            gridcolor='#E8E8E8',
            tickfont=dict(family=AQUILA_FONT, color=AQUILA_COLORS[0]),
            tickformat=','
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, color=AQUILA_COLORS[0]),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            font=dict(family=AQUILA_FONT)
        ),
        height=450,
        margin=dict(l=60, r=20, t=80, b=40),
        hovermode='x unified'
    )

    # ========================================================================
    # Count Chart
    # ========================================================================
    count_fig = go.Figure()

    # Current period bars
    count_fig.add_trace(go.Bar(
        x=df_plot['x_label'],
        y=df_plot['count_current'],
        name='Count (Current)',
        marker_color=AQUILA_COLORS[2],  # Copper
        hovertemplate='%{x}<br>Count (Current): %{y}<extra></extra>'
    ))

    # Prior year bars
    count_fig.add_trace(go.Bar(
        x=df_plot['x_label'],
        y=df_plot['count_prior'],
        name='Count (Prior Year)',
        marker_color=AQUILA_COLORS[3],  # Brass
        opacity=0.7,
        hovertemplate='%{x}<br>Count (Prior Year): %{y}<extra></extra>'
    ))

    count_fig.update_layout(
        title=dict(
            text='Number of Requirements with Year-over-Year Comparison',
            font=dict(family=AQUILA_FONT, size=18, color=AQUILA_COLORS[0])
        ),
        xaxis=dict(
            title='Month',
            gridcolor='#E8E8E8',
            tickfont=dict(family=AQUILA_FONT, color=AQUILA_COLORS[0])
        ),
        yaxis=dict(
            title='Number of Requirements',
            gridcolor='#E8E8E8',
            tickfont=dict(family=AQUILA_FONT, color=AQUILA_COLORS[0])
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, color=AQUILA_COLORS[0]),
        barmode='group',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            font=dict(family=AQUILA_FONT)
        ),
        height=300,
        margin=dict(l=60, r=20, t=80, b=40),
        hovermode='x unified'
    )

    # ========================================================================
    # Metric Cards
    # ========================================================================
    total_sf_text = f"{metrics['total_sf_current']:,.0f}"
    total_sf_change = f"vs {metrics['total_sf_prior']:,.0f} prior year ({metrics['sf_pct_change']:+.1f}%)"
    total_sf_change_color = 'green' if metrics['sf_pct_change'] > 0 else 'red'

    count_text = f"{metrics['count_current']}"
    count_change = f"vs {metrics['count_prior']} prior year ({metrics['count_pct_change']:+.1f}%)"
    count_change_color = 'green' if metrics['count_pct_change'] > 0 else 'red'

    avg_sf_text = f"{metrics['avg_sf_current']:,.0f}"
    avg_sf_change = f"vs {metrics['avg_sf_prior']:,.0f} prior year ({metrics['avg_sf_pct_change']:+.1f}%)"
    avg_sf_change_color = 'green' if metrics['avg_sf_pct_change'] > 0 else 'red'

    yoy_growth_text = f"{metrics['sf_pct_change']:+.1f}%"
    yoy_icon = "↑" if metrics['sf_pct_change'] > 0 else "↓"

    # ========================================================================
    # Data Table
    # ========================================================================
    # Create table data from monthly aggregations
    table_data = []
    for _, row in df_plot.iterrows():
        if row['count_current'] > 0 or row['count_prior'] > 0:
            sf_current = row['sf_low_current'] + row['sf_high_current']
            sf_prior = row['sf_low_prior'] + row['sf_high_prior']
            pct_change = ((sf_current - sf_prior) / sf_prior * 100) if sf_prior > 0 else 0

            table_data.append({
                'Month': row['month_name'],
                'SF Low (Current)': f"{row['sf_low_current']:,.0f}",
                'SF High (Current)': f"{row['sf_high_current']:,.0f}",
                'Count (Current)': int(row['count_current']),
                'SF Low (Prior)': f"{row['sf_low_prior']:,.0f}",
                'SF High (Prior)': f"{row['sf_high_prior']:,.0f}",
                'Count (Prior)': int(row['count_prior']),
                'pct_change_sf': f"{pct_change:+.1f}%"
            })

    table_columns = [
        {'name': 'Month', 'id': 'Month'},
        {'name': 'SF Low (Current)', 'id': 'SF Low (Current)'},
        {'name': 'SF High (Current)', 'id': 'SF High (Current)'},
        {'name': 'Count (Current)', 'id': 'Count (Current)'},
        {'name': 'SF Low (Prior)', 'id': 'SF Low (Prior)'},
        {'name': 'SF High (Prior)', 'id': 'SF High (Prior)'},
        {'name': 'Count (Prior)', 'id': 'Count (Prior)'},
        {'name': 'YoY Change %', 'id': 'pct_change_sf'}
    ]

    return (sf_fig, count_fig,
            total_sf_text, html.Span(total_sf_change, style={'color': total_sf_change_color}),
            count_text, html.Span(count_change, style={'color': count_change_color}),
            avg_sf_text, html.Span(avg_sf_change, style={'color': avg_sf_change_color}),
            yoy_growth_text, yoy_icon,
            table_data, table_columns)


@app.callback(
    Output('download-csv', 'data'),
    Input('export-btn', 'n_clicks'),
    [State('submarket-filter', 'value'),
     State('industry-filter', 'value'),
     State('size-filter', 'value'),
     State('date-range', 'start_date'),
     State('date-range', 'end_date')],
    prevent_initial_call=True
)
def export_csv(n_clicks, submarkets, industries, sizes, start_date, end_date):
    """Export filtered data to CSV"""

    if n_clicks is None:
        return None

    # Handle "All" selection
    if 'All' in submarkets:
        submarkets = ['CBD', 'SW', 'NW', 'E', 'C']

    if 'All' in sizes:
        sizes = ['All']

    # Convert date strings to datetime
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # Get aggregated data
    monthly_current, monthly_prior = aggregate_monthly(df_global, submarkets, industries, sizes, start_date, end_date)

    # Merge for export
    df_export = monthly_current.merge(
        monthly_prior,
        on='month_name',
        how='outer',
        suffixes=('_current', '_prior')
    ).sort_values('sort_order_current')

    # Format date
    df_export['month'] = df_export['date_current'].dt.strftime('%Y-%m')

    # Select and rename columns
    df_export = df_export[[
        'month',
        'sf_low_current', 'sf_high_current', 'sf_avg_current', 'count_current',
        'sf_low_prior', 'sf_high_prior', 'sf_avg_prior', 'count_prior',
        'sf_avg_3m_rolling_current', 'sf_avg_3m_rolling_prior'
    ]].rename(columns={
        'month': 'Month',
        'sf_low_current': 'SF Low (Current)',
        'sf_high_current': 'SF High (Current)',
        'sf_avg_current': 'SF Avg (Current)',
        'count_current': 'Count (Current)',
        'sf_low_prior': 'SF Low (Prior Year)',
        'sf_high_prior': 'SF High (Prior Year)',
        'sf_avg_prior': 'SF Avg (Prior Year)',
        'count_prior': 'Count (Prior Year)',
        'sf_avg_3m_rolling_current': 'SF Avg 3M Rolling (Current)',
        'sf_avg_3m_rolling_prior': 'SF Avg 3M Rolling (Prior Year)'
    })

    return dcc.send_data_frame(df_export.to_csv, f"austin_requirements_{datetime.now().strftime('%Y%m%d')}.csv", index=False)


# ============================================================================
# CALLBACKS - ANNUAL DEMAND CHART
# ============================================================================

@app.callback(
    Output('demand-chart', 'figure'),
    [Input('demand-submarket-filter', 'value'),
     Input('demand-size-filter', 'value')]
)
def update_demand_chart(submarket, sizes):
    if not submarket:
        submarket = 'Citywide'
    if not sizes:
        sizes = ['All']

    window_by_size, window_total, window_labels_list = aggregate_annual_demand(
        df_global_raw, df_global, submarket, sizes
    )

    if not window_labels_list:
        fig = go.Figure()
        fig.update_layout(
            title='No data for selected filters',
            font=dict(family=AQUILA_FONT, color=AQUILA_COLORS[0]),
            plot_bgcolor='white', paper_bgcolor='white'
        )
        return fig

    category_colors = {
        'Mega Requirements': AQUILA_COLORS[0],
        '50k-100k SF':       AQUILA_COLORS[1],
        '25k-50k SF':        AQUILA_COLORS[2],
        '10k-25k SF':        AQUILA_COLORS[3],
        'Sub 10k SF':        AQUILA_COLORS[4],
    }
    category_order = ['Mega Requirements', '50k-100k SF', '25k-50k SF', '10k-25k SF', 'Sub 10k SF']

    fig = go.Figure()

    for category in category_order:
        if sizes and 'All' not in sizes and category not in sizes:
            continue
        cat_data = (
            window_by_size[window_by_size['size_category'] == category]
            .set_index('window_label').reindex(window_labels_list).reset_index()
        )
        cat_data['segment_demand'] = cat_data['segment_demand'].fillna(0)
        fig.add_trace(go.Bar(
            x=cat_data['window_label'],
            y=cat_data['segment_demand'],
            name=category,
            marker_color=category_colors[category],
            hovertemplate=(
                f'<b>{category}</b><br>'
                'Period: %{x}<br>'
                'Demand: %{y:,.0f} SF<extra></extra>'
            ),
        ))

    total_data = (
        window_total.set_index('window_label').reindex(window_labels_list).reset_index()
    )
    total_data['total_demand'] = total_data['total_demand'].fillna(0)
    fig.add_trace(go.Scatter(
        x=total_data['window_label'],
        y=total_data['total_demand'],
        mode='lines+markers',
        name='Total Demand',
        line=dict(color=AQUILA_COLORS[3], width=3),
        marker=dict(size=10, color=AQUILA_COLORS[3], symbol='circle'),
        yaxis='y2',
        hovertemplate=(
            '<b>Total Demand</b><br>'
            'Period: %{x}<br>'
            'Total: %{y:,.0f} SF<extra></extra>'
        ),
    ))

    market_names = {
        'Citywide': 'Citywide', 'CBD': 'CBD', 'SW': 'Southwest',
        'NW': 'Northwest', 'E': 'East', 'C': 'Central',
    }
    market_label = market_names.get(submarket, submarket)
    current_period = window_labels_list[-1] if window_labels_list else ''

    fig.update_layout(
        title={
            'text': (
                f'Office Demand by Tenant Size \u2013 {market_label} (Rolling 12-Month Windows)'
                f'<br><sup>Current period: {current_period}</sup>'
            ),
            'font': dict(family=AQUILA_FONT, size=22, color=AQUILA_COLORS[0]),
            'x': 0.5, 'xanchor': 'center', 'y': 0.97, 'yanchor': 'top',
        },
        barmode='group',
        bargroupgap=0,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, size=12, color=AQUILA_COLORS[0]),
        xaxis=dict(
            title='', showgrid=False, showline=True, linecolor='lightgrey',
            tickfont=dict(size=11), tickangle=-45,
        ),
        yaxis=dict(
            title=dict(text='Segment Demand (SF)', font=dict(size=14)),
            showgrid=True, gridcolor='#e9e9ea', showline=True, linecolor='lightgrey',
            tickformat=',', rangemode='tozero',
        ),
        yaxis2=dict(
            title=dict(text='Total Demand (SF)', font=dict(size=14)),
            overlaying='y', side='right', showgrid=False, showline=True,
            linecolor='lightgrey', tickformat=',', rangemode='tozero',
        ),
        legend=dict(
            orientation='h', yanchor='top', y=-0.25, xanchor='center', x=0.5,
            font=dict(size=12), traceorder='normal',
        ),
        height=650,
        margin=dict(t=110, b=160, l=80, r=80),
        hovermode='x unified',
    )
    return fig


# ============================================================================
# WSGI SERVER (for Vercel and other WSGI hosts)
# ============================================================================

server = app.server

# ============================================================================
# RUN APP
# ============================================================================

if __name__ == '__main__':
    print("\n" + "="*80)
    print("STARTING DASHBOARD")
    print("="*80)
    print("\nDashboard will be available at: http://127.0.0.1:8050/")
    print("Press Ctrl+C to stop the server\n")

    app.run(debug=True, host='127.0.0.1', port=8050)
