#!/usr/bin/env python3
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402
"""
Create Office Market Metrics Charts
Generates vacancy rate, rental rate, and operating expense charts
for CBD, Northwest, Southwest, and The Domain (competitive set / micromarket).

Outputs 12 HTML charts to charts/office/:
  office_vacancy_rate_{submarket}.html   (line chart)
  office_rental_rate_{submarket}.html    (stacked bar: base rent + opex)
  office_opex_{submarket}.html           (line chart)

Usage:
    python create_office_market_metrics_charts.py

Quarterly update: just re-run this script whenever new data is in Supabase.
"""

import re
import os
import sys
import pandas as pd
import plotly.graph_objects as go
from dotenv import load_dotenv
from aquila_graphing_tools import (
    AQUILA_COLORS,
    AQUILA_FONT,
    commit_and_push_all,
)
from aquila.charts import write_chart_html

# Load environment
load_dotenv('aquila_graph.env')


def _get_supabase_client():
    """Use service role key via aquila package for full access to market_tables_office."""
    from aquila.connectors.supabase import get_supabase_client
    return get_supabase_client(use_service_role=True)

# -- Brand color aliases ------------------------------------------------------
NAVY           = AQUILA_COLORS[0]   # #172344
GLASS_BLUE     = AQUILA_COLORS[1]   # #C2DAF1
GLASS_BLUE_ALT = AQUILA_COLORS[2]   # #88ABC8
CONCRETE       = AQUILA_COLORS[3]   # #AAA9A8

# -- Submarket configuration ---------------------------------------------------
# Each entry: (display_name, aquila_micromarket, table_type, slug, line_color)
SUBMARKETS = [
    ('CBD',        'CBD',       'competitive set', 'cbd',       NAVY),
    ('Northwest',  'Northwest', 'competitive set', 'northwest', GLASS_BLUE),
    ('Southwest',  'Southwest', 'competitive set', 'southwest', GLASS_BLUE_ALT),
    ('The Domain', 'Domain',    'micromarket',     'domain',    CONCRETE),
]

OUTPUT_DIR = 'charts/office'


# -- Helpers -------------------------------------------------------------------

def _quarter_sort_key(q_str):
    """Convert '2025 Q4' -> sortable float 2025.4"""
    m = re.match(r'(\d{4})\s*[Qq](\d)', str(q_str))
    if m:
        return int(m.group(1)) + int(m.group(2)) / 10
    return 0


def _shared_layout(title_text, y_title):
    """Return a shared Plotly layout dict with AQUILA branding."""
    return dict(
        title=dict(
            text=title_text,
            font=dict(family=AQUILA_FONT, size=18, color=NAVY),
            x=0.5,
            xanchor='center',
        ),
        xaxis=dict(
            title='',
            tickfont=dict(family=AQUILA_FONT, size=11, color=NAVY),
            showgrid=False,
            linecolor='#E8E8E8',
            tickangle=-45,
        ),
        yaxis=dict(
            title=y_title,
            title_font=dict(family=AQUILA_FONT, size=12, color=NAVY),
            tickfont=dict(family=AQUILA_FONT, size=11, color=NAVY),
            gridcolor='#E8E8E8',
            zeroline=False,
        ),
        legend=dict(
            font=dict(family=AQUILA_FONT, size=11, color=NAVY),
            bgcolor='white',
            bordercolor='#E8E8E8',
            borderwidth=1,
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, color=NAVY),
        height=550,
        margin=dict(l=70, r=40, t=80, b=80),
        hovermode='x unified',
    )


# -- Data fetching -------------------------------------------------------------

def fetch_data(supabase):
    """
    Load market_tables_office for all 4 submarkets.
    Returns a dict keyed by slug -> DataFrame (sorted ascending by quarter).
    """
    print("Querying market_tables_office...")
    response = (
        supabase.table('market_tables_office')
        .select('aquila_micromarket, table_type, quarter, total_vacancy_rate, average_rental_rate, average_opex')
        .execute()
    )
    df_all = pd.DataFrame(response.data)
    print(f"  Total rows loaded: {len(df_all)}")

    for col in ['total_vacancy_rate', 'average_rental_rate', 'average_opex']:
        df_all[col] = pd.to_numeric(df_all[col], errors='coerce')

    df_all['_sort'] = df_all['quarter'].apply(_quarter_sort_key)
    df_all = df_all.sort_values('_sort').reset_index(drop=True)

    result = {}
    for display_name, micro, ttype, slug, _ in SUBMARKETS:
        mask = (df_all['aquila_micromarket'] == micro) & (df_all['table_type'] == ttype)
        sub = df_all[mask].copy().reset_index(drop=True)
        print(f"  {display_name} ({ttype}): {len(sub)} rows, "
              f"quarters {sub['quarter'].iloc[0] if len(sub) else 'n/a'} – "
              f"{sub['quarter'].iloc[-1] if len(sub) else 'n/a'}")
        result[slug] = sub

    return result


# -- Chart builders ------------------------------------------------------------

def build_vacancy_chart(df, display_name, line_color, y_range=None, dtick=None):
    """Line chart — total vacancy rate over time."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['quarter'],
        y=df['total_vacancy_rate'],
        mode='lines',
        name='Vacancy Rate',
        line=dict(color=line_color, width=2.5),
        hovertemplate='Quarter: %{x}<br>Vacancy Rate: %{y:.1%}<extra></extra>',
    ))
    layout = _shared_layout(
        title_text=f'{display_name} — Vacancy Rate',
        y_title='Total Vacancy Rate',
    )
    layout['yaxis']['tickformat'] = '.0%'
    layout['yaxis']['rangemode'] = 'tozero'
    if y_range is not None:
        layout['yaxis']['range'] = y_range
    if dtick is not None:
        layout['yaxis']['dtick'] = dtick
    fig.update_layout(**layout)
    return fig


def build_rental_chart(df, display_name, y_range=None, dtick=None):
    """Stacked bar chart — base rent (bottom, Navy) + opex (top, Concrete)."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df['quarter'],
        y=df['average_rental_rate'],
        name='Base Rent',
        marker_color=NAVY,
        hovertemplate='Quarter: %{x}<br>Base Rent: $%{y:.2f}/SF<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        x=df['quarter'],
        y=df['average_opex'],
        name='Opex',
        marker_color=GLASS_BLUE,
        hovertemplate='Quarter: %{x}<br>Opex: $%{y:.2f}/SF<extra></extra>',
    ))
    layout = _shared_layout(
        title_text=f'{display_name} — Full Service Rent',
        y_title='Rent ($/SF/YR)',
    )
    layout['yaxis']['tickprefix'] = '$'
    if y_range is not None:
        layout['yaxis']['range'] = y_range
    if dtick is not None:
        layout['yaxis']['dtick'] = dtick
    layout['barmode'] = 'stack'
    layout['bargap'] = 0.3
    layout['legend'] = dict(
        font=dict(family=AQUILA_FONT, size=11, color=NAVY),
        bgcolor='white',
        bordercolor='#E8E8E8',
        borderwidth=1,
        orientation='h',
        yanchor='top',
        y=-0.2,
        xanchor='center',
        x=0.5,
    )
    fig.update_layout(**layout)
    return fig


def build_opex_chart(df, display_name, line_color, y_range=None, dtick=None):
    """Line chart — average operating expenses over time."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['quarter'],
        y=df['average_opex'],
        mode='lines',
        name='Operating Expenses',
        line=dict(color=line_color, width=2.5),
        hovertemplate='Quarter: %{x}<br>Opex: $%{y:.2f}/SF<extra></extra>',
    ))
    layout = _shared_layout(
        title_text=f'{display_name} — Operating Expenses',
        y_title='Opex ($/SF/YR)',
    )
    layout['yaxis']['tickprefix'] = '$'
    if y_range is not None:
        layout['yaxis']['range'] = y_range
    if dtick is not None:
        layout['yaxis']['dtick'] = dtick
    fig.update_layout(**layout)
    return fig


# -- Main ----------------------------------------------------------------------

def main():
    print("=" * 60)
    print("GENERATING: Office Market Metrics Charts (12 charts)")
    print("=" * 60)

    try:
        supabase = _get_supabase_client()
        print("Connected to Supabase\n")

        data = fetch_data(supabase)

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        charts_saved = []

        # -- Standardized y-axis scales for cross-submarket comparison ---
        # Vacancy: auto-scale to data (no fixed range)
        # Rental rate: CBD/NW/SW share $0-$70 in $10 increments; Domain uses auto
        RENT_RANGE_SHARED = [0, 70]
        RENT_DTICK_SHARED = 10
        # Opex: CBD/NW/SW share $10-$25 in $5 increments; Domain uses auto
        OPEX_RANGE_SHARED = [10, 25]
        OPEX_DTICK_SHARED = 5

        domain_slug = 'domain'

        print("\nBuilding charts...")
        for display_name, _micro, _ttype, slug, line_color in SUBMARKETS:
            df = data[slug]
            if df.empty:
                print(f"  WARNING: No data for {display_name} — skipping")
                continue

            is_domain = (slug == domain_slug)

            # Vacancy rate — auto-scale to data
            path = os.path.join(OUTPUT_DIR, f'office_vacancy_rate_{slug}.html')
            fig = build_vacancy_chart(
                df, display_name, line_color,
            )
            write_chart_html(fig, path)
            charts_saved.append(path)
            print(f"  Saved: {path}")

            # Rental rate (stacked bar: base + opex) — Domain uses own scale
            path = os.path.join(OUTPUT_DIR, f'office_rental_rate_{slug}.html')
            fig = build_rental_chart(
                df, display_name,
                y_range=None if is_domain else RENT_RANGE_SHARED,
                dtick=None if is_domain else RENT_DTICK_SHARED,
            )
            write_chart_html(fig, path)
            charts_saved.append(path)
            print(f"  Saved: {path}")

            # Operating expenses — Domain uses own scale
            path = os.path.join(OUTPUT_DIR, f'office_opex_{slug}.html')
            fig = build_opex_chart(
                df, display_name, line_color,
                y_range=None if is_domain else OPEX_RANGE_SHARED,
                dtick=None if is_domain else OPEX_DTICK_SHARED,
            )
            write_chart_html(fig, path)
            charts_saved.append(path)
            print(f"  Saved: {path}")

        print(f"\nTotal charts saved: {len(charts_saved)}")

        print("\nCommitting and pushing to GitHub...")
        commit_and_push_all("Add office market metrics charts (vacancy, rent, opex by submarket)")
        print("Done.")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
