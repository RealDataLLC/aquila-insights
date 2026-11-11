#!/usr/bin/env python3
"""
Election 2026 -- How Texas Counties Swung, Governor 2022 vs 2026.

One chart (charts/economic-indicators/election_texas_county_swing.html): each county's
Democratic minus Republican margin for Governor in 2022 (O'Rourke vs Abbott) and 2026
(Hinojosa vs Abbott), sorted by swing, with the Austin metro counties highlighted.

Reads data/election_texas_counties.csv (typed in, source URL and status per row). 2026
figures are unofficial county counts as of Nov 4-10, 2026; replace them with the canvassed
returns after the Nov 17 canvass deadline. Caldwell and Montgomery had no 2026 results posted
and are left out until they do.

Usage:
    python -m generators.economic.election_texas_counties
"""

import csv
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402

import plotly.graph_objects as go

from aquila.brand import NAVY, CONCRETE, COPPER
from aquila.charts import write_chart_html
from generators.economic.election import _style

OUT_DIR = os.path.join('charts', 'economic-indicators')
DATA = os.path.join('data', 'election_texas_counties.csv')


def _fmt(m):
    return f'D+{m:.0f}' if m >= 0.5 else f'R+{-m:.0f}' if m <= -0.5 else 'Even'


def _load():
    """{county: {'2022': margin, '2026': margin, 'austin': bool}}"""
    out = {}
    with open(DATA, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            c = out.setdefault(r['county'], {'austin': r['austin_metro'] == '1'})
            c[r['year']] = float(r['dem_pct']) - float(r['rep_pct'])
    return out


def chart_county_swing():
    print('\n[1] Texas county swing, Governor 2022 vs 2026...')
    data = _load()
    state = data.pop('Statewide')
    rows = sorted(data.items(), key=lambda kv: kv[1]['2026'] - kv[1]['2022'])  # biggest swing on top
    rows.append(('Statewide', state))
    for name, c in rows:
        print(f'    {name}: {_fmt(c["2022"])} -> {_fmt(c["2026"])}, swing {c["2026"] - c["2022"]:+.1f}')

    def label(name, c):
        flip = ' (flipped)' if c['2022'] < 0 < c['2026'] else ''
        if name == 'Statewide':
            return f'<b>Texas statewide</b>{flip}'
        return (f'<span style="color:{COPPER}"><b>{name}</b></span>' if c['austin'] else name) + flip

    y = [label(n, c) for n, c in rows]
    fig = go.Figure()
    for yi, (_, c) in zip(y, rows):
        fig.add_trace(go.Scatter(x=[c['2022'], c['2026']], y=[yi, yi], mode='lines', showlegend=False,
                                 line=dict(color=CONCRETE, width=3), hoverinfo='skip'))
    fig.add_trace(go.Scatter(
        x=[c['2022'] for _, c in rows], y=y, mode='markers', name='2022: O\'Rourke vs Abbott',
        marker=dict(symbol='diamond', size=12, color='white', line=dict(color=NAVY, width=2)),
        text=[_fmt(c['2022']) for _, c in rows], hovertemplate='%{y}<br>2022: %{text}<extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=[c['2026'] for _, c in rows], y=y, mode='markers+text', name='2026: Hinojosa vs Abbott',
        marker=dict(size=13, color=NAVY), text=[f'{_fmt(c["2026"])}  ({c["2026"] - c["2022"]:+.0f})'
                                                for _, c in rows],
        textposition='middle right', textfont=dict(size=11),
        hovertemplate='%{y}<br>2026: %{text}<extra></extra>',
    ))
    fig.add_vline(x=0, line=dict(color=NAVY, width=1))

    austin = [(n, c['2026'] - c['2022']) for n, c in rows if c['austin']]
    travis = dict(austin)['Travis']
    suburbs = sorted((s for n, s in austin if n != 'Travis'), reverse=True)
    flips = [n for n, c in rows if c['2022'] < 0 < c['2026'] and n != 'Statewide']
    _style(
        fig,
        f'Austin\'s Suburbs Swung {suburbs[-1]:.0f}-{suburbs[0]:.0f} Points Toward Democrats; Travis Moved Only {travis:.0f}',
        f'Governor, Democratic minus Republican margin, 2022 vs 2026 | Swing in parentheses | '
        f'Austin metro in copper | Flipped to Democrats: {", ".join(flips)}',
        'County election offices (2026, unofficial counts Nov 4-10, 2026; Hidalgo via The Monitor) and official 2022 '
        'returns via Wikipedia\'s county table; Texas SOS for statewide.<br>Caldwell and Montgomery had not posted '
        '2026 results. Travis started from D+47, so it had the least room to move.',
        hovermode='closest', height=720, margin=dict(l=200, r=60, t=120, b=150),
        legend=dict(orientation='v', yanchor='top', y=0.99, xanchor='right', x=0.99,
                    bgcolor='rgba(255,255,255,0.85)'),
    )
    fig.update_xaxes(title='Margin (points): Republican ahead <- 0 -> Democrat ahead', range=[-22, 66],
                     zeroline=False, gridcolor='#E8E8E8', tickvals=[-20, -10, 0, 10, 20, 30, 40, 50, 60],
                     ticktext=['R+20', 'R+10', '0', 'D+10', 'D+20', 'D+30', 'D+40', 'D+50', 'D+60'])
    fig.update_yaxes(gridcolor='rgba(0,0,0,0)')
    write_chart_html(fig, os.path.join(OUT_DIR, 'election_texas_county_swing.html'))
    print('  [OK] election_texas_county_swing.html')
    return fig


def main():
    print('=' * 60)
    print('Election 2026 -- How Texas Counties Swung')
    print('=' * 60)
    os.makedirs(OUT_DIR, exist_ok=True)
    chart_county_swing()


if __name__ == '__main__':
    main()
