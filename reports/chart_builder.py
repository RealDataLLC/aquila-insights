"""
Chart builder for AQUILA Office Quarterly Report.
Generates static PNG charts using Plotly + Kaleido.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from aquila_graphing_tools import AQUILA_COLORS, AQUILA_FONT

# ── Brand Color Aliases ──────────────────────────────────────
NAVY       = AQUILA_COLORS[0]  # #172344
GLASS_BLUE = AQUILA_COLORS[1]  # #C2DAF1
GLASS_ALT  = AQUILA_COLORS[2]  # #88ABC8  (vacancy rate lines)
CONCRETE   = AQUILA_COLORS[3]  # #AAA9A8
COPPER     = AQUILA_COLORS[4]  # #AB6D3A
BRASS      = AQUILA_COLORS[5]  # #DEB76D
GREENSPACE = AQUILA_COLORS[6]  # #556B30

# ── Shared Layout Config ─────────────────────────────────────
LAYOUT_DEFAULTS = dict(
    font=dict(family=AQUILA_FONT, color=NAVY, size=15),
    plot_bgcolor='white',
    paper_bgcolor='white',
    margin=dict(l=50, r=50, t=10, b=90),
    legend=dict(
        orientation='h',
        yanchor='top',
        y=-0.28,
        xanchor='left',
        x=0,
        font=dict(size=12),
    ),
    bargap=0.3,
)


def _apply_axes(fig, y1_title=None, y2_title=None, y2_tickformat=None):
    """Apply consistent axis styling."""
    fig.update_xaxes(
        tickfont=dict(size=12, color=NAVY),
        tickangle=-45,
        showgrid=False,
        showline=True,
        linecolor='#e9e9ea',
    )
    fig.update_yaxes(
        tickfont=dict(size=12, color=NAVY),
        showgrid=True,
        gridcolor='#e9e9ea',
        showline=False,
        secondary_y=False,
    )
    if y1_title:
        fig.update_yaxes(title_text=y1_title, title_font=dict(size=12), secondary_y=False)
    if y2_title:
        fig.update_yaxes(
            title_text=y2_title,
            title_font=dict(size=12),
            tickfont=dict(size=12, color='black'),
            showgrid=False,
            secondary_y=True,
        )
    if y2_tickformat:
        fig.update_yaxes(tickformat=y2_tickformat, secondary_y=True)


def build_vacancy_sf_chart(df):
    """
    Chart 1: Vacancy SF vs Vacancy Rate
    Stacked bar (Direct Vacant + Sublease Vacant) + line (Vacancy Rate %)
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Sublease bars (bottom)
    fig.add_trace(
        go.Bar(
            x=df['quarter'], y=df['vacant_available_sf_sublet'],
            name='Sublease Vacant SF',
            marker_color=GLASS_BLUE,
        ),
        secondary_y=False,
    )
    # Direct bars (top of stack)
    fig.add_trace(
        go.Bar(
            x=df['quarter'], y=df['vacant_available_sf_direct'],
            name='Direct Vacant SF',
            marker_color=NAVY,
        ),
        secondary_y=False,
    )
    # Vacancy rate line
    fig.add_trace(
        go.Scatter(
            x=df['quarter'], y=df['total_vacancy_rate'],
            name='Total Vacancy Rate',
            mode='lines+markers',
            line=dict(color=CONCRETE, width=2),
            marker=dict(size=5, color=CONCRETE),
        ),
        secondary_y=True,
    )

    fig.update_layout(**LAYOUT_DEFAULTS, barmode='stack')
    _apply_axes(fig, y1_title='Vacant SF', y2_title='Total Vacancy Rate', y2_tickformat='.0%')
    fig.update_yaxes(range=[0, df['total_vacancy_rate'].max()+.05], secondary_y=True)

    return fig


def build_absorption_chart(df):
    """
    Chart 2: Net Absorption + Occupancy Rate
    Bar (Net Absorption) + line (Occupancy Rate %)
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Absorption bars
    colors = [NAVY if v >= 0 else GLASS_BLUE for v in df['total_net_absorption']]
    fig.add_trace(
        go.Bar(
            x=df['quarter'], y=df['total_net_absorption'],
            name='Total Net Absorption',
            marker_color=colors,
        ),
        secondary_y=False,
    )
    # Occupancy rate line
    fig.add_trace(
        go.Scatter(
            x=df['quarter'], y=df['occupancy_rate'],
            name='Occupancy Rate',
            mode='lines+markers',
            line=dict(color=CONCRETE, width=2),
            marker=dict(size=5, color=CONCRETE),
        ),
        secondary_y=True,
    )

    fig.update_layout(**LAYOUT_DEFAULTS)
    _apply_axes(fig, y1_title='Total Net Absorption', y2_title='Total Occupancy Rate', y2_tickformat='.0%')
    fig.update_yaxes(
        range=[df['occupancy_rate'].min()-.05, 1],
        secondary_y=True
    )

    return fig


def build_rental_chart(df):
    """
    Chart 3: Vacancy vs Rental Rates
    Stacked bar (Base Rent + Opex) + line (Vacancy Rate %)
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Base rent bars (bottom)
    fig.add_trace(
        go.Bar(
            x=df['quarter'], y=df['average_rental_rate'],
            name='Base Rent',
            marker_color=NAVY,
        ),
        secondary_y=False,
    )
    # Opex bars (top)
    fig.add_trace(
        go.Bar(
            x=df['quarter'], y=df['average_opex'],
            name='Opex',
            marker_color=GLASS_BLUE,
        ),
        secondary_y=False,
    )
    # Vacancy rate line
    fig.add_trace(
        go.Scatter(
            x=df['quarter'], y=df['total_vacancy_rate'],
            name='Total Vacancy Rate',
            mode='lines+markers',
            line=dict(color=CONCRETE, width=2),
            marker=dict(size=5, color=CONCRETE),
        ),
        secondary_y=True,
    )

    fig.update_layout(**LAYOUT_DEFAULTS, barmode='stack')
    _apply_axes(fig, y1_title='Rent ($/SF/YR)', y2_title='Total Vacancy Rate', y2_tickformat='.0%')
    fig.update_yaxes(range=[0, df['total_vacancy_rate'].max()+.05], secondary_y=True)

    return fig


def build_long_term_vacancy_chart(df, submarket_name):
    """Long-term vacancy SF vs vacancy rate for a single submarket."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=df['quarter'], y=df['vacant_available_sf_sublet'],
            name='Sublease Vacant SF', marker_color=GLASS_BLUE,
            showlegend=True,
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(
            x=df['quarter'], y=df['vacant_available_sf_direct'],
            name='Direct Vacant SF', marker_color=NAVY,
            showlegend=True,
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df['quarter'], y=df['total_vacancy_rate'],
            name='Total Vacancy Rate', mode='lines',
            line=dict(color=GLASS_ALT, width=2),
        ),
        secondary_y=True,
    )

    layout = {**LAYOUT_DEFAULTS}
    layout['margin'] = dict(l=40, r=40, t=10, b=70)
    layout['legend'] = dict(
        orientation='h', yanchor='top', y=-0.28, xanchor='left', x=0, font=dict(size=10)
    )
    fig.update_layout(**layout, barmode='stack')
    _apply_axes(fig, y2_tickformat='.0%')
    fig.update_yaxes(range=[0, None], secondary_y=True)
    fig.update_xaxes(tickfont=dict(size=9), dtick=2)

    return fig


def build_long_term_asking_rates(df):
    """Long-term citywide Class A & B asking rates — two lines."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['quarter'], y=df['average_class_a_rent'],
        name='Class A', mode='lines', line=dict(color=NAVY, width=2),
    ))
    fig.add_trace(go.Scatter(
        x=df['quarter'], y=df['average_class_b_rent'],
        name='Class B', mode='lines', line=dict(color=COPPER, width=2),
    ))
    layout = {**LAYOUT_DEFAULTS}
    layout['margin'] = dict(l=40, r=20, t=10, b=70)
    layout['legend'] = dict(
        orientation='h', yanchor='top', y=-0.28, xanchor='left', x=0, font=dict(size=10)
    )
    fig.update_layout(**layout)
    fig.update_xaxes(tickfont=dict(size=9), dtick=4, tickangle=-45)
    fig.update_yaxes(tickfont=dict(size=10), tickprefix='$', showgrid=True, gridcolor='#e9e9ea')
    return fig


def build_long_term_absorption(df_cw, df_cbd=None, df_nw=None, df_sw=None):
    """
    Long-term absorption grouped bars by submarket (CBD / NW / SW) + citywide occupancy rate line.
    df_cw is used for the occupancy rate line. Submarket DFs are used for absorption bars.
    Falls back to df_cw absorption if no submarket DFs are provided.
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    submarket_traces = [
        ('CBD',       df_cbd, NAVY),
        ('Northwest', df_nw,  GLASS_BLUE),
        ('Southwest', df_sw,  COPPER),
    ]
    has_submarket_data = any(df is not None and not df.empty for _, df, _ in submarket_traces)

    if has_submarket_data:
        for label, df, color in submarket_traces:
            if df is None or df.empty:
                continue
            fig.add_trace(go.Bar(
                x=df['quarter'], y=df['total_net_absorption'],
                name=label, marker_color=color,
            ), secondary_y=False)
    else:
        # Fallback: single citywide bar
        colors = [NAVY if v and v >= 0 else BRASS for v in df_cw['total_net_absorption']]
        fig.add_trace(go.Bar(
            x=df_cw['quarter'], y=df_cw['total_net_absorption'],
            name='Net Absorption', marker_color=colors,
        ), secondary_y=False)

    # Citywide occupancy rate line
    if not df_cw.empty:
        fig.add_trace(go.Scatter(
            x=df_cw['quarter'], y=df_cw['occupancy_rate'],
            name='Citywide Occupancy Rate', mode='lines',
            line=dict(color=BRASS, width=2),
        ), secondary_y=True)

    layout = {**LAYOUT_DEFAULTS}
    layout['margin'] = dict(l=40, r=40, t=10, b=70)
    layout['legend'] = dict(
        orientation='h', yanchor='top', y=-0.28, xanchor='left', x=0, font=dict(size=10)
    )
    fig.update_layout(**layout, barmode='relative')
    _apply_axes(fig, y2_tickformat='.0%')
    fig.update_yaxes(range=[0, 1.0], secondary_y=True)
    fig.update_xaxes(tickfont=dict(size=9), dtick=2)

    return fig


def build_cbd_suburban_asking_chart(df_cbd, df_suburban):
    """
    Page 2: Average Class A Asking Rates — CBD vs Suburban line chart.
    Uses average_class_a_rent from competitive set data.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_cbd['quarter'], y=df_cbd['average_class_a_rent'],
        name='CBD', mode='lines',
        line=dict(color=NAVY, width=2),
    ))
    fig.add_trace(go.Scatter(
        x=df_suburban['quarter'], y=df_suburban['average_class_a_rent'],
        name='Suburban', mode='lines',
        line=dict(color=COPPER, width=2),
    ))
    layout = {**LAYOUT_DEFAULTS}
    layout['margin'] = dict(l=40, r=20, t=10, b=70)
    layout['legend'] = dict(
        orientation='h', yanchor='top', y=-0.28, xanchor='left', x=0, font=dict(size=10)
    )
    fig.update_layout(**layout)
    fig.update_xaxes(tickfont=dict(size=9), dtick=4, tickangle=-45)
    fig.update_yaxes(tickfont=dict(size=10), tickprefix='$', showgrid=True, gridcolor='#e9e9ea')
    return fig


def build_cbd_suburban_vacancy_chart(df_cbd, df_suburban):
    """
    Page 2: Vacant SF vs Vacancy Rate — CBD vs Suburban stacked bars + vacancy rate line.
    Sublease (CBD, Suburban) stacked, then Direct (CBD, Suburban) stacked, rate as line.
    Shows combined CBD + Suburban on same axis with separate bar groups per quarter.
    """
    import pandas as pd
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        x=df_suburban['quarter'], y=df_suburban['vacant_available_sf_sublet'],
        name='Suburban Sublease', marker_color=COPPER,
    ), secondary_y=False)
    fig.add_trace(go.Bar(
        x=df_suburban['quarter'], y=df_suburban['vacant_available_sf_direct'],
        name='Suburban Direct', marker_color=COPPER,
        marker_pattern_shape='/',
    ), secondary_y=False)
    fig.add_trace(go.Bar(
        x=df_cbd['quarter'], y=df_cbd['vacant_available_sf_sublet'],
        name='CBD Sublease', marker_color=GLASS_BLUE,
    ), secondary_y=False)
    fig.add_trace(go.Bar(
        x=df_cbd['quarter'], y=df_cbd['vacant_available_sf_direct'],
        name='CBD Direct', marker_color=NAVY,
    ), secondary_y=False)

    # Combined vacancy rate (total direct+sublease SF / combined NRA)
    import numpy as np
    combined = pd.merge(
        df_cbd[['quarter', 'total_vacancy_rate', 'net_rentable_area']],
        df_suburban[['quarter', 'total_vacancy_rate', 'net_rentable_area']],
        on='quarter', how='inner', suffixes=('_cbd', '_sub')
    )
    combined['combined_rate'] = (
        (combined['total_vacancy_rate_cbd'] * combined['net_rentable_area_cbd'] +
         combined['total_vacancy_rate_sub'] * combined['net_rentable_area_sub']) /
        (combined['net_rentable_area_cbd'] + combined['net_rentable_area_sub'])
    )
    fig.add_trace(go.Scatter(
        x=combined['quarter'], y=combined['combined_rate'],
        name='Total Vacancy Rate', mode='lines',
        line=dict(color=GLASS_ALT, width=2),
    ), secondary_y=True)

    layout = {**LAYOUT_DEFAULTS}
    layout['margin'] = dict(l=40, r=40, t=10, b=70)
    layout['legend'] = dict(
        orientation='h', yanchor='top', y=-0.28, xanchor='left', x=0, font=dict(size=9)
    )
    fig.update_layout(**layout, barmode='stack')
    _apply_axes(fig, y2_tickformat='.0%')
    fig.update_yaxes(range=[0, None], secondary_y=True)
    fig.update_xaxes(tickfont=dict(size=9), dtick=4, tickangle=-45)
    return fig


def build_cbd_suburban_direct_sublease_chart(df_cbd, df_suburban):
    """
    Page 2: Direct & Sublease Vacancy — fully stacked bars per quarter.
    Stack order (bottom to top): CBD Sublease, CBD Direct, Suburban Sublease, Suburban Direct.
    All four segments stack on top of each other for each quarter.
    """
    import pandas as pd

    # Align on quarter so all four series share the same x-axis
    quarters = sorted(set(df_cbd['quarter'].tolist() + df_suburban['quarter'].tolist()))
    cbd = df_cbd.set_index('quarter')
    sub = df_suburban.set_index('quarter')

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=quarters,
        y=[cbd.loc[q, 'vacant_available_sf_sublet'] if q in cbd.index else 0 for q in quarters],
        name='CBD Sublease', marker_color=GLASS_BLUE,
    ))
    fig.add_trace(go.Bar(
        x=quarters,
        y=[cbd.loc[q, 'vacant_available_sf_direct'] if q in cbd.index else 0 for q in quarters],
        name='CBD Direct', marker_color=NAVY,
    ))
    fig.add_trace(go.Bar(
        x=quarters,
        y=[sub.loc[q, 'vacant_available_sf_sublet'] if q in sub.index else 0 for q in quarters],
        name='Suburban Sublease', marker_color=COPPER,
    ))
    fig.add_trace(go.Bar(
        x=quarters,
        y=[sub.loc[q, 'vacant_available_sf_direct'] if q in sub.index else 0 for q in quarters],
        name='Suburban Direct', marker_color=COPPER,
        marker_pattern_shape='/',
    ))

    layout = {**LAYOUT_DEFAULTS}
    layout['margin'] = dict(l=40, r=20, t=10, b=70)
    layout['legend'] = dict(
        orientation='h', yanchor='top', y=-0.28, xanchor='left', x=0, font=dict(size=9)
    )
    fig.update_layout(**layout, barmode='stack')
    fig.update_xaxes(tickfont=dict(size=9), dtick=4, tickangle=-45)
    fig.update_yaxes(tickfont=dict(size=10), showgrid=True, gridcolor='#e9e9ea')
    return fig


def build_cbd_suburban_under_construction_chart(df_cbd, df_suburban, df_east=None):
    """
    Page 2: SF Under Construction — stacked bars by submarket.
    Suburban = NW + SW; optionally includes East.
    """
    import pandas as pd

    traces = [
        ('CBD', df_cbd, NAVY),
        ('Suburban', df_suburban, COPPER),
    ]
    if df_east is not None and not df_east.empty:
        traces.append(('East', df_east, GLASS_BLUE))

    fig = go.Figure()
    for name, df, color in traces:
        fig.add_trace(go.Bar(
            x=df['quarter'], y=df['sqft_under_construction'],
            name=name, marker_color=color,
        ))

    layout = {**LAYOUT_DEFAULTS}
    layout['margin'] = dict(l=40, r=20, t=10, b=70)
    layout['legend'] = dict(
        orientation='h', yanchor='top', y=-0.28, xanchor='left', x=0, font=dict(size=10)
    )
    fig.update_layout(**layout, barmode='stack')
    fig.update_xaxes(tickfont=dict(size=9), dtick=4, tickangle=-45)
    fig.update_yaxes(tickfont=dict(size=10), showgrid=True, gridcolor='#e9e9ea')
    return fig


def export_chart(fig, output_path, width=None, height=None, scale=None):
    """Export a Plotly figure to PNG."""
    from reports.report_config import CHART_WIDTH, CHART_HEIGHT, CHART_SCALE
    w = width or CHART_WIDTH
    h = height or CHART_HEIGHT
    s = scale if scale is not None else CHART_SCALE
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.write_image(output_path, format='png', width=w, height=h, scale=s)
    return output_path


def generate_performance_charts(df, submarket, table_type, charts_dir):
    """
    Generate the 3 performance charts for a given submarket/table_type.
    Returns dict of chart paths.
    """
    prefix = f"{submarket}_{table_type}".replace(' ', '_').lower()

    vacancy_path = os.path.join(charts_dir, f"{prefix}_vacancy_sf.png")
    absorption_path = os.path.join(charts_dir, f"{prefix}_absorption.png")
    rental_path = os.path.join(charts_dir, f"{prefix}_rental.png")

    fig1 = build_vacancy_sf_chart(df)
    export_chart(fig1, vacancy_path, width=520, height=300)

    fig2 = build_absorption_chart(df)
    export_chart(fig2, absorption_path, width=520, height=300)

    fig3 = build_rental_chart(df)
    export_chart(fig3, rental_path, width=520, height=300)

    return {
        'vacancy_sf': vacancy_path,
        'absorption': absorption_path,
        'rental': rental_path,
    }


def generate_long_term_charts(data, charts_dir):
    """
    Generate long-term performance charts (2 pages).
    Page 1 - Of Submarkets: Citywide/CBD/NW/SW vacancy + asking rates + absorption.
    Page 2 - CBD vs Suburban: Class A asking rates, vacancy, direct/sublease, under construction.
    Returns dict of chart paths.
    """
    from reports.data_loader import get_long_term_data
    from reports.report_config import CHART_SMALL_WIDTH, CHART_SMALL_HEIGHT

    chart_paths = {}

    # ── Page 1: Of Submarkets ─────────────────────────────────────
    # Citywide uses "overall" table_type; submarkets use "competitive set"
    df_cw = get_long_term_data(data, 'Citywide', 'overall')
    for submarket, ttype in [('Citywide', 'overall'), ('CBD', 'competitive set'),
                              ('Northwest', 'competitive set'), ('Southwest', 'competitive set')]:
        df = get_long_term_data(data, submarket, ttype)
        if not df.empty:
            key = f"lt_vacancy_{submarket.lower().replace(' ', '_')}"
            path = os.path.join(charts_dir, f"{key}.png")
            fig = build_long_term_vacancy_chart(df, submarket)
            export_chart(fig, path, width=CHART_SMALL_WIDTH, height=CHART_SMALL_HEIGHT)
            chart_paths[key] = path

    # Citywide asking rates (use overall for citywide)
    if df_cw.empty:
        df_cw = get_long_term_data(data, 'Citywide', 'overall')
    if not df_cw.empty:
        path = os.path.join(charts_dir, "lt_asking_rates.png")
        fig = build_long_term_asking_rates(df_cw)
        export_chart(fig, path, width=CHART_SMALL_WIDTH, height=CHART_SMALL_HEIGHT)
        chart_paths['lt_asking_rates'] = path

    # ── Page 2: CBD vs Suburban ───────────────────────────────────
    df_cbd = get_long_term_data(data, 'CBD', 'competitive set')
    df_nw  = get_long_term_data(data, 'Northwest', 'competitive set')
    df_sw  = get_long_term_data(data, 'Southwest', 'competitive set')
    df_east = get_long_term_data(data, 'East', 'competitive set')

    # Absorption by submarket (CBD / NW / SW) + citywide occupancy rate
    if not df_cw.empty:
        path = os.path.join(charts_dir, "lt_absorption.png")
        fig = build_long_term_absorption(
            df_cw,
            df_cbd=df_cbd if not df_cbd.empty else None,
            df_nw=df_nw if not df_nw.empty else None,
            df_sw=df_sw if not df_sw.empty else None,
        )
        export_chart(fig, path, width=CHART_SMALL_WIDTH, height=CHART_SMALL_HEIGHT)
        chart_paths['lt_absorption'] = path

    # Combine NW + SW into a single Suburban DataFrame by summing SF columns
    import pandas as pd
    if not df_nw.empty and not df_sw.empty:
        sf_cols = ['vacant_available_sf_direct', 'vacant_available_sf_sublet',
                   'net_rentable_area', 'sqft_under_construction']
        avg_cols = ['average_class_a_rent', 'average_rental_rate', 'average_opex',
                    'total_vacancy_rate', 'total_net_absorption']
        merged = pd.merge(df_nw[['quarter'] + sf_cols + avg_cols],
                          df_sw[['quarter'] + sf_cols + avg_cols],
                          on='quarter', how='outer', suffixes=('_nw', '_sw'))
        df_suburban = pd.DataFrame()
        df_suburban['quarter'] = merged['quarter']
        for col in sf_cols:
            df_suburban[col] = merged[f'{col}_nw'].fillna(0) + merged[f'{col}_sw'].fillna(0)
        # Weighted average for rate/rent columns by NRA
        nra_nw = merged['net_rentable_area_nw'].fillna(0)
        nra_sw = merged['net_rentable_area_sw'].fillna(0)
        total_nra = nra_nw + nra_sw
        for col in avg_cols:
            df_suburban[col] = (
                (merged[f'{col}_nw'].fillna(0) * nra_nw +
                 merged[f'{col}_sw'].fillna(0) * nra_sw) /
                total_nra.replace(0, float('nan'))
            )
        df_suburban = df_suburban.sort_values('quarter').reset_index(drop=True)
    elif not df_nw.empty:
        df_suburban = df_nw.copy()
    elif not df_sw.empty:
        df_suburban = df_sw.copy()
    else:
        df_suburban = pd.DataFrame()

    if not df_cbd.empty and not df_suburban.empty:
        path = os.path.join(charts_dir, "lt_cbd_suburban_asking.png")
        fig = build_cbd_suburban_asking_chart(df_cbd, df_suburban)
        export_chart(fig, path, width=CHART_SMALL_WIDTH, height=CHART_SMALL_HEIGHT)
        chart_paths['lt_cbd_suburban_asking'] = path

        path = os.path.join(charts_dir, "lt_cbd_suburban_vacancy.png")
        fig = build_cbd_suburban_vacancy_chart(df_cbd, df_suburban)
        export_chart(fig, path, width=CHART_SMALL_WIDTH, height=CHART_SMALL_HEIGHT)
        chart_paths['lt_cbd_suburban_vacancy'] = path

        path = os.path.join(charts_dir, "lt_cbd_suburban_direct_sublease.png")
        fig = build_cbd_suburban_direct_sublease_chart(df_cbd, df_suburban)
        export_chart(fig, path, width=CHART_SMALL_WIDTH, height=CHART_SMALL_HEIGHT)
        chart_paths['lt_cbd_suburban_direct_sublease'] = path

        path = os.path.join(charts_dir, "lt_cbd_suburban_under_construction.png")
        fig = build_cbd_suburban_under_construction_chart(
            df_cbd, df_suburban, df_east if not df_east.empty else None
        )
        export_chart(fig, path, width=CHART_SMALL_WIDTH, height=CHART_SMALL_HEIGHT)
        chart_paths['lt_cbd_suburban_under_construction'] = path

    return chart_paths


def generate_all_charts(data, config):
    """
    Master chart generator. Generates all charts for the report.
    Returns a nested dict of chart file paths.
    """
    from reports.data_loader import get_performance_data
    charts_dir = config.CHARTS_DIR
    os.makedirs(charts_dir, exist_ok=True)

    all_charts = {}
    count = 0

    # Performance charts for competitive set pages
    # Note: Citywide uses "overall" table_type in Supabase
    for submarket in config.SUBMARKETS_COMP:
        ttype = 'overall' if submarket == 'Citywide' else 'competitive set'
        df = get_performance_data(data, submarket, ttype)
        if not df.empty:
            key = f"{submarket}_{ttype}"
            all_charts[key] = generate_performance_charts(
                df, submarket, ttype, charts_dir
            )
            count += 3
            print(f"    Generated 3 charts for {key}")

    # Performance charts for micromarket pages
    for micro in config.MICROMARKETS:
        df = get_performance_data(data, micro, 'micromarket')
        if not df.empty:
            key = f"{micro}_micromarket"
            all_charts[key] = generate_performance_charts(
                df, micro, 'micromarket', charts_dir
            )
            count += 3
            print(f"    Generated 3 charts for {key}")

    # Performance charts for overall pages
    for submarket in config.SUBMARKETS_OVERALL:
        df = get_performance_data(data, submarket, 'overall')
        if not df.empty:
            key = f"{submarket}_overall"
            all_charts[key] = generate_performance_charts(
                df, submarket, 'overall', charts_dir
            )
            count += 3
            print(f"    Generated 3 charts for {key}")

    # Long-term charts
    lt_charts = generate_long_term_charts(data, charts_dir)
    all_charts['long_term'] = lt_charts
    count += len(lt_charts)
    print(f"    Generated {len(lt_charts)} long-term charts")

    print(f"\n  Total charts generated: {count}")
    return all_charts
