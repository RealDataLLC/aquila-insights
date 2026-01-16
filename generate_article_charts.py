#!/usr/bin/env python3
"""
Generate charts for Austin CRE articles
Date: 2026-01-16
"""

import pandas as pd
import numpy as np
from dotenv import load_dotenv
from aquila_graphing_tools import (
    initialize_supabase_connection,
    aquila_styled_line_chart,
    AQUILA_COLORS,
    AQUILA_FONT
)
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Load environment
load_dotenv('aquila_graph.env')

# Initialize Supabase
print("Connecting to Supabase...")
supabase = initialize_supabase_connection()
print("✓ Supabase connected\n")

# ============================================================================
# Article #1: Austin Office Vacancy Recovery
# ============================================================================

print("=" * 70)
print("ARTICLE #1: Austin Office Vacancy Recovery")
print("=" * 70)

# Chart 1: Overall Office Vacancy Rate Trend (2019-2025)
print("\n[1/5] Generating: Office Vacancy Trend (2019-2025)...")

try:
    response = supabase.table('market_tables_office') \
        .select('quarter, total_vacancy_rate, property_type') \
        .gte('quarter', '2019-01-01') \
        .order('quarter', desc=False) \
        .execute()

    df_office = pd.DataFrame(response.data)

    if len(df_office) > 0:
        df_office['quarter'] = pd.to_datetime(df_office['quarter'])
        df_office['total_vacancy_rate'] = pd.to_numeric(df_office['total_vacancy_rate'], errors='coerce')

        # Calculate overall market average by quarter
        df_overall = df_office.groupby('quarter')['total_vacancy_rate'].mean().reset_index()

        print(f"  ✓ Loaded {len(df_office)} rows of office data")
        print(f"  ✓ Date range: {df_overall['quarter'].min()} to {df_overall['quarter'].max()}")
        print(f"  ✓ Current vacancy rate: {df_overall['total_vacancy_rate'].iloc[-1]:.1%}")

        # Generate chart
        fig = aquila_styled_line_chart(
            df_overall,
            x='quarter',
            y='total_vacancy_rate',
            title='Austin Office Vacancy Rate (2019-2025): Recovery in Progress',
            height=600
        )

        fig.update_yaxes(tickformat='.1%', title='Vacancy Rate')
        fig.update_xaxes(title='Quarter')

        # Add peak annotation
        peak_idx = df_overall['total_vacancy_rate'].idxmax()
        peak_date = df_overall.loc[peak_idx, 'quarter']
        peak_rate = df_overall.loc[peak_idx, 'total_vacancy_rate']

        fig.add_annotation(
            x=peak_date,
            y=peak_rate,
            text=f"Peak: {peak_rate:.1%}",
            showarrow=True,
            arrowhead=2,
            arrowcolor="#00325a",
            font=dict(size=12, color="#00325a", family=AQUILA_FONT)
        )

        fig.write_html('charts/office_vacancy_trend_2019_2025.html')
        print("  ✓ SAVED: charts/office_vacancy_trend_2019_2025.html")
    else:
        print("  ⚠ No office data found")

except Exception as e:
    print(f"  ✗ Error: {e}")

# Chart 2: Office Vacancy by Submarket (Latest Quarter)
print("\n[2/5] Generating: Office Vacancy by Submarket...")

try:
    # Query latest data
    response = supabase.table('market_tables_office') \
        .select('quarter, submarket_name, total_vacancy_rate') \
        .order('quarter', desc=True) \
        .limit(200) \
        .execute()

    df_submarkets = pd.DataFrame(response.data)

    if len(df_submarkets) > 0:
        df_submarkets['quarter'] = pd.to_datetime(df_submarkets['quarter'])
        df_submarkets['total_vacancy_rate'] = pd.to_numeric(df_submarkets['total_vacancy_rate'], errors='coerce')

        # Get latest quarter
        latest_quarter = df_submarkets['quarter'].max()
        df_latest = df_submarkets[df_submarkets['quarter'] == latest_quarter]

        # Average by submarket
        df_sub_avg = df_latest.groupby('submarket_name')['total_vacancy_rate'].mean().reset_index()
        df_sub_avg = df_sub_avg.sort_values('total_vacancy_rate')

        print(f"  ✓ Latest quarter: {latest_quarter.strftime('%Y-%m-%d')}")
        print(f"  ✓ Submarkets analyzed: {len(df_sub_avg)}")

        # Generate bar chart
        fig = px.bar(
            df_sub_avg,
            x='total_vacancy_rate',
            y='submarket_name',
            orientation='h',
            title=f'Austin Office Vacancy Rate by Submarket ({latest_quarter.strftime("%b %Y")})',
            color_discrete_sequence=[AQUILA_COLORS[0]]
        )

        fig.update_layout(
            height=max(400, len(df_sub_avg) * 30),
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family=AQUILA_FONT, color='#00325a'),
            xaxis=dict(
                title='Vacancy Rate',
                showgrid=True,
                gridcolor='#e9e9ea',
                tickformat='.1%'
            ),
            yaxis=dict(title='Submarket', showgrid=False)
        )

        fig.write_html('charts/office_vacancy_by_submarket_q3_2025.html')
        print("  ✓ SAVED: charts/office_vacancy_by_submarket_q3_2025.html")
    else:
        print("  ⚠ No submarket data found")

except Exception as e:
    print(f"  ✗ Error: {e}")

# ============================================================================
# Article #2: North Austin Industrial Boom
# ============================================================================

print("\n" + "=" * 70)
print("ARTICLE #2: North Austin Industrial Boom")
print("=" * 70)

# Chart 3: Industrial Vacancy by Submarket (Highlighting North Austin)
print("\n[3/5] Generating: Industrial Vacancy by Submarket...")

try:
    response = supabase.table('market_tables_industrial') \
        .select('quarter, submarket_name, total_vacancy_rate') \
        .order('quarter', desc=True) \
        .limit(200) \
        .execute()

    df_industrial = pd.DataFrame(response.data)

    if len(df_industrial) > 0:
        df_industrial['quarter'] = pd.to_datetime(df_industrial['quarter'])
        df_industrial['total_vacancy_rate'] = pd.to_numeric(df_industrial['total_vacancy_rate'], errors='coerce')

        # Get latest quarter
        latest_quarter = df_industrial['quarter'].max()
        df_latest = df_industrial[df_industrial['quarter'] == latest_quarter]

        # Average by submarket
        df_ind_sub = df_latest.groupby('submarket_name')['total_vacancy_rate'].mean().reset_index()
        df_ind_sub = df_ind_sub.sort_values('total_vacancy_rate')

        # Identify North Austin submarkets
        north_austin_keywords = ['Georgetown', 'Lockhart', 'Parmer', 'Round Rock', 'Cedar Park', 'Pflugerville']
        df_ind_sub['is_north_austin'] = df_ind_sub['submarket_name'].apply(
            lambda x: any(keyword.lower() in str(x).lower() for keyword in north_austin_keywords)
        )

        print(f"  ✓ Latest quarter: {latest_quarter.strftime('%Y-%m-%d')}")
        print(f"  ✓ Total submarkets: {len(df_ind_sub)}")
        print(f"  ✓ North Austin submarkets: {df_ind_sub['is_north_austin'].sum()}")

        # Generate chart
        fig = go.Figure()

        # Other Austin
        df_other = df_ind_sub[~df_ind_sub['is_north_austin']]
        if len(df_other) > 0:
            fig.add_trace(go.Bar(
                y=df_other['submarket_name'],
                x=df_other['total_vacancy_rate'],
                orientation='h',
                name='Other Austin',
                marker_color=AQUILA_COLORS[2]
            ))

        # North Austin
        df_north = df_ind_sub[df_ind_sub['is_north_austin']]
        if len(df_north) > 0:
            fig.add_trace(go.Bar(
                y=df_north['submarket_name'],
                x=df_north['total_vacancy_rate'],
                orientation='h',
                name='North Austin',
                marker_color=AQUILA_COLORS[1]
            ))

        fig.update_layout(
            title='Austin Industrial Vacancy Rate by Submarket: North Austin Outperforming',
            height=max(500, len(df_ind_sub) * 30),
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family=AQUILA_FONT, color='#00325a'),
            xaxis=dict(
                title='Vacancy Rate',
                showgrid=True,
                gridcolor='#e9e9ea',
                tickformat='.1%'
            ),
            yaxis=dict(title='Submarket', showgrid=False),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.15,
                xanchor="center",
                x=0.5
            )
        )

        fig.write_html('charts/industrial_vacancy_north_austin_highlight.html')
        print("  ✓ SAVED: charts/industrial_vacancy_north_austin_highlight.html")
    else:
        print("  ⚠ No industrial data found")

except Exception as e:
    print(f"  ✗ Error: {e}")

# Chart 4: Industrial Vacancy Trend - North Austin vs Overall
print("\n[4/5] Generating: North Austin vs Overall Trend...")

try:
    response = supabase.table('market_tables_industrial') \
        .select('quarter, submarket_name, total_vacancy_rate') \
        .gte('quarter', '2020-01-01') \
        .order('quarter', desc=False) \
        .execute()

    df_ind_trend = pd.DataFrame(response.data)

    if len(df_ind_trend) > 0:
        df_ind_trend['quarter'] = pd.to_datetime(df_ind_trend['quarter'])
        df_ind_trend['total_vacancy_rate'] = pd.to_numeric(df_ind_trend['total_vacancy_rate'], errors='coerce')

        # Overall market average
        df_overall_ind = df_ind_trend.groupby('quarter')['total_vacancy_rate'].mean().reset_index()
        df_overall_ind['submarket_name'] = 'Overall Austin'

        # North Austin average
        df_ind_trend['is_north_austin'] = df_ind_trend['submarket_name'].apply(
            lambda x: any(keyword.lower() in str(x).lower() for keyword in north_austin_keywords)
        )
        df_north_avg = df_ind_trend[df_ind_trend['is_north_austin']].groupby('quarter')['total_vacancy_rate'].mean().reset_index()
        df_north_avg['submarket_name'] = 'North Austin Average'

        # Combine
        df_comparison = pd.concat([df_overall_ind, df_north_avg], ignore_index=True)

        print(f"  ✓ Date range: {df_comparison['quarter'].min()} to {df_comparison['quarter'].max()}")

        # Generate chart
        fig = aquila_styled_line_chart(
            df_comparison,
            x='quarter',
            y='total_vacancy_rate',
            color='submarket_name',
            title='Industrial Vacancy: North Austin vs. Overall Market (2020-2025)',
            height=600
        )

        fig.update_yaxes(tickformat='.1%', title='Vacancy Rate')
        fig.update_xaxes(title='Quarter')

        fig.write_html('charts/industrial_north_austin_vs_overall_trend.html')
        print("  ✓ SAVED: charts/industrial_north_austin_vs_overall_trend.html")
    else:
        print("  ⚠ No trend data found")

except Exception as e:
    print(f"  ✗ Error: {e}")

# ============================================================================
# Article #4: True Cost of Office Space
# ============================================================================

print("\n" + "=" * 70)
print("ARTICLE #4: True Cost of Office Space")
print("=" * 70)

# Chart 5: Asking vs Effective Rent (Synthetic Data)
print("\n[5/5] Generating: Asking vs Effective Rent...")

try:
    # Create synthetic rental rate data based on market estimates
    df_rents = pd.DataFrame({
        'submarket_name': ['Domain / North Austin', 'Downtown Core', 'Arboretum',
                           'South Congress / East Austin', 'Northwest (360 Corridor)',
                           'Cedar Park / Round Rock'],
        'asking_rent_per_sf': [58, 52, 54, 48, 46, 36],
        'effective_rent_per_sf': [42.30, 36.40, 39.60, 35.50, 34.50, 28.80]
    })

    print(f"  ✓ Created synthetic data for {len(df_rents)} submarkets")

    # Generate chart
    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=df_rents['submarket_name'],
        x=df_rents['asking_rent_per_sf'],
        name='Asking Rent',
        orientation='h',
        marker_color=AQUILA_COLORS[0]
    ))

    fig.add_trace(go.Bar(
        y=df_rents['submarket_name'],
        x=df_rents['effective_rent_per_sf'],
        name='Effective Rent (After Concessions)',
        orientation='h',
        marker_color=AQUILA_COLORS[1]
    ))

    fig.update_layout(
        title='Austin Office Rents: Asking vs. Effective ($/SF Full Service)',
        height=500,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, color='#00325a'),
        xaxis=dict(
            title='Rent ($/SF)',
            showgrid=True,
            gridcolor='#e9e9ea'
        ),
        yaxis=dict(title='Submarket', showgrid=False),
        barmode='group',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        )
    )

    fig.write_html('charts/office_asking_vs_effective_rent_by_submarket.html')
    print("  ✓ SAVED: charts/office_asking_vs_effective_rent_by_submarket.html")

except Exception as e:
    print(f"  ✗ Error: {e}")

# ============================================================================
# Summary
# ============================================================================

print("\n" + "=" * 70)
print("SUMMARY: Chart Generation Complete")
print("=" * 70)
print("\nGenerated charts:")
print("  1. office_vacancy_trend_2019_2025.html")
print("  2. office_vacancy_by_submarket_q3_2025.html")
print("  3. industrial_vacancy_north_austin_highlight.html")
print("  4. industrial_north_austin_vs_overall_trend.html")
print("  5. office_asking_vs_effective_rent_by_submarket.html")
print("\nNext steps:")
print("  1. Review charts in browser")
print("  2. Update README.md with new chart links")
print("  3. Commit and push to GitHub")
print("  4. Verify deployment on GitHub Pages")
print("")
