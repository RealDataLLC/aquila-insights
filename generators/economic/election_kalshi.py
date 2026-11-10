#!/usr/bin/env python3
"""
Election 2026 -- How Close Was Kalshi?
8 charts grading Kalshi's prediction markets against the November 3, 2026 midterms,
using closing prices one month out (Oct 3), one week out (Oct 27) and the day before (Nov 2).

Charts (all in charts/economic-indicators/):
  1. election_kalshi_accuracy.html        -- Share of settled races the Nov 2 favorite won, by office
  2. election_kalshi_accuracy_trend.html  -- Favorites won vs average favorite price, at each snapshot
  3. election_kalshi_senate_odds.html     -- Democratic win odds in competitive Senate races, at each snapshot
  4. election_kalshi_senate_seats.html    -- Priced Democratic Senate seat count at each snapshot vs the result
  5. election_kalshi_misses.html          -- Where the week-out and day-before favorites lost, by state
  6. election_kalshi_calibration.html     -- Favorites' win rate vs their price, by price band
  7. election_kalshi_texas_money.html     -- Money traded on Kalshi's Texas races vs campaign money
  8. election_kalshi_texas_polls.html     -- Texas final poll margins vs results, with Kalshi's favorite

Reads data/election_kalshi_prices.csv, written by election_kalshi_fetch.py from Kalshi's
public API. Pre-vote prices keep election-night trading out of the grade; Kalshi's own
recap ("98% of races") graded on later prices. Alaska and Mississippi Senate were still
unsettled on Kalshi as of Nov 10, 2026: when they settle, re-run the fetch, update
SENATE_RESULT_SEATS, re-run this.

Chart 7 also reads data/election_kalshi_texas_volume.csv (same fetch). Campaign money is typed
in below (TX_CAMPAIGN_MONEY) from FEC and Texas Ethics Commission reporting; refresh it after
the FEC post-general reports (due Dec 3, 2026).

Chart 8 reads data/election_texas_polls.csv (poll averages, polls and reported results, typed in with a
source URL per row). Results there are as reported Nov 6-10, 2026 and not certified: replace them with the
Texas Secretary of State canvass when it is published.

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

SOURCE = 'Kalshi public market data, last trade at each day\'s close (midnight ET); settlement per Kalshi, as of Nov 10, 2026'
WEEK = '2026-10-27'
TX_VOLUME = os.path.join('data', 'election_kalshi_texas_volume.csv')

# Campaign money per Texas race with a Kalshi market, $M:
# event ticker -> (label, Democrat $, Republican $, basis). Candidate committees only: outside groups
# are left out because Kalshi is compared with what the campaigns themselves raised.
# Senate and TX-23: FEC receipts, cycle to Oct 14, 2026 (pre-general report).
# Governor: spending Oct 15, 2025-Oct 24, 2026 (Texas Tribune, from TEC filings).
# Lt. Governor: cycle receipts (Houston Chronicle, from TEC filings).
# AG: lower bounds. Middleton's $16.8M self-funding through the May runoff + $3.37M raised Jul-Oct;
# Johnson's Jan-Jun ($0.98M) + Jul-Oct ($1.09M) reports.
TX_CAMPAIGN_MONEY = {
    'SENATETX-26': ('Senate: Talarico (D) vs Paxton (R)', 146.35, 22.33, 'raised'),
    'GOVPARTYTX-26': ('Governor: Hinojosa (D) vs Abbott (R)', 36.8, 281.0, 'spent'),
    'KXLTGOVTX-26': ('Lt. Governor: Goodwin (D) vs Patrick (R)', 3.1, 26.7, 'raised'),
    'KXATTYGENTX-26': ('Attorney General: Johnson (D) vs Middleton (R)', 2.07, 20.17, 'raised, at least'),
    'KXHOUSERACE-TX23-26': ('TX-23 House: Padilla Stout (D) vs Herrera (R)', 1.12, 3.12, 'raised'),
}


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


STATE_ABBR = {
    'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA', 'Colorado': 'CO',
    'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID',
    'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA',
    'Maine': 'ME', 'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN',
    'Mississippi': 'MS', 'Missouri': 'MO', 'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV',
    'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC',
    'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA',
    'Rhode Island': 'RI', 'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX',
    'Utah': 'UT', 'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV',
    'Wisconsin': 'WI', 'Wyoming': 'WY',
}


def _state(office, race):
    """Two-letter state from a race name ('AL-02 House', 'West Virginia Senate')."""
    if office == 'House':
        return race[:2]
    for name in sorted(STATE_ABBR, key=len, reverse=True):
        if race.startswith(name + ' '):
            return STATE_ABBR[name]
    return race


def _results(races):
    """Settled races: [(office, race, state, favorite won, favorite price, favorite party, winner party)]."""
    out = []
    for (office, _), markets in races.items():
        if office not in OFFICES:
            continue
        winner = _winner(markets)
        fav, price = _favorite(markets)
        if winner is None or price is None:
            continue
        race = markets[0]['race']
        won = fav is not None and fav['market_ticker'] == winner['market_ticker']
        out.append((office, race, _state(office, race), won, price, fav['party'] if fav else '', winner['party']))
    return out


def _money(v):
    return f'${v:,.0f}M' if v >= 10 else f'${v:,.1f}M' if v >= 1 else f'${v * 1000:,.0f}K'


def chart_misses(snaps):
    print('\n[5] Where the favorites lost, week out and day before...')
    per = {}
    for snap in (WEEK, DAY):
        res = _results(snaps[snap])
        misses = [r for r in res if not r[3]]
        per[snap] = (res, misses)
        print(f'    {SNAPSHOTS[snap][0]}: {len(misses)} misses of {len(res)}')
        for m in sorted(misses, key=lambda m: (m[2], m[1])):
            print(f'      {m[1]}: {m[5]} favorite at {m[4]:.0%}, {m[6]} won')
    states = defaultdict(lambda: {WEEK: [], DAY: []})
    for snap in (WEEK, DAY):
        for m in per[snap][1]:
            states[m[2]][snap].append((m[1], m[4]))
    order = sorted(states, key=lambda s: (len(states[s][DAY]), len(states[s][WEEK]), s))
    most = len(states[order[-1]][DAY])
    top = sorted(s for s in order if len(states[s][DAY]) == most)

    fig = go.Figure()
    for snap in (WEEK, DAY):
        label, color = SNAPSHOTS[snap]
        fig.add_trace(go.Bar(
            y=order, x=[len(states[s][snap]) for s in order], orientation='h', name=label, marker_color=color,
            marker_line=dict(color=NAVY, width=1),
            text=[len(states[s][snap]) or '' for s in order], textposition='outside',
            customdata=['<br>'.join(f'{r} (favorite at {p:.0%})' for r, p in states[s][snap]) or 'none'
                        for s in order],
            hovertemplate=f'%{{y}}, {label}<br>%{{customdata}}<extra></extra>',
        ))
    wk, dy = per[WEEK], per[DAY]
    every_r = all(m[5] == 'R' and m[6] == 'D' for snap in (WEEK, DAY) for m in per[snap][1])
    _style(
        fig,
        f'Kalshi Favorites Lost {len(dy[1])} Races the Day Before, Most in ' + ' and '.join(top),
        f'Races where the closing favorite lost, by state | Week out: {len(wk[1])} of {len(wk[0])} '
        f'({len(wk[1]) / len(wk[0]):.1%}) | Day before: {len(dy[1])} of {len(dy[0])} '
        f'({len(dy[1]) / len(dy[0]):.1%})'
        + ('<br>Every miss was a Republican favorite beaten by a Democrat' if every_r else ''),
        f'{SOURCE}.<br>Senate, Governor, AG, SoS, Lt. Governor and House races; hover a bar for the races. '
        f'Unsettled races excluded.',
        hovermode='closest', barmode='group', bargap=0.25, height=640, margin=dict(l=80, r=60, t=130, b=150),
    )
    fig.update_xaxes(title='Races where the favorite lost', dtick=1, gridcolor='#E8E8E8')
    fig.update_yaxes(gridcolor='rgba(0,0,0,0)')
    _save(fig, 'election_kalshi_misses.html')


BANDS = [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.01)]


def chart_calibration(snaps):
    print('\n[6] Favorite win rate vs price, by band...')
    labels = [f'{lo:.0%}-{min(hi, 1):.0%}' for lo, hi in BANDS]
    fig = go.Figure()
    counts_by = {}
    for snap in (WEEK, DAY):
        label, color = SNAPSHOTS[snap]
        res = _results(snaps[snap])
        won, priced, counts = [], [], []
        for lo, hi in BANDS:
            band = [r for r in res if lo <= r[4] < hi]
            w = sum(r[3] for r in band)
            won.append(w / len(band) * 100 if band else None)
            priced.append(sum(r[4] for r in band) / len(band) * 100 if band else None)
            counts.append((w, len(band)))
        counts_by[snap] = counts
        print(f'    {label}: ' + '; '.join(f'{lb} won {w}/{n}' for lb, (w, n) in zip(labels, counts)))
        fig.add_trace(go.Bar(
            x=labels, y=won, name=f'{label}: favorite won', marker_color=color, offsetgroup=snap,
            marker_line=dict(color=NAVY, width=1),
            text=[f'{p:.0f}%<br>({w}/{n})' if n else '' for p, (w, n) in zip(won, counts)],
            textposition='inside', insidetextanchor='start',  # at the bar's foot, clear of the diamonds
            textfont=dict(color='white' if snap == DAY else NAVY),
            hovertemplate=f'{label}<br>Favorites priced %{{x}}: won %{{y:.0f}}%<extra></extra>',
        ))
        fig.add_trace(go.Scatter(
            x=labels, y=priced, mode='markers', name=f'{label}: average price (implied odds)', offsetgroup=snap,
            marker=dict(symbol='diamond', size=11, color=COPPER if snap == DAY else 'white',
                        line=dict(color=COPPER, width=2)),
            hovertemplate=f'{label}<br>%{{x}}: priced %{{y:.0f}}% on average<extra></extra>',
        ))
    (w5, n5), (w6, n6) = counts_by[DAY][:2]
    _style(
        fig,
        f'Day-Before Favorites Priced at 50-70% Won Only {w5 + w6} of {n5 + n6} Races',
        'Favorite win rate by closing price, one week out and the day before | '
        'Diamonds = odds the price implied; bars = share that won',
        f'{SOURCE}.<br>Each settled race counted once, at its favorite\'s price. '
        f'Favorites priced 90% or higher won every race.',
        hovermode='closest', barmode='group', bargap=0.25,
        legend=dict(orientation='v', yanchor='top', y=0.99, xanchor='left', x=0.01,
                    bgcolor='rgba(255,255,255,0.85)'),
        scattermode='group',
    )
    fig.update_xaxes(title="Favorite's Kalshi price")
    fig.update_yaxes(title='Share of races (%)', range=[0, 105], ticksuffix='%')
    _save(fig, 'election_kalshi_calibration.html')


def chart_texas_money(snaps):
    print('\n[7] Kalshi money vs campaign money, Texas...')
    vol = defaultdict(lambda: [0.0, 0.0])
    with open(TX_VOLUME, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            vol[r['event_ticker']][0] += float(r['contracts']) / 1e6
            vol[r['event_ticker']][1] += float(r['open_interest']) / 1e6
    day = {e: m for (_, e), m in snaps[DAY].items()}
    rows = []
    for ticker, (label, d, r, basis) in TX_CAMPAIGN_MONEY.items():
        traded, payout = vol[ticker]
        fav, price = _favorite(day[ticker])
        win = _winner(day[ticker])
        call = (f'{"Democrat" if fav["party"] == "D" else "Republican"} favored at {price:.0%} the day before; '
                f'{"Democrat" if win["party"] == "D" else "Republican"} won')
        rows.append(dict(label=f'{label}<br><sup>{call}</sup>', traded=traded, payout=payout, campaigns=d + r,
                         d=d, r=r, basis=basis))
        print(f'    {label}: Kalshi traded {_money(traded)}, paid out {_money(payout)}; campaigns '
              f'{_money(d + r)} ({basis})  [{call}]')
    rows.reverse()  # Plotly draws the first bar at the bottom; keep the Senate on top
    y = [x['label'] for x in rows]

    fig = go.Figure()
    for key, name, color in (('traded', 'Traded on Kalshi (contracts x $1)', NAVY),
                             ('payout', 'Kalshi pot paid out at settlement', GLASS_BLUE),
                             ('campaigns', 'Both campaigns, raised or spent', COPPER)):
        fig.add_trace(go.Bar(
            y=y, x=[x[key] for x in rows], orientation='h', name=name, marker_color=color,
            text=[_money(x[key]) for x in rows], textposition='outside',
            customdata=[[_money(x['d']), _money(x['r']), x['basis']] for x in rows],
            hovertemplate=f'%{{y}}<br>{name}: %{{text}}'
                          + ('<br>D %{customdata[0]}, R %{customdata[1]} (%{customdata[2]})' if key == 'campaigns'
                             else '') + '<extra></extra>',
        ))
    sen = rows[-1]
    # Plotly reads text with two '$' as LaTeX; use the HTML entity in titles and notes.
    _style(
        fig,
        f'{_money(sen["traded"])} Traded on Talarico vs Paxton, More Than the Two Campaigns Raised Combined '
        f'({_money(sen["campaigns"])})',
        'Each Texas race with a Kalshi market vs the two campaigns\' own money | Traded counts every contract that '
        'changed hands; paid out is the money at stake at settlement | Log scale',
        'Kalshi public market data, market open through settlement; each contract settles at $1. Campaigns = the two '
        'candidates\' committees only, not outside groups. Senate and TX-23: FEC receipts to Oct 14, 2026.'
        '<br>Governor: spending Oct 15, 2025-Oct 24, 2026 (Texas Tribune, TEC filings). Lt. Governor: '
        'cycle receipts (Houston Chronicle, TEC). AG: at least Middleton\'s $16.8M self-funding + $3.4M raised '
        'Jul-Oct, and Johnson\'s 2026 reports.<br>Kalshi listed no market on TX-09, 15, 28, 32, 34 or 35. '
        'As of Nov 10, 2026.',
        hovermode='closest', barmode='group', bargap=0.2, height=820,
        margin=dict(l=360, r=80, t=120, b=210),
        legend=dict(orientation='h', yanchor='top', y=-0.06, xanchor='center', x=0.5),
    )
    for a in fig.layout.annotations:
        a.text = a.text.replace('$', '&#36;')
        if a.text.startswith('Source'):
            a.x = -0.46  # start under the race labels, not the plot, so the note isn't clipped
    fig.layout.title.text = fig.layout.title.text.replace('$', '&#36;')
    fig.update_xaxes(type='log', title=None, range=[-1.3, 2.9], gridcolor='#E8E8E8',
                     tickvals=[0.1, 1, 10, 100, 500], ticktext=['$100K', '$1M', '$10M', '$100M', '$500M'])
    fig.update_yaxes(gridcolor='rgba(0,0,0,0)')
    _save(fig, 'election_kalshi_texas_money.html')


TX_POLLS = os.path.join('data', 'election_texas_polls.csv')


def _margin(d, r):
    if abs(d - r) < 0.05:
        return 'Tied'
    return f'D+{d - r:.1f}' if d > r else f'R+{r - d:.1f}'


def chart_texas_polls(snaps):
    """Final poll margin vs result in each Texas race, with Kalshi's day-before favorite.

    Poll margin = mean of the aggregator averages where any exist (Senate, Governor), else the mean of
    the October public polls (Lt. Governor, AG; the Republican-sponsored Stratus poll is left out of the CSV).
    TX-23 had only one poll, a Democrat-aligned internal, and is labeled so.
    """
    print('\n[8] Texas polls vs Kalshi vs result...')
    rows = defaultdict(lambda: {'poll_avg': [], 'poll': [], 'result': None})
    with open(TX_POLLS, encoding='utf-8') as f:
        for r in csv.DictReader(f):
            d, rp = float(r['dem']), float(r['rep'])
            if r['kind'] == 'result':
                rows[r['event_ticker']]['result'] = (d, rp)
            else:
                rows[r['event_ticker']][r['kind']].append(d - rp)
    day = {e: m for (_, e), m in snaps[DAY].items()}
    races = []
    for ticker, (label, *_rest) in TX_CAMPAIGN_MONEY.items():
        src = rows[ticker]
        polls = src['poll_avg'] or src['poll']
        basis = (f'average of {len(polls)} polling averages' if src['poll_avg'] else
                 f'mean of {len(polls)} October polls' if len(polls) > 1 else 'one D-aligned internal poll')
        poll = sum(polls) / len(polls)
        d, rp = src['result']
        fav, price = _favorite(day[ticker])
        kalshi = f'{"Democrat" if fav["party"] == "D" else "Republican"} {price:.0%}'
        races.append(dict(label=label, poll=poll, result=d - rp, kalshi=kalshi, basis=basis))
        print(f'    {label}: polls {_margin(poll, 0)} ({basis}), result {_margin(d, rp)}, '
              f'miss {d - rp - poll:.1f} pts toward D; Kalshi day before: {kalshi}')
    races.reverse()  # Plotly draws the first row at the bottom; keep the Senate on top
    y = [f'{x["label"]}<br><sup>Kalshi the day before: {x["kalshi"]} | polls: {x["basis"]}</sup>' for x in races]

    fig = go.Figure()
    for yi, x in zip(y, races):  # connector from the polls to the result
        fig.add_trace(go.Scatter(x=[x['poll'], x['result']], y=[yi, yi], mode='lines', showlegend=False,
                                 line=dict(color=CONCRETE, width=3), hoverinfo='skip'))
    fig.add_trace(go.Scatter(
        x=[x['poll'] for x in races], y=y, mode='markers+text', name='Final polls',
        marker=dict(symbol='diamond', size=14, color='white', line=dict(color=COPPER, width=2.5)),
        text=[_margin(x['poll'], 0) for x in races], textposition='top center',
        hovertemplate='%{y}<br>Final polls: %{text}<extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=[x['result'] for x in races], y=y, mode='markers+text', name='Result',
        marker=dict(size=14, color=NAVY),
        text=[_margin(x['result'], 0) for x in races], textposition='top center',
        hovertemplate='%{y}<br>Result: %{text}<extra></extra>',
    ))
    fig.add_vline(x=0, line=dict(color=NAVY, width=1))
    misses = [x['result'] - x['poll'] for x in races]
    poll_r = sum(x['poll'] < 0 for x in races)
    kalshi_r = sum(x['kalshi'].startswith('Republican') for x in races)
    _style(
        fig,
        f'Texas Polls Missed Every Race by {min(misses):.0f}-{max(misses):.0f} Points, and Kalshi Leaned With Them',
        f'Final poll margin vs result, each Texas race with a Kalshi market | Polls had the Republican ahead in '
        f'{poll_r} of {len(races)} races, Kalshi favored the Republican in {kalshi_r}; the Democrat won all '
        f'{len(races)}',
        'Polls: Senate = 270toWin and RealClearPolitics; Governor = 270toWin, Decision Desk HQ, FiftyPlusOne, '
        'RealClearPolitics, Silver Bulletin (as of Nov 1-2); Lt. Governor and AG = October public polls (Texas '
        'Southern, Texas Public<br>Opinion Research, UH Hobby, UT/Texas Politics Project), no aggregator average; '
        'TX-23 = Normington Petts, Oct 5-7, Democrat-aligned. Results as reported Nov 6-10, 2026, not certified. '
        'Kalshi: Nov 2 closing price.',
        hovermode='closest', showlegend=True, height=640, margin=dict(l=420, r=60, t=120, b=170),
        legend=dict(orientation='v', yanchor='top', y=0.99, xanchor='left', x=0.01, bgcolor='rgba(255,255,255,0.85)'),
    )
    for a in fig.layout.annotations:
        if a.text.startswith('Source'):
            a.x = -0.55  # start under the race labels so the note isn't clipped
    fig.update_xaxes(title='Margin (points): Republican ahead <- 0 -> Democrat ahead', range=[-8, 15],
                     zeroline=False, gridcolor='#E8E8E8', tickvals=[-5, 0, 5, 10, 15],
                     ticktext=['R+5', '0', 'D+5', 'D+10', 'D+15'])
    fig.update_yaxes(gridcolor='rgba(0,0,0,0)')
    _save(fig, 'election_kalshi_texas_polls.html')


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
    chart_misses(snaps)
    chart_calibration(snaps)
    chart_texas_money(snaps)
    chart_texas_polls(snaps)


if __name__ == '__main__':
    main()
