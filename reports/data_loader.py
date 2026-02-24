"""
Data loader for AQUILA Office Quarterly Report.
Reads from Supabase (primary) and Excel files (secondary) into DataFrames.
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
    # Prefer SUPABASE_KEY (service role) over SUPABASE_PUBLIC_KEY (anon)
    key = vals.get('SUPABASE_KEY', vals.get('SUPABASE_PUBLIC_KEY', ''))
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in aquila_graph.env")
    return create_client(url, key)


def load_supabase_market_data():
    """
    Load all rows from market_tables_office in Supabase.
    Returns dict keyed by (aquila_micromarket, table_type) with DataFrames sorted by quarter.
    """
    print("  Loading Supabase market_tables_office...")
    supabase = _get_supabase_client()
    response = supabase.table('market_tables_office').select('*').execute()
    df = pd.DataFrame(response.data)

    # Add sort key for quarter ordering
    df['_sort'] = df['quarter'].apply(_parse_quarter_sort_key)
    df = df.sort_values('_sort')

    # Compute derived columns
    df['full_service_rent'] = pd.to_numeric(df['average_rental_rate'], errors='coerce').fillna(0) + \
                              pd.to_numeric(df['average_opex'], errors='coerce').fillna(0)
    df['occupancy_rate'] = 1.0 - pd.to_numeric(df['total_vacancy_rate'], errors='coerce').fillna(0)

    # Ensure numeric types
    numeric_cols = [
        'net_rentable_area', 'vacant_available_sf_direct', 'vacant_available_sf_sublet',
        'total_vacancy_rate', 'total_net_absorption', 'average_rental_rate',
        'average_opex', 'average_class_a_rent', 'average_class_b_rent',
        'sqft_under_construction'
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Build dict keyed by (micromarket, table_type)
    result = {}
    for (micro, ttype), group in df.groupby(['aquila_micromarket', 'table_type']):
        key = f"{micro}_{ttype}"
        result[key] = group.reset_index(drop=True)

    print(f"    Loaded {len(df)} rows, {len(result)} groups")
    return result, df


def load_major_leases_sales(path):
    """Load major leases and sales from Excel."""
    print(f"  Loading Major Leases & Sales...")
    leases = pd.DataFrame()
    sales = pd.DataFrame()
    if os.path.exists(path):
        try:
            leases = pd.read_excel(path, sheet_name='Major Leases')
            sales = pd.read_excel(path, sheet_name='Major Sales')
            print(f"    Leases: {len(leases)} rows, Sales: {len(sales)} rows")
        except Exception as e:
            print(f"    Warning: {e}")
    else:
        print(f"    File not found: {path}")
    return leases, sales


def load_office_avail(path):
    """Load large availability data from Excel."""
    print(f"  Loading Office Availability...")
    result = {}
    if os.path.exists(path):
        try:
            xl = pd.ExcelFile(path)
            for sheet in xl.sheet_names:
                result[sheet] = pd.read_excel(path, sheet_name=sheet)
                print(f"    {sheet}: {len(result[sheet])} rows")
        except Exception as e:
            print(f"    Warning: {e}")
    else:
        print(f"    File not found: {path}")
    return result


def load_pipeline(path):
    """Load citywide development pipeline from Excel."""
    print(f"  Loading Citywide Pipeline...")
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
    """Load building list per submarket/micromarket from Excel."""
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


def load_availability_tables(path):
    """Load direct & sublease availability matrices from Excel."""
    print(f"  Loading Availability Tables...")
    result = {}
    if os.path.exists(path):
        try:
            xl = pd.ExcelFile(path)
            for sheet in xl.sheet_names:
                result[sheet] = pd.read_excel(path, sheet_name=sheet)
                print(f"    {sheet}: {len(result[sheet])} rows")
        except Exception as e:
            print(f"    Warning: {e}")
    else:
        print(f"    File not found: {path}")
    return result


def load_quarterly_changes(directory):
    """
    Load all CSV files from the Quarterly Changes directory.
    Returns an ordered list of dicts: {title, columns, rows, empty}
    Preserves file order and derives a human-readable title from the filename.
    """
    print(f"  Loading Quarterly Changes...")
    result = []
    if not os.path.isdir(directory):
        print(f"    Directory not found: {directory}")
        return result

    # Derive clean title: "NRA_Changes [Q4].csv" -> "NRA Changes"
    # Override map: base filename prefix -> display title
    _title_overrides = {
        'NRA_Changes': 'Existing Supply NRA Changes',
        'NRA Changes': 'Existing Supply NRA Changes',
    }

    def _clean_title(filename):
        name = os.path.splitext(filename)[0]          # strip .csv
        name = name.split('[')[0].strip()              # strip " [Q4]"
        # Check for override before replacing underscores
        if name in _title_overrides:
            return _title_overrides[name]
        name = name.replace('_', ' ')
        return _title_overrides.get(name, name)

    csv_files = sorted(f for f in os.listdir(directory) if f.lower().endswith('.csv'))
    for fname in csv_files:
        path = os.path.join(directory, fname)
        try:
            df = pd.read_csv(path)
            # Drop rows where ALL cells are NaN
            df = df.dropna(how='all').reset_index(drop=True)
            title = _clean_title(fname)
            print(f"    {title}: {len(df)} rows")
            result.append({
                'title': title,
                'columns': list(df.columns),
                'df': df,
                'empty': df.empty,
            })
        except Exception as e:
            print(f"    Warning loading {fname}: {e}")

    return result


def load_all_data(config):
    """
    Master loader: reads all data sources and returns a single nested dict.
    """
    print("=" * 60)
    print("LOADING ALL DATA SOURCES")
    print("=" * 60)

    market_data, market_df_all = load_supabase_market_data()
    leases, sales = load_major_leases_sales(config.MAJOR_LEASES_SALES)
    office_avail = load_office_avail(config.OFFICE_AVAIL)
    pipeline = load_pipeline(config.CITYWIDE_PIPELINE)
    building_list = load_building_list(config.BUILDING_LIST)
    avail_tables = load_availability_tables(config.AVAILABILITY_TABLES)
    quarterly_changes = load_quarterly_changes(config.QUARTERLY_CHANGES_DIR)

    print("=" * 60)
    print("DATA LOADING COMPLETE")
    print("=" * 60)

    return {
        'market': market_data,          # Dict of DataFrames keyed by "Submarket_type"
        'market_all': market_df_all,    # Full DataFrame for long-term charts
        'leases': leases,
        'sales': sales,
        'office_avail': office_avail,
        'pipeline': pipeline,
        'building_list': building_list,
        'avail_tables': avail_tables,
        'quarterly_changes': quarterly_changes,
    }


def get_performance_data(data, submarket, table_type, n_quarters=8):
    """
    Get the last n_quarters of performance data for a specific submarket/table_type.
    Returns a DataFrame with standard columns.
    """
    key = f"{submarket}_{table_type}"
    if key not in data['market']:
        print(f"  Warning: No data for {key}")
        return pd.DataFrame()

    df = data['market'][key].copy()
    # Take last n_quarters
    df = df.tail(n_quarters).reset_index(drop=True)
    return df


def get_kpi_data(data, submarket, table_type=None):
    """
    Get KPI values for the most recent quarter.
    Returns a dict with the 4 KPI values shown on header pages.
    Auto-detects table_type: Citywide uses "overall", others use "competitive set".
    """
    if table_type is None:
        table_type = "overall" if submarket == "Citywide" else "competitive set"
    df = get_performance_data(data, submarket, table_type, n_quarters=1)
    if df.empty:
        return {}

    row = df.iloc[0]
    return {
        'net_absorption': row.get('total_net_absorption', 0),
        'vacancy_rate': row.get('total_vacancy_rate', 0),
        'avg_rent': row.get('full_service_rent', 0),
        'under_construction': row.get('sqft_under_construction', 0),
        'quarter': row.get('quarter', ''),
    }


def get_long_term_data(data, submarket=None, table_type=None):
    """
    Get all historical data for long-term performance charts.
    If submarket/table_type specified, filter to that combination.
    """
    df = data['market_all'].copy()
    if submarket:
        df = df[df['aquila_micromarket'] == submarket]
    if table_type:
        df = df[df['table_type'] == table_type]
    return df.sort_values('_sort').reset_index(drop=True)
