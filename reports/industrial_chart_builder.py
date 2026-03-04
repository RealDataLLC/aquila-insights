"""
Chart builder for AQUILA Industrial Quarterly Report.
Generates static PNG charts using Plotly + Kaleido.

Reuses vacancy and absorption chart functions from the office chart_builder.
Adds industrial-specific rental chart (no opex) and regional comparison charts.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from aquila_graphing_tools import AQUILA_COLORS, AQUILA_FONT

# Import shared chart primitives from office chart builder
from reports.chart_builder import (
    NAVY, GLASS_BLUE, GLASS_ALT, COPPER, BRASS, GREENSPACE, CONCRETE,
    LAYOUT_DEFAULTS, _apply_axes,
    build_vacancy_sf_chart, build_absorption_chart,
)


def export_chart(fig, output_path, width=None, height=None, scale=None):
    """Export a Plotly figure to PNG. Uses industrial config for defaults."""
    from reports.industrial_report_config import CHART_WIDTH, CHART_HEIGHT, CHART_SCALE
    w = width or CHART_WIDTH
    h = height or CHART_HEIGHT
    s = scale if scale is not None else CHART_SCALE
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.write_image(output_path, format='png', width=w, height=h, scale=s)
    return output_path


def build_industrial_rental_chart(df):
    """
    Industrial Rental Chart: Single bar (Avg Base Rent) + Vacancy Rate line.
    Unlike office version, there's no opex stacking — industrial uses NNN/base rent only.
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Average base rent bars
    fig.add_trace(
        go.Bar(
            x=df['quarter'], y=df['average_rental_rate'],
            name='Average Base Rent',
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
            line=dict(color=GLASS_ALT, width=2),
            marker=dict(size=5, color=GLASS_ALT),
        ),
        secondary_y=True,
    )

    fig.update_layout(**LAYOUT_DEFAULTS)
    _apply_axes(fig, y1_title='Rent ($/SF/YR)', y2_title='Total Vacancy Rate', y2_tickformat='.0%')
    fig.update_yaxes(range=[0, None], secondary_y=True)

    return fig


def build_regional_comparison_chart(data_by_submarket, metric_col, submarkets, n_quarters=8):
    """
    Multi-line chart comparing a metric across all submarkets.
    One line per submarket with distinct AQUILA colors.
    Only shows the last n_quarters of data.
    """
    fig = go.Figure()

    for i, submarket in enumerate(submarkets):
        df = data_by_submarket.get(submarket)
        if df is None or df.empty:
            continue
        # Only use last n_quarters
        df = df.tail(n_quarters)
        fig.add_trace(go.Scatter(
            x=df['quarter'], y=df[metric_col],
            name=submarket,
            mode='lines+markers',
            line=dict(color=AQUILA_COLORS[i % len(AQUILA_COLORS)], width=2),
            marker=dict(size=4),
        ))

    layout = {**LAYOUT_DEFAULTS}
    layout['legend'] = dict(
        orientation='h', yanchor='bottom', y=1.02, xanchor='left', x=0,
        font=dict(size=10),
    )
    fig.update_layout(**layout)

    if 'vacancy' in metric_col:
        fig.update_yaxes(tickformat='.1%', showgrid=True, gridcolor='#e9e9ea')
    elif 'rental' in metric_col or 'rent' in metric_col:
        fig.update_yaxes(tickprefix='$', tickformat=',.2f', showgrid=True, gridcolor='#e9e9ea')

    fig.update_xaxes(tickfont=dict(size=12, color=NAVY), tickangle=-45, showgrid=False)

    return fig


def generate_performance_charts(df, submarket, property_type, charts_dir):
    """
    Generate the 3 performance charts for a given submarket/property_type.
    Returns dict of chart paths: {vacancy_sf, absorption, rental}.
    """
    prefix = f"{submarket}_{property_type}".replace(' ', '_').lower()

    vacancy_path = os.path.join(charts_dir, f"{prefix}_vacancy_sf.png")
    absorption_path = os.path.join(charts_dir, f"{prefix}_absorption.png")
    rental_path = os.path.join(charts_dir, f"{prefix}_rental.png")

    fig1 = build_vacancy_sf_chart(df)
    export_chart(fig1, vacancy_path, width=520, height=300)

    fig2 = build_absorption_chart(df)
    export_chart(fig2, absorption_path, width=520, height=300)

    fig3 = build_industrial_rental_chart(df)
    export_chart(fig3, rental_path, width=520, height=300)

    return {
        'vacancy_sf': vacancy_path,
        'absorption': absorption_path,
        'rental': rental_path,
    }


def generate_all_charts(data, config):
    """
    Master chart generator for the industrial report.
    Generates ~52 charts total.
    Returns nested dict of chart file paths.
    """
    from reports.industrial_data_loader import get_performance_data, get_regional_comparison_data
    charts_dir = config.CHARTS_DIR
    os.makedirs(charts_dir, exist_ok=True)

    all_charts = {}
    count = 0

    # Regional performance charts (Industrial + Flex)
    for ptype in config.PROPERTY_TYPES:
        df = get_performance_data(data, 'Regional', ptype)
        if not df.empty:
            key = f"Regional_{ptype}"
            all_charts[key] = generate_performance_charts(
                df, 'Regional', ptype, charts_dir
            )
            count += 3
            print(f"    Generated 3 charts for {key}")

    # Submarket performance charts (7 submarkets × 2 types = 42 charts)
    for submarket in config.SUBMARKETS:
        for ptype in config.PROPERTY_TYPES:
            df = get_performance_data(data, submarket, ptype)
            if not df.empty:
                key = f"{submarket}_{ptype}"
                all_charts[key] = generate_performance_charts(
                    df, submarket, ptype, charts_dir
                )
                count += 3
                print(f"    Generated 3 charts for {key}")

    # Regional comparison charts (vacancy rate + avg rent for combined Industrial+Flex)
    for ptype in config.PROPERTY_TYPES:
        comparison_data = get_regional_comparison_data(data, ptype, config.SUBMARKETS)
        if comparison_data:
            # Vacancy rate comparison
            key_vac = f"regional_comparison_{ptype.lower()}_vacancy"
            path_vac = os.path.join(charts_dir, f"{key_vac}.png")
            fig_vac = build_regional_comparison_chart(
                comparison_data, 'total_vacancy_rate', config.SUBMARKETS
            )
            export_chart(fig_vac, path_vac, width=1100, height=340)
            all_charts[key_vac] = path_vac
            count += 1

            # Avg rent comparison
            key_rent = f"regional_comparison_{ptype.lower()}_rent"
            path_rent = os.path.join(charts_dir, f"{key_rent}.png")
            fig_rent = build_regional_comparison_chart(
                comparison_data, 'average_rental_rate', config.SUBMARKETS
            )
            export_chart(fig_rent, path_rent, width=1100, height=340)
            all_charts[key_rent] = path_rent
            count += 1

            print(f"    Generated 2 regional comparison charts for {ptype}")

    print(f"\n  Total charts generated: {count}")
    return all_charts
