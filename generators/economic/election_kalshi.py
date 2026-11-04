#!/usr/bin/env python3
"""
Election 2026 -- How Close Was Kalshi?
3 charts grading Kalshi's prediction markets against the November 3, 2026 midterms.

Charts (all in charts/economic-indicators/):
  1. election_kalshi_accuracy.html      -- Share of resolved races the market favorite won, by office
  2. election_kalshi_senate_odds.html   -- Final Democratic win odds in key Senate races vs who won
  3. election_kalshi_senate_seats.html  -- Priced Democratic Senate seat count vs the result so far

The figures are typed in from the sources below (no API). Results are as of the
morning of Nov 4, 2026 with Alaska and Mississippi Senate still uncalled; re-run
when they are, and update SENATE_RESULT_SEATS.

Usage:
    python -m generators.economic.election_kalshi
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402

import plotly.graph_objects as go

from aquila.brand import AQUILA_COLORS, NAVY, GLASS_BLUE, CONCRETE, COPPER
from aquila.charts import write_chart_html
from generators.economic.election import _style

OUT_DIR = os.path.join('charts', 'economic-indicators')
SIGNAL = AQUILA_COLORS[11]

# Kalshi recap, "2026 midterms recap" (news.kalshi.com), races resolved by 6:00 AM ET Nov 4.
# (office, favorites won, races resolved)
# Listed bottom-up (Plotly draws the first horizontal bar at the bottom).
ACCURACY = [
    ('Lieutenant Governor', 9, 10),
    ('Attorney General', 26, 27),
    ('Governor', 33, 34),
    ('Senate', 32, 33),
    ('House', 356, 360),
    ('Secretary of State', 23, 23),
]

# Kalshi "Final 2026 midterm odds" (Nov 2, noon ET): Democratic win probability.
# Winner from network calls Nov 3-4 (NBC, CNN, CBS). Only races Kalshi published odds for.
SENATE_ODDS = [
    ('South Carolina', 33, 'D'),
    ('Iowa', 52, 'D'),
    ('Kansas', 63, 'D'),
    ('Ohio', 71, 'D'),
    ('Maine', 73, 'D'),
    ('Michigan', 78, 'D'),
]

# Kalshi "2026 Midterm odds" (Oct 26): Democratic Senate seats after the election.
# The article prices 51, 52 and 53+; the remainder is 50 or fewer.
SENATE_SEATS_PRICED = [('50 or fewer', 32), ('51', 11), ('52', 18), ('53+', 39)]
# 47 held + 7 flips called (IA, KS, OH, ME, NC, SC, TX); AK and MS uncalled.
SENATE_RESULT_SEATS = 54
SENATE_UNCALLED = 2

SOURCE = 'Kalshi market data and recaps (news.kalshi.com); race calls from NBC News, CNN and CBS News, Nov 4, 2026'


def _save(fig, name):
    write_chart_html(fig, os.path.join(OUT_DIR, name))
    print(f'  [OK] {name}')


def chart_accuracy():
    print('\n[1] Favorites won, by office...')
    labels = [f'{o}  ({w}/{n})' for o, w, n in ACCURACY]
    pct = [w / n * 100 for _, w, n in ACCURACY]
    total_w = sum(w for _, w, _ in ACCURACY)
    total_n = sum(n for _, _, n in ACCURACY)
    print(f'    overall: {total_w}/{total_n} = {total_w / total_n:.1%}')

    fig = go.Figure(go.Bar(
        y=labels, x=pct, orientation='h',
        marker_color=[NAVY if p == 100 else GLASS_BLUE for p in pct],
        marker_line=dict(color=NAVY, width=1),
        text=[f'{p:.0f}%' for p in pct], textposition='outside',
        hovertemplate='%{y}: %{x:.1f}%<extra></extra>',
    ))
    fig.add_vline(x=total_w / total_n * 100, line=dict(color=COPPER, width=1.5, dash='dash'))
    _style(
        fig,
        'Kalshi Picked the Winner in 98% of Races',
        f'Share of resolved Nov 3, 2026 races won by the market favorite | Copper line = all races, '
        f'{total_w / total_n:.0%} ({total_w}/{total_n})',
        f'{SOURCE}. Kalshi\'s own count, races resolved by 6 AM ET Nov 4; not independently audited.',
        hovermode='closest', showlegend=False, margin=dict(l=200, r=60, t=110, b=120),
    )
    fig.update_xaxes(title='Favorite won (%)', range=[0, 108], ticksuffix='%', gridcolor='#E8E8E8')
    fig.update_yaxes(gridcolor='rgba(0,0,0,0)')
    _save(fig, 'election_kalshi_accuracy.html')


def chart_senate_odds():
    print('\n[2] Final Senate odds vs result...')
    states = [s for s, _, _ in SENATE_ODDS]
    odds = [p for _, p, _ in SENATE_ODDS]
    called = [(p >= 50) == (w == 'D') for _, p, w in SENATE_ODDS]

    fig = go.Figure()
    fig.add_vrect(x0=0, x1=50, fillcolor=CONCRETE, opacity=0.08, line_width=0, layer='below')
    fig.add_vrect(x0=50, x1=100, fillcolor=GLASS_BLUE, opacity=0.25, line_width=0, layer='below')
    fig.add_trace(go.Bar(
        y=states, x=odds, orientation='h',
        marker_color=[NAVY if c else SIGNAL for c in called],
        text=[f'{p}%' + ('' if c else '  Missed: Democrat won') for p, c in zip(odds, called)],
        textposition='outside',
        hovertemplate='%{y}: Democrat %{x}% on Kalshi<extra></extra>',
    ))
    fig.add_vline(x=50, line=dict(color=NAVY, width=1, dash='dot'))
    _style(
        fig,
        'Kalshi Had the Senate Toss-Ups Right, Except South Carolina',
        'Final Kalshi odds of a Democratic win, Nov 2 | Right of 50% = Democrat favored | Democrats won all six',
        f'{SOURCE}.<br>Races with published final odds only; Kalshi did not quantify TX, NC or GA.',
        hovermode='closest', showlegend=False, margin=dict(l=140, r=60, t=110, b=160),
    )
    fig.update_xaxes(title='Kalshi probability of a Democratic win (%)', range=[0, 100],
                     ticksuffix='%', gridcolor='#E8E8E8')
    _save(fig, 'election_kalshi_senate_odds.html')


def chart_senate_seats():
    print('\n[3] Priced Senate seats vs result...')
    buckets = [b for b, _ in SENATE_SEATS_PRICED]
    probs = [p for _, p in SENATE_SEATS_PRICED]
    fig = go.Figure(go.Bar(
        x=buckets, y=probs,
        marker_color=[CONCRETE, GLASS_BLUE, GLASS_BLUE, NAVY],
        text=[f'{p}%' for p in probs], textposition='outside',
        hovertemplate='%{x} seats: %{y}%<extra></extra>',
    ))
    result = f'{SENATE_RESULT_SEATS}' + (f'-{SENATE_RESULT_SEATS + SENATE_UNCALLED}' if SENATE_UNCALLED else '')
    fig.add_annotation(
        x='53+', y=probs[-1], yshift=40, showarrow=True, arrowhead=2, arrowcolor=COPPER, ax=0, ay=-50,
        text=f'<b>Result: {result} seats</b>' + (f'<br>{SENATE_UNCALLED} races uncalled' if SENATE_UNCALLED else ''),
        font=dict(size=12, color=COPPER),
    )
    _style(
        fig,
        "The Senate Landed in Kalshi's Top Bucket",
        'Kalshi odds for Democratic Senate seats, Oct 26, 2026 | 61% of the odds sat on 52 or fewer | Democrats held 47',
        f'{SOURCE}. "50 or fewer" is the remainder of the priced buckets.',
        hovermode='closest', showlegend=False,
    )
    fig.update_xaxes(title='Democratic Senate seats')
    fig.update_yaxes(title='Kalshi probability (%)', range=[0, 70], ticksuffix='%')
    _save(fig, 'election_kalshi_senate_seats.html')


def main():
    print('=' * 60)
    print('Election 2026 -- How Close Was Kalshi?')
    print('=' * 60)
    os.makedirs(OUT_DIR, exist_ok=True)
    chart_accuracy()
    chart_senate_odds()
    chart_senate_seats()


if __name__ == '__main__':
    main()
