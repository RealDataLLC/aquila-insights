import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402
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


def main():
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
        # Helper function to strip quotes from env vars
        def get_env_stripped(key):
            val = os.getenv(key)
            if val is not None:
                return val.strip('"').strip("'")
            return val

        credentials_dict = {
            "type": get_env_stripped("GOOGLE_SERVICE_ACCOUNT_TYPE") or "service_account",
            "project_id": get_env_stripped("GOOGLE_PROJECT_ID"),
            "private_key_id": get_env_stripped("GOOGLE_PRIVATE_KEY_ID"),
            "private_key": (get_env_stripped("GOOGLE_PRIVATE_KEY") or "").replace('\\n', '\n'),
            "client_email": get_env_stripped("GOOGLE_CLIENT_EMAIL"),
            "client_id": get_env_stripped("GOOGLE_CLIENT_ID"),
            "auth_uri": get_env_stripped("GOOGLE_AUTH_URI"),
            "token_uri": get_env_stripped("GOOGLE_TOKEN_URI"),
            "auth_provider_x509_cert_url": get_env_stripped("GOOGLE_AUTH_PROVIDER_X509_CERT_URL"),
            "client_x509_cert_url": get_env_stripped("GOOGLE_CLIENT_X509_CERT_URL"),
            "universe_domain": get_env_stripped("GOOGLE_UNIVERSE_DOMAIN"),
        }

        # Remove any keys with None values to avoid breaking oauth2client
        credentials_dict = {k: v for k, v in credentials_dict.items() if v is not None}

        # Defensive: ensure "type" is present and correct, else fail with friendly error
        if credentials_dict.get("type") != "service_account":
            raise ValueError(
                f'GOOGLE_SERVICE_ACCOUNT_TYPE missing or incorrect in environment variables. '
                f'Expected "service_account", got: {credentials_dict.get("type")!r}'
            )

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
    print(f"    - Loaded {len(df_2025_plus)} rows")

    # Tab 1: Through 2024 data (find by name)
    print("  Reading Tab 1: 'DITM & Crab Trap MASTER Report (Through 2024)' data...")
    try:
        tab1 = sheet.worksheet("DITM & Crab Trap MASTER Report (Through 2024)")
    except Exception as e:
        print(f"    [ERROR] Could not find tab by name, trying index 2: {e}")
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
    # STEP 3: Standardize data
    # ============================================================================
    print("\nStep 3: Standardizing data...")

    def standardize_tab0(df):
        """Standardize Tab 0 (2025+) data, include 'USE' column"""
        df_std = pd.DataFrame()
        df_std['date'] = pd.to_datetime(df['DATE OF REQUIREMENT'], errors='coerce')
        df_std['sf_low'] = pd.to_numeric(df['REQUIRED SF (LOW)'], errors='coerce')
        df_std['sf_high'] = pd.to_numeric(df['REQUIRED SF (HIGH)'], errors='coerce')
        df_std['market'] = df.get('MARKET', '').astype(str)
        # Always include USE column, with fallback empty string if missing
        df_std['USE'] = df.get('USE', '').astype(str)
        df_std['source_tab'] = '2025+'
        return df_std

    def standardize_tab1(df):
        """Standardize Tab 1 (Through 2024) data, include 'USE' column (match on 'USE' or 'Use')"""
        df_std = pd.DataFrame()

        print("  Tab 1 column names (first 20):")
        for col in list(df.columns)[:20]:
            print(f"    - {col}")

        # Date
        date_cols = [col for col in df.columns if 'DATE' in col.upper() and 'REQUIREMENT' in col.upper()]
        if not date_cols:
            # Try broader search
            date_cols = [col for col in df.columns if 'DATE' in col.upper() and 'REQ' in col.upper()]
        if date_cols:
            print(f"  Using date column: '{date_cols[0]}'")
            df_std['date'] = pd.to_datetime(df[date_cols[0]], errors='coerce')
        else:
            print("  [ERROR] No date column found")
            df_std['date'] = pd.NaT

        # SF columns
        sf_low_col = next((col for col in df.columns if 'SF' in col.upper() and 'LOW' in col.upper()), None)
        sf_high_col = next((col for col in df.columns if 'SF' in col.upper() and 'HIGH' in col.upper()), None)

        if sf_low_col:
            print(f"  Using SF LOW column: '{sf_low_col}'")
            df_std['sf_low'] = pd.to_numeric(
                df[sf_low_col].astype(str).str.replace(',', '').str.replace('$', ''),
                errors='coerce'
            )
        else:
            print("  [ERROR] No SF LOW column found")
            df_std['sf_low'] = np.nan

        if sf_high_col:
            print(f"  Using SF HIGH column: '{sf_high_col}'")
            df_std['sf_high'] = pd.to_numeric(
                df[sf_high_col].astype(str).str.replace(',', '').str.replace('$', ''),
                errors='coerce'
            )
        else:
            print("  [ERROR] No SF HIGH column found")
            df_std['sf_high'] = np.nan

        # Market column - try to find it
        market_col = None
        if 'MARKET' in df.columns:
            market_col = 'MARKET'
        else:
            # Try to find any column with MARKET in it
            market_candidates = [col for col in df.columns if 'MARKET' in col.upper()]
            if market_candidates:
                market_col = market_candidates[0]

        if market_col:
            print(f"  Using MARKET column: '{market_col}'")
            df_std['market'] = df[market_col].astype(str)
        else:
            print("  [ERROR] No MARKET column found")
            df_std['market'] = ''

        # Always include USE column, fallback to 'Use' if not present, else empty string
        if 'USE' in df.columns:
            df_std['USE'] = df['USE'].astype(str)
        elif 'Use' in df.columns:
            df_std['USE'] = df['Use'].astype(str)
        else:
            df_std['USE'] = ''

        df_std['source_tab'] = 'Through 2024'

        return df_std

    # Standardize both datasets
    df_std_2025 = standardize_tab0(df_2025_plus)
    df_std_2024 = standardize_tab1(df_through_2024)

    # Filter so that only rows where 'USE' contains the word 'office' (case-insensitive) are kept
    df_std_2025 = df_std_2025[df_std_2025['USE'].str.contains('office', case=False, na=False)].copy()
    df_std_2024 = df_std_2024[df_std_2024['USE'].str.contains('office', case=False, na=False)].copy()

    # Check if Through 2024 data is empty
    print(f"\n  Validation:")
    print(f"    Tab 0 (2025+) standardized & filtered: {len(df_std_2025)} rows")
    print(f"    Tab 1 (Through 2024) standardized & filtered: {len(df_std_2024)} rows")

    if len(df_std_2024) == 0:
        print("  [WARN] WARNING: Through 2024 tab produced 0 rows after standardization and office filtering!")
        print("  [WARN] Charts will only contain 2025+ data!")
    else:
        # Check data quality
        valid_dates_2024 = df_std_2024['date'].notna().sum()
        valid_sf_2024 = df_std_2024['sf_low'].notna().sum()
        print(f"    Tab 1 valid dates: {valid_dates_2024} / {len(df_std_2024)}")
        print(f"    Tab 1 valid SF: {valid_sf_2024} / {len(df_std_2024)}")

        if valid_dates_2024 == 0:
            print("  [WARN] WARNING: No valid dates found in Through 2024 data!")
        if valid_sf_2024 == 0:
            print("  [WARN] WARNING: No valid SF values found in Through 2024 data!")

    # Combine datasets
    df_combined = pd.concat([df_std_2024, df_std_2025], ignore_index=True)

    # Calculate average SF
    df_combined['sf_avg'] = (df_combined['sf_low'] + df_combined['sf_high']) / 2

    print(f"\n  Tab 0 (2025+): {len(df_std_2025)} rows")
    print(f"    Date range: {df_std_2025['date'].min()} to {df_std_2025['date'].max()}")
    print(f"    Valid SF records: {df_std_2025['sf_low'].notna().sum()}")

    print(f"  Tab 1 (Through 2024): {len(df_std_2024)} rows")
    print(f"    Date range: {df_std_2024['date'].min()} to {df_std_2024['date'].max()}")
    print(f"    Valid SF records: {df_std_2024['sf_low'].notna().sum()}")

    # Filter out records with no SF data
    df_combined = df_combined[df_combined['sf_avg'].notna()].copy()

    # Filter to 2018 onwards
    df_combined = df_combined[df_combined['date'] >= '2018-01-01'].copy()

    # USE column already filtered, no need to filter again



    print(f"\n  Combined dataset: {len(df_combined)} rows from 2018+")
    print(f"    Date range: {df_combined['date'].min()} to {df_combined['date'].max()}")
    print(f"    Total SF (avg): {df_combined['sf_avg'].sum():,.0f}")

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
        - Far NW, FNW, Domain, Cedar Park -> NW
        - Urban Core -> CBD and C
        - Citywide, Flexible, Market Wide, Austin MSA, Austin Metro -> all markets
        - NC -> C
        - Bee Caves -> SW
        - CBD, SW, NW, E, C -> themselves
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

            # Urban Core -> CBD and C
            if 'URBAN CORE' in part:
                applicable_markets.extend(['CBD', 'C'])

            # Far NW, FNW, Domain, Cedar Park -> NW
            elif any(keyword in part for keyword in ['FAR NW', 'FNW', 'DOMAIN', 'CEDAR PARK']):
                applicable_markets.append('NW')

            # NC -> C
            elif part == 'NC':
                applicable_markets.append('C')

            # Bee Caves -> SW
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
        print(f"    '{test}' -> {result}")

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
    # STEP 6: Generate market-specific charts (ANNUAL, not quarterly)
    # ============================================================================
    print("\nStep 6: Generating market-specific charts (annual with 2026 projection)...")

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

    # Add year column (annual x-axis)
    df_expanded['year'] = df_expanded['date'].dt.year

    # Colors for each size category
    category_colors = {
        'Mega Requirements': AQUILA_COLORS[0],   # Navy
        '50k-100k SF':       AQUILA_COLORS[1],   # Glass Blue
        '25k-50k SF':        AQUILA_COLORS[2],   # Glass Blue Alt
        '10k-25k SF':        AQUILA_COLORS[3],   # Concrete
        'Sub 10k SF':        AQUILA_COLORS[4],   # Copper
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

    # Compute 2026 projection parameters (once, across all data)
    from datetime import datetime as _dt
    _today = _dt.now()
    _current_year = _today.year
    _day_of_year = _today.timetuple().tm_yday
    _comparison_date_2025 = _dt(2025, 1, 1) + pd.Timedelta(days=_day_of_year - 1)

    # Whole-dataset 2025 vs 2026 YTD for the pace factor
    _df_2025_all = df_expanded[df_expanded['year'] == 2025]
    _df_2026_all = df_expanded[df_expanded['year'] == _current_year]
    _total_2025_all = _df_2025_all['sf_avg'].sum()
    _ytd_2025_all = _df_2025_all[_df_2025_all['date'] <= _comparison_date_2025]['sf_avg'].sum()
    _global_factor = (_total_2025_all / _ytd_2025_all) if _ytd_2025_all > 0 else (365.0 / _day_of_year)
    print(f"  Global annualization factor: {_global_factor:.2f}x (as of {_today:%b %d, %Y})")

    # Generate a chart for each market, aggregating ANNUAL
    for market_code in ['CBD', 'SW', 'NW', 'E', 'C']:
        print(f"\n  Generating chart for {market_names[market_code]}...")

        # Filter to this market
        df_market = df_expanded[df_expanded['submarket'] == market_code].copy()

        if len(df_market) == 0:
            print(f"    [WARN] No data for {market_code}, skipping")
            continue

        # Drop NA years
        df_market = df_market[df_market['year'].notna()].copy()
        df_market['year'] = df_market['year'].astype(int)

        # Split into historical (completed years) and current year
        df_hist = df_market[df_market['year'] < _current_year].copy()
        df_curr = df_market[df_market['year'] == _current_year].copy()

        # Aggregate historical by year and size category
        annual_by_size = df_hist.groupby(['year', 'size_category'], observed=False).agg(
            segment_demand=('sf_avg', 'sum'),
            count=('sf_avg', 'count')
        ).reset_index()
        annual_by_size['is_projected'] = False

        annual_total = df_hist.groupby('year').agg(
            total_demand=('sf_avg', 'sum')
        ).reset_index()
        annual_total['is_projected'] = False

        # Compute market-level YTD 2026 and project full year using global factor
        ytd_market_2026 = df_curr['sf_avg'].sum()
        projected_market_total = ytd_market_2026 * _global_factor

        # Distribute projected total by this market's 2025 annual size mix
        market_2025_by_size = df_hist[df_hist['year'] == 2025].groupby('size_category', observed=False)['sf_avg'].sum()
        market_2025_total = market_2025_by_size.sum()

        # Fall back to YTD 2026 mix if no 2025 data
        if market_2025_total == 0:
            market_ytd_by_size = df_curr.groupby('size_category', observed=False)['sf_avg'].sum()
            market_ytd_total = market_ytd_by_size.sum()
            for size_cat in demand_labels:
                val = market_ytd_by_size.get(size_cat, 0)
                pct = val / market_ytd_total if market_ytd_total > 0 else 1.0 / len(demand_labels)
                proj_row = pd.DataFrame([{
                    'year': _current_year, 'size_category': size_cat,
                    'segment_demand': projected_market_total * pct, 'count': 0, 'is_projected': True
                }])
                annual_by_size = pd.concat([annual_by_size, proj_row], ignore_index=True)
        else:
            for size_cat in demand_labels:
                size_val = market_2025_by_size.get(size_cat, 0)
                pct = size_val / market_2025_total
                proj_row = pd.DataFrame([{
                    'year': _current_year, 'size_category': size_cat,
                    'segment_demand': projected_market_total * pct, 'count': 0, 'is_projected': True
                }])
                annual_by_size = pd.concat([annual_by_size, proj_row], ignore_index=True)

        proj_total_row = pd.DataFrame([{
            'year': _current_year, 'total_demand': projected_market_total, 'is_projected': True
        }])
        annual_total = pd.concat([annual_total, proj_total_row], ignore_index=True)

        years = sorted(annual_by_size['year'].unique())

        if len(years) == 0:
            print(f"    [SKIP] No annual data for {market_code}, skipping")
            continue

        print(f"    YTD {_current_year}: {ytd_market_2026:,.0f} SF -> Projected: {projected_market_total:,.0f} SF")

        min_year = min(years)
        max_year = max(years)

        # Create figure
        fig = go.Figure()

        # One trace per category across ALL years — use per-bar rgba colors and
        # pattern lists so the projected (2026) bar gets a hatch while historical
        # bars stay solid. This keeps exactly 5 bar traces total so bargroupgap=0
        # truly eliminates all gaps within each year group.
        for category in category_order:
            cat_data = annual_by_size[annual_by_size['size_category'] == category].copy()
            cat_data = cat_data.set_index('year').reindex(years).reset_index()
            cat_data['segment_demand'] = cat_data['segment_demand'].fillna(0)
            cat_data['is_projected'] = cat_data['is_projected'].fillna(False).astype(bool)
            cat_data['year_label'] = cat_data['year'].astype(str)

            base_color = category_colors[category]
            r = int(base_color[1:3], 16)
            g = int(base_color[3:5], 16)
            b = int(base_color[5:7], 16)
            bar_colors = [
                f'rgba({r},{g},{b},0.45)' if p else f'rgba({r},{g},{b},1.0)'
                for p in cat_data['is_projected']
            ]
            patterns = ['/' if p else '' for p in cat_data['is_projected']]
            hover_suffixes = ['<b>(Projected)</b>' if p else '<b>(Actual)</b>' for p in cat_data['is_projected']]

            fig.add_trace(go.Bar(
                x=cat_data['year_label'],
                y=cat_data['segment_demand'],
                name=category,
                marker=dict(
                    color=bar_colors,
                    pattern=dict(shape=patterns, fgcolor=base_color, size=8),
                ),
                legendgroup=category,
                showlegend=True,
                customdata=hover_suffixes,
                hovertemplate=(
                    f'<b>{category}</b><br>'
                    'Year: %{x}<br>'
                    'Demand: %{y:,.0f} SF<br>'
                    '%{customdata}<extra></extra>'
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
            fig.add_trace(go.Scatter(
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

        if len(proj_total_line) > 0 and len(actual_total_line) > 0:
            last_actual = actual_total_line.iloc[-1]
            first_proj = proj_total_line.iloc[0]
            fig.add_trace(go.Scatter(
                x=[last_actual['year_label'], first_proj['year_label']],
                y=[last_actual['total_demand'], first_proj['total_demand']],
                mode='lines',
                line=dict(color=AQUILA_COLORS[0], width=3, dash='dash'),
                yaxis='y2',
                legendgroup='total',
                showlegend=False,
                hoverinfo='skip',
            ))
            fig.add_trace(go.Scatter(
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
                    f'<b>Annualized as of {_today:%b %d, %Y}</b><extra></extra>'
                ),
            ))

        caption = (
            f'<i>Note: {_current_year} bar is annualized from YTD demand '
            f'(as of {_today:%b %d, %Y}) '
            f'using a {_global_factor:.1f}x pace factor vs. {_current_year - 1}</i>'
        )

        fig.update_layout(
            title={
                'text': (
                    f'Office Demand by Tenant Size \u2013 {market_names[market_code]} '
                    f'(Annual: {min_year}\u2013{max_year} with {_current_year} Annualized Projection)'
                    f'<br><sup>{caption}</sup>'
                ),
                'font': dict(family=AQUILA_FONT, size=24, color=AQUILA_COLORS[0]),
                'x': 0.5,
                'xanchor': 'center',
                'y': 0.97,
                'yanchor': 'top',
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
            margin=dict(t=110, b=120, l=80, r=80),
            hovermode='x unified',
        )

        # Save chart
        filename = f'charts/office/requirements_demand_by_tenant_size_{market_code.lower()}.html'
        fig.write_html(filename)
        print(f"    [OK] Saved {filename}")

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
            print(f"  [OK] {filename}")

    print("\n" + "="*80)
    print("[OK] Complete!")
    print("="*80)



if __name__ == '__main__':
    main()
