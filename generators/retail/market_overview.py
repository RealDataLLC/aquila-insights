#!/usr/bin/env python3
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402
"""
Retail Market Overview Charts
Generates 14 HTML charts from Supabase inventory_retail and stats_retail tables.

Charts are organized by story/theme:
  Story 1 — Market Fundamentals (4 charts)
  Story 2 — Building Stock & Composition (2 charts)
  Story 3 — Supply Pipeline & Growth (3 charts)
  Story 4 — East Austin Rent Surge (2 charts)
  Story 5 — Submarket Deep Dives (3 charts)

Usage:
    python -m generators.retail.market_overview
"""

import re
import os
import sys
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from dotenv import load_dotenv
from aquila.brand import AQUILA_COLORS, AQUILA_FONT, NAVY, GLASS_BLUE, GLASS_ALT, CONCRETE, COPPER, BRASS, GREENSPACE, SIGNAL
from aquila.charts import write_chart_html

load_dotenv('aquila_graph.env')

OUTPUT_DIR = 'charts/retail'

# Top 8 submarkets by existing RBA (from our analysis)
TOP_8 = ['Hays County', 'Georgetown', 'South', 'Cedar Park', 'Central', 'Southwest', 'Round Rock', 'North/Domain']
TOP_8_COLORS = {
    'Hays County': NAVY, 'Georgetown': GLASS_BLUE, 'South': GLASS_ALT,
    'Cedar Park': CONCRETE, 'Central': COPPER, 'Southwest': BRASS,
    'Round Rock': GREENSPACE, 'North/Domain': AQUILA_COLORS[8],
}


# -- Helpers -------------------------------------------------------------------

def _quarter_sort_key(q_str):
    """Convert '2025 Q4' -> sortable float 2025.4"""
    m = re.match(r'(\d{4})\s*[Qq](\d)', str(q_str))
    if m:
        return int(m.group(1)) + int(m.group(2)) / 10
    return 0


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
    filters: list of (method, args) tuples, e.g. [('eq', ('building_status', 'Existing'))]
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
        if offset % 10000 == 0:
            print(f"    ... {offset} rows fetched")
    return pd.DataFrame(all_rows)


# -- Data Loading --------------------------------------------------------------

def load_data(supabase):
    """Load inventory and stats data from Supabase."""
    print("Loading inventory_retail...")
    df_inv = _fetch_all(supabase, 'inventory_retail',
        'costar_property_id,costar_submarket_name,aquila_submarket,building_status,costar_property_type,year_built,rentable_building_area,zip')
    df_inv['submarket'] = df_inv['aquila_submarket'].fillna(df_inv['costar_submarket_name'])
    print(f"  [OK] {len(df_inv)} inventory rows")

    # stats_retail has ~739K rows; filter server-side to reduce volume.
    # Earliest chart needs 2015 Q1 (quarter strings sort lexically: "2015 Q1" < "2025 Q4").
    # Net absorption needs one prior quarter (2017 Q4) for diff.
    print("Loading stats_retail (Existing, 2015+)...")
    df_stats = _fetch_all(supabase, 'stats_retail',
        'costar_property_id,quarter,building_status,rentable_building_area,vacant_available_sf_direct,vacant_available_sf_sublet,nnn_rent_direct,all_service_type_rent_overall',
        filters=[
            ('eq', ('building_status', 'Existing')),
            ('gte', ('quarter', '2015 Q1')),
        ])
    print(f"  [OK] {len(df_stats)} stats rows")

    # Add sort key and filter
    df_stats['_sort'] = df_stats['quarter'].apply(_quarter_sort_key)
    df_stats = df_stats.sort_values('_sort').reset_index(drop=True)

    # Merge submarket from inventory
    df_stats = df_stats.merge(
        df_inv[['costar_property_id', 'submarket']].drop_duplicates(),
        on='costar_property_id', how='left'
    )

    return df_inv, df_stats


# -- Story 1: Market Fundamentals (4 charts) -----------------------------------

def chart_vacancy_by_submarket(df_stats):
    """Chart 1: Vacancy rate by submarket (line chart)."""
    df = df_stats[(df_stats['building_status'] == 'Existing') & (df_stats['_sort'] >= 2018.1)].copy()
    df = df[df['submarket'].isin(TOP_8)]

    agg = df.groupby(['quarter', 'submarket', '_sort']).agg(
        vac_sf=('vacant_available_sf_direct', lambda x: x.fillna(0).sum() + df.loc[x.index, 'vacant_available_sf_sublet'].fillna(0).sum()),
        rba=('rentable_building_area', 'sum')
    ).reset_index()
    # Recompute vacancy properly
    grp = df.groupby(['quarter', 'submarket', '_sort']).apply(
        lambda g: pd.Series({
            'vacancy_rate': (g['vacant_available_sf_direct'].fillna(0).sum() + g['vacant_available_sf_sublet'].fillna(0).sum()) / g['rentable_building_area'].sum() if g['rentable_building_area'].sum() > 0 else 0
        })
    ).reset_index()
    grp = grp.sort_values('_sort')

    fig = go.Figure()
    for sub in TOP_8:
        s = grp[grp['submarket'] == sub]
        fig.add_trace(go.Scatter(x=s['quarter'], y=s['vacancy_rate'], mode='lines', name=sub,
                                 line=dict(color=TOP_8_COLORS[sub], width=2),
                                 hovertemplate='%{x}<br>%{y:.1%}<extra>' + sub + '</extra>'))
    layout = _shared_layout('Retail Vacancy Rate by Submarket', 'Vacancy Rate')
    layout['yaxis']['tickformat'] = '.0%'
    fig.update_layout(**layout)
    return fig


def chart_nnn_rent_by_submarket(df_stats):
    """Chart 2: RBA-weighted NNN rent by submarket (line chart)."""
    df = df_stats[(df_stats['building_status'] == 'Existing') & (df_stats['_sort'] >= 2018.1)].copy()
    df = df[df['submarket'].isin(TOP_8)]
    df['nnn_rent_direct'] = pd.to_numeric(df['nnn_rent_direct'], errors='coerce')

    grp = df.groupby(['quarter', 'submarket', '_sort']).apply(
        lambda g: pd.Series({
            'wt_nnn': (g['nnn_rent_direct'].fillna(0) * g['rentable_building_area']).sum() /
                      g.loc[g['nnn_rent_direct'].notna(), 'rentable_building_area'].sum()
                      if g.loc[g['nnn_rent_direct'].notna(), 'rentable_building_area'].sum() > 0 else np.nan
        })
    ).reset_index()
    grp = grp.sort_values('_sort')

    fig = go.Figure()
    for sub in TOP_8:
        s = grp[grp['submarket'] == sub].dropna(subset=['wt_nnn'])
        fig.add_trace(go.Scatter(x=s['quarter'], y=s['wt_nnn'], mode='lines', name=sub,
                                 line=dict(color=TOP_8_COLORS[sub], width=2),
                                 hovertemplate='%{x}<br>$%{y:.2f}/SF<extra>' + sub + '</extra>'))
    layout = _shared_layout('Retail NNN Rent by Submarket (RBA-Weighted)', 'NNN Rent ($/SF/YR)')
    layout['yaxis']['tickprefix'] = '$'
    fig.update_layout(**layout)
    return fig


def chart_net_absorption(df_stats):
    """Chart 3: Citywide net absorption (bar chart)."""
    df = df_stats[(df_stats['building_status'] == 'Existing') & (df_stats['_sort'] >= 2017.4)].copy()

    grp = df.groupby(['quarter', '_sort']).apply(
        lambda g: pd.Series({
            'occupied_sf': g['rentable_building_area'].sum() - g['vacant_available_sf_direct'].fillna(0).sum() - g['vacant_available_sf_sublet'].fillna(0).sum()
        })
    ).reset_index().sort_values('_sort')

    grp['net_absorption'] = grp['occupied_sf'].diff()
    grp = grp[grp['_sort'] >= 2018.1].copy()

    colors = [NAVY if v >= 0 else SIGNAL for v in grp['net_absorption']]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=grp['quarter'], y=grp['net_absorption'], marker_color=colors,
                         hovertemplate='%{x}<br>%{y:,.0f} SF<extra></extra>'))
    layout = _shared_layout('Retail Net Absorption - Citywide', 'Net Absorption (SF)')
    layout['yaxis']['tickformat'] = ','
    layout['hovermode'] = 'x'
    fig.update_layout(**layout)
    return fig


def chart_occupancy_by_submarket(df_stats):
    """Chart 4: Occupancy rate by submarket (line chart)."""
    df = df_stats[(df_stats['building_status'] == 'Existing') & (df_stats['_sort'] >= 2018.1)].copy()
    df = df[df['submarket'].isin(TOP_8)]

    grp = df.groupby(['quarter', 'submarket', '_sort']).apply(
        lambda g: pd.Series({
            'occupancy': (g['rentable_building_area'].sum() - g['vacant_available_sf_direct'].fillna(0).sum() - g['vacant_available_sf_sublet'].fillna(0).sum()) / g['rentable_building_area'].sum() if g['rentable_building_area'].sum() > 0 else 0
        })
    ).reset_index().sort_values('_sort')

    fig = go.Figure()
    for sub in TOP_8:
        s = grp[grp['submarket'] == sub]
        fig.add_trace(go.Scatter(x=s['quarter'], y=s['occupancy'], mode='lines', name=sub,
                                 line=dict(color=TOP_8_COLORS[sub], width=2),
                                 hovertemplate='%{x}<br>%{y:.1%}<extra>' + sub + '</extra>'))
    layout = _shared_layout('Retail Occupancy Rate by Submarket', 'Occupancy Rate')
    layout['yaxis']['tickformat'] = '.0%'
    fig.update_layout(**layout)
    return fig


# -- Story 2: Building Stock & Composition (2 charts) --------------------------

def chart_building_age(df_inv):
    """Chart 5: RBA by building age decade per submarket (stacked horizontal bar)."""
    df = df_inv[(df_inv['building_status'] == 'Existing') & df_inv['year_built'].notna()].copy()
    df['year_built'] = pd.to_numeric(df['year_built'], errors='coerce')
    df = df.dropna(subset=['year_built'])

    bins = [0, 1970, 1980, 1990, 2000, 2010, 2020, 2100]
    labels = ['Pre-1970', '1970s', '1980s', '1990s', '2000s', '2010s', '2020s']
    df['decade'] = pd.cut(df['year_built'], bins=bins, labels=labels, right=False)

    agg = df.groupby(['submarket', 'decade'], observed=False)['rentable_building_area'].sum().reset_index()
    sub_totals = agg.groupby('submarket')['rentable_building_area'].sum().sort_values(ascending=True)
    sub_order = sub_totals.index.tolist()

    decade_colors = dict(zip(labels, AQUILA_COLORS[:7]))

    fig = go.Figure()
    for decade in labels:
        d = agg[agg['decade'] == decade].set_index('submarket').reindex(sub_order).fillna(0)
        fig.add_trace(go.Bar(
            y=d.index, x=d['rentable_building_area'], name=decade, orientation='h',
            marker_color=decade_colors[decade],
            hovertemplate='%{y}<br>' + decade + ': %{x:,.0f} SF<extra></extra>'
        ))

    layout = _shared_layout('Austin Retail: Rentable SF by Building Age', 'RBA (SF)', height=650)
    layout['barmode'] = 'stack'
    layout['xaxis']['tickformat'] = ','
    layout['xaxis']['title'] = 'Rentable Building Area (SF)'
    layout['xaxis']['tickangle'] = 0
    layout['yaxis']['title'] = ''
    layout['legend'] = dict(font=dict(family=AQUILA_FONT, size=11, color=NAVY), orientation='h', yanchor='bottom', y=-0.15, xanchor='center', x=0.5)
    layout['margin'] = dict(l=130, r=40, t=80, b=80)
    fig.update_layout(**layout)
    return fig


def chart_property_type_mix(df_inv):
    """Chart 6: Property type mix by submarket (stacked horizontal bar)."""
    df = df_inv[df_inv['building_status'] == 'Existing'].copy()
    # Simplify property type names
    df['ptype'] = df['costar_property_type'].str.replace('Retail ', '', regex=False).str.strip('()')
    df.loc[df['ptype'] == 'Retail', 'ptype'] = 'General Retail'

    agg = df.groupby(['submarket', 'ptype'])['rentable_building_area'].sum().reset_index()
    sub_totals = agg.groupby('submarket')['rentable_building_area'].sum().sort_values(ascending=True)
    sub_order = sub_totals.index.tolist()
    ptype_order = agg.groupby('ptype')['rentable_building_area'].sum().sort_values(ascending=False).index.tolist()

    fig = go.Figure()
    for i, pt in enumerate(ptype_order):
        d = agg[agg['ptype'] == pt].set_index('submarket').reindex(sub_order).fillna(0)
        fig.add_trace(go.Bar(
            y=d.index, x=d['rentable_building_area'], name=pt, orientation='h',
            marker_color=AQUILA_COLORS[i % len(AQUILA_COLORS)],
            hovertemplate='%{y}<br>' + pt + ': %{x:,.0f} SF<extra></extra>'
        ))

    layout = _shared_layout('Retail Property Type Mix by Submarket', '', height=650)
    layout['barmode'] = 'stack'
    layout['xaxis']['tickformat'] = ','
    layout['xaxis']['title'] = 'Rentable Building Area (SF)'
    layout['xaxis']['tickangle'] = 0
    layout['yaxis']['title'] = ''
    layout['legend'] = dict(font=dict(family=AQUILA_FONT, size=11, color=NAVY), orientation='h', yanchor='bottom', y=-0.15, xanchor='center', x=0.5)
    layout['margin'] = dict(l=130, r=40, t=80, b=80)
    fig.update_layout(**layout)
    return fig


# -- Story 3: Supply Pipeline & Growth (3 charts) ------------------------------

def chart_pipeline(df_inv):
    """Chart 7: Supply pipeline by submarket (stacked horizontal bar)."""
    df = df_inv[df_inv['building_status'].isin(['Under Construction', 'Proposed'])].copy()

    agg = df.groupby(['submarket', 'building_status'])['rentable_building_area'].sum().reset_index()
    pipeline_total = agg.groupby('submarket')['rentable_building_area'].sum().sort_values(ascending=True)
    pipeline_total = pipeline_total[pipeline_total > 0]
    sub_order = pipeline_total.index.tolist()

    fig = go.Figure()
    for status, color in [('Under Construction', NAVY), ('Proposed', GLASS_BLUE)]:
        d = agg[agg['building_status'] == status].set_index('submarket').reindex(sub_order).fillna(0)
        fig.add_trace(go.Bar(
            y=d.index, x=d['rentable_building_area'], name=status, orientation='h',
            marker_color=color,
            hovertemplate='%{y}<br>' + status + ': %{x:,.0f} SF<extra></extra>'
        ))

    layout = _shared_layout('Retail Supply Pipeline by Submarket', '', height=550)
    layout['barmode'] = 'stack'
    layout['xaxis']['tickformat'] = ','
    layout['xaxis']['title'] = 'Rentable Building Area (SF)'
    layout['xaxis']['tickangle'] = 0
    layout['yaxis']['title'] = ''
    layout['margin'] = dict(l=130, r=40, t=80, b=80)
    fig.update_layout(**layout)
    return fig


def chart_pipeline_pct(df_inv):
    """Chart 8: Pipeline as % of existing inventory by submarket."""
    existing = df_inv[df_inv['building_status'] == 'Existing'].groupby('submarket')['rentable_building_area'].sum()
    pipeline = df_inv[df_inv['building_status'].isin(['Under Construction', 'Proposed'])].groupby('submarket')['rentable_building_area'].sum()

    pct = (pipeline / existing * 100).dropna().sort_values(ascending=True)
    pct = pct[pct > 0]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=pct.index, x=pct.values, orientation='h', marker_color=NAVY,
        text=[f'{v:.1f}%' for v in pct.values], textposition='outside',
        textfont=dict(family=AQUILA_FONT, size=11, color=NAVY),
        hovertemplate='%{y}<br>Pipeline: %{x:.1f}% of existing<extra></extra>'
    ))

    layout = _shared_layout('Retail Pipeline as % of Existing Inventory', '', height=550)
    layout['xaxis']['title'] = '% of Existing Inventory'
    layout['xaxis']['ticksuffix'] = '%'
    layout['xaxis']['tickangle'] = 0
    layout['yaxis']['title'] = ''
    layout['margin'] = dict(l=130, r=80, t=80, b=60)
    fig.update_layout(**layout, showlegend=False)
    return fig


def chart_inventory_growth(df_stats, df_inv):
    """Chart 9: Inventory growth 2018 vs 2025 by submarket."""
    df = df_stats[df_stats['building_status'] == 'Existing'].copy()

    q2018 = df[df['quarter'] == '2018 Q1'].groupby('submarket')['rentable_building_area'].sum()
    q2025 = df[df['quarter'] == '2025 Q4'].groupby('submarket')['rentable_building_area'].sum()

    combined = pd.DataFrame({'2018 Q1': q2018, '2025 Q4': q2025}).dropna()
    combined['growth_pct'] = (combined['2025 Q4'] - combined['2018 Q1']) / combined['2018 Q1'] * 100
    combined = combined.sort_values('2025 Q4', ascending=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(y=combined.index, x=combined['2018 Q1'], name='2018 Q1', orientation='h',
                         marker_color=GLASS_BLUE, hovertemplate='%{y}<br>2018 Q1: %{x:,.0f} SF<extra></extra>'))
    fig.add_trace(go.Bar(y=combined.index, x=combined['2025 Q4'], name='2025 Q4', orientation='h',
                         marker_color=NAVY, hovertemplate='%{y}<br>2025 Q4: %{x:,.0f} SF<extra></extra>'))

    layout = _shared_layout('Retail Inventory Growth by Submarket (2018 vs 2025)', '', height=650)
    layout['barmode'] = 'group'
    layout['xaxis']['tickformat'] = ','
    layout['xaxis']['title'] = 'Rentable Building Area (SF)'
    layout['xaxis']['tickangle'] = 0
    layout['yaxis']['title'] = ''
    layout['legend'] = dict(font=dict(family=AQUILA_FONT, size=11, color=NAVY), orientation='h', yanchor='bottom', y=-0.12, xanchor='center', x=0.5)
    layout['margin'] = dict(l=130, r=40, t=80, b=80)
    fig.update_layout(**layout)
    return fig


# -- Story 4: East Austin Rent Surge (2 charts) --------------------------------

def chart_east_vs_citywide_rent(df_stats):
    """Chart 10: East Austin NNN rent vs citywide."""
    df = df_stats[(df_stats['building_status'] == 'Existing') & (df_stats['_sort'] >= 2015.1)].copy()
    df['nnn_rent_direct'] = pd.to_numeric(df['nnn_rent_direct'], errors='coerce')

    def weighted_nnn(g):
        valid = g.dropna(subset=['nnn_rent_direct'])
        if valid['rentable_building_area'].sum() == 0:
            return np.nan
        return (valid['nnn_rent_direct'] * valid['rentable_building_area']).sum() / valid['rentable_building_area'].sum()

    east = df[df['submarket'] == 'East'].groupby(['quarter', '_sort']).apply(weighted_nnn).reset_index(name='wt_nnn').sort_values('_sort')
    city = df.groupby(['quarter', '_sort']).apply(weighted_nnn).reset_index(name='wt_nnn').sort_values('_sort')

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=east['quarter'], y=east['wt_nnn'], mode='lines', name='East Austin',
                             line=dict(color=NAVY, width=3),
                             hovertemplate='%{x}<br>$%{y:.2f}/SF<extra>East</extra>'))
    fig.add_trace(go.Scatter(x=city['quarter'], y=city['wt_nnn'], mode='lines', name='Citywide Avg',
                             line=dict(color=CONCRETE, width=2, dash='dash'),
                             hovertemplate='%{x}<br>$%{y:.2f}/SF<extra>Citywide</extra>'))

    layout = _shared_layout('East Austin Retail NNN Rent vs Citywide', 'NNN Rent ($/SF/YR)')
    layout['yaxis']['tickprefix'] = '$'
    fig.update_layout(**layout)
    return fig


def chart_east_occ_vs_rent(df_stats):
    """Chart 11: East Austin occupancy vs rent (dual axis)."""
    df = df_stats[(df_stats['building_status'] == 'Existing') & (df_stats['_sort'] >= 2015.1) & (df_stats['submarket'] == 'East')].copy()
    df['nnn_rent_direct'] = pd.to_numeric(df['nnn_rent_direct'], errors='coerce')

    grp = df.groupby(['quarter', '_sort']).apply(
        lambda g: pd.Series({
            'occupancy': (g['rentable_building_area'].sum() - g['vacant_available_sf_direct'].fillna(0).sum() - g['vacant_available_sf_sublet'].fillna(0).sum()) / g['rentable_building_area'].sum() if g['rentable_building_area'].sum() > 0 else 0,
            'wt_nnn': (g.dropna(subset=['nnn_rent_direct'])['nnn_rent_direct'] * g.dropna(subset=['nnn_rent_direct'])['rentable_building_area']).sum() / g.dropna(subset=['nnn_rent_direct'])['rentable_building_area'].sum() if g.dropna(subset=['nnn_rent_direct'])['rentable_building_area'].sum() > 0 else np.nan,
        })
    ).reset_index().sort_values('_sort')

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=grp['quarter'], y=grp['occupancy'], fill='tozeroy', name='Occupancy Rate',
                             line=dict(color=GLASS_BLUE, width=1), fillcolor='rgba(194, 218, 241, 0.4)',
                             yaxis='y', hovertemplate='%{x}<br>Occupancy: %{y:.1%}<extra></extra>'))
    fig.add_trace(go.Scatter(x=grp['quarter'], y=grp['wt_nnn'], mode='lines', name='NNN Rent',
                             line=dict(color=NAVY, width=3), yaxis='y2',
                             hovertemplate='%{x}<br>$%{y:.2f}/SF<extra></extra>'))

    layout = _shared_layout('East Austin Retail: Occupancy vs NNN Rent', 'Occupancy Rate')
    layout['yaxis']['tickformat'] = '.0%'
    layout['yaxis']['range'] = [0.90, 1.0]
    layout['yaxis2'] = dict(
        title='NNN Rent ($/SF/YR)', tickprefix='$', overlaying='y', side='right',
        title_font=dict(family=AQUILA_FONT, size=12, color=NAVY),
        tickfont=dict(family=AQUILA_FONT, size=11, color=NAVY),
        showgrid=False,
    )
    layout['legend'] = dict(font=dict(family=AQUILA_FONT, size=11, color=NAVY), orientation='h', yanchor='bottom', y=-0.2, xanchor='center', x=0.5)
    fig.update_layout(**layout)
    return fig


# -- Story 5: Submarket Deep Dives (3 charts) ----------------------------------

def chart_northeast_occupancy(df_stats):
    """Chart 12: Northeast Austin occupancy deep dive with annotation."""
    df = df_stats[(df_stats['building_status'] == 'Existing') & (df_stats['_sort'] >= 2019.1) & (df_stats['submarket'] == 'Northeast')].copy()

    grp = df.groupby(['quarter', '_sort']).apply(
        lambda g: pd.Series({
            'occupancy': (g['rentable_building_area'].sum() - g['vacant_available_sf_direct'].fillna(0).sum() - g['vacant_available_sf_sublet'].fillna(0).sum()) / g['rentable_building_area'].sum() if g['rentable_building_area'].sum() > 0 else 0
        })
    ).reset_index().sort_values('_sort')

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=grp['quarter'], y=grp['occupancy'], mode='lines', name='Northeast',
                             line=dict(color=NAVY, width=3),
                             hovertemplate='%{x}<br>%{y:.1%}<extra></extra>'))

    # Add annotation at the cliff
    fig.add_annotation(x='2023 Q4', y=0.9735, text='97.4% - Cliff begins', showarrow=True,
                       arrowhead=2, arrowcolor=SIGNAL, font=dict(family=AQUILA_FONT, size=12, color=SIGNAL),
                       ax=60, ay=-40)
    fig.add_annotation(x='2025 Q4', y=0.9045, text='90.5%', showarrow=True,
                       arrowhead=2, arrowcolor=SIGNAL, font=dict(family=AQUILA_FONT, size=12, color=SIGNAL),
                       ax=40, ay=-30)

    layout = _shared_layout('Northeast Austin Retail Occupancy', 'Occupancy Rate')
    layout['yaxis']['tickformat'] = '.0%'
    layout['showlegend'] = False
    fig.update_layout(**layout)
    return fig


def chart_urban_vs_suburban(df_stats):
    """Chart 13: Urban vs suburban occupancy comparison."""
    df = df_stats[(df_stats['building_status'] == 'Existing') & (df_stats['_sort'] >= 2018.1)].copy()

    urban_subs = ['CBD', 'Central', 'East']
    suburban_subs = ['Georgetown', 'Cedar Park', 'Far Northeast', 'Hays County']

    def group_occ(df_sub, subs):
        d = df_sub[df_sub['submarket'].isin(subs)]
        grp = d.groupby(['quarter', '_sort']).apply(
            lambda g: pd.Series({
                'occupancy': (g['rentable_building_area'].sum() - g['vacant_available_sf_direct'].fillna(0).sum() - g['vacant_available_sf_sublet'].fillna(0).sum()) / g['rentable_building_area'].sum() if g['rentable_building_area'].sum() > 0 else 0
            })
        ).reset_index().sort_values('_sort')
        return grp

    urban = group_occ(df, urban_subs)
    suburban = group_occ(df, suburban_subs)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=urban['quarter'], y=urban['occupancy'], mode='lines', name='Urban (CBD+Central+East)',
                             line=dict(color=NAVY, width=2.5),
                             hovertemplate='%{x}<br>%{y:.1%}<extra>Urban</extra>'))
    fig.add_trace(go.Scatter(x=suburban['quarter'], y=suburban['occupancy'], mode='lines', name='Suburban (Georgetown+Cedar Park+Far NE+Hays)',
                             line=dict(color=GREENSPACE, width=2.5),
                             hovertemplate='%{x}<br>%{y:.1%}<extra>Suburban</extra>'))

    layout = _shared_layout('Urban vs Suburban Retail Occupancy', 'Occupancy Rate')
    layout['yaxis']['tickformat'] = '.0%'
    layout['legend'] = dict(font=dict(family=AQUILA_FONT, size=11, color=NAVY), orientation='h', yanchor='bottom', y=-0.2, xanchor='center', x=0.5)
    fig.update_layout(**layout)
    return fig


def chart_suburban_rent_growth(df_stats):
    """Chart 14: Suburban rent growth comparison."""
    df = df_stats[(df_stats['building_status'] == 'Existing') & (df_stats['_sort'] >= 2015.1)].copy()
    df['nnn_rent_direct'] = pd.to_numeric(df['nnn_rent_direct'], errors='coerce')

    subs = ['Georgetown', 'Cedar Park', 'Far Northeast', 'Hays County']
    colors = {
        'Georgetown': NAVY, 'Cedar Park': GLASS_BLUE,
        'Far Northeast': COPPER, 'Hays County': GREENSPACE
    }

    fig = go.Figure()
    for sub in subs:
        d = df[df['submarket'] == sub]
        grp = d.groupby(['quarter', '_sort']).apply(
            lambda g: pd.Series({
                'wt_nnn': (g.dropna(subset=['nnn_rent_direct'])['nnn_rent_direct'] * g.dropna(subset=['nnn_rent_direct'])['rentable_building_area']).sum() / g.dropna(subset=['nnn_rent_direct'])['rentable_building_area'].sum() if g.dropna(subset=['nnn_rent_direct'])['rentable_building_area'].sum() > 0 else np.nan,
            })
        ).reset_index().sort_values('_sort').dropna(subset=['wt_nnn'])

        fig.add_trace(go.Scatter(x=grp['quarter'], y=grp['wt_nnn'], mode='lines', name=sub,
                                 line=dict(color=colors[sub], width=2),
                                 hovertemplate='%{x}<br>$%{y:.2f}/SF<extra>' + sub + '</extra>'))

    layout = _shared_layout('Suburban Retail NNN Rent Growth', 'NNN Rent ($/SF/YR)')
    layout['yaxis']['tickprefix'] = '$'
    fig.update_layout(**layout)
    return fig


# -- Main ----------------------------------------------------------------------

def main():
    print("=" * 60)
    print("GENERATING: Retail Market Overview Charts (14 charts)")
    print("=" * 60)

    from aquila.connectors.supabase import get_supabase_client
    supabase = get_supabase_client(use_service_role=True)
    print("[OK] Connected to Supabase\n")

    df_inv, df_stats = load_data(supabase)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    charts = []

    # Story 1: Market Fundamentals
    print("\n--- Story 1: Market Fundamentals ---")
    for name, func, args in [
        ('retail_vacancy_rate_by_submarket', chart_vacancy_by_submarket, (df_stats,)),
        ('retail_nnn_rent_by_submarket', chart_nnn_rent_by_submarket, (df_stats,)),
        ('retail_net_absorption_citywide', chart_net_absorption, (df_stats,)),
        ('retail_occupancy_by_submarket', chart_occupancy_by_submarket, (df_stats,)),
    ]:
        print(f"  Building: {name}...")
        fig = func(*args)
        path = os.path.join(OUTPUT_DIR, f'{name}.html')
        write_chart_html(fig, path)
        charts.append(path)
        print(f"  [OK] Saved: {path}")

    # Story 2: Building Stock
    print("\n--- Story 2: Building Stock & Composition ---")
    for name, func, args in [
        ('retail_building_age_by_submarket', chart_building_age, (df_inv,)),
        ('retail_property_type_by_submarket', chart_property_type_mix, (df_inv,)),
    ]:
        print(f"  Building: {name}...")
        fig = func(*args)
        path = os.path.join(OUTPUT_DIR, f'{name}.html')
        write_chart_html(fig, path)
        charts.append(path)
        print(f"  [OK] Saved: {path}")

    # Story 3: Pipeline
    print("\n--- Story 3: Supply Pipeline & Growth ---")
    for name, func, args in [
        ('retail_pipeline_by_submarket', chart_pipeline, (df_inv,)),
        ('retail_pipeline_pct_by_submarket', chart_pipeline_pct, (df_inv,)),
        ('retail_inventory_growth', chart_inventory_growth, (df_stats, df_inv)),
    ]:
        print(f"  Building: {name}...")
        fig = func(*args)
        path = os.path.join(OUTPUT_DIR, f'{name}.html')
        write_chart_html(fig, path)
        charts.append(path)
        print(f"  [OK] Saved: {path}")

    # Story 4: East Austin
    print("\n--- Story 4: East Austin Rent Surge ---")
    for name, func, args in [
        ('retail_east_austin_rent', chart_east_vs_citywide_rent, (df_stats,)),
        ('retail_east_austin_occ_vs_rent', chart_east_occ_vs_rent, (df_stats,)),
    ]:
        print(f"  Building: {name}...")
        fig = func(*args)
        path = os.path.join(OUTPUT_DIR, f'{name}.html')
        write_chart_html(fig, path)
        charts.append(path)
        print(f"  [OK] Saved: {path}")

    # Story 5: Submarket Deep Dives
    print("\n--- Story 5: Submarket Deep Dives ---")
    for name, func, args in [
        ('retail_northeast_occupancy', chart_northeast_occupancy, (df_stats,)),
        ('retail_urban_vs_suburban', chart_urban_vs_suburban, (df_stats,)),
        ('retail_suburban_rent_growth', chart_suburban_rent_growth, (df_stats,)),
    ]:
        print(f"  Building: {name}...")
        fig = func(*args)
        path = os.path.join(OUTPUT_DIR, f'{name}.html')
        write_chart_html(fig, path)
        charts.append(path)
        print(f"  [OK] Saved: {path}")

    print(f"\n{'=' * 60}")
    print(f"[OK] SUCCESS: {len(charts)} retail charts generated")
    print("=" * 60)


if __name__ == '__main__':
    main()
