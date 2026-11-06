#!/usr/bin/env python3
"""
Election 2026 -- How Close Was Kalshi?
4 charts grading Kalshi's prediction markets against the November 3, 2026 midterms,
using closing prices one month out (Oct 3), one week out (Oct 27) and the day before (Nov 2).

Charts (all in charts/economic-indicators/):
  1. election_kalshi_accuracy.html        -- Share of settled races the Nov 2 favorite won, by office
  2. election_kalshi_accuracy_trend.html  -- Favorites won vs average favorite price, at each snapshot
  3. election_kalshi_senate_odds.html     -- Democratic win odds in competitive Senate races, at each snapshot
  4. election_kalshi_senate_seats.html    -- Priced Democratic Senate seat count at each snapshot vs the result

Reads data/election_kalshi_prices.csv, written by election_kalshi_fetch.py from Kalshi's
public API. Pre-vote prices keep election-night trading out of the grade; Kalshi's own
recap ("98% of races") graded on later prices. Alaska and Mississippi Senate were unsettled
as of Nov 6, 2026: when they settle, re-run the fetch, update SENATE_RESULT_SEATS, re-run this.

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
DATA = os.path.join('data', 'election_kalshi_prices.csv')
SIGNAL = AQUILA_COLORS[11]

# Snapshot label in the CSV -> chart label and color, earliest first.
SNAPSHOTS = {
    '2026-10-03': ('One month out (Oct 3)', CONCRETE),
    '2026-10-27': ('One week out (Oct 27)', GLASS_BLUE),
    '2026-11-02': ('Day before (Nov 2)', NAVY),
}
DAY = '2026-11-02'

# Plotly draws the first horizontal bar at the bottom.
OFFICES = ['Lieutenant Governor', 'Attorney General', 'Governor', 'Senate', 'House', 'Secretary of State']
# Senate races on the odds chart: Democrat vs Republican, Democrat priced in this band on Nov 2.
COMPETITIVE = (0.10, 0.90)
# Democratic Senate seats: 47 held + 7 flips called (IA, KS, OH, ME, NC, SC, TX); AK and MS unsettled.
SENATE_RESULT_SEATS = 54
SENATE_UNCALLED = 2

SOURCE = 'Kalshi public market data, last trade at each day\'s close (midnight ET); settlement per Kalshi, as of Nov 6, 2026'


def _load():
    """{snapshot: {(office, event_ticker): [market rows]}}"""
    snaps = defaultdict(lambda: defaultdict(list))
    with open(DATA, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            r['price'] = float(r['price']) if r['price'] else None
            snaps[r['snapshot']][(r['office'], r['event_ticker'])].append(r)
    return snaps


def _favorite(markets):
    """(favorite market or None on a tie / no prices, its price)."""
    priced = [m for m in markets if m['price'] is not None]
    if not priced:
        return None, None
    top = max(m['price'] for m in priced)
    favs = [m for m in priced if m['price'] == top]
    return (favs[0] if len(favs) == 1 else None), top


def _winner(markets):
    winners = [m for m in markets if m['result'] == 'yes']
    return winners[0] if len(winners) == 1 else None


def _graded(races):
    """Settled races with a price: [(office, race name, favorite won, favorite price)]."""
    out = []
    for (office, _), markets in races.items():
        if office not in OFFICES:
            continue
        winner = _winner(markets)
        fav, price = _favorite(markets)
        if winner is None or price is None:
            continue
        out.append((office, markets[0]['race'], fav is not None and fav['market_ticker'] == winner['market_ticker'], price))
    return out


def _save(fig, name):
    write_chart_html(fig, os.path.join(OUT_DIR, name))
    print(f'  [OK] {name}')


def chart_accuracy(snaps):
    print('\n[1] Nov 2 favorites won, by office...')
    graded = _graded(snaps[DAY])
    tally = {o: [0, 0] for o in OFFICES}
    for office, race, won, _ in graded:
        tally[office][0] += won
        tally[office][1] += 1
        if not won:
            print(f'    miss: {race}')
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
        f'Share of settled Nov 3, 2026 races won by the Nov 2 closing favorite | Copper line = all races, '
        f'{share:.0%} ({total_w}/{total_n})',
        f'{SOURCE}.<br>Kalshi\'s own recap reported 98%, graded on later prices. '
        f'Unsettled races and races with no market are excluded.',
        hovermode='closest', showlegend=False, margin=dict(l=200, r=60, t=110, b=140),
    )
    fig.update_xaxes(title='Favorite won (%)', range=[0, 108], ticksuffix='%', gridcolor='#E8E8E8')
    fig.update_yaxes(gridcolor='rgba(0,0,0,0)')
    _save(fig, 'election_kalshi_accuracy.html')


def chart_accuracy_trend(snaps):
    print('\n[2] Favorites won at each snapshot...')
    labels, won, priced, counts = [], [], [], []
    for snap, (label, _) in SNAPSHOTS.items():
        graded = _graded(snaps[snap])
        w = sum(g[2] for g in graded)
        n = len(graded)
        labels.append(label)
        won.append(w / n * 100)
        priced.append(sum(g[3] for g in graded) / n * 100)
        counts.append((w, n))
        print(f'    {label}: {w}/{n} = {w / n:.1%}, avg favorite price {priced[-1]:.1f}c')

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels, y=won, name='Favorite won', marker_color=NAVY,
        text=[f'{p:.1f}%<br>({w}/{n})' for p, (w, n) in zip(won, counts)], textposition='outside',
        hovertemplate='%{x}: favorite won %{y:.1f}%<extra></extra>',
    ))
    fig.add_trace(go.Bar(
        x=labels, y=priced, name='Average favorite price (implied odds)', marker_color=GLASS_BLUE,
        text=[f'{p:.0f}%' for p in priced], textposition='outside',
        hovertemplate='%{x}: favorites priced at %{y:.1f}% on average<extra></extra>',
    ))
    _style(
        fig,
        f'Kalshi Favorites Won {won[0]:.1f}% of Races a Month Out and {won[-1]:.1f}% the Day Before',
        'Settled Nov 3, 2026 races, graded on each day\'s closing prices | '
        'Favorites won slightly more often than their prices implied',
        f'{SOURCE}.<br>All Senate, Governor, AG, SoS, Lt. Governor and House races Kalshi listed; '
        f'unsettled races excluded.',
        hovermode='closest', barmode='group', bargap=0.3,
    )
    fig.update_yaxes(title='Share of races (%)', range=[80, 101], ticksuffix='%')
    _save(fig, 'election_kalshi_accuracy_trend.html')


def chart_senate_odds(snaps):
    print('\n[3] Senate odds at each snapshot vs result...')
    rows = []
    for key, markets in snaps[DAY].items():
        if key[0] != 'Senate':
            continue
        dem = [m for m in markets if m['party'] == 'D']
        rep = [m for m in markets if m['party'] == 'R']
        if len(dem) != 1 or len(rep) != 1 or dem[0]['price'] is None:
            continue
        if not COMPETITIVE[0] <= dem[0]['price'] <= COMPETITIVE[1]:
            continue
        winner = _winner(markets)
        odds = {}
        for snap in SNAPSHOTS:
            d = [m for m in snaps[snap][key] if m['party'] == 'D']
            odds[snap] = round(d[0]['price'] * 100) if d and d[0]['price'] is not None else None
        rows.append((markets[0]['race'].replace(' Senate', ''), odds, winner['party'] if winner else None))
    rows.sort(key=lambda r: r[1][DAY])

    def result(odds, w):
        if not w:
            return 'uncalled'
        return f'{w} won' + ('' if (odds[DAY] >= 50) == (w == 'D') else ', missed')

    for state, odds, w in rows:
        print(f'    {state}: ' + ' -> '.join(str(v) for v in odds.values()) + f'  ({result(odds, w)})')
    ylabels = [f'{s}  ({result(o, w)})' for s, o, w in rows]
    misses = [s for s, o, w in rows if w and (o[DAY] >= 50) != (w == 'D')]
    week = '2026-10-27'
    flipped = [s for s, o, w in rows if None not in (o[week], o[DAY]) and (o[week] >= 50) != (o[DAY] >= 50)]

    fig = go.Figure()
    fig.add_vrect(x0=0, x1=50, fillcolor=CONCRETE, opacity=0.08, line_width=0, layer='below')
    fig.add_vrect(x0=50, x1=100, fillcolor=GLASS_BLUE, opacity=0.25, line_width=0, layer='below')
    for (s, o, _), y in zip(rows, ylabels):
        xs = [v for v in o.values() if v is not None]
        fig.add_trace(go.Scatter(x=[min(xs), max(xs)], y=[y, y], mode='lines', showlegend=False,
                                 line=dict(color=CONCRETE, width=2), hoverinfo='skip'))
    for snap, (label, color) in SNAPSHOTS.items():
        fig.add_trace(go.Scatter(
            x=[o[snap] for _, o, _ in rows], y=ylabels, mode='markers', name=label,
            marker=dict(color=color, size=12 if snap == DAY else 10, line=dict(color='white', width=1)),
            hovertemplate=f'%{{y}}<br>{label}: Democrat %{{x}}%<extra></extra>',
        ))
    fig.add_vline(x=50, line=dict(color=NAVY, width=1, dash='dot'))
    title = ('By Nov 2, Kalshi Had the Competitive Senate Races Right, Except ' + ' and '.join(misses)
             if misses else 'By Nov 2, Kalshi Had Every Competitive Senate Race Right')
    subtitle = f'Kalshi odds of a Democratic win at each day\'s close | Right of 50% = Democrat favored'
    if flipped:
        subtitle += f' | {" and ".join(flipped)} flipped to the Democrat in the final week'
    _style(
        fig, title, subtitle,
        f'{SOURCE}.<br>Democrat-vs-Republican races priced between {COMPETITIVE[0]:.0%} and '
        f'{COMPETITIVE[1]:.0%} for the Democrat on Nov 2.',
        hovermode='closest', margin=dict(l=220, r=60, t=110, b=170),
        legend=dict(orientation='h', yanchor='top', y=-0.12, xanchor='center', x=0.5),
    )
    fig.update_xaxes(title='Kalshi probability of a Democratic win (%)', range=[0, 100],
                     ticksuffix='%', gridcolor='#E8E8E8')
    fig.update_yaxes(gridcolor='#F0F0F0')
    _save(fig, 'election_kalshi_senate_odds.html')


def chart_senate_seats(snaps):
    print('\n[4] Priced Senate seats at each snapshot vs result...')
    buckets = ['50 or fewer', '51', '52', '53+']
    fig = go.Figure()
    top = {}
    for snap, (label, color) in SNAPSHOTS.items():
        markets = next(m for (o, _), m in snaps[snap].items() if o == 'Senate seat count')
        b = dict.fromkeys(buckets, 0.0)
        for m in markets:
            c = m['candidate']
            b['53+' if c.startswith('Above') else c if c in b else '50 or fewer'] += m['price'] or 0
        total = sum(b.values())  # last trades sum a little over 100%; scale to 100
        probs = [v / total * 100 for v in b.values()]
        top[snap] = probs[-1]
        print(f'    {label}: raw sum {total:.3f}; ' + ', '.join(f'{k} {p:.0f}%' for k, p in zip(buckets, probs)))
        fig.add_trace(go.Bar(
            x=buckets, y=probs, name=label, marker_color=color,
            text=[f'{p:.0f}%' for p in probs], textposition='outside',
            hovertemplate=f'{label}<br>%{{x}} seats: %{{y:.1f}}%<extra></extra>',
        ))
    result = f'{SENATE_RESULT_SEATS}' + (f'-{SENATE_RESULT_SEATS + SENATE_UNCALLED}' if SENATE_UNCALLED else '')
    fig.add_annotation(
        x='53+', y=max(top.values()), yshift=40, showarrow=True, arrowhead=2, arrowcolor=COPPER, ax=0, ay=-50,
        text=f'<b>Result: {result} seats</b>' + (f'<br>{SENATE_UNCALLED} races uncalled' if SENATE_UNCALLED else ''),
        font=dict(size=12, color=COPPER),
    )
    first = list(SNAPSHOTS)[0]
    _style(
        fig,
        f"Kalshi Priced the Senate Result at {top[first]:.0f}% a Month Out, {top[DAY]:.0f}% the Day Before",
        'Kalshi odds for Democratic Senate seats at each day\'s close | Democrats held 47 before the election',
        f'{SOURCE}.<br>Market "How many Senate seats will Democrats hold"; last trades scaled to sum to 100%.',
        hovermode='closest', barmode='group', bargap=0.25,
    )
    fig.update_xaxes(title='Democratic Senate seats')
    fig.update_yaxes(title='Kalshi probability (%)', range=[0, 80], ticksuffix='%')
    _save(fig, 'election_kalshi_senate_seats.html')


def main():
    print('=' * 60)
    print('Election 2026 -- How Close Was Kalshi?')
    print('=' * 60)
    os.makedirs(OUT_DIR, exist_ok=True)
    snaps = _load()
    chart_accuracy(snaps)
    chart_accuracy_trend(snaps)
    chart_senate_odds(snaps)
    chart_senate_seats(snaps)


if __name__ == '__main__':
    main()
