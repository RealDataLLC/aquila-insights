#!/usr/bin/env python3
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402
"""
Create Industrial NNN Rental Rates Chart
Generates a line chart of average NNN rental rates for Northeast, Southeast,
and Williamson submarkets from 2022 Q1 to 2026 Q2.

Usage:
    python3 create_industrial_nnn_rent_chart.py
"""

import re
import os
import sys
import pandas as pd
import plotly.graph_objects as go
from dotenv import load_dotenv
from aquila_graphing_tools import initialize_supabase_connection, AQUILA_COLORS, AQUILA_FONT
from aquila.charts import write_chart_html

# Load environment
load_dotenv('aquila_graph.env')

# -- Config ------------------------------------------------------------------
SUBMARKETS = ['Northeast', 'Southeast', 'Williamson']
START_QUARTER = '2022 Q1'
END_QUARTER   = '2026 Q2'          # Update this as new data arrives
OUTPUT_PATH   = 'charts/industrial/industrial_nnn_rent_by_submarket.html'

# Northeast=Navy, Southeast=Glass Blue, Williamson=Copper (avoids two similar blues on one chart)
SUBMARKET_COLORS = {
    'Northeast':  AQUILA_COLORS[0],   # Navy
    'Southeast':  AQUILA_COLORS[1],   # Glass Blue
    'Williamson': AQUILA_COLORS[4],   # Copper
}


def parse_quarter(q_str):
    """Convert '2022 Q1' -> pd.Timestamp for sorting."""
    m = re.match(r'(\d{4})\s*[Qq](\d)', str(q_str))
    if m:
        year, q = int(m.group(1)), int(m.group(2))
        return pd.Timestamp(f"{year}-{(q-1)*3+1:02d}-01")
    return pd.NaT


def fetch_data(supabase):
    print("Querying industrial NNN rent data...")
    response = (
        supabase.table('market_tables_industrial')
        .select('submarket_name, quarter, average_rental_rate')
        .eq('property_type', 'Industrial')
        .in_('submarket_name', SUBMARKETS)
        .execute()
    )
    df = pd.DataFrame(response.data)
    print(f"  Loaded {len(df)} rows")

    df['average_rental_rate'] = pd.to_numeric(df['average_rental_rate'], errors='coerce')
    df['date'] = df['quarter'].apply(parse_quarter)
    df = df.dropna(subset=['date', 'average_rental_rate'])

    # Filter to requested date range
    start_dt = parse_quarter(START_QUARTER)
    end_dt   = parse_quarter(END_QUARTER)
    df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]
    df = df.sort_values('date')

    print(f"  Quarters included: {df['quarter'].nunique()} | Submarkets: {df['submarket_name'].unique().tolist()}")
    return df


def build_chart(df):
    fig = go.Figure()

    for submarket in SUBMARKETS:
        sub = df[df['submarket_name'] == submarket].sort_values('date')
        if sub.empty:
            print(f"  WARNING: No data for {submarket}")
            continue

        fig.add_trace(go.Scatter(
            x=sub['quarter'],
            y=sub['average_rental_rate'],
            mode='lines',
            name=submarket,
            line=dict(color=SUBMARKET_COLORS[submarket], width=2.5),

            hovertemplate=(
                f"<b>{submarket}</b><br>"
                "Quarter: %{x}<br>"
                "Avg NNN Rate: $%{y:.2f}/SF<extra></extra>"
            ),
        ))

    fig.update_layout(
        title=dict(
            text='Historical NNN Rental Rates',
            font=dict(family=AQUILA_FONT, size=20, color='#172344'),
            x=0.5,
            xanchor='center',
        ),
        xaxis=dict(
            title='',
            tickfont=dict(family=AQUILA_FONT, size=11, color='#172344'),
            showgrid=False,
            linecolor='#E8E8E8',
            tickangle=-45,
        ),
        yaxis=dict(
            title='Average Rental Rate',
            tickprefix='$',
            tickformat=',.2f',
            tickfont=dict(family=AQUILA_FONT, size=11, color='#172344'),
            gridcolor='#E8E8E8',
            zeroline=False,
        ),
        legend=dict(
            title=dict(text='', font=dict(family=AQUILA_FONT, size=12, color='#172344')),
            font=dict(family=AQUILA_FONT, size=11, color='#172344'),
            orientation='h',
            yanchor='top',
            y=-0.25,
            xanchor='center',
            x=0.5,
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, color='#172344'),
        height=600,
        margin=dict(l=60, r=40, t=80, b=80),
        hovermode='x unified',
    )

    return fig


def main():
    print("=" * 60)
    print("GENERATING: Industrial NNN Rental Rates Chart")
    print("=" * 60)

    try:
        supabase = initialize_supabase_connection()
        print("Connected to Supabase")

        df = fetch_data(supabase)

        if df.empty:
            print("ERROR: No data returned. Check filters.")
            sys.exit(1)

        fig = build_chart(df)

        os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
        write_chart_html(fig, OUTPUT_PATH)
        print(f"\nSaved: {OUTPUT_PATH}")

        print("\nNext steps:")
        print("  1. Review chart in browser")
        print("  2. Update README.md with chart link")
        print("  3. Commit and push to GitHub")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
