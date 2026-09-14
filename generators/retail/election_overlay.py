#!/usr/bin/env python3
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402
"""
Retail Absorption vs the Election Calendar

Story 9 — "What actually moves Austin CRE" (2 charts)
  Chart 23 — Quarterly net absorption, with post-election quarters marked
  Chart 24 — Post-election quarters vs the rest: mean says one thing, median says the other

THE POINT IS A NULL RESULT. Post-election quarters land 27th, 20th, 2nd and
23rd out of 31. There is no election effect visible in Austin retail
absorption, and with four observations -- one of them 2021 Q1, which is
entirely COVID -- there could not be a credible one either way. Chart 24
exists to show that the SAME four observations support "+7% higher" (mean) or
"-21% lower" (median) depending on which statistic you quote. That is the
methodological argument; do not restate it as a finding about elections.

WHY THE WINDOW ENDS AT 2025 Q4. Absorption here is derived from quarter-over-
quarter change in occupied SF across the Existing panel. That is sound until
2026 Q1, where AquilaResearch's owner-occupied revert (README R1) moves ~635
buildings out of `Existing` -- buildings leaving the panel read as a false
-858k SF of "absorption" against a true comp-set figure near -256k. The seam
is excluded rather than patched. Cross-checked against
market_tables_retail.total_net_absorption over the overlapping clean period:
2023 Q1 reads +703k here vs +635k comp-set, 2025 Q1 +239k vs +253k -- same
series, different panel, no divergence in the story.

market_tables_retail is NOT used as the source because it begins at 2019 Q1
(its first quarter carries no absorption), which would drop the 2018 midterm
and leave only three elections.

Usage:
    PYTHONUTF8=1 python -m generators.retail.election_overlay
"""

import re
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dotenv import load_dotenv

from aquila.brand import AQUILA_FONT, NAVY, CONCRETE, COPPER
from aquila.charts import write_chart_html
from aquila.connectors.supabase import get_supabase_client

load_dotenv('aquila_graph.env')

OUTPUT_DIR = 'charts/retail'

START_QUARTER = '2018 Q2'   # first quarter with a prior quarter to diff against
END_QUARTER = '2025 Q4'     # see module docstring -- 2026 Q1 is the R1 seam

# US general elections are held in November, inside Q4. The first quarter in
# which a new government could plausibly influence a leasing decision is the
# following Q1, which is what gets marked.
POST_ELECTION = {
    '2019 Q1': '2018 midterm',
    '2021 Q1': '2020 presidential',
    '2023 Q1': '2022 midterm',
    '2025 Q1': '2024 presidential',
}


# -- Helpers -------------------------------------------------------------------

def _quarter_sort_key(q_str):
    """Convert '2025 Q4' -> sortable float 2025.4"""
    m = re.match(r'(\d{4})\s*[Qq](\d)', str(q_str))
    return int(m.group(1)) + int(m.group(2)) / 10 if m else 0


def _shared_layout(title_text, y_title, height=580, subtitle=None):
    """Title centred per brand; subtitle left-aligned, legend below the plot.

    add_aquila_logo() parks the watermark in the top-right margin at y=1.02, so
    the subtitle sits at y=1.075 and is left-aligned to stay clear of it. Keep
    each subtitle line under ~55 characters or it runs under the logo.
    """
    annotations = []
    if subtitle:
        annotations.append(dict(
            text=subtitle, xref='paper', yref='paper', x=0, xanchor='left', y=1.075, yanchor='bottom',
            showarrow=False, align='left', font=dict(family=AQUILA_FONT, size=12, color=CONCRETE)))

    return dict(
        title=dict(text=title_text, font=dict(family=AQUILA_FONT, size=18, color=NAVY),
                   x=0.5, xanchor='center', y=0.965, yanchor='top'),
        annotations=annotations,
        xaxis=dict(title='', tickfont=dict(family=AQUILA_FONT, size=10, color=NAVY), showgrid=False,
                   linecolor='#E8E8E8', tickangle=-45),
        yaxis=dict(title=y_title, title_font=dict(family=AQUILA_FONT, size=12, color=NAVY),
                   tickfont=dict(family=AQUILA_FONT, size=11, color=NAVY), gridcolor='#E8E8E8',
                   zeroline=True, zerolinecolor='#AAA9A8', zerolinewidth=1),
        legend=dict(font=dict(family=AQUILA_FONT, size=11, color=NAVY), bgcolor='rgba(0,0,0,0)',
                    orientation='h', yanchor='top', y=-0.22, x=0.5, xanchor='center'),
        plot_bgcolor='white', paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, color=NAVY),
        height=height, margin=dict(l=85, r=60, t=125, b=115),
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


# -- Data Loading --------------------------------------------------------------

def load_absorption(supabase):
    """Citywide quarterly net absorption from the Existing panel."""
    print("Loading stats_retail (Existing, 2018+)...")
    df = _fetch_all(supabase, 'stats_retail',
                    'costar_property_id,quarter,rentable_building_area,'
                    'vacant_available_sf_direct,vacant_available_sf_sublet',
                    filters=[('eq', ('building_status', 'Existing')),
                             ('gte', ('quarter', '2018 Q1'))])
    for col in ['rentable_building_area', 'vacant_available_sf_direct', 'vacant_available_sf_sublet']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['_sort'] = df['quarter'].apply(_quarter_sort_key)
    print(f"  [OK] {len(df)} rows")

    grp = df.groupby(['quarter', '_sort'], as_index=False).apply(
        lambda d: pd.Series({
            'occupied_sf': d['rentable_building_area'].sum()
                           - d['vacant_available_sf_direct'].fillna(0).sum()
                           - d['vacant_available_sf_sublet'].fillna(0).sum(),
        }), include_groups=False
    ).reset_index(drop=True).sort_values('_sort')
    grp['net_abs'] = grp['occupied_sf'].diff()

    grp = grp[(grp['_sort'] >= _quarter_sort_key(START_QUARTER))
              & (grp['_sort'] <= _quarter_sort_key(END_QUARTER))].dropna(subset=['net_abs'])
    grp['is_post'] = grp['quarter'].isin(POST_ELECTION)
    grp['rank'] = grp['net_abs'].rank(ascending=False).astype(int)
    print(f"  [OK] {len(grp)} quarters, {grp['quarter'].iloc[0]} -> {grp['quarter'].iloc[-1]}")
    return grp.reset_index(drop=True)


# -- Charts --------------------------------------------------------------------

def chart_election_overlay(df):
    """Chart 23: quarterly absorption with post-election quarters called out."""
    n = len(df)
    fig = go.Figure()
    for is_post, color, label in ((False, NAVY, 'All other quarters'),
                                  (True, COPPER, 'First quarter after a general election')):
        s = df[df['is_post'] == is_post]
        fig.add_trace(go.Bar(x=s['quarter'], y=s['net_abs'], name=label, marker_color=color,
                             marker_line_width=0, width=0.72,
                             customdata=s['rank'],
                             hovertemplate='%{y:+,.0f} SF<br>rank %{customdata} of ' + str(n)
                                           + '<extra></extra>'))

    layout = _shared_layout(
        'Austin Retail Absorption Does Not Track the Election Calendar',
        'Net absorption (SF)',
        subtitle=(f"Post-election quarters rank "
                  f"{', '.join(str(r) for r in df[df['is_post']]['rank'])} of {n}<br>"
                  f"Two midterms, both divided government: 2019 Q1 ranked "
                  f"{df.loc[df['quarter'] == '2019 Q1', 'rank'].iloc[0]}, 2023 Q1 ranked "
                  f"{df.loc[df['quarter'] == '2023 Q1', 'rank'].iloc[0]}"))
    layout['yaxis']['tickformat'] = ','
    layout['barmode'] = 'overlay'
    # Splitting into two traces makes Plotly order the x categories per trace,
    # which parks the four highlighted bars at the end of the axis. Pin the
    # chronological order explicitly.
    layout['xaxis']['categoryorder'] = 'array'
    layout['xaxis']['categoryarray'] = list(df['quarter'])
    fig.update_layout(**layout)

    # Rank labels on the four marked bars -- identity is not left to colour.
    for _, row in df[df['is_post']].iterrows():
        fig.add_annotation(x=row['quarter'], y=row['net_abs'], text=f"#{row['rank']}",
                           showarrow=False, yshift=14,
                           font=dict(family=AQUILA_FONT, size=11, color=COPPER))
    return fig


def chart_mean_vs_median(df):
    """Chart 24: the same four quarters, two statistics, opposite conclusions."""
    post, other = df[df['is_post']], df[~df['is_post']]
    stats = [('Mean', post['net_abs'].mean(), other['net_abs'].mean()),
             ('Median', post['net_abs'].median(), other['net_abs'].median())]
    labels = [s[0] for s in stats]

    fig = go.Figure()
    for idx, (name, color) in enumerate(((f'Post-election quarters (n={len(post)})', COPPER),
                                         (f'All other quarters (n={len(other)})', NAVY))):
        vals = [s[1 + idx] for s in stats]
        fig.add_trace(go.Bar(x=labels, y=vals, name=name, marker_color=color,
                             marker_line=dict(color='white', width=2), width=0.34,
                             text=[f"{v:,.0f}" for v in vals], textposition='outside',
                             textfont=dict(family=AQUILA_FONT, size=11, color=NAVY),
                             hovertemplate='%{y:,.0f} SF<extra>' + name + '</extra>'))

    mean_gap = post['net_abs'].mean() / other['net_abs'].mean() - 1
    med_gap = post['net_abs'].median() / other['net_abs'].median() - 1
    layout = _shared_layout(
        'The Same Four Quarters, Two Opposite Headlines',
        'Net absorption (SF)',
        subtitle=(f"By the mean, post-election quarters run {mean_gap:+.0%} vs the rest<br>"
                  f"By the median, the same quarters run {med_gap:+.0%} — n=4, so both are noise"))
    layout['yaxis']['tickformat'] = ','
    layout['barmode'] = 'group'
    layout['xaxis']['tickangle'] = 0
    layout['xaxis']['tickfont'] = dict(family=AQUILA_FONT, size=13, color=NAVY)
    fig.update_layout(**layout)
    return fig


# -- Main ----------------------------------------------------------------------

def main():
    supabase = get_supabase_client(use_service_role=True)
    df = load_absorption(supabase)

    charts = [
        (chart_election_overlay(df), 'retail_absorption_election_overlay.html'),
        (chart_mean_vs_median(df), 'retail_election_mean_vs_median.html'),
    ]
    print()
    for fig, name in charts:
        path = f'{OUTPUT_DIR}/{name}'
        write_chart_html(fig, path)
        print(f"  [OK] {path}")
    print(f"\n{len(charts)} charts written to {OUTPUT_DIR}/")


if __name__ == '__main__':
    main()
