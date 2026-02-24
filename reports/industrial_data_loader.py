"""
Data loader for AQUILA Industrial Quarterly Report.
Reads from Supabase (primary) and Excel files (fallback) into DataFrames.
"""
import os
import sys
import re
import pandas as pd

# Add repo root to path so we can import aquila_graphing_tools
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'aquila_graph.env'
))


def _parse_quarter_sort_key(q_str):
    """Convert '2025 Q4' to a sortable value like 2025.4"""
    m = re.match(r'(\d{4})\s*Q(\d)', str(q_str))
    if m:
        return int(m.group(1)) + int(m.group(2)) / 10
    return 0


def _parse_formatted_value(val):
    """Parse formatted Excel strings: '$17.00' -> 17.0, '10.0%' -> 0.10, '616,904' -> 616904"""
    if pd.isna(val) or val is None:
        return float('nan')
    s = str(val).strip()
    if s == '' or s == '-' or s == '--':
        return float('nan')
    is_pct = s.endswith('%')
    s = s.replace('$', '').replace('%', '').replace(',', '').strip()
    if s == '' or s == '-':
        return float('nan')
    try:
        f = float(s)
        return f / 100.0 if is_pct else f
    except ValueError:
        return float('nan')


def _get_supabase_client():
    """Create a Supabase client using the service role key for full table access."""
    from supabase import create_client
    from dotenv import dotenv_values
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'aquila_graph.env'
    )
    vals = dotenv_values(env_path)
    url = vals.get('SUPABASE_URL', '')
    key = vals.get('SUPABASE_KEY', vals.get('SUPABASE_PUBLIC_KEY', ''))
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in aquila_graph.env")
    return create_client(url, key)


def load_supabase_industrial_data():
    """
    Load all rows from market_tables_industrial in Supabase.
    Returns (dict keyed by 'Submarket_PropertyType', full DataFrame).
    """
    print("  Loading Supabase market_tables_industrial...")
    supabase = _get_supabase_client()
    response = supabase.table('market_tables_industrial').select('*').execute()
    df = pd.DataFrame(response.data)

    if df.empty:
        print("    Warning: Supabase returned empty DataFrame")
        return {}, df

    # Add sort key for quarter ordering
    df['_sort'] = df['quarter'].apply(_parse_quarter_sort_key)
    df = df.sort_values('_sort')

    # Compute derived columns
    df['occupancy_rate'] = 1.0 - pd.to_numeric(df['total_vacancy_rate'], errors='coerce').fillna(0)

    # Ensure numeric types
    numeric_cols = [
        'net_rentable_area', 'vacant_available_sf_direct', 'vacant_available_sf_sublet',
        'total_vacancy_rate', 'total_net_absorption', 'average_rental_rate',
        'costar_average_rental_rate', 'occupancy'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Build dict keyed by (submarket_name, property_type)
    result = {}
    for (submarket, ptype), group in df.groupby(['submarket_name', 'property_type']):
        key = f"{submarket}_{ptype}"
        result[key] = group.reset_index(drop=True)

    print(f"    Loaded {len(df)} rows, {len(result)} groups")
    return result, df


def load_excel_submarket_tables(path):
    """
    Fallback: load performance data from the formatted Excel submarket tables file.
    Parses formatted strings ($, %, commas) into numeric values.
    Returns (dict keyed by 'Submarket_PropertyType', full DataFrame).
    """
    print(f"  Loading Excel submarket tables: {os.path.basename(path)}...")
    if not os.path.exists(path):
        print(f"    File not found: {path}")
        return {}, pd.DataFrame()

    xl = pd.ExcelFile(path)
    all_dfs = []
    result = {}

    # Column mapping: Excel header -> standard column name
    col_map = {
        'Quarter': 'quarter',
        'Net Rentable Area': 'net_rentable_area',
        'Direct Vacant SF': 'vacant_available_sf_direct',
        'Sublease Vacant SF': 'vacant_available_sf_sublet',
        'Net Absorption': 'total_net_absorption',
        'Total Vacancy Rate': 'total_vacancy_rate',
        'Average Rental Rate': 'average_rental_rate',
    }

    for sheet_name in xl.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet_name)
        # Rename columns to standard names
        df = df.rename(columns=col_map)

        # Parse formatted values
        for col in ['net_rentable_area', 'vacant_available_sf_direct',
                     'vacant_available_sf_sublet', 'total_net_absorption',
                     'total_vacancy_rate', 'average_rental_rate']:
            if col in df.columns:
                df[col] = df[col].apply(_parse_formatted_value)

        # Parse submarket and property type from sheet name (e.g., "East_Industrial")
        parts = sheet_name.rsplit('_', 1)
        if len(parts) == 2:
            submarket, ptype = parts
        else:
            submarket, ptype = sheet_name, 'Unknown'

        df['submarket_name'] = submarket
        df['property_type'] = ptype
        df['_sort'] = df['quarter'].apply(_parse_quarter_sort_key)
        df = df.sort_values('_sort')
        df['occupancy_rate'] = 1.0 - df['total_vacancy_rate'].fillna(0)

        key = f"{submarket}_{ptype}"
        result[key] = df.reset_index(drop=True)
        all_dfs.append(df)
        print(f"    {key}: {len(df)} rows")

    df_all = pd.concat(all_dfs, ignore_index=True) if all_dfs else pd.DataFrame()
    return result, df_all


def load_market_data(config):
    """
    Load industrial market performance data.
    Strategy: try Supabase first, fall back to Excel submarket tables file.
    Returns (dict keyed by 'Submarket_PropertyType', full DataFrame).
    """
    try:
        result, df_all = load_supabase_industrial_data()
        if result:
            print("    Using Supabase as data source")
            return result, df_all
        print("    Supabase returned empty, falling back to Excel...")
    except Exception as e:
        print(f"    Supabase failed ({e}), falling back to Excel...")

    result, df_all = load_excel_submarket_tables(config.SUBMARKET_TABLES)
    if result:
        print("    Using Excel as data source")
    else:
        print("    WARNING: No market data loaded from either source!")
    return result, df_all


def load_major_leases_sales(path):
    """Load major leases and sales from Excel."""
    print(f"  Loading Major Leases & Sales...")
    leases = pd.DataFrame()
    sales = pd.DataFrame()
    if os.path.exists(path):
        try:
            leases = pd.read_excel(path, sheet_name='Major Leases')
            # Drop fully empty first column if present
            if leases.columns[0] == leases.columns[0] and leases.iloc[:, 0].isna().all():
                leases = leases.iloc[:, 1:]
            sales = pd.read_excel(path, sheet_name='Major Sales')
            print(f"    Leases: {len(leases)} rows, Sales: {len(sales)} rows")
        except Exception as e:
            print(f"    Warning: {e}")
    else:
        print(f"    File not found: {path}")
    return leases, sales


def load_large_availabilities(path):
    """
    Load large availability data from Excel.
    Industrial report splits by generation (First Gen / Second Gen) not by submarket.
    Returns dict with keys 'first_gen' and 'second_gen'.
    """
    print(f"  Loading Large Availabilities...")
    result = {'first_gen': pd.DataFrame(), 'second_gen': pd.DataFrame()}
    if not os.path.exists(path):
        print(f"    File not found: {path}")
        return result

    try:
        xl = pd.ExcelFile(path)
        for sheet_name in xl.sheet_names:
            lower = sheet_name.lower()
            if 'first' in lower and ('gen' in lower or 'avail' in lower):
                result['first_gen'] = pd.read_excel(path, sheet_name=sheet_name)
                print(f"    First Gen ({sheet_name}): {len(result['first_gen'])} rows")
            elif 'second' in lower and ('gen' in lower or 'avail' in lower):
                result['second_gen'] = pd.read_excel(path, sheet_name=sheet_name)
                print(f"    Second Gen ({sheet_name}): {len(result['second_gen'])} rows")

        # If no matching sheets found, try sheets with "Availabilities" in name
        if result['first_gen'].empty and result['second_gen'].empty:
            for sheet_name in xl.sheet_names:
                if 'avail' in sheet_name.lower() and 'first' in sheet_name.lower():
                    result['first_gen'] = pd.read_excel(path, sheet_name=sheet_name)
                elif 'avail' in sheet_name.lower() and 'second' in sheet_name.lower():
                    result['second_gen'] = pd.read_excel(path, sheet_name=sheet_name)

        if result['first_gen'].empty and result['second_gen'].empty:
            print(f"    Warning: No First/Second Gen sheets found. Available sheets: {xl.sheet_names}")
    except Exception as e:
        print(f"    Warning: {e}")

    return result


def load_pipeline(path):
    """Load development pipeline from Excel (Under Construction + Proposed sheets)."""
    print(f"  Loading Development Pipeline...")
    result = {}
    if os.path.exists(path):
        try:
            xl = pd.ExcelFile(path)
            for sheet in xl.sheet_names:
                if sheet.lower() != 'ignore':
                    result[sheet] = pd.read_excel(path, sheet_name=sheet)
                    print(f"    {sheet}: {len(result[sheet])} rows")
        except Exception as e:
            print(f"    Warning: {e}")
    else:
        print(f"    File not found: {path}")
    return result


def load_building_list(path):
    """Load building list from Excel (16 sheets: 8 submarkets × 2 property types)."""
    print(f"  Loading Building Lists...")
    result = {}
    if os.path.exists(path):
        try:
            xl = pd.ExcelFile(path)
            for sheet in xl.sheet_names:
                df = pd.read_excel(path, sheet_name=sheet)
                if len(df) > 0:
                    result[sheet] = df
                    print(f"    {sheet}: {len(df)} rows")
        except Exception as e:
            print(f"    Warning: {e}")
    else:
        print(f"    File not found: {path}")
    return result


def load_quarterly_changes(changes_dir):
    """
    Load quarterly changes from CSV files in the Quarterly Changes folder.
    Industrial CSVs use [Q{N}] suffix pattern.
    Returns list of dicts: [{title, columns, df, empty}, ...]
    """
    print(f"  Loading Quarterly Changes...")
    results = []
    if not os.path.exists(changes_dir):
        print(f"    Directory not found: {changes_dir}")
        return results

    # Title override map
    title_map = {
        'existing supply nra changes': 'Existing Supply NRA Changes',
        'nra_changes': 'Existing Supply NRA Changes',
        'status_changes': 'Status Changes',
        'vacancy_changes': 'Vacancy Changes',
    }

    csv_files = sorted([f for f in os.listdir(changes_dir) if f.lower().endswith('.csv')])
    for fname in csv_files:
        fpath = os.path.join(changes_dir, fname)
        try:
            df = pd.read_csv(fpath)
            # Clean up title from filename
            base = os.path.splitext(fname)[0]
            # Remove [Q4] suffix pattern
            base = re.sub(r'\s*\[Q\d+\]\s*$', '', base)
            # Lookup override title
            title_key = base.lower().replace(' ', '_').strip()
            title = title_map.get(title_key, base)
            # Also try matching on partial name
            for k, v in title_map.items():
                if k in base.lower().replace(' ', '_'):
                    title = v
                    break

            is_empty = df.empty or len(df) == 0
            results.append({
                'title': title,
                'columns': list(df.columns),
                'df': df,
                'empty': is_empty,
            })
            print(f"    {title}: {len(df)} rows")
        except Exception as e:
            print(f"    Warning reading {fname}: {e}")

    return results


def load_all_data(config):
    """
    Master loader: reads all data sources and returns a single nested dict.
    """
    print("=" * 60)
    print("LOADING ALL DATA SOURCES")
    print("=" * 60)

    market_data, market_df_all = load_market_data(config)
    leases, sales = load_major_leases_sales(config.MAJOR_LEASES_SALES)
    large_avail = load_large_availabilities(config.LARGE_AVAIL)
    pipeline = load_pipeline(config.PIPELINE)
    building_list = load_building_list(config.BUILDING_LIST)

    # Quarterly changes (may not exist for all quarters)
    quarterly_changes = []
    if hasattr(config, 'QUARTERLY_CHANGES_DIR'):
        quarterly_changes = load_quarterly_changes(config.QUARTERLY_CHANGES_DIR)

    print("=" * 60)
    print("DATA LOADING COMPLETE")
    print("=" * 60)

    return {
        'market': market_data,          # Dict of DataFrames keyed by "Submarket_PropertyType"
        'market_all': market_df_all,    # Full DataFrame for cross-submarket charts
        'leases': leases,
        'sales': sales,
        'large_avail': large_avail,     # {'first_gen': df, 'second_gen': df}
        'pipeline': pipeline,
        'building_list': building_list,
        'quarterly_changes': quarterly_changes,
    }


def get_performance_data(data, submarket, property_type, n_quarters=8):
    """
    Get the last n_quarters of performance data for a submarket/property_type.
    Returns a DataFrame with standard columns.
    """
    key = f"{submarket}_{property_type}"
    if key not in data['market']:
        print(f"  Warning: No data for {key}")
        return pd.DataFrame()

    df = data['market'][key].copy()
    df = df.tail(n_quarters).reset_index(drop=True)
    return df


def get_kpi_data(data, property_type):
    """
    Get KPI values for the most recent quarter for a given property type.
    Uses 'Regional_{property_type}' for citywide KPIs.
    Returns a dict with KPI values.
    """
    df = get_performance_data(data, 'Regional', property_type, n_quarters=1)
    if df.empty:
        return {}

    row = df.iloc[0]
    return {
        'net_absorption': row.get('total_net_absorption', 0),
        'vacancy_rate': row.get('total_vacancy_rate', 0),
        'avg_rent': row.get('average_rental_rate', 0),
        'nra': row.get('net_rentable_area', 0),
        'quarter': row.get('quarter', ''),
    }


def get_regional_comparison_data(data, property_type, submarkets):
    """
    Get cross-submarket data for regional comparison tables/charts.
    Returns dict of {submarket: DataFrame} for the given property type.
    """
    result = {}
    for sub in submarkets:
        key = f"{sub}_{property_type}"
        if key in data['market']:
            result[sub] = data['market'][key].copy()
    return result
