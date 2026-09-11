#!/usr/bin/env python3
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402
"""
Georgetown Retail Performance vs Rest of Austin
Generates 5 HTML charts from Supabase inventory_retail and stats_retail tables.

Focus: new supply (net deliveries) and net absorption.

  Chart 1 - Georgetown net deliveries vs net absorption, annual
  Chart 2 - Georgetown share of metro supply and absorption, annual
  Chart 3 - Indexed inventory and occupied SF growth (2018 Q4 = 100)
  Chart 4 - Inventory growth vs absorption capture by submarket (scatter)
  Chart 5 - Pipeline depth: years of absorption to fill the pipeline

NOTE: stats_retail is large (~740k rows). Supabase/PostgREST range pagination
without a total ordering returns rows in an unstable order across pages, which
silently repeats some rows and drops others. _fetch_all() therefore orders by a
unique key and verifies the fetched row count against an exact server-side
count. Panel coverage expands sharply at 2018 Q3, so every series starts at
2018 Q4.

Usage:
    python -m generators.retail.georgetown_performance
"""

import re
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from aquila.brand import AQUILA_FONT, NAVY, GLASS_BLUE, CONCRETE, COPPER, BRASS, SIGNAL
from aquila.charts import write_chart_html
from aquila.connectors.supabase import get_supabase_client

OUTPUT_DIR = 'charts/retail'
FOCUS = 'Georgetown'
BASE_Q = 20184   # 2018 Q4 - first quarter of full panel coverage
END_Q = 20262    # 2026 Q2 - latest quarter (partial year)


# -- Helpers -------------------------------------------------------------------

def _sort_key(q):
    """'2025 Q4' -> 20254 (year * 10 + quarter)."""
    m = re.match(r'(\d{4})\s*[Qq](\d)', str(q))
    return int(m.group(1)) * 10 + int(m.group(2)) if m else np.nan


def _fetch_all(supabase, table, cols='*', filters=None, order_by=None, chunk=1000):
    """Paginate a Supabase table in 1000-row chunks.

    ``order_by`` must be a set of columns that uniquely identifies a row.
    Without a total ordering, PostgreSQL is free to return rows in a different
    order on every page, which silently repeats some rows and drops others --
    the paged result then looks like it contains duplicates. Always pass a
    unique key here, and verify the row count against the server.
    """
    rows, offset = [], 0
    while True:
        q = supabase.table(table).select(cols)
        for method, args in (filters or []):
            q = getattr(q, method)(*args)
        for col in (order_by or []):
            q = q.order(col)
        data = q.range(offset, offset + chunk - 1).execute().data
        if not data:
            break
        rows.extend(data)
        if len(data) < chunk:
            break
        offset += chunk

    df = pd.DataFrame(rows)
    # Cross-check against an exact server-side count so a short read is loud.
    cq = supabase.table(table).select(cols.split(',')[0], count='exact')
    for method, args in (filters or []):
        cq = getattr(cq, method)(*args)
    expected = cq.limit(1).execute().count
    if expected is not None and len(df) != expected:
        raise RuntimeError(f"{table}: fetched {len(df):,} rows but server reports {expected:,}")
    return df


def _layout(title, subtitle, y_title, height=560, **kw):
    text = f"{title}<br><span style='font-size:12px;color:#AAA9A8'>{subtitle}</span>"
    base = dict(
        title=dict(text=text, font=dict(family=AQUILA_FONT, size=18, color=NAVY), x=0.5, xanchor='center'),
        xaxis=dict(title='', tickfont=dict(family=AQUILA_FONT, size=11, color=NAVY),
                   showgrid=False, linecolor='#E8E8E8'),
        yaxis=dict(title=y_title, title_font=dict(family=AQUILA_FONT, size=12, color=NAVY),
                   tickfont=dict(family=AQUILA_FONT, size=11, color=NAVY),
                   gridcolor='#E8E8E8', zeroline=True, zerolinecolor='#AAA9A8'),
        legend=dict(font=dict(family=AQUILA_FONT, size=11, color=NAVY), bgcolor='white',
                    bordercolor='#E8E8E8', borderwidth=1),
        plot_bgcolor='white', paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, color=NAVY),
        height=height, margin=dict(l=80, r=50, t=95, b=70),
    )
    base.update(kw)
    return base


# -- Data Loading --------------------------------------------------------------

def load_data(supabase):
    """Load inventory + stats, de-duplicate, and attach submarket / group labels."""
    print("Loading inventory_retail...")
    df_inv = _fetch_all(supabase, 'inventory_retail',
        'costar_property_id,property_name,city,building_status,costar_submarket_name,'
        'aquila_submarket,year_built,rentable_building_area',
        order_by=['costar_property_id'])
    df_inv['submarket'] = df_inv['aquila_submarket'].fillna(df_inv['costar_submarket_name'])
    df_inv['rba'] = pd.to_numeric(df_inv['rentable_building_area'], errors='coerce')
    print(f"  [OK] {len(df_inv):,} inventory rows")

    print("Loading stats_retail (Existing, 2018+)...")
    df = _fetch_all(supabase, 'stats_retail',
        'costar_property_id,quarter,building_status,rentable_building_area,'
        'vacant_available_sf_direct,vacant_available_sf_sublet',
        filters=[('eq', ('building_status', 'Existing')), ('gte', ('quarter', '2018 Q1'))],
        order_by=['quarter', 'costar_property_id'])
    dupes = df.duplicated(subset=['costar_property_id', 'quarter']).sum()
    if dupes:
        raise RuntimeError(f"stats_retail returned {dupes:,} duplicate (property, quarter) rows")
    print(f"  [OK] {len(df):,} stats rows (row count verified against server)")

    for c in ['rentable_building_area', 'vacant_available_sf_direct', 'vacant_available_sf_sublet']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df['_sort'] = df['quarter'].map(_sort_key)
    df = df[df['_sort'] >= BASE_Q]
    df['vac_sf'] = df['vacant_available_sf_direct'].fillna(0) + df['vacant_available_sf_sublet'].fillna(0)
    df['occ_sf'] = df['rentable_building_area'].fillna(0) - df['vac_sf']

    df = df.merge(df_inv[['costar_property_id', 'submarket']].drop_duplicates('costar_property_id'),
                  on='costar_property_id', how='left')
    df['group'] = np.where(df['submarket'] == FOCUS, FOCUS, 'Rest of Austin')
    return df_inv, df


def _quarterly(df):
    """Collapse to a quarterly time series with net absorption and net deliveries."""
    g = (df.groupby(['_sort', 'quarter'])
           .agg(rba=('rentable_building_area', 'sum'), occ=('occ_sf', 'sum'), vac=('vac_sf', 'sum'))
           .reset_index().sort_values('_sort'))
    g['net_abs'] = g['occ'].diff()
    g['net_new'] = g['rba'].diff()
    g['vac_rate'] = 100 * g['vac'] / g['rba']
    return g


def _annual(g):
    """Q4-over-Q4 annual totals; the final year is year-to-date."""
    g = g.copy()
    g['yr'], g['q'] = g['_sort'] // 10, g['_sort'] % 10
    last_yr, last_q = END_Q // 10, END_Q % 10
    out = []
    for y in range(BASE_Q // 10 + 1, last_yr + 1):
        end_q = 4 if y < last_yr else last_q
        end = g[(g.yr == y) & (g.q == end_q)]
        beg = g[(g.yr == y - 1) & (g.q == 4)]
        if end.empty or beg.empty:
            continue
        label = f"{y} YTD" if y == last_yr and last_q < 4 else str(y)
        out.append(dict(year=y, label=label,
                        net_abs=end.occ.iloc[0] - beg.occ.iloc[0],
                        net_new=end.rba.iloc[0] - beg.rba.iloc[0],
                        vac_rate=end.vac_rate.iloc[0]))
    return pd.DataFrame(out)


# -- Chart 1: Supply vs absorption, annual -------------------------------------

def chart_supply_vs_absorption(ann_gt, latest_q):
    fig = go.Figure()
    fig.add_bar(x=ann_gt['label'], y=ann_gt['net_new'], name='Net New Supply',
                marker_color=NAVY, hovertemplate='%{x}<br>Supply: %{y:,.0f} SF<extra></extra>')
    fig.add_bar(x=ann_gt['label'], y=ann_gt['net_abs'], name='Net Absorption',
                marker_color=GLASS_BLUE, hovertemplate='%{x}<br>Absorption: %{y:,.0f} SF<extra></extra>')
    fig.add_trace(go.Scatter(x=ann_gt['label'], y=ann_gt['vac_rate'], name='Vacancy Rate (right)',
                             mode='lines+markers', yaxis='y2',
                             line=dict(color=COPPER, width=2.5), marker=dict(size=7),
                             hovertemplate='%{x}<br>Vacancy: %{y:.2f}%<extra></extra>'))
    fig.update_layout(**_layout(
        'Georgetown Retail: New Supply vs Net Absorption',
        f'Annual, Q4-over-Q4 | through {latest_q} | CoStar Georgetown submarket (north Williamson County)',
        'Square Feet', barmode='group',
        yaxis2=dict(title='Vacancy Rate', overlaying='y', side='right', ticksuffix='%',
                    showgrid=False, range=[0, max(8, ann_gt['vac_rate'].max() * 1.5)],
                    title_font=dict(family=AQUILA_FONT, size=12, color=COPPER),
                    tickfont=dict(family=AQUILA_FONT, size=11, color=COPPER)),
        hovermode='x unified'))
    fig.update_yaxes(tickformat=',')
    write_chart_html(fig, f'{OUTPUT_DIR}/retail_georgetown_supply_vs_absorption.html')
    print('  [OK] retail_georgetown_supply_vs_absorption.html')


# -- Chart 2: Georgetown share of the metro ------------------------------------

def chart_metro_share(ann_gt, ann_roa, gt_inv_share, latest_q):
    tot_new = ann_gt['net_new'].values + ann_roa['net_new'].values
    tot_abs = ann_gt['net_abs'].values + ann_roa['net_abs'].values
    share_new = np.where(tot_new != 0, 100 * ann_gt['net_new'].values / tot_new, np.nan)
    share_abs = np.where(tot_abs != 0, 100 * ann_gt['net_abs'].values / tot_abs, np.nan)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ann_gt['label'], y=share_new, name='Share of Metro New Supply',
                             mode='lines+markers', line=dict(color=NAVY, width=3), marker=dict(size=9),
                             hovertemplate='%{x}<br>Supply share: %{y:.1f}%<extra></extra>'))
    fig.add_trace(go.Scatter(x=ann_gt['label'], y=share_abs, name='Share of Metro Net Absorption',
                             mode='lines+markers', line=dict(color=GLASS_BLUE, width=3), marker=dict(size=9),
                             hovertemplate='%{x}<br>Absorption share: %{y:.1f}%<extra></extra>'))
    fig.add_hline(y=gt_inv_share, line=dict(color=CONCRETE, width=2, dash='dash'),
                  annotation_text=f'Georgetown = {gt_inv_share:.1f}% of metro retail inventory',
                  annotation_position='top left',
                  annotation_font=dict(family=AQUILA_FONT, size=11, color=CONCRETE))
    fig.update_layout(**_layout(
        'Georgetown Punches Above Its Weight in Retail Supply and Demand',
        f'Georgetown share of Austin metro retail, annual | through {latest_q}',
        'Share of Metro Total', hovermode='x unified'))
    fig.update_yaxes(ticksuffix='%')
    write_chart_html(fig, f'{OUTPUT_DIR}/retail_georgetown_metro_share.html')
    print('  [OK] retail_georgetown_metro_share.html')


# -- Chart 3: Indexed growth ---------------------------------------------------

def chart_indexed_growth(q_gt, q_roa, latest_q):
    fig = go.Figure()
    specs = [
        (q_gt, 'rba', 'Georgetown - Inventory', NAVY, 'solid'),
        (q_gt, 'occ', 'Georgetown - Occupied SF', GLASS_BLUE, 'dot'),
        (q_roa, 'rba', 'Rest of Austin - Inventory', CONCRETE, 'solid'),
        (q_roa, 'occ', 'Rest of Austin - Occupied SF', BRASS, 'dot'),
    ]
    for g, col, name, color, dash in specs:
        base = g[col].iloc[0]
        fig.add_trace(go.Scatter(x=g['quarter'], y=100 * g[col] / base, name=name, mode='lines',
                                 line=dict(color=color, width=3, dash=dash),
                                 hovertemplate='%{x}<br>' + name + ': %{y:.1f}<extra></extra>'))
    fig.update_layout(**_layout(
        'Georgetown Retail Inventory Is Growing Far Faster Than the Rest of Austin',
        f'Indexed to 2018 Q4 = 100 | Existing retail stock | through {latest_q}',
        'Index (2018 Q4 = 100)', hovermode='x unified',
        xaxis=dict(title='', tickfont=dict(family=AQUILA_FONT, size=10, color=NAVY),
                   showgrid=False, linecolor='#E8E8E8', tickangle=-45, dtick=4)))
    write_chart_html(fig, f'{OUTPUT_DIR}/retail_georgetown_indexed_growth.html')
    print('  [OK] retail_georgetown_indexed_growth.html')


# -- Chart 4: Growth vs capture by submarket -----------------------------------

def chart_growth_vs_capture(sub, latest_q):
    d = sub[sub['net_new'] > 50000].copy()
    colors = [NAVY if s == FOCUS else CONCRETE for s in d['submarket']]
    sizes = np.sqrt(d['rba_end'] / d['rba_end'].max()) * 55 + 10

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=d['inv_growth_pct'], y=d['capture_pct'], mode='markers+text',
        text=d['submarket'], textposition='top center',
        textfont=dict(family=AQUILA_FONT, size=10, color=NAVY),
        marker=dict(size=sizes, color=colors, opacity=0.85, line=dict(color='white', width=1.5)),
        customdata=np.column_stack([d['net_new'], d['net_abs'], d['rba_end'], d['vac_end']]),
        hovertemplate=('<b>%{text}</b><br>Inventory growth: %{x:.1f}%<br>'
                       'Absorption capture: %{y:.0f}%<br>New supply: %{customdata[0]:,.0f} SF<br>'
                       'Net absorption: %{customdata[1]:,.0f} SF<br>'
                       'Inventory: %{customdata[2]:,.0f} SF<br>'
                       'Vacancy: %{customdata[3]:.1f}%<extra></extra>')))
    fig.add_hline(y=100, line=dict(color=CONCRETE, width=1.5, dash='dash'),
                  annotation_text='Demand exactly matches new supply', annotation_position='bottom right',
                  annotation_font=dict(family=AQUILA_FONT, size=10, color=CONCRETE))
    fig.update_layout(**_layout(
        'Georgetown Absorbed Almost Everything It Built',
        f'Submarkets adding >50k SF since 2018 Q4 | bubble size = current inventory | through {latest_q}',
        'Absorption Capture (net absorption / new supply)',
        height=620,
        xaxis=dict(title='Inventory Growth Since 2018 Q4', ticksuffix='%',
                   title_font=dict(family=AQUILA_FONT, size=12, color=NAVY),
                   tickfont=dict(family=AQUILA_FONT, size=11, color=NAVY),
                   showgrid=True, gridcolor='#E8E8E8', linecolor='#E8E8E8'),
        showlegend=False))
    fig.update_yaxes(ticksuffix='%')
    write_chart_html(fig, f'{OUTPUT_DIR}/retail_georgetown_growth_vs_capture.html')
    print('  [OK] retail_georgetown_growth_vs_capture.html')


# -- Chart 5: Pipeline depth ---------------------------------------------------

def chart_pipeline_depth(pipe, latest_q):
    d = pipe.sort_values('years_of_supply', ascending=True)
    colors = [SIGNAL if s == FOCUS else (NAVY if y >= 3 else CONCRETE)
              for s, y in zip(d['submarket'], d['years_of_supply'])]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=d['years_of_supply'], y=d['submarket'], orientation='h', marker_color=colors,
        text=[f'{v:.1f} yrs' for v in d['years_of_supply']], textposition='outside',
        textfont=dict(family=AQUILA_FONT, size=11, color=NAVY),
        customdata=np.column_stack([d['pipeline_sf'], d['abs_run_rate'], d['pipeline_pct']]),
        hovertemplate=('<b>%{y}</b><br>Years of supply: %{x:.1f}<br>'
                       'Pipeline: %{customdata[0]:,.0f} SF<br>'
                       'Absorption run-rate: %{customdata[1]:,.0f} SF/yr<br>'
                       'Pipeline as pct of inventory: %{customdata[2]:.1f}%<extra></extra>')))
    fig.update_layout(**_layout(
        "Georgetown Carries the Metro's Deepest Retail Pipeline",
        f'Under construction + proposed / trailing absorption run-rate | as of {latest_q}',
        '', height=620,
        xaxis=dict(title='Years of Absorption to Fill the Pipeline',
                   title_font=dict(family=AQUILA_FONT, size=12, color=NAVY),
                   tickfont=dict(family=AQUILA_FONT, size=11, color=NAVY),
                   showgrid=True, gridcolor='#E8E8E8', linecolor='#E8E8E8'),
        yaxis=dict(title='', tickfont=dict(family=AQUILA_FONT, size=11, color=NAVY),
                   showgrid=False),
        showlegend=False))
    write_chart_html(fig, f'{OUTPUT_DIR}/retail_georgetown_pipeline_depth.html')
    print('  [OK] retail_georgetown_pipeline_depth.html')


# -- Main ----------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    supabase = get_supabase_client(use_service_role=True)
    df_inv, df = load_data(supabase)

    latest_q = df.loc[df['_sort'] == df['_sort'].max(), 'quarter'].iloc[0]

    q_gt = _quarterly(df[df['group'] == FOCUS])
    q_roa = _quarterly(df[df['group'] == 'Rest of Austin'])
    ann_gt, ann_roa = _annual(q_gt), _annual(q_roa)

    # Georgetown's static share of metro inventory (the benchmark line in chart 2)
    end = df[df['_sort'] == END_Q]
    gt_inv_share = (100 * end[end['group'] == FOCUS]['rentable_building_area'].sum()
                    / end['rentable_building_area'].sum())

    # Per-submarket supply / absorption since the base quarter
    rows = []
    for smk, d in df.groupby('submarket'):
        g = _quarterly(d)
        beg, fin = g[g['_sort'] == BASE_Q], g[g['_sort'] == END_Q]
        if beg.empty or fin.empty:
            continue
        beg, fin = beg.iloc[0], fin.iloc[0]
        net_new = fin.rba - beg.rba
        rows.append(dict(submarket=smk, rba_end=fin.rba, net_new=net_new, net_abs=fin.occ - beg.occ,
                         inv_growth_pct=100 * net_new / beg.rba,
                         capture_pct=100 * (fin.occ - beg.occ) / net_new if net_new else np.nan,
                         vac_end=fin.vac_rate))
    sub = pd.DataFrame(rows)

    # Pipeline depth: UC + proposed vs trailing absorption run-rate (2023 Q4 -> 2026 Q2 = 2.5 yrs)
    pipe_sf = (df_inv[df_inv['building_status'].isin(['Under Construction', 'Proposed'])]
               .groupby('submarket')['rba'].sum())
    depth = []
    for smk, d in df.groupby('submarket'):
        g = _quarterly(d)
        start, fin = g[g['_sort'] == 20234], g[g['_sort'] == END_Q]
        if start.empty or fin.empty or smk not in pipe_sf.index:
            continue
        run_rate = (fin.occ.iloc[0] - start.occ.iloc[0]) / 2.5
        if run_rate <= 0:
            continue
        depth.append(dict(submarket=smk, pipeline_sf=pipe_sf[smk], abs_run_rate=run_rate,
                          years_of_supply=pipe_sf[smk] / run_rate,
                          pipeline_pct=100 * pipe_sf[smk] / fin.rba.iloc[0]))
    pipe = pd.DataFrame(depth)

    print('\nGenerating charts...')
    chart_supply_vs_absorption(ann_gt, latest_q)
    chart_metro_share(ann_gt, ann_roa, gt_inv_share, latest_q)
    chart_indexed_growth(q_gt, q_roa, latest_q)
    chart_growth_vs_capture(sub, latest_q)
    chart_pipeline_depth(pipe, latest_q)
    print(f'\n[DONE] 5 charts written to {OUTPUT_DIR}/')


if __name__ == '__main__':
    main()
