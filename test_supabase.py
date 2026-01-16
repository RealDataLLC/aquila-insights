#!/usr/bin/env python3
"""Test Supabase connection and explore available tables"""

from dotenv import load_dotenv
from aquila_graphing_tools import initialize_supabase_connection

load_dotenv('aquila_graph.env')

print("Testing Supabase connection...")
supabase = initialize_supabase_connection()
print("✓ Connected\n")

# Try to list tables by querying with limit
test_tables = [
    'market_tables_office',
    'market_tables_industrial',
    'stats_office',
    'stats_industrial',
    'inventory_office',
    'inventory_industrial'
]

print("Testing access to tables:")
print("=" * 60)

for table_name in test_tables:
    try:
        response = supabase.table(table_name).select('*').limit(1).execute()
        if response.data:
            columns = list(response.data[0].keys())
            print(f"✓ {table_name}")
            print(f"  Columns: {', '.join(columns[:5])}...")
            print(f"  Sample record count: {len(response.data)}")
        else:
            print(f"⚠ {table_name} - No data")
    except Exception as e:
        print(f"✗ {table_name} - Error: {str(e)[:50]}")
    print()
