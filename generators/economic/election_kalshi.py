#!/usr/bin/env python3
"""
Election 2026 -- How Close Was Kalshi?
3 charts grading Kalshi's prediction markets against the November 3, 2026 midterms,
using prices at the close of Nov 2, the day before the vote.

Charts (all in charts/economic-indicators/):
  1. election_kalshi_accuracy.html      -- Share of settled races the Nov 2 favorite won, by office
  2. election_kalshi_senate_odds.html   -- Nov 2 Democratic win odds in competitive Senate races vs who won
  3. election_kalshi_senate_seats.html  -- Nov 2 priced Democratic Senate seat count vs the result so far

Reads data/election_kalshi_nov2.csv, written by election_kalshi_fetch.py from Kalshi's
public API. Day-before prices keep election-night trading out of the grade; Kalshi's own
recap ("98% of races") graded on later prices. Alaska and Mississippi Senate were unsettled
as of Nov 5, 2026: when they settle, re-run the fetch, update SENATE_RESULT_SEATS, re-run this.

Usage:
    python -m generators.economic.election_kalshi_fetch   # refresh the CSV
    python -m generators.economic.election_kalshi
"""

import csv
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402

import plotly.graph_objects as go

from aquila.brand import AQUILA_COLORS, NAVY, GLASS_BLUE, CONCRETE, COPPER
from aquila.charts import write_chart_html
from generators.economic.election import _style

OUT_DIR = os.path.join('charts', 'economic-indicators')
DATA = os.path.join('data', 'election_kalshi_nov2.csv')
SIGNAL = AQUILA_COLORS[11]

# Plotly draws the first horizontal bar at the bottom.
OFFICES = ['Lieutenant Governor', 'Attorney General', 'Governor', 'Senate', 'House', 'Secretary of State']
# Senate races shown on chart 2: Democrat vs Republican markets with the Democrat priced in this band.
COMPETITIVE = (0.10, 0.90)
# Democratic Senate seats: 47 held + 7 flips called (IA, KS, OH, ME, NC, SC, TX); AK and MS unsettled.
SENATE_RESULT_SEATS = 54
SENATE_UNCALLED = 2

SNAPSHOT = 'Nov 2, 2026 close (midnight ET)'
SOURCE = 'Kalshi public market data, last trade at the Nov 2, 2026 close; settlement per Kalshi, as of Nov 5, 2026'


def _load():
    races = defaultdict(list)
    with open(DATA, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            r['price'] = float(r['price_nov2']) if r['price_nov2'] else None
            races[(r['office'], r['event_ticker'])].append(r)
    return races


def _grade(markets):
    """(favorite won, settled). A tie for favorite counts as a miss."""
    winners = [m for m in markets if m['result'] == 'yes']
    if len(winners) != 1:
        return None, False
    priced = [m for m in markets if m['price'] is not None]
    top = max(m['price'] for m in priced)
    favs = [m for m in priced if m['price'] == top]
    return len(favs) == 1 and favs[0] is winners[0], True


def _save(fig, name):
    write_chart_html(fig, os.path.join(OUT_DIR, name))
    print(f'  [OK] {name}')


def chart_accuracy(races):
    print('\n[1] Favorites won, by office...')
    tally = {o: [0, 0] for o in OFFICES}
    for (office, _), markets in races.items():
        if office not in tally:
            continue
        won, settled = _grade(markets)
        if settled:
            tally[office][0] += won
            tally[office][1] += 1
            if not won:
                print(f'    miss: {markets[0]["race"]}')
    accuracy = [(o, w, n) for o, (w, n) in tally.items() if n]
    labels = [f'{o}  ({w}/{n})' for o, w, n in accuracy]
    pct = [w / n * 100 for _, w, n in accuracy]
    total_w = sum(w for _, w, _ in accuracy)
    total_n = sum(n for _, _, n in accuracy)
    share = total_w / total_n
    print(f'    overall: {total_w}/{total_n} = {share:.1%}')

    fig = go.Figure(go.Bar(
        y=labels, x=pct, orientation='h',
        marker_color=[NAVY if p == 100 else GLASS_BLUE for p in pct],
        marker_line=dict(color=NAVY, width=1),
        text=[f'{p:.0f}%' for p in pct], textposition='outside',
        hovertemplate='%{y}: %{x:.1f}%<extra></extra>',
    ))
    fig.add_vline(x=share * 100, line=dict(color=COPPER, width=1.5, dash='dash'))
    _style(
        fig,
        f'The Day Before the Vote, Kalshi Favorites Won {share:.0%} of Races',
        f'Share of settled Nov 3, 2026 races won by the {SNAPSHOT} favorite | Copper line = all races, '
        f'{share:.0%} ({total_w}/{total_n})',
        f'{SOURCE}.<br>Kalshi\'s own recap reported 98%, graded on later prices. '
        f'Unsettled races and races with no market are excluded.',
        hovermode='closest', showlegend=False, margin=dict(l=200, r=60, t=110, b=140),
    )
    fig.update_xaxes(title='Favorite won (%)', range=[0, 108], ticksuffix='%', gridcolor='#E8E8E8')
    fig.update_yaxes(gridcolor='rgba(0,0,0,0)')
    _save(fig, 'election_kalshi_accuracy.html')


def chart_senate_odds(races):
    print('\n[2] Nov 2 Senate odds vs result...')
    rows = []
    for (office, _), markets in races.items():
        if office != 'Senate':
            continue
        dem = [m for m in markets if m['party'] == 'D']
        rep = [m for m in markets if m['party'] == 'R']
        if len(dem) != 1 or len(rep) != 1 or dem[0]['price'] is None:
            continue
        p = dem[0]['price']
        if not COMPETITIVE[0] <= p <= COMPETITIVE[1]:
            continue
        winner = next((m['party'] for m in markets if m['result'] == 'yes'), None)
        state = markets[0]['race'].replace(' Senate', '')
        rows.append((state, round(p * 100), winner))
    rows.sort(key=lambda r: r[1])
    for r in rows:
        print(f'    {r[0]}: D {r[1]}%, won {r[2] or "uncalled"}')
    misses = [s for s, p, w in rows if w and (p >= 50) != (w == 'D')]

    def color(p, w):
        if not w:
            return CONCRETE
        return NAVY if (p >= 50) == (w == 'D') else SIGNAL

    def label(p, w):
        if not w:
            return f'{p}%  Uncalled'
        if (p >= 50) != (w == 'D'):
            return f'{p}%  Missed: {"Democrat" if w == "D" else "Republican"} won'
        return f'{p}%'

    fig = go.Figure()
    fig.add_vrect(x0=0, x1=50, fillcolor=CONCRETE, opacity=0.08, line_width=0, layer='below')
    fig.add_vrect(x0=50, x1=100, fillcolor=GLASS_BLUE, opacity=0.25, line_width=0, layer='below')
    fig.add_trace(go.Bar(
        y=[s for s, _, _ in rows], x=[p for _, p, _ in rows], orientation='h',
        marker_color=[color(p, w) for _, p, w in rows],
        text=[label(p, w) for _, p, w in rows], textposition='outside',
        hovertemplate='%{y}: Democrat %{x}% on Kalshi<extra></extra>',
    ))
    fig.add_vline(x=50, line=dict(color=NAVY, width=1, dash='dot'))
    called = sum(1 for _, _, w in rows if w)
    title = ('Kalshi Had the Competitive Senate Races Right, Except ' + ' and '.join(misses)
             if misses else 'Kalshi Had Every Competitive Senate Race Right')
    _style(
        fig,
        title,
        f'Kalshi odds of a Democratic win, {SNAPSHOT} | Right of 50% = Democrat favored | '
        f'{called - len(misses)} of {called} called races right',
        f'{SOURCE}.<br>Democrat-vs-Republican races priced between {COMPETITIVE[0]:.0%} and '
        f'{COMPETITIVE[1]:.0%} for the Democrat.',
        hovermode='closest', showlegend=False, margin=dict(l=140, r=60, t=110, b=160),
    )
    fig.update_xaxes(title='Kalshi probability of a Democratic win (%)', range=[0, 100],
                     ticksuffix='%', gridcolor='#E8E8E8')
    _save(fig, 'election_kalshi_senate_odds.html')


def chart_senate_seats(races):
    print('\n[3] Priced Senate seats vs result...')
    markets = next(m for (o, _), m in races.items() if o == 'Senate seat count')
    buckets = {'50 or fewer': 0.0, '51': 0.0, '52': 0.0, '53+': 0.0}
    for m in markets:
        c = m['candidate']
        key = '53+' if c.startswith('Above') else c if c in buckets else '50 or fewer'
        buckets[key] += m['price'] or 0
    total = sum(buckets.values())  # last trades sum a little over 100%; scale to 100
    probs = [v / total * 100 for v in buckets.values()]
    print(f'    raw sum {total:.3f}; ' + ', '.join(f'{k} {p:.1f}%' for k, p in zip(buckets, probs)))

    fig = go.Figure(go.Bar(
        x=list(buckets), y=probs,
        marker_color=[CONCRETE, GLASS_BLUE, GLASS_BLUE, NAVY],
        text=[f'{p:.0f}%' for p in probs], textposition='outside',
        hovertemplate='%{x} seats: %{y:.1f}%<extra></extra>',
    ))
    result = f'{SENATE_RESULT_SEATS}' + (f'-{SENATE_RESULT_SEATS + SENATE_UNCALLED}' if SENATE_UNCALLED else '')
    fig.add_annotation(
        x='53+', y=probs[-1], yshift=40, showarrow=True, arrowhead=2, arrowcolor=COPPER, ax=0, ay=-50,
        text=f'<b>Result: {result} seats</b>' + (f'<br>{SENATE_UNCALLED} races uncalled' if SENATE_UNCALLED else ''),
        font=dict(size=12, color=COPPER),
    )
    _style(
        fig,
        f"The Senate Landed in Kalshi's Top Bucket, Priced at {probs[-1]:.0f}%",
        f'Kalshi odds for Democratic Senate seats, {SNAPSHOT} | Democrats held 47',
        f'{SOURCE}.<br>Market "How many Senate seats will Democrats hold"; last trades scaled to sum to 100%.',
        hovermode='closest', showlegend=False,
    )
    fig.update_xaxes(title='Democratic Senate seats')
    fig.update_yaxes(title='Kalshi probability (%)', range=[0, 80], ticksuffix='%')
    _save(fig, 'election_kalshi_senate_seats.html')


def main():
    print('=' * 60)
    print('Election 2026 -- How Close Was Kalshi?')
    print('=' * 60)
    os.makedirs(OUT_DIR, exist_ok=True)
    races = _load()
    chart_accuracy(races)
    chart_senate_odds(races)
    chart_senate_seats(races)


if __name__ == '__main__':
    main()
