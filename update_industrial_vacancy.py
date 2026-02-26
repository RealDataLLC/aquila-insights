#!/usr/bin/env python3
"""
Update Supabase/SQL Charts
Regenerates industrial vacancy charts from Supabase database

Usage:
    python3 update_supabase_charts.py
    python3 update_supabase_charts.py --update-readme
"""

import pandas as pd
from dotenv import load_dotenv
from aquila_graphing_tools import (
    initialize_supabase_connection,
    aquila_styled_line_chart
)
from datetime import datetime
import sys
import os

# Load environment
load_dotenv('aquila_graph.env')

def fetch_industrial_data(supabase):
    """Fetch industrial market data from Supabase"""
    print("Querying industrial market data...")

    try:
        response = supabase.table('market_tables_industrial') \
            .select('*') \
            .gte('quarter', '2019-01-01') \
            .order('quarter', desc=False) \
            .execute()

        df = pd.DataFrame(response.data)
        print(f"✓ Loaded {len(df)} rows of industrial data")

        # Convert types
        import re
        def _parse_quarter(q_str):
            m = re.match(r'(\d{4})\s*[Qq](\d)', str(q_str))
            if m:
                year, q = int(m.group(1)), int(m.group(2))
                return pd.Timestamp(f"{year}-{(q-1)*3+1:02d}-01")
            return pd.NaT
        df['quarter'] = df['quarter'].apply(_parse_quarter)
        df['total_vacancy_rate'] = pd.to_numeric(df['total_vacancy_rate'], errors='coerce')

        return df

    except Exception as e:
        if '403' in str(e):
            print(f"✗ ERROR: 403 Forbidden - Check Supabase RLS policies")
            print("  Solution: Use service_role key OR adjust RLS policies")
        raise

def generate_industrial_vacancy_chart(df):
    """Generate industrial vacancy rate chart"""
    print("\n[1/1] Generating: Industrial Vacancy Rate by Submarket...")

    # Filter to Industrial property type
    df_industrial = df[df["property_type"] == "Industrial"]

    if len(df_industrial) == 0:
        print("  ⚠ No Industrial data found")
        return

    # Create chart
    fig = aquila_styled_line_chart(
        df_industrial,
        x="quarter",
        y="total_vacancy_rate",
        color="submarket_name",
        title="Industrial Vacancy Rate by Submarket and Property Type",
        height=800
    )

    # Format as percentage
    fig.update_yaxes(
        tickformat=".1%",
        title="Vacancy Rate"
    )

    fig.update_xaxes(title="Quarter")

    # Save
    os.makedirs("charts", exist_ok=True)
    fig.write_html("charts/industrial/vacancy_rate_industrial.html")
    print("  ✓ Saved: charts/vacancy_rate_industrial.html")

def update_readme_dates():
    """Update README.md with today's date for Supabase charts"""
    print("\nUpdating README.md dates...")

    today = datetime.now().strftime('%Y-%m-%d')

    # Read README
    with open('README.md', 'r') as f:
        content = f.read()

    # Update date for industrial vacancy chart
    import re
    pattern = r'Vacancy Rate by Submarket \[\d{4}-\d{2}-\d{2}\]'
    replacement = f'Vacancy Rate by Submarket [{today}]'

    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)

        # Write back
        with open('README.md', 'w') as f:
            f.write(content)

        print(f"  ✓ Updated README.md date to {today}")
    else:
        print("  ⚠ Could not find chart link in README.md")

def main():
    """Main execution"""
    print("=" * 70)
    print("UPDATING SUPABASE CHARTS")
    print("=" * 70)

    try:
        # Connect to Supabase
        print("\nConnecting to Supabase...")
        supabase = initialize_supabase_connection()
        print("✓ Connected")

        # Fetch data
        df = fetch_industrial_data(supabase)

        # Generate charts
        generate_industrial_vacancy_chart(df)

        print("\n" + "=" * 70)
        print("✓ SUCCESS: All Supabase charts updated")
        print("=" * 70)

        # Update README if requested
        if '--update-readme' in sys.argv:
            update_readme_dates()

        print("\nGenerated charts:")
        print("  • vacancy_rate_industrial.html")
        print("\nNext steps:")
        print("  1. Review chart in browser")
        print("  2. Commit: git add charts/ README.md && git commit -m 'Update industrial vacancy chart'")
        print("  3. Push to GitHub")
        print("")

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
