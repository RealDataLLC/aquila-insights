#!/usr/bin/env python3
"""
Census + LODES + QCEW Office Market Article Charts
Generates 10 charts tying public demographic, employment, and business data
to Austin office market performance at the submarket level.

Data sources:
  - Census ACS 5-Year (tract level, spatially joined to submarkets via KMZ)
  - Census ACS 1-Year (MSA level, for peer city comparisons)
  - Census LODES (block-level employment density)
  - BLS QCEW (quarterly establishment counts)
  - FRED (office-sector job growth indices)

Charts:
  GROUP A - ACS by Submarket (tract + spatial join)
    A1. census_population_by_submarket.html
    A2. census_occupations_by_submarket.html
    A3. census_education_by_submarket.html
    A4. census_income_by_submarket.html
  GROUP B - LODES Employment Density (block + spatial join)
    B1. lodes_office_employment_by_submarket.html
    B2. lodes_office_employment_growth.html
  GROUP C - BLS QCEW Establishment Trends
    C1. qcew_professional_services_travis.html
    C2. qcew_office_sector_mix.html
  GROUP D - MSA Comparisons
    D1. census_austin_vs_peers.html
    D2. fred_office_sectors_indexed.html

Usage:
    python -m generators.economic.census_office
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dotenv import load_dotenv
from plotly.subplots import make_subplots

from aquila.brand import AQUILA_COLORS, AQUILA_FONT, NAVY, GLASS_BLUE, CONCRETE, COPPER, BRASS
from aquila.charts import write_chart_html
from aquila.connectors.census import (
    AUSTIN_COUNTIES,
    MEDIAN_HH_INCOME,
    POPULATION,
    _fetch_acs_raw,
    fetch_lodes_wac,
    fetch_qcew,
    fetch_tracts_acs,
)
from aquila.connectors.fred import fetch_fred_series
from aquila.geo import build_block_group_submarket_map, build_tract_submarket_map

load_dotenv('aquila_graph.env')

OUTPUT_DIR = 'charts/economic-indicators'
SUBMARKET_ORDER = ['CBD', 'Northwest', 'Southwest', 'East']
SUBMARKET_COLORS = {
    'CBD':       AQUILA_COLORS[0],   # Navy
    'Northwest': AQUILA_COLORS[1],   # Glass Blue
    'Southwest': AQUILA_COLORS[2],   # Glass Alt
    'East':      AQUILA_COLORS[4],   # Copper
}

# ACS variables for occupations (C24010: Sex by Occupation)
OCC_MGMT_M   = 'C24010_003E'
OCC_MGMT_F   = 'C24010_039E'
OCC_STEM_M   = 'C24010_006E'
OCC_STEM_F   = 'C24010_042E'
OCC_ADMIN_M  = 'C24010_021E'
OCC_ADMIN_F  = 'C24010_057E'

# ACS variables for education (B15003: Educational Attainment 25+)
EDU_TOTAL    = 'B15003_001E'
EDU_BACHELORS = 'B15003_022E'
EDU_MASTERS  = 'B15003_023E'
EDU_PROF     = 'B15003_024E'
EDU_DOCTORAL = 'B15003_025E'


# -- Shared layout helper -----------------------------------------------------

def _base_layout(title, y_title, height=520, x_title=''):
    return dict(
        title=dict(
            text=title, font=dict(family=AQUILA_FONT, size=17, color=NAVY),
            x=0.5, xanchor='center',
        ),
        xaxis=dict(
            title=x_title,
            title_font=dict(family=AQUILA_FONT, size=12, color=NAVY),
            tickfont=dict(family=AQUILA_FONT, size=11, color=NAVY),
            showgrid=False, linecolor='#E8E8E8',
        ),
        yaxis=dict(
            title=y_title,
            title_font=dict(family=AQUILA_FONT, size=12, color=NAVY),
            tickfont=dict(family=AQUILA_FONT, size=11, color=NAVY),
            gridcolor='#E8E8E8', zeroline=False,
        ),
        legend=dict(
            font=dict(family=AQUILA_FONT, size=11, color=NAVY),
            bgcolor='white', bordercolor='#E8E8E8', borderwidth=1,
        ),
        plot_bgcolor='white', paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, color=NAVY),
        height=height,
        margin=dict(l=70, r=40, t=80, b=80),
        hovermode='x unified',
    )


def _source_annotation(text, y=-0.15):
    """Return a source-citation annotation dict for the bottom of a chart."""
    return dict(
        text=text,
        xref='paper', yref='paper', x=0.5, y=y,
        showarrow=False, font=dict(size=10, color=CONCRETE, family=AQUILA_FONT),
        xanchor='center',
    )


def _out(filename):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return os.path.join(OUTPUT_DIR, filename)


def _aggregate_tracts(df_tracts, tract_map, value_cols):
    """Join tract data to submarket map and aggregate by submarket."""
    df = df_tracts.copy()
    df['submarket'] = df['GEOID'].map(tract_map)
    df = df[df['submarket'].isin(SUBMARKET_ORDER)]
    for col in value_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df.groupby('submarket')[value_cols].sum().reset_index()


# =============================================================================
# GROUP A — Census ACS by Submarket
# =============================================================================

def chart_a1_population(tract_map):
    """A1: Population by submarket over time (line)."""
    print("\n[A1] Population by Submarket...")
    years = list(range(2015, 2024))
    frames = []
    for yr in years:
        df_yr = fetch_tracts_acs(yr, [POPULATION], AUSTIN_COUNTIES)
        if df_yr.empty:
            continue
        agg = _aggregate_tracts(df_yr, tract_map, [POPULATION])
        agg['year'] = yr
        frames.append(agg)
    if not frames:
        print("  [SKIP] No population data")
        return
    df = pd.concat(frames, ignore_index=True)
    df[POPULATION] = df[POPULATION] / 1000  # convert to thousands

    fig = go.Figure()
    for sub in SUBMARKET_ORDER:
        sub_df = df[df['submarket'] == sub].sort_values('year')
        if sub_df.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub_df['year'], y=sub_df[POPULATION],
            name=sub, mode='lines+markers',
            line=dict(color=SUBMARKET_COLORS[sub], width=2.5),
            marker=dict(size=6),
        ))
    fig.update_layout(**_base_layout(
        'Population by Office Submarket (Thousands)',
        'Population (Thousands)',
    ))
    fig.update_xaxes(tickmode='linear', dtick=1)
    write_chart_html(fig, _out('census_population_by_submarket.html'))
    print("  [OK] census_population_by_submarket.html")


def chart_a2_occupations(tract_map):
    """A2: Office-using occupations by submarket (stacked bar, latest year)."""
    print("\n[A2] Occupations by Submarket...")
    occ_vars = [OCC_MGMT_M, OCC_MGMT_F, OCC_STEM_M, OCC_STEM_F, OCC_ADMIN_M, OCC_ADMIN_F]
    df_tracts = fetch_tracts_acs(2023, occ_vars, AUSTIN_COUNTIES)
    if df_tracts.empty:
        print("  [SKIP] No occupation data")
        return

    df_tracts['mgmt']  = df_tracts[OCC_MGMT_M].fillna(0) + df_tracts[OCC_MGMT_F].fillna(0)
    df_tracts['stem']  = df_tracts[OCC_STEM_M].fillna(0) + df_tracts[OCC_STEM_F].fillna(0)
    df_tracts['admin'] = df_tracts[OCC_ADMIN_M].fillna(0) + df_tracts[OCC_ADMIN_F].fillna(0)
    df = _aggregate_tracts(df_tracts, tract_map, ['mgmt', 'stem', 'admin'])
    df = df[df['submarket'].isin(SUBMARKET_ORDER)].set_index('submarket').reindex(SUBMARKET_ORDER).reset_index()
    df[['mgmt', 'stem', 'admin']] = df[['mgmt', 'stem', 'admin']] / 1000

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df['submarket'], y=df['mgmt'], name='Management & Financial',
                         marker_color=NAVY))
    fig.add_trace(go.Bar(x=df['submarket'], y=df['stem'], name='STEM & Technology',
                         marker_color=COPPER))
    fig.add_trace(go.Bar(x=df['submarket'], y=df['admin'], name='Office & Admin Support',
                         marker_color=BRASS))
    fig.update_layout(
        **_base_layout('Office-Using Occupations by Submarket (2023)', 'Workers (Thousands)'),
        barmode='stack',
        annotations=[_source_annotation('Source: U.S. Census Bureau ACS 5-Year 2023, Table C24010')],
    )
    write_chart_html(fig, _out('census_occupations_by_submarket.html'))
    print("  [OK] census_occupations_by_submarket.html")


def chart_a3_education(tract_map):
    """A3: Educational attainment (bachelor's+) by submarket (horizontal bar)."""
    print("\n[A3] Education by Submarket...")
    edu_vars = [EDU_TOTAL, EDU_BACHELORS, EDU_MASTERS, EDU_PROF, EDU_DOCTORAL]
    df_tracts = fetch_tracts_acs(2023, edu_vars, AUSTIN_COUNTIES)
    if df_tracts.empty:
        print("  [SKIP] No education data")
        return

    df = _aggregate_tracts(df_tracts, tract_map, edu_vars)
    df['bachelors_plus'] = (df[EDU_BACHELORS] + df[EDU_MASTERS] + df[EDU_PROF] + df[EDU_DOCTORAL])
    df['pct_bachelors_plus'] = df['bachelors_plus'] / df[EDU_TOTAL] * 100
    df = df[df['submarket'].isin(SUBMARKET_ORDER)].sort_values('pct_bachelors_plus')

    fig = go.Figure()
    colors = [SUBMARKET_COLORS.get(s, AQUILA_COLORS[3]) for s in df['submarket']]
    fig.add_trace(go.Bar(
        x=df['pct_bachelors_plus'], y=df['submarket'],
        orientation='h',
        marker_color=colors,
        text=[f"{v:.1f}%" for v in df['pct_bachelors_plus']],
        textposition='outside',
        textfont=dict(family=AQUILA_FONT, size=12, color=NAVY),
    ))
    layout = _base_layout(
        "Bachelor's Degree or Higher by Submarket (2023)",
        '', height=420,
    )
    layout['xaxis'].update(ticksuffix='%', range=[0, max(df['pct_bachelors_plus']) * 1.2])
    layout['xaxis']['title'] = "Share of Population 25+ (%)"
    layout['yaxis'].update(showgrid=False)
    layout['hovermode'] = 'y unified'
    layout['annotations'] = [_source_annotation(
        'Source: U.S. Census Bureau ACS 5-Year 2023, Table B15003', y=-0.18,
    )]
    fig.update_layout(**layout)
    write_chart_html(fig, _out('census_education_by_submarket.html'))
    print("  [OK] census_education_by_submarket.html")


def chart_a4_income(tract_map):
    """A4: Median household income by submarket, multi-year bars."""
    print("\n[A4] Income by Submarket...")
    years = [2019, 2021, 2023]
    year_data = {}
    for yr in years:
        df_tracts = fetch_tracts_acs(yr, [POPULATION, MEDIAN_HH_INCOME], AUSTIN_COUNTIES)
        if df_tracts.empty:
            continue
        # Population-weighted average of tract medians
        df_tracts['submarket'] = df_tracts['GEOID'].map(tract_map)
        df_tracts = df_tracts[df_tracts['submarket'].isin(SUBMARKET_ORDER)]
        df_tracts[POPULATION] = pd.to_numeric(df_tracts[POPULATION], errors='coerce').fillna(0)
        df_tracts[MEDIAN_HH_INCOME] = pd.to_numeric(df_tracts[MEDIAN_HH_INCOME], errors='coerce')
        result = {}
        for sub, grp in df_tracts.groupby('submarket'):
            pop = grp[POPULATION].sum()
            if pop == 0:
                continue
            valid = grp.dropna(subset=[MEDIAN_HH_INCOME])
            if valid.empty:
                continue
            result[sub] = (valid[MEDIAN_HH_INCOME] * valid[POPULATION]).sum() / valid[POPULATION].sum()
        year_data[yr] = result

    if not year_data:
        print("  [SKIP] No income data")
        return

    fig = go.Figure()
    bar_colors = [AQUILA_COLORS[0], AQUILA_COLORS[2], AQUILA_COLORS[4]]
    for i, (yr, income_map) in enumerate(sorted(year_data.items())):
        x_vals, y_vals = [], []
        for sub in SUBMARKET_ORDER:
            x_vals.append(sub)
            y_vals.append(income_map.get(sub, None))
        fig.add_trace(go.Bar(
            x=x_vals, y=y_vals, name=str(yr),
            marker_color=bar_colors[i],
            text=[f"${v:,.0f}" if v else '' for v in y_vals],
            textposition='outside',
            textfont=dict(family=AQUILA_FONT, size=11, color=NAVY),
        ))
    layout = _base_layout(
        'Median Household Income by Submarket',
        'Median Household Income',
    )
    layout['barmode'] = 'group'
    layout['yaxis']['tickprefix'] = '$'
    layout['yaxis']['tickformat'] = ',.0f'
    layout['annotations'] = [_source_annotation(
        'Source: U.S. Census Bureau ACS 5-Year Estimates, Table B19013 (population-weighted by tract)',
    )]
    fig.update_layout(**layout)
    write_chart_html(fig, _out('census_income_by_submarket.html'))
    print("  [OK] census_income_by_submarket.html")


# =============================================================================
# GROUP B — LODES Employment Density
# =============================================================================

def chart_b1_lodes_snapshot(bg_map):
    """B1: Office employment by submarket, 2023 snapshot (bar)."""
    print("\n[B1] LODES Office Employment Snapshot...")
    df = fetch_lodes_wac(2023)
    if df.empty:
        print("  [SKIP] No LODES data")
        return

    # Aggregate LODES blocks to block groups (first 12 digits of 15-digit GEOID)
    df['bg_geoid'] = df['w_geocode'].str[:12]
    df['submarket'] = df['bg_geoid'].map(bg_map)
    df = df[df['submarket'].isin(SUBMARKET_ORDER)]
    agg = df.groupby('submarket')['office_jobs'].sum().reindex(SUBMARKET_ORDER).reset_index()
    total = agg['office_jobs'].sum()
    agg['pct'] = agg['office_jobs'] / total * 100

    fig = go.Figure()
    colors = [SUBMARKET_COLORS[s] for s in agg['submarket']]
    fig.add_trace(go.Bar(
        x=agg['submarket'], y=agg['office_jobs'],
        marker_color=colors,
        text=[f"{row['office_jobs']:,.0f}<br>({row['pct']:.1f}%)" for _, row in agg.iterrows()],
        textposition='outside',
        textfont=dict(family=AQUILA_FONT, size=11, color=NAVY),
    ))
    layout = _base_layout(
        'Office-Using Employment by Submarket (2023)',
        'Office-Using Jobs',
    )
    layout['yaxis']['tickformat'] = ',.0f'
    layout['annotations'] = [_source_annotation(
        'Source: Census LEHD/LODES 2023. Office-using = Info (NAICS 51) + Finance (52) + Professional Services (54) + Management (55).',
    )]
    fig.update_layout(**layout)
    write_chart_html(fig, _out('lodes_office_employment_by_submarket.html'))
    print("  [OK] lodes_office_employment_by_submarket.html")


def chart_b2_lodes_growth(bg_map):
    """B2: Office employment growth by submarket 2015-2023 (indexed line)."""
    print("\n[B2] LODES Office Employment Growth...")
    years = [2015, 2017, 2019, 2021, 2022, 2023]
    year_agg = {}
    for yr in years:
        df = fetch_lodes_wac(yr)
        if df.empty:
            continue
        df['bg_geoid'] = df['w_geocode'].str[:12]
        df['submarket'] = df['bg_geoid'].map(bg_map)
        df = df[df['submarket'].isin(SUBMARKET_ORDER)]
        agg = df.groupby('submarket')['office_jobs'].sum()
        year_agg[yr] = agg

    if not year_agg:
        print("  [SKIP] No LODES data")
        return

    df_all = pd.DataFrame(year_agg).T
    df_all.index.name = 'year'
    # Index to 100 at base year
    base_yr = min(yr for yr in years if yr in df_all.index)
    for sub in SUBMARKET_ORDER:
        if sub in df_all.columns and df_all.loc[base_yr, sub] > 0:
            df_all[sub] = df_all[sub] / df_all.loc[base_yr, sub] * 100

    fig = go.Figure()
    for sub in SUBMARKET_ORDER:
        if sub not in df_all.columns:
            continue
        fig.add_trace(go.Scatter(
            x=df_all.index, y=df_all[sub],
            name=sub, mode='lines+markers',
            line=dict(color=SUBMARKET_COLORS[sub], width=2.5),
            marker=dict(size=6),
        ))
    # Total dashed line (sum across all submarkets, then index)
    available_subs = [s for s in SUBMARKET_ORDER if s in df_all.columns]
    if available_subs:
        df_raw = pd.DataFrame(year_agg).T[available_subs]
        df_total = df_raw.sum(axis=1)
        base_total = df_total.iloc[0] if not df_total.empty else None
        if base_total and base_total > 0:
            df_total_idx = df_total / base_total * 100
            fig.add_trace(go.Scatter(
                x=df_total_idx.index, y=df_total_idx.values,
                name='Total (All Submarkets)', mode='lines',
                line=dict(color=CONCRETE, width=1.5, dash='dash'),
            ))

    layout = _base_layout(
        f'Office Employment Growth by Submarket (Indexed to {base_yr})',
        f'Index ({base_yr} = 100)',
    )
    layout['annotations'] = [_source_annotation(
        'Source: Census LEHD/LODES. Office-using = Info + Finance + Professional Services + Management.',
    )]
    fig.update_layout(**layout)
    fig.add_hline(y=100, line_dash='dot', line_color=CONCRETE, line_width=1)
    write_chart_html(fig, _out('lodes_office_employment_growth.html'))
    print("  [OK] lodes_office_employment_growth.html")


# =============================================================================
# GROUP C — BLS QCEW Establishment Trends
# =============================================================================

def _find_qcew_col(df, candidates):
    """Return the first column name from candidates that exists in df, or None."""
    return next((c for c in candidates if c in df.columns), None)


def _parse_qcew_row(df, naics):
    """Filter QCEW DataFrame to a specific NAICS private-sector row. Returns the row or None."""
    if df.empty:
        return None
    ind_col = next((c for c in df.columns if 'industry' in c.lower()), None)
    if ind_col is None:
        return None
    mask = df[ind_col].astype(str).str.strip() == str(naics)
    own_col = next((c for c in df.columns if 'own' in c.lower()), None)
    if own_col:
        mask &= df[own_col].astype(str).str.strip() == '5'  # own_code 5 = private
    rows = df[mask]
    if rows.empty:
        return None
    return rows.iloc[0]


def _parse_qcew_estabs(df, naics):
    """Extract establishment count for a NAICS code from QCEW data."""
    row = _parse_qcew_row(df, naics)
    if row is None:
        return None
    estab_col = _find_qcew_col(df, ['annual_avg_estabs', 'annual_avg_estabs_count',
                                     'qtrly_estabs_count', 'qtrly_estabs'])
    if estab_col is None:
        return None
    return pd.to_numeric(row[estab_col], errors='coerce')


def _parse_qcew_employment(df, naics):
    """Extract employment level for a NAICS code from QCEW data."""
    row = _parse_qcew_row(df, naics)
    if row is None:
        return None
    emp_col = _find_qcew_col(df, ['annual_avg_emplvl', 'annual_avg_emp_count'])
    if emp_col is None:
        return None
    return pd.to_numeric(row[emp_col], errors='coerce')


def chart_c1_qcew_prof_services():
    """C1: Professional services establishment count + employment (dual axis)."""
    print("\n[C1] QCEW Professional Services...")
    years = list(range(2015, 2025))
    estab_data = {}
    for yr in years:
        df = fetch_qcew('48453', yr)
        if df.empty:
            continue
        estabs = _parse_qcew_estabs(df, '54')
        if estabs is not None:
            estab_data[yr] = estabs

    if not estab_data:
        print("  [SKIP] No QCEW data")
        return

    # Supplement employment with FRED if QCEW employment is sparse
    fred_emp = fetch_fred_series('AUST448PBSV', 'Professional & Business Services (Thousands)')
    fred_annual = None
    if not fred_emp.empty:
        fred_emp['year'] = fred_emp['date'].dt.year
        fred_annual = fred_emp.groupby('year')['Professional & Business Services (Thousands)'].mean()

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    yr_list = sorted(estab_data.keys())
    estab_vals = [estab_data[y] for y in yr_list]
    fig.add_trace(go.Bar(
        x=yr_list, y=estab_vals, name='Establishments',
        marker_color=NAVY, opacity=0.85,
    ), secondary_y=False)

    # Overlay employment
    if fred_annual is not None and not fred_annual.empty:
        emp_yrs = [y for y in yr_list if y in fred_annual.index]
        emp_vals = [fred_annual[y] * 1000 for y in emp_yrs]
        fig.add_trace(go.Scatter(
            x=emp_yrs, y=emp_vals, name='Employment (BLS via FRED)',
            mode='lines+markers',
            line=dict(color=COPPER, width=2.5),
            marker=dict(size=6),
        ), secondary_y=True)
        fig.update_yaxes(title_text='Employment', secondary_y=True,
                         title_font=dict(family=AQUILA_FONT, size=12, color=COPPER),
                         tickfont=dict(family=AQUILA_FONT, size=11),
                         tickformat=',.0f', showgrid=False)

    fig.update_layout(
        **_base_layout(
            'Professional Services: Firms & Employment — Travis County',
            'Number of Establishments',
        ),
        annotations=[_source_annotation(
            'Source: BLS QCEW (establishments), BLS via FRED (employment). NAICS 54 Private sector, Travis County.',
        )],
    )
    fig.update_yaxes(tickformat=',.0f', secondary_y=False)
    write_chart_html(fig, _out('qcew_professional_services_travis.html'))
    print("  [OK] qcew_professional_services_travis.html")


def chart_c2_qcew_sector_mix():
    """C2: Office industry sector mix -- establishment count and avg firm size (grouped bar)."""
    print("\n[C2] QCEW Office Sector Mix...")
    latest_year = 2023
    sectors = {
        '51': ('Information / Tech', NAVY),
        '52': ('Finance & Insurance', GLASS_BLUE),
        '54': ('Professional Services', COPPER),
        '55': ('Management of Companies', BRASS),
    }
    df = fetch_qcew('48453', latest_year)
    if df.empty:
        print("  [SKIP] No QCEW sector mix data")
        return

    rows = []
    for naics, (label, color) in sectors.items():
        estabs = _parse_qcew_estabs(df, naics)
        if estabs is None:
            continue
        emp = _parse_qcew_employment(df, naics)
        avg_size = emp / estabs if (estabs and estabs > 0 and emp) else None
        rows.append({'sector': label, 'estabs': estabs, 'avg_size': avg_size, 'color': color})

    if not rows:
        print("  [SKIP] No sector rows matched")
        return

    df_plot = pd.DataFrame(rows)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=df_plot['sector'], y=df_plot['estabs'],
        name='Establishments',
        marker_color=df_plot['color'].tolist(),
        text=[f"{v:,.0f}" for v in df_plot['estabs']],
        textposition='outside',
        textfont=dict(family=AQUILA_FONT, size=11, color=NAVY),
    ), secondary_y=False)
    if df_plot['avg_size'].notna().any():
        fig.add_trace(go.Scatter(
            x=df_plot['sector'], y=df_plot['avg_size'],
            name='Avg Employees/Firm',
            mode='markers',
            marker=dict(color=CONCRETE, size=12, symbol='diamond'),
        ), secondary_y=True)
        fig.update_yaxes(title_text='Avg Employees per Firm', secondary_y=True,
                         title_font=dict(family=AQUILA_FONT, size=12, color=CONCRETE),
                         tickfont=dict(family=AQUILA_FONT, size=11), showgrid=False)

    fig.update_layout(
        **_base_layout(
            f'Office Industry Sector Mix — Travis County ({latest_year})',
            'Number of Establishments',
        ),
        annotations=[_source_annotation(
            f'Source: BLS QCEW {latest_year}, Travis County, Private sector. Office-using NAICS sectors shown.',
        )],
    )
    fig.update_yaxes(tickformat=',.0f', secondary_y=False)
    write_chart_html(fig, _out('qcew_office_sector_mix.html'))
    print("  [OK] qcew_office_sector_mix.html")


# =============================================================================
# GROUP D — MSA-Level Comparisons
# =============================================================================

PEER_MSAS = {
    '12420': 'Austin',
    '19100': 'Dallas-Fort Worth',
    '26420': 'Houston',
    '34980': 'Nashville',
    '19740': 'Denver',
    '38060': 'Phoenix',
}
PEER_COLORS = {
    'Austin':           AQUILA_COLORS[0],
    'Dallas-Fort Worth': AQUILA_COLORS[1],
    'Houston':          AQUILA_COLORS[2],
    'Nashville':        AQUILA_COLORS[4],
    'Denver':           AQUILA_COLORS[5],
    'Phoenix':          AQUILA_COLORS[6],
}


def chart_d1_peer_population():
    """D1: Austin vs peer cities population growth, indexed to 2012."""
    print("\n[D1] Austin vs Peer Cities Population...")
    years = list(range(2012, 2024))
    msa_data = {msa: {} for msa in PEER_MSAS}

    # Fetch each MSA separately per year using fetch_acs_msa
    for yr in years:
        for msa_fips in PEER_MSAS:
            geo = f"metropolitan statistical area/micropolitan statistical area:{msa_fips}"
            try:
                df = _fetch_acs_raw(yr, [POPULATION], geo, 'acs1')
                if not df.empty:
                    val = pd.to_numeric(df.iloc[0][POPULATION], errors='coerce')
                    msa_data[msa_fips][yr] = val
                time.sleep(0.2)
            except Exception:
                pass

    # Index to 100 at 2012
    base_yr = 2012
    fig = go.Figure()
    for msa_fips, city_name in PEER_MSAS.items():
        pop_map = msa_data[msa_fips]
        if base_yr not in pop_map or pop_map.get(base_yr) is None:
            continue
        base_val = pop_map[base_yr]
        if not base_val or np.isnan(float(base_val)):
            continue
        yr_list = sorted(k for k, v in pop_map.items() if v is not None and not np.isnan(float(v)))
        idx_vals = [pop_map[y] / base_val * 100 for y in yr_list]
        is_austin = (city_name == 'Austin')
        fig.add_trace(go.Scatter(
            x=yr_list, y=idx_vals,
            name=city_name, mode='lines+markers',
            line=dict(color=PEER_COLORS[city_name], width=3 if is_austin else 1.5),
            marker=dict(size=7 if is_austin else 5),
        ))

    fig.update_layout(
        **_base_layout(
            f'Population Growth: Austin vs. Sun Belt Peers (Indexed to {base_yr})',
            f'Population Index ({base_yr} = 100)',
        ),
        annotations=[_source_annotation(
            'Source: U.S. Census Bureau ACS 1-Year Estimates (MSA level)',
        )],
    )
    fig.add_hline(y=100, line_dash='dot', line_color=CONCRETE, line_width=1)
    write_chart_html(fig, _out('census_austin_vs_peers.html'))
    print("  [OK] census_austin_vs_peers.html")


def chart_d1b_peer_population_2019():
    """D1b: Austin vs peer cities population growth, indexed to 2019."""
    print("\n[D1b] Austin vs Peer Cities Population (Indexed to 2019)...")
    years = list(range(2019, 2024))
    msa_data = {msa: {} for msa in PEER_MSAS}

    for yr in years:
        for msa_fips in PEER_MSAS:
            geo = f"metropolitan statistical area/micropolitan statistical area:{msa_fips}"
            try:
                df = _fetch_acs_raw(yr, [POPULATION], geo, 'acs1')
                if not df.empty:
                    val = pd.to_numeric(df.iloc[0][POPULATION], errors='coerce')
                    msa_data[msa_fips][yr] = val
                time.sleep(0.2)
            except Exception:
                pass

    base_yr = 2019
    fig = go.Figure()
    for msa_fips, city_name in PEER_MSAS.items():
        pop_map = msa_data[msa_fips]
        if base_yr not in pop_map or pop_map.get(base_yr) is None:
            continue
        base_val = pop_map[base_yr]
        if not base_val or np.isnan(float(base_val)):
            continue
        yr_list = sorted(k for k, v in pop_map.items() if v is not None and not np.isnan(float(v)))
        idx_vals = [pop_map[y] / base_val * 100 for y in yr_list]
        is_austin = (city_name == 'Austin')
        fig.add_trace(go.Scatter(
            x=yr_list, y=idx_vals,
            name=city_name, mode='lines+markers',
            line=dict(color=PEER_COLORS[city_name], width=3 if is_austin else 1.5),
            marker=dict(size=7 if is_austin else 5),
        ))

    fig.update_layout(
        **_base_layout(
            f'Population Growth: Austin vs. Sun Belt Peers (Indexed to {base_yr})',
            f'Population Index ({base_yr} = 100)',
        ),
        annotations=[_source_annotation(
            'Source: U.S. Census Bureau ACS 1-Year Estimates (MSA level)',
        )],
    )
    fig.add_hline(y=100, line_dash='dot', line_color=CONCRETE, line_width=1)
    write_chart_html(fig, _out('census_austin_vs_peers_2019.html'))
    print("  [OK] census_austin_vs_peers_2019.html")


def chart_d2_fred_sectors_indexed():
    """D2: Austin vs National office-sector job growth, indexed to Jan 2015."""
    print("\n[D2] Austin vs National Office Sectors (FRED)...")
    series = {
        'AUST448PBSV':  ('Austin Prof & Business Svcs', NAVY,       'solid'),
        'AUST448INFO':  ('Austin Information / Tech',   COPPER,     'solid'),
        'USPBS':        ('US Prof & Business Svcs',     NAVY,       'dash'),
        'USINFO':       ('US Information / Tech',       COPPER,     'dash'),
    }
    base_date = pd.Timestamp('2015-01-01')
    fig = go.Figure()
    for sid, (label, color, dash) in series.items():
        df = fetch_fred_series(sid, label)
        if df.empty:
            continue
        df = df[df['date'] >= base_date].sort_values('date')
        base_val = df[label].iloc[0] if not df.empty else None
        if base_val is None or base_val == 0:
            continue
        df['indexed'] = df[label] / base_val * 100
        fig.add_trace(go.Scatter(
            x=df['date'], y=df['indexed'],
            name=label, mode='lines',
            line=dict(color=color, width=2.5 if dash == 'solid' else 1.5, dash=dash),
        ))

    fig.update_layout(
        **_base_layout(
            'Office-Sector Job Growth: Austin vs. National (Jan 2015 = 100)',
            'Employment Index (Jan 2015 = 100)',
        ),
        annotations=[_source_annotation(
            'Source: Bureau of Labor Statistics via FRED. Solid = Austin MSA; Dashed = National.',
        )],
    )
    fig.add_hline(y=100, line_dash='dot', line_color=CONCRETE, line_width=1)
    write_chart_html(fig, _out('fred_office_sectors_indexed.html'))
    print("  [OK] fred_office_sectors_indexed.html")


def chart_d2b_fred_sectors_indexed_2020():
    """D2b: Austin vs National office-sector job growth, indexed to April 2020."""
    print("\n[D2b] Austin vs National Office Sectors (FRED, Apr 2020)...")
    series = {
        'AUST448PBSV':  ('Austin Prof & Business Svcs', NAVY,       'solid'),
        'AUST448INFO':  ('Austin Information / Tech',   COPPER,     'solid'),
        'USPBS':        ('US Prof & Business Svcs',     NAVY,       'dash'),
        'USINFO':       ('US Information / Tech',       COPPER,     'dash'),
    }
    base_date = pd.Timestamp('2020-04-01')
    fig = go.Figure()
    for sid, (label, color, dash) in series.items():
        df = fetch_fred_series(sid, label)
        if df.empty:
            continue
        df = df[df['date'] >= base_date].sort_values('date')
        base_val = df[label].iloc[0] if not df.empty else None
        if base_val is None or base_val == 0:
            continue
        df['indexed'] = df[label] / base_val * 100
        fig.add_trace(go.Scatter(
            x=df['date'], y=df['indexed'],
            name=label, mode='lines',
            line=dict(color=color, width=2.5 if dash == 'solid' else 1.5, dash=dash),
        ))

    fig.update_layout(
        **_base_layout(
            'Office-Sector Job Growth: Austin vs. National (Apr 2020 = 100)',
            'Employment Index (Apr 2020 = 100)',
        ),
        annotations=[_source_annotation(
            'Source: Bureau of Labor Statistics via FRED. Solid = Austin MSA; Dashed = National.',
        )],
    )
    fig.add_hline(y=100, line_dash='dot', line_color=CONCRETE, line_width=1)
    write_chart_html(fig, _out('fred_office_sectors_indexed_apr2020.html'))
    print("  [OK] fred_office_sectors_indexed_apr2020.html")


# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 70)
    print("Census + LODES + QCEW Office Market Charts")
    print("=" * 70)

    # Build spatial maps once (cached in aquila.geo module)
    print("\nBuilding spatial submarket maps...")
    tract_map = build_tract_submarket_map()
    bg_map = build_block_group_submarket_map()

    # GROUP A — ACS by Submarket
    chart_a1_population(tract_map)
    chart_a2_occupations(tract_map)
    chart_a3_education(tract_map)
    chart_a4_income(tract_map)

    # GROUP B — LODES Employment
    chart_b1_lodes_snapshot(bg_map)
    chart_b2_lodes_growth(bg_map)

    # GROUP C — QCEW Establishment Trends
    chart_c1_qcew_prof_services()
    chart_c2_qcew_sector_mix()

    # GROUP D — MSA Comparisons
    chart_d1_peer_population()
    chart_d1b_peer_population_2019()
    chart_d2_fred_sectors_indexed()
    chart_d2b_fred_sectors_indexed_2020()

    print("\n" + "=" * 70)
    print("Done. Charts written to:", OUTPUT_DIR)
    print("=" * 70)


if __name__ == '__main__':
    main()
