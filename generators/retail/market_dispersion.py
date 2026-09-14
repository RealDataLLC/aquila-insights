#!/usr/bin/env python3
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402
"""
Retail Market Dispersion + Northeast Deep Dive

Story 7 — "The average hides the market" (2 charts)
  Chart 19 — Submarket vacancy dispersion: min/max band vs the mean
  Chart 20 — Best-to-worst spread, in basis points

Story 8 — "What happened in the Northeast" (2 charts)
  Chart 21 — Northeast vacant SF: new deliveries vs existing stock
  Chart 22 — Lease-up of post-2024 Northeast deliveries

WHY market_tables_retail FOR THE DISPERSION CHARTS. It is the AQUILA
competitive-set aggregate and already carries the vacancy roll-up, so these
charts do not re-derive it from raw stats_retail. Vacancy is unaffected by the
2026 Q1 rent break documented in AquilaResearch/README.md (R2) -- that break is
confined to the rent columns, and nothing here plots rent. If you add a rent
series to this module, chain it off same_store_rent the way
AquilaResearch/reports/retail_data_loader.same_store_index() does; do NOT plot
the raw weighted average across the 2026 Q1 seam.

Usage:
    PYTHONUTF8=1 python -m generators.retail.market_dispersion
"""

import re
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dotenv import load_dotenv

from aquila.brand import AQUILA_FONT, NAVY, GLASS_BLUE, CONCRETE, COPPER, SIGNAL
from aquila.charts import write_chart_html
from aquila.connectors.supabase import get_supabase_client

load_dotenv('aquila_graph.env')

OUTPUT_DIR = 'charts/retail'

# Vacancy data is clean through here. The rent columns are NOT (see module
# docstring); bump this as new quarters land.
END_QUARTER = '2026 Q2'
START_QUARTER = '2023 Q1'

# Submarkets below this are too small for a vacancy rate to mean much -- a
# single 40k box moves them 150bps and they would dominate the min/max band
# for reasons that have nothing to do with the market.
MIN_SUBMARKET_RBA = 2_000_000

# The Northeast decomposition splits buildings against this baseline: anything
# with no RBA in this quarter but RBA later is a "delivery".
NE_BASELINE = '2024 Q1'

# The submarket held out of the dispersion band. It is the finding, not a
# convenience: it accounts for the whole of the market's apparent widening.
OUTLIER = 'Northeast'


SOURCE = ('Source: CoStar via AQUILA market data. Submarket figures are the AQUILA competitive set. Chart: AQUILA Commercial.')


# -- Helpers -------------------------------------------------------------------

def _quarter_sort_key(q_str):
    """Convert '2025 Q4' -> sortable float 2025.4"""
    m = re.match(r'(\d{4})\s*[Qq](\d)', str(q_str))
    return int(m.group(1)) + int(m.group(2)) / 10 if m else 0


def _shared_layout(title_text, y_title, height=580, subtitle=None, source=None):
    """Title centred per brand; subtitle left-aligned and legend below the plot.

    Both of those placements are deliberate. add_aquila_logo() parks the
    watermark in the TOP-RIGHT margin at y=1.02, so a centred subtitle long
    enough to be useful runs underneath it; left-aligning keeps the two apart.
    The legend sits below the x-axis because these charts direct-label their
    final points in the right margin, which is exactly where a default legend
    would land.
    """
    annotations = []
    if subtitle:
        # y=1.075 (not 1.045) clears the logo, whose bottom sits at y=1.02.
        # Keep each line under ~55 characters: the logo's left edge is around
        # x=0.88 and a longer line runs underneath it and then off the figure.
        annotations.append(dict(
            text=subtitle, xref='paper', yref='paper', x=0, xanchor='left', y=1.075, yanchor='bottom',
            showarrow=False, align='left', font=dict(family=AQUILA_FONT, size=12, color=CONCRETE)))
    if source:
        # Below the legend and the rotated tick labels; margin sized to fit.
        annotations.append(dict(
            text=source, xref='paper', yref='paper', x=0, xanchor='left', y=-0.36, yanchor='top',
            showarrow=False, align='left', font=dict(family=AQUILA_FONT, size=10, color=CONCRETE)))

    return dict(
        title=dict(text=title_text, font=dict(family=AQUILA_FONT, size=18, color=NAVY),
                   x=0.5, xanchor='center', y=0.965, yanchor='top'),
        annotations=annotations,
        xaxis=dict(title='', tickfont=dict(family=AQUILA_FONT, size=11, color=NAVY), showgrid=False,
                   linecolor='#E8E8E8', tickangle=-45),
        yaxis=dict(title=y_title, title_font=dict(family=AQUILA_FONT, size=12, color=NAVY),
                   tickfont=dict(family=AQUILA_FONT, size=11, color=NAVY), gridcolor='#E8E8E8', zeroline=False),
        legend=dict(font=dict(family=AQUILA_FONT, size=11, color=NAVY), bgcolor='rgba(0,0,0,0)',
                    orientation='h', yanchor='top', y=-0.20, x=0.5, xanchor='center'),
        plot_bgcolor='white', paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, color=NAVY),
        height=height, margin=dict(l=75, r=120, t=125, b=155),
        hovermode='x unified',
    )


def _fetch_all(supabase, table, select_cols='*', filters=None):
    """Paginate through a Supabase table in 1000-row chunks."""
    all_rows, offset, chunk = [], 0, 1000
    while True:
        query = supabase.table(table).select(select_cols)
        if filters:
            for method, args in filters:
                query = getattr(query, method)(*args)
        rows = query.range(offset, offset + chunk - 1).execute().data
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < chunk:
            break
        offset += chunk
    return pd.DataFrame(all_rows)


def _end_label(q):
    """'2026 Q2' -> 'Q2 2026', for subtitles."""
    year, quarter = q.split()
    return f"{quarter} {year}"


# -- Data Loading --------------------------------------------------------------

def load_market_tables(supabase):
    """Comp-set submarket aggregates from the materialized view."""
    print("Loading market_tables_retail...")
    df = _fetch_all(supabase, 'market_tables_retail',
                    'submarket_name,property_type,quarter,net_rentable_area,'
                    'vacant_available_sf_direct,vacant_available_sf_sublet')
    for col in ['net_rentable_area', 'vacant_available_sf_direct', 'vacant_available_sf_sublet']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['_sort'] = df['quarter'].apply(_quarter_sort_key)
    print(f"  [OK] {len(df)} rows")
    return df


def submarket_vacancy(df_mt):
    """Roll the two property types up to one vacancy rate per submarket-quarter.

    Summed, not averaged: Shopping Center and Freestanding are different-sized
    populations, so averaging their two rates would weight a 200k SF strip the
    same as 3M SF of centers.
    """
    df = df_mt[(df_mt['submarket_name'] != 'Regional')
               & (df_mt['_sort'] >= _quarter_sort_key(START_QUARTER))
               & (df_mt['_sort'] <= _quarter_sort_key(END_QUARTER))].copy()

    grp = df.groupby(['submarket_name', 'quarter', '_sort'], as_index=False).apply(
        lambda d: pd.Series({
            'rba': d['net_rentable_area'].sum(),
            'vac_sf': d['vacant_available_sf_direct'].fillna(0).sum()
                      + d['vacant_available_sf_sublet'].fillna(0).sum(),
        }), include_groups=False
    ).reset_index(drop=True)
    grp['vacancy'] = np.where(grp['rba'] > 0, grp['vac_sf'] / grp['rba'], np.nan)

    latest = grp[grp['quarter'] == END_QUARTER].set_index('submarket_name')['rba']
    keep = latest[latest > MIN_SUBMARKET_RBA].index
    grp = grp[grp['submarket_name'].isin(keep)]
    print(f"  [OK] {len(keep)} submarkets above {MIN_SUBMARKET_RBA:,} SF")
    return grp.sort_values('_sort')


def load_northeast(supabase):
    """Property-level Northeast panel, for the decomposition charts."""
    print("Loading inventory_retail (Northeast)...")
    inv = _fetch_all(supabase, 'inventory_retail',
                     'costar_property_id,property_name,aquila_submarket,costar_submarket_name,year_built')
    inv['submarket'] = inv['aquila_submarket'].fillna(inv['costar_submarket_name'])
    ne_ids = inv[inv['submarket'] == 'Northeast']['costar_property_id'].tolist()
    print(f"  [OK] {len(ne_ids)} Northeast properties")

    print("Loading stats_retail (Northeast, Existing)...")
    st = _fetch_all(supabase, 'stats_retail',
                    'costar_property_id,quarter,rentable_building_area,'
                    'vacant_available_sf_direct,vacant_available_sf_sublet',
                    filters=[('eq', ('building_status', 'Existing')),
                             ('gte', ('quarter', NE_BASELINE)),
                             ('in_', ('costar_property_id', ne_ids))])
    for col in ['rentable_building_area', 'vacant_available_sf_direct', 'vacant_available_sf_sublet']:
        st[col] = pd.to_numeric(st[col], errors='coerce')
    st['vac'] = st['vacant_available_sf_direct'].fillna(0) + st['vacant_available_sf_sublet'].fillna(0)
    st['_sort'] = st['quarter'].apply(_quarter_sort_key)
    st = st[st['_sort'] <= _quarter_sort_key(END_QUARTER)]
    print(f"  [OK] {len(st)} stats rows")
    return st


# -- Story 7: Dispersion -------------------------------------------------------

def _spread_stats(grp, exclude_northeast):
    """Per-quarter mean/min/max of submarket vacancy, optionally ex-Northeast."""
    d = grp[grp['submarket_name'] != OUTLIER] if exclude_northeast else grp
    stats = d.groupby(['quarter', '_sort'], as_index=False)['vacancy'].agg(['mean', 'min', 'max'])
    stats = stats.reset_index().sort_values('_sort')
    stats['spread_bps'] = (stats['max'] - stats['min']) * 10000
    return stats


def chart_dispersion_band(grp):
    """Chart 19: Northeast against the range of every other submarket.

    The band EXCLUDES Northeast on purpose. Include it and Northeast simply is
    the maximum from 2025 on, so the band's ceiling and the Northeast line are
    the same line -- the chart then reads as a filled region rather than as one
    submarket leaving the pack, which is the actual finding.
    """
    stats = _spread_stats(grp, exclude_northeast=True)
    ne = grp[grp['submarket_name'] == OUTLIER].sort_values('_sort')

    fig = go.Figure()
    # Band first so the lines draw on top of it.
    fig.add_trace(go.Scatter(x=stats['quarter'], y=stats['max'], mode='lines', name='_band_top',
                             line=dict(width=0), hoverinfo='skip', showlegend=False))
    n_other = grp.loc[grp['submarket_name'] != OUTLIER, 'submarket_name'].nunique()
    fig.add_trace(go.Scatter(x=stats['quarter'], y=stats['min'], mode='lines',
                             name=f'Range of the other {n_other} submarkets',
                             line=dict(width=0), fill='tonexty', fillcolor='rgba(194,218,241,0.55)',
                             hoverinfo='skip'))
    fig.add_trace(go.Scatter(x=stats['quarter'], y=stats['mean'], mode='lines',
                             name='Average, excluding Northeast', line=dict(color=NAVY, width=2),
                             hovertemplate='%{y:.2%}<extra>Average ex-Northeast</extra>'))
    fig.add_trace(go.Scatter(x=ne['quarter'], y=ne['vacancy'], mode='lines', name=OUTLIER,
                             line=dict(color=SIGNAL, width=2),
                             hovertemplate='%{y:.2%}<extra>Northeast</extra>'))

    first, last = stats.iloc[0], stats.iloc[-1]
    subtitle = (f"Strip out the Northeast and vacancy FELL {first['mean']:.2%} → {last['mean']:.2%}<br>"
                f"Northeast went {ne['vacancy'].iloc[0]:.2%} → {ne['vacancy'].iloc[-1]:.2%}, "
                f"{(ne['vacancy'].iloc[-1] - last['max']) * 10000:,.0f} bps clear of the next-worst")
    layout = _shared_layout('Austin Retail Tightened — Except in One Submarket', 'Vacancy Rate',
                            subtitle=subtitle, source=SOURCE)
    layout['yaxis']['tickformat'] = '.0%'
    fig.update_layout(**layout)

    # After update_layout -- _shared_layout sets `annotations`, which would
    # replace anything added before it.
    for series, color, label in ((stats['mean'], NAVY, 'Average'), (ne['vacancy'], SIGNAL, OUTLIER)):
        fig.add_annotation(x=END_QUARTER, y=series.iloc[-1], text=f"  {label} {series.iloc[-1]:.1%}",
                           showarrow=False, xanchor='left', font=dict(family=AQUILA_FONT, size=11, color=color))
    return fig


def chart_spread(grp):
    """Chart 20: the spread with and without Northeast, which is the whole point.

    Plotted together because the pair IS the argument: the all-submarket spread
    nearly tripled, and the same spread without one 3.6M SF submarket did not
    widen at all.
    """
    all_sub = _spread_stats(grp, exclude_northeast=False)
    ex_ne = _spread_stats(grp, exclude_northeast=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=all_sub['quarter'], y=all_sub['spread_bps'], mode='lines',
                             name='All submarkets', line=dict(color=NAVY, width=2),
                             hovertemplate='%{y:,.0f} bps<extra>All submarkets</extra>'))
    # Dashed: the two series are IDENTICAL until 2024 Q4 (Northeast is not the
    # extreme before then), so a solid copper line would simply hide the navy
    # one and make the divergence look like the navy series starting late.
    fig.add_trace(go.Scatter(x=ex_ne['quarter'], y=ex_ne['spread_bps'], mode='lines',
                             name='Excluding Northeast', line=dict(color=COPPER, width=2, dash='dot'),
                             hovertemplate='%{y:,.0f} bps<extra>Excluding Northeast</extra>'))

    a, e = all_sub.iloc[-1], ex_ne.iloc[-1]
    subtitle = (f"All submarkets: {all_sub['spread_bps'].iloc[0]:,.0f} → {a['spread_bps']:,.0f} bps<br>"
                f"Without the Northeast: {ex_ne['spread_bps'].iloc[0]:,.0f} → {e['spread_bps']:,.0f} bps")
    layout = _shared_layout('Austin\'s Widening Vacancy Gap Is One Submarket', 'Spread (basis points)',
                            subtitle=subtitle, source=SOURCE)
    layout['yaxis']['tickformat'] = ','
    layout['yaxis']['rangemode'] = 'tozero'
    fig.update_layout(**layout)

    for row, color, label in ((a, NAVY, 'All'), (e, COPPER, 'Excl. NE')):
        fig.add_annotation(x=END_QUARTER, y=row['spread_bps'], text=f"  {label} {row['spread_bps']:,.0f}",
                           showarrow=False, xanchor='left', font=dict(family=AQUILA_FONT, size=11, color=color))
    return fig


# -- Story 8: Northeast --------------------------------------------------------

def _ne_decompose(st):
    """Split each quarter's Northeast vacant SF into new deliveries vs existing stock."""
    base = st[st['quarter'] == NE_BASELINE].set_index('costar_property_id')
    existed = set(base[base['rentable_building_area'].fillna(0) > 0].index)
    st = st.copy()
    st['cohort'] = np.where(st['costar_property_id'].isin(existed),
                            f'Stock existing at {_end_label(NE_BASELINE)}',
                            f'Delivered since {_end_label(NE_BASELINE)}')
    out = st.groupby(['quarter', '_sort', 'cohort'], as_index=False).agg(
        vac=('vac', 'sum'), rba=('rentable_building_area', 'sum'))
    return out.sort_values('_sort'), existed


def chart_ne_decomposition(st):
    """Chart 21: stacked vacant SF by cohort."""
    dec, _ = _ne_decompose(st)
    old = f'Stock existing at {_end_label(NE_BASELINE)}'
    new = f'Delivered since {_end_label(NE_BASELINE)}'
    quarters = dec.drop_duplicates('quarter').sort_values('_sort')['quarter']

    fig = go.Figure()
    for cohort, color in ((old, NAVY), (new, COPPER)):
        s = dec[dec['cohort'] == cohort].set_index('quarter').reindex(quarters).fillna(0)
        fig.add_trace(go.Bar(x=quarters, y=s['vac'], name=cohort, marker_color=color,
                             marker_line=dict(color='white', width=2), width=0.72,
                             hovertemplate='%{y:,.0f} SF<extra>' + cohort + '</extra>'))

    total = dec.groupby('quarter', as_index=False)['vac'].sum().set_index('quarter').reindex(quarters)
    start, end = total['vac'].iloc[0], total['vac'].iloc[-1]
    subtitle = (f"Vacant SF {start:,.0f} → {end:,.0f}; roughly half of the increase is space that was "
                f"built after {_end_label(NE_BASELINE)} and has not leased")
    layout = _shared_layout('Northeast Retail Vacancy: Where the Empty Space Came From',
                            'Vacant SF', subtitle=subtitle, source=SOURCE)
    layout['barmode'] = 'stack'
    layout['yaxis']['tickformat'] = ','
    fig.update_layout(**layout)
    return fig


def chart_ne_leaseup(st):
    """Chart 22: occupancy of the post-baseline deliveries as they stack up."""
    dec, existed = _ne_decompose(st)
    new = f'Delivered since {_end_label(NE_BASELINE)}'
    s = dec[(dec['cohort'] == new) & (dec['rba'] > 0)].copy()
    s['occupancy'] = 1 - s['vac'] / s['rba']

    counts = (st[~st['costar_property_id'].isin(existed) & (st['rentable_building_area'].fillna(0) > 0)]
              .groupby('quarter')['costar_property_id'].nunique())
    s['n'] = s['quarter'].map(counts).fillna(0).astype(int)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s['quarter'], y=s['occupancy'], mode='lines+markers',
                             name='Occupancy of new deliveries',
                             line=dict(color=COPPER, width=2), marker=dict(size=8, color=COPPER,
                             line=dict(color='white', width=2)),
                             customdata=np.stack([s['n'], s['rba']], axis=-1),
                             hovertemplate='%{y:.1%} occupied<br>%{customdata[0]} buildings · '
                                           '%{customdata[1]:,.0f} SF<extra></extra>',
                             showlegend=False))
    last, first = s.iloc[-1], s.iloc[0]
    # The cohort grows as buildings deliver, so the first few quarters rest on a
    # handful of buildings. Say so on the chart -- otherwise the early swing
    # reads as a collapse in leasing rather than the panel filling out.
    subtitle = (f"{int(last['n'])} buildings totalling {last['rba']:,.0f} SF delivered since "
                f"{_end_label(NE_BASELINE)}; lease-up has stalled near half full<br>"
                f"<span style='font-size:11px'>Cohort grows from {int(first['n'])} building"
                f"{'s' if first['n'] != 1 else ''} in {_end_label(first['quarter'])} to "
                f"{int(last['n'])}; treat the first few quarters as a thin panel</span>")
    layout = _shared_layout('Northeast\'s New Retail Is Half Empty', 'Occupancy', subtitle=subtitle, source=SOURCE)
    layout['yaxis']['tickformat'] = '.0%'
    layout['yaxis']['range'] = [0, 1]
    fig.update_layout(**layout)

    fig.add_annotation(x=last['quarter'], y=last['occupancy'], text=f"  {last['occupancy']:.0%}",
                       showarrow=False, xanchor='left',
                       font=dict(family=AQUILA_FONT, size=12, color=COPPER))
    return fig


# -- Main ----------------------------------------------------------------------

def main():
    supabase = get_supabase_client(use_service_role=True)

    df_mt = load_market_tables(supabase)
    grp = submarket_vacancy(df_mt)
    st_ne = load_northeast(supabase)

    charts = [
        (chart_dispersion_band(grp), 'retail_vacancy_dispersion.html'),
        (chart_spread(grp), 'retail_vacancy_spread.html'),
        (chart_ne_decomposition(st_ne), 'retail_northeast_vacancy_sources.html'),
        (chart_ne_leaseup(st_ne), 'retail_northeast_leaseup.html'),
    ]
    print()
    for fig, name in charts:
        path = f'{OUTPUT_DIR}/{name}'
        write_chart_html(fig, path)
        print(f"  [OK] {path}")
    print(f"\n{len(charts)} charts written to {OUTPUT_DIR}/")


if __name__ == '__main__':
    main()
