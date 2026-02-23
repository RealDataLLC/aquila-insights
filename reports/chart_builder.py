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
NAVY = AQUILA_COLORS[0]       # #172344
GLASS_BLUE = AQUILA_COLORS[1] # #C2DAF1
COPPER = AQUILA_COLORS[2]     # #AB6D3A
BRASS = AQUILA_COLORS[3]      # #DEB76D
GREENSPACE = AQUILA_COLORS[4] # #556B30
CONCRETE = AQUILA_COLORS[5]   # #AAA9A8

# ── Shared Layout Config ─────────────────────────────────────
LAYOUT_DEFAULTS = dict(
    font=dict(family=AQUILA_FONT, color=NAVY, size=15),
    plot_bgcolor='white',
    paper_bgcolor='white',
    margin=dict(l=50, r=50, t=10, b=40),
    legend=dict(
        orientation='h',
        yanchor='bottom',
        y=1.02,
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
            tickfont=dict(size=12, color=COPPER),
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
            line=dict(color=COPPER, width=2),
            marker=dict(size=5, color=COPPER),
        ),
        secondary_y=True,
    )

    fig.update_layout(**LAYOUT_DEFAULTS, barmode='stack')
    _apply_axes(fig, y1_title='Vacant SF', y2_title='Total Vacancy Rate', y2_tickformat='.0%')

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
            line=dict(color=BRASS, width=2),
            marker=dict(size=5, color=BRASS),
        ),
        secondary_y=True,
    )

    fig.update_layout(**LAYOUT_DEFAULTS)
    _apply_axes(fig, y1_title='Total Net Absorption', y2_title='Total Occupancy Rate', y2_tickformat='.0%')

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
            marker_color=CONCRETE,
        ),
        secondary_y=False,
    )
    # Vacancy rate line
    fig.add_trace(
        go.Scatter(
            x=df['quarter'], y=df['total_vacancy_rate'],
            name='Total Vacancy Rate',
            mode='lines+markers',
            line=dict(color=COPPER, width=2),
            marker=dict(size=5, color=COPPER),
        ),
        secondary_y=True,
    )

    fig.update_layout(**LAYOUT_DEFAULTS, barmode='stack')
    _apply_axes(fig, y1_title='Rent ($/SF/YR)', y2_title='Total Vacancy Rate', y2_tickformat='.0%')

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
            line=dict(color=COPPER, width=2),
        ),
        secondary_y=True,
    )

    layout = {**LAYOUT_DEFAULTS}
    layout['margin'] = dict(l=40, r=40, t=10, b=50)
    layout['legend'] = dict(
        orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0, font=dict(size=10)
    )
    fig.update_layout(**layout, barmode='stack')
    _apply_axes(fig, y2_tickformat='.0%')
    fig.update_xaxes(tickfont=dict(size=9), dtick=2)

    return fig


def build_long_term_asking_rates(df):
    """Long-term citywide Class A & B asking rates line chart."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df['quarter'], y=df['full_service_rent'],
            name='Avg. Calculated Full Service Rent',
            mode='lines', line=dict(color=NAVY, width=2),
        )
    )
    layout = {**LAYOUT_DEFAULTS}
    layout['margin'] = dict(l=40, r=20, t=10, b=50)
    fig.update_layout(**layout)
    fig.update_xaxes(tickfont=dict(size=9), dtick=4, tickangle=-45)
    fig.update_yaxes(tickfont=dict(size=10), tickprefix='$', showgrid=True, gridcolor='#e9e9ea')
    return fig


def build_long_term_absorption(df):
    """Long-term absorption bar chart + occupancy rate line."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    colors = [NAVY if v and v >= 0 else BRASS for v in df['total_net_absorption']]
    fig.add_trace(
        go.Bar(
            x=df['quarter'], y=df['total_net_absorption'],
            name='Net Absorption', marker_color=colors,
        ),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=df['quarter'], y=df['occupancy_rate'],
            name='Calculated Occupancy Rate', mode='lines',
            line=dict(color=COPPER, width=2),
        ),
        secondary_y=True,
    )

    layout = {**LAYOUT_DEFAULTS}
    layout['margin'] = dict(l=40, r=40, t=10, b=50)
    layout['legend'] = dict(
        orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0, font=dict(size=10)
    )
    fig.update_layout(**layout)
    _apply_axes(fig, y2_tickformat='.0%')
    fig.update_xaxes(tickfont=dict(size=9), dtick=2)

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
    Generate long-term performance charts (pages 44-45).
    Returns dict of chart paths.
    """
    from reports.data_loader import get_long_term_data
    from reports.report_config import CHART_SMALL_WIDTH, CHART_SMALL_HEIGHT

    chart_paths = {}

    # Page 44: 4 vacancy charts (Citywide, CBD, NW, SW) + asking rates + absorption
    for submarket in ['Citywide', 'CBD', 'Northwest', 'Southwest']:
        df = get_long_term_data(data, submarket, 'competitive set')
        if not df.empty:
            key = f"lt_vacancy_{submarket.lower().replace(' ', '_')}"
            path = os.path.join(charts_dir, f"{key}.png")
            fig = build_long_term_vacancy_chart(df, submarket)
            export_chart(fig, path, width=CHART_SMALL_WIDTH, height=CHART_SMALL_HEIGHT)
            chart_paths[key] = path

    # Citywide asking rates
    df_cw = get_long_term_data(data, 'Citywide', 'competitive set')
    if not df_cw.empty:
        path = os.path.join(charts_dir, "lt_asking_rates.png")
        fig = build_long_term_asking_rates(df_cw)
        export_chart(fig, path, width=CHART_SMALL_WIDTH, height=CHART_SMALL_HEIGHT)
        chart_paths['lt_asking_rates'] = path

    # Absorption & occupancy
    if not df_cw.empty:
        path = os.path.join(charts_dir, "lt_absorption.png")
        fig = build_long_term_absorption(df_cw)
        export_chart(fig, path, width=CHART_SMALL_WIDTH, height=CHART_SMALL_HEIGHT)
        chart_paths['lt_absorption'] = path

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
