#!/usr/bin/env python3
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402
"""
Retail Demographics Charts
Generates 4 HTML charts combining Census ACS data with Supabase inventory.

Charts (Story 6 — Demographics & Retail Demand):
  Chart 15 — Retail SF per Capita by Submarket
  Chart 16 — Population Growth vs Retail Pipeline
  Chart 17 — Median Income vs NNN Rent
  Chart 18 — Demographic Profile by Submarket

Usage:
    python -m generators.retail.demographics
"""

import os
import sys
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dotenv import load_dotenv
from aquila.brand import AQUILA_COLORS, AQUILA_FONT, NAVY, GLASS_BLUE, GLASS_ALT, CONCRETE, COPPER, BRASS, GREENSPACE, SIGNAL
from aquila.charts import write_chart_html
from aquila.connectors.census import (
    fetch_acs_by_zcta, POPULATION, MEDIAN_HH_INCOME, MEDIAN_AGE, AVG_HOUSEHOLD_SIZE,
)

load_dotenv('aquila_graph.env')

OUTPUT_DIR = 'charts/retail'


# -- Helpers -------------------------------------------------------------------

def _shared_layout(title_text, y_title, height=550):
    return dict(
        title=dict(text=title_text, font=dict(family=AQUILA_FONT, size=18, color=NAVY), x=0.5, xanchor='center'),
        xaxis=dict(title='', tickfont=dict(family=AQUILA_FONT, size=11, color=NAVY), showgrid=False, linecolor='#E8E8E8', tickangle=-45),
        yaxis=dict(title=y_title, title_font=dict(family=AQUILA_FONT, size=12, color=NAVY), tickfont=dict(family=AQUILA_FONT, size=11, color=NAVY), gridcolor='#E8E8E8', zeroline=False),
        legend=dict(font=dict(family=AQUILA_FONT, size=11, color=NAVY), bgcolor='white', bordercolor='#E8E8E8', borderwidth=1),
        plot_bgcolor='white', paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, color=NAVY),
        height=height, margin=dict(l=70, r=40, t=80, b=80),
        hovermode='x unified',
    )


def _fetch_all(supabase, table, select_cols='*', filters=None):
    """Paginate through a Supabase table in 1000-row chunks.
    filters: list of (method, args) tuples, e.g. [('eq', ('col', 'val'))]
    """
    all_rows = []
    offset = 0
    chunk = 1000
    while True:
        query = supabase.table(table).select(select_cols)
        if filters:
            for method, args in filters:
                query = getattr(query, method)(*args)
        resp = query.range(offset, offset + chunk - 1).execute()
        rows = resp.data
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < chunk:
            break
        offset += chunk
    return pd.DataFrame(all_rows)


# -- Data Loading --------------------------------------------------------------

def load_inventory(supabase):
    """Load inventory_retail with submarket and zip."""
    print("Loading inventory_retail...")
    df = _fetch_all(supabase, 'inventory_retail',
        'costar_property_id,costar_submarket_name,aquila_submarket,building_status,rentable_building_area,zip')
    df['submarket'] = df['aquila_submarket'].fillna(df['costar_submarket_name'])
    # Normalize zip to 5 digits
    df['zip5'] = df['zip'].astype(str).str[:5]
    print(f"  [OK] {len(df)} inventory rows")
    return df


def load_stats_latest_rent(supabase):
    """Load latest quarter NNN rent from stats_retail for income-vs-rent chart."""
    print("Loading latest stats_retail rents (2025 Q4, Existing)...")
    # Fetch only the latest quarter to avoid loading 739K rows
    df = _fetch_all(supabase, 'stats_retail',
        'costar_property_id,quarter,building_status,rentable_building_area,nnn_rent_direct',
        filters=[
            ('eq', ('building_status', 'Existing')),
            ('eq', ('quarter', '2025 Q4')),
        ])
    df['nnn_rent_direct'] = pd.to_numeric(df['nnn_rent_direct'], errors='coerce')
    print(f"  [OK] {len(df)} rows for 2025 Q4")
    return df


def load_census_data():
    """Fetch Census ACS data for 2023 and 2018 (for growth comparison)."""
    print("Fetching Census ACS 2023...")
    df_2023 = fetch_acs_by_zcta([POPULATION, MEDIAN_HH_INCOME, MEDIAN_AGE, AVG_HOUSEHOLD_SIZE], year=2023)
    print("Fetching Census ACS 2018...")
    df_2018 = fetch_acs_by_zcta([POPULATION], year=2018)
    return df_2023, df_2018


def build_submarket_demographics(df_inv, df_census_2023, df_census_2018):
    """
    Aggregate census zip-level data to submarket level.
    Joins inventory zips to census ZCTAs, then population-weights to submarket.
    """
    # Get distinct zip-to-submarket mapping from inventory
    zip_sub = df_inv[['zip5', 'submarket']].drop_duplicates()

    # Merge census 2023
    merged = zip_sub.merge(df_census_2023[['zcta', POPULATION, MEDIAN_HH_INCOME, MEDIAN_AGE, AVG_HOUSEHOLD_SIZE]],
                           left_on='zip5', right_on='zcta', how='inner')

    # Population-weighted aggregation to submarket
    result = []
    for sub, grp in merged.groupby('submarket'):
        pop = grp[POPULATION].sum()
        if pop == 0:
            continue
        weights = grp[POPULATION] / pop
        row = {
            'submarket': sub,
            'population': pop,
            'median_hh_income': (grp[MEDIAN_HH_INCOME].fillna(0) * weights).sum(),
            'median_age': (grp[MEDIAN_AGE].fillna(0) * weights).sum(),
            'avg_household_size': (grp[AVG_HOUSEHOLD_SIZE].fillna(0) * weights).sum(),
            'n_zips': len(grp),
        }
        result.append(row)

    df_sub = pd.DataFrame(result)

    # Add 2018 population for growth calc
    zip_pop_2018 = zip_sub.merge(df_census_2018[['zcta', POPULATION]].rename(columns={POPULATION: 'pop_2018'}),
                                  left_on='zip5', right_on='zcta', how='inner')
    pop_2018_by_sub = zip_pop_2018.groupby('submarket')['pop_2018'].sum().reset_index()
    df_sub = df_sub.merge(pop_2018_by_sub, on='submarket', how='left')
    df_sub['pop_growth_pct'] = (df_sub['population'] - df_sub['pop_2018']) / df_sub['pop_2018'] * 100

    # Add existing RBA by submarket
    existing_rba = df_inv[df_inv['building_status'] == 'Existing'].groupby('submarket')['rentable_building_area'].sum().reset_index()
    existing_rba.columns = ['submarket', 'existing_rba']
    df_sub = df_sub.merge(existing_rba, on='submarket', how='left')
    df_sub['sf_per_capita'] = df_sub['existing_rba'] / df_sub['population']

    # Add pipeline % for scatter
    pipeline_rba = df_inv[df_inv['building_status'].isin(['Under Construction', 'Proposed'])].groupby('submarket')['rentable_building_area'].sum().reset_index()
    pipeline_rba.columns = ['submarket', 'pipeline_rba']
    df_sub = df_sub.merge(pipeline_rba, on='submarket', how='left')
    df_sub['pipeline_rba'] = df_sub['pipeline_rba'].fillna(0)
    df_sub['pipeline_pct'] = df_sub['pipeline_rba'] / df_sub['existing_rba'] * 100

    print(f"  [OK] Aggregated demographics for {len(df_sub)} submarkets")
    return df_sub


# -- Chart Builders ------------------------------------------------------------

def chart_sf_per_capita(df_sub):
    """Chart 15: Retail SF per Capita by Submarket (horizontal bar)."""
    df = df_sub.sort_values('sf_per_capita', ascending=True).copy()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df['submarket'], x=df['sf_per_capita'], orientation='h',
        marker_color=NAVY,
        text=[f'{v:.1f}' for v in df['sf_per_capita']],
        textposition='outside',
        textfont=dict(family=AQUILA_FONT, size=11, color=NAVY),
        hovertemplate='%{y}<br>%{x:.1f} SF per capita<extra></extra>',
    ))

    layout = _shared_layout('Retail SF per Capita by Submarket', '', height=650)
    layout['xaxis']['title'] = 'Retail SF per Capita'
    layout['xaxis']['tickangle'] = 0
    layout['yaxis']['title'] = ''
    layout['margin'] = dict(l=130, r=80, t=80, b=60)
    fig.update_layout(**layout, showlegend=False)
    return fig


def chart_population_vs_pipeline(df_sub):
    """Chart 16: Population Growth vs Retail Pipeline scatter."""
    df = df_sub.dropna(subset=['pop_growth_pct', 'pipeline_pct']).copy()
    df = df[df['pipeline_pct'] > 0]  # Only submarkets with pipeline

    # Size bubbles by RBA (scale to reasonable range)
    max_rba = df['existing_rba'].max()
    df['bubble_size'] = (df['existing_rba'] / max_rba * 40) + 10

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['pop_growth_pct'], y=df['pipeline_pct'],
        mode='markers+text',
        marker=dict(size=df['bubble_size'], color=NAVY, opacity=0.7, line=dict(width=1, color='white')),
        text=df['submarket'],
        textposition='top center',
        textfont=dict(family=AQUILA_FONT, size=10, color=NAVY),
        hovertemplate='%{text}<br>Pop Growth: %{x:.1f}%<br>Pipeline: %{y:.1f}%<br>RBA: %{customdata:,.0f} SF<extra></extra>',
        customdata=df['existing_rba'],
    ))

    layout = _shared_layout('Population Growth vs Retail Pipeline', 'Pipeline (% of Existing Inventory)')
    layout['xaxis']['title'] = 'Population Growth 2018-2023 (%)'
    layout['xaxis']['ticksuffix'] = '%'
    layout['xaxis']['tickangle'] = 0
    layout['yaxis']['ticksuffix'] = '%'
    layout['hovermode'] = 'closest'
    layout['margin'] = dict(l=70, r=40, t=80, b=80)
    fig.update_layout(**layout, showlegend=False)
    return fig


def chart_income_vs_rent(df_sub, df_inv, df_stats_latest):
    """Chart 17: Median Income vs NNN Rent scatter."""
    # Get RBA-weighted NNN rent by submarket from latest quarter
    merged = df_stats_latest.merge(
        df_inv[['costar_property_id', 'submarket']].drop_duplicates(),
        on='costar_property_id', how='left'
    )

    rent_by_sub = merged.groupby('submarket').apply(
        lambda g: pd.Series({
            'wt_nnn': (g.dropna(subset=['nnn_rent_direct'])['nnn_rent_direct'] *
                       g.dropna(subset=['nnn_rent_direct'])['rentable_building_area']).sum() /
                      g.dropna(subset=['nnn_rent_direct'])['rentable_building_area'].sum()
                      if g.dropna(subset=['nnn_rent_direct'])['rentable_building_area'].sum() > 0 else np.nan,
        })
    ).reset_index()

    df = df_sub.merge(rent_by_sub, on='submarket', how='inner').dropna(subset=['wt_nnn', 'median_hh_income'])

    max_rba = df['existing_rba'].max()
    df['bubble_size'] = (df['existing_rba'] / max_rba * 40) + 10

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['median_hh_income'], y=df['wt_nnn'],
        mode='markers+text',
        marker=dict(size=df['bubble_size'], color=NAVY, opacity=0.7, line=dict(width=1, color='white')),
        text=df['submarket'],
        textposition='top center',
        textfont=dict(family=AQUILA_FONT, size=10, color=NAVY),
        hovertemplate='%{text}<br>Median Income: $%{x:,.0f}<br>NNN Rent: $%{y:.2f}/SF<br>RBA: %{customdata:,.0f} SF<extra></extra>',
        customdata=df['existing_rba'],
    ))

    layout = _shared_layout('Median Household Income vs NNN Rent', 'NNN Rent ($/SF/YR)')
    layout['xaxis']['title'] = 'Median Household Income'
    layout['xaxis']['tickprefix'] = '$'
    layout['xaxis']['tickformat'] = ','
    layout['xaxis']['tickangle'] = 0
    layout['yaxis']['tickprefix'] = '$'
    layout['hovermode'] = 'closest'
    layout['margin'] = dict(l=70, r=40, t=80, b=80)
    fig.update_layout(**layout, showlegend=False)
    return fig


def chart_demographic_profile(df_sub):
    """Chart 18: Demographic profile by submarket, normalized to metro average."""
    # Compute metro-wide averages (population-weighted)
    total_pop = df_sub['population'].sum()
    metro_income = (df_sub['median_hh_income'] * df_sub['population']).sum() / total_pop
    metro_age = (df_sub['median_age'] * df_sub['population']).sum() / total_pop
    metro_pop = total_pop / len(df_sub)  # Average submarket population

    # Normalize each metric to metro average (100%)
    df = df_sub.copy()
    df['pop_idx'] = df['population'] / metro_pop * 100
    df['income_idx'] = df['median_hh_income'] / metro_income * 100
    df['age_idx'] = df['median_age'] / metro_age * 100

    # Sort by population
    df = df.sort_values('population', ascending=True)

    fig = go.Figure()
    metrics = [
        ('pop_idx', 'Population', NAVY),
        ('income_idx', 'Median Income', GLASS_BLUE),
        ('age_idx', 'Median Age', COPPER),
    ]
    for col, name, color in metrics:
        fig.add_trace(go.Bar(
            y=df['submarket'], x=df[col], name=name, orientation='h',
            marker_color=color,
            hovertemplate='%{y}<br>' + name + ': %{x:.0f}% of metro avg<extra></extra>',
        ))

    # Add reference line at 100%
    fig.add_vline(x=100, line_dash='dash', line_color=CONCRETE, line_width=1.5,
                  annotation_text='Metro Avg', annotation_position='top',
                  annotation_font=dict(family=AQUILA_FONT, size=10, color=CONCRETE))

    layout = _shared_layout('Demographic Profile by Submarket (vs Metro Average)', '', height=700)
    layout['barmode'] = 'group'
    layout['xaxis']['title'] = '% of Metro Average'
    layout['xaxis']['ticksuffix'] = '%'
    layout['xaxis']['tickangle'] = 0
    layout['yaxis']['title'] = ''
    layout['legend'] = dict(font=dict(family=AQUILA_FONT, size=11, color=NAVY), orientation='h',
                            yanchor='bottom', y=-0.12, xanchor='center', x=0.5)
    layout['margin'] = dict(l=130, r=40, t=80, b=80)
    fig.update_layout(**layout)
    return fig


# -- Main ----------------------------------------------------------------------

def main():
    print("=" * 60)
    print("GENERATING: Retail Demographics Charts (4 charts)")
    print("=" * 60)

    from aquila.connectors.supabase import get_supabase_client
    supabase = get_supabase_client(use_service_role=True)
    print("[OK] Connected to Supabase\n")

    # Load data
    df_inv = load_inventory(supabase)
    df_stats_latest = load_stats_latest_rent(supabase)
    df_census_2023, df_census_2018 = load_census_data()

    # Aggregate to submarket level
    df_sub = build_submarket_demographics(df_inv, df_census_2023, df_census_2018)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    charts = []

    print("\n--- Story 6: Demographics & Retail Demand ---")

    # Chart 15: SF per Capita
    print("  Building: retail_sf_per_capita...")
    fig = chart_sf_per_capita(df_sub)
    path = os.path.join(OUTPUT_DIR, 'retail_sf_per_capita.html')
    write_chart_html(fig, path)
    charts.append(path)
    print(f"  [OK] Saved: {path}")

    # Chart 16: Population Growth vs Pipeline
    print("  Building: retail_population_vs_pipeline...")
    fig = chart_population_vs_pipeline(df_sub)
    path = os.path.join(OUTPUT_DIR, 'retail_population_vs_pipeline.html')
    write_chart_html(fig, path)
    charts.append(path)
    print(f"  [OK] Saved: {path}")

    # Chart 17: Income vs Rent
    print("  Building: retail_income_vs_rent...")
    fig = chart_income_vs_rent(df_sub, df_inv, df_stats_latest)
    path = os.path.join(OUTPUT_DIR, 'retail_income_vs_rent.html')
    write_chart_html(fig, path)
    charts.append(path)
    print(f"  [OK] Saved: {path}")

    # Chart 18: Demographic Profile
    print("  Building: retail_demographic_profile...")
    fig = chart_demographic_profile(df_sub)
    path = os.path.join(OUTPUT_DIR, 'retail_demographic_profile.html')
    write_chart_html(fig, path)
    charts.append(path)
    print(f"  [OK] Saved: {path}")

    print(f"\n{'=' * 60}")
    print(f"[OK] SUCCESS: {len(charts)} demographic charts generated")
    print("=" * 60)


if __name__ == '__main__':
    main()
