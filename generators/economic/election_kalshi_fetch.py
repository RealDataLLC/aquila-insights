#!/usr/bin/env python3
"""
Pull Kalshi prices for every Nov 3, 2026 race as of the close of Nov 2 (the day before the vote).

Writes data/election_kalshi_nov2.csv, one row per market, which election_kalshi.py reads.
Grading on the day-before price keeps election-night trading (prices moving to 99c as
results come in) out of the accuracy count. Kalshi's own recap graded on later prices.

Snapshot: the last trade at or before 2026-11-03 05:00 UTC (midnight ET, end of Nov 2),
from hourly candles; if a market didn't trade in the 14 days before, the bid/ask midpoint.
`result` is Kalshi's settlement (yes/no), blank while a race is unsettled.

Public market-data API, no key needed. Re-run when uncalled races settle, then re-run
election_kalshi.py.

Usage:
    python -m generators.economic.election_kalshi_fetch
"""

import csv
import datetime as dt
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

API = 'https://api.elections.kalshi.com/trade-api/v2'
SNAPSHOT = dt.datetime(2026, 11, 3, 5, 0, tzinfo=dt.timezone.utc)  # midnight ET ending Nov 2
SNAP_TS = int(SNAPSHOT.timestamp())
LOOKBACK = 14 * 86400
OUT = os.path.join('data', 'election_kalshi_nov2.csv')

# Race series by office. Kalshi lists each race as its own series (SENATEIA, GOVPARTYTX, ...);
# every House district is one event in KXHOUSERACE.
OFFICE_PATTERNS = [
    ('Senate', re.compile(r'^SENATE[A-Z]{2}$|^KXSENATE[A-Z]{2}$|^SENATE(OH|FL)S$')),
    ('Governor', re.compile(r'^(KX)?GOVPARTY[A-Z]{2}$')),
    ('Attorney General', re.compile(r'^(KX)?ATTYGEN[A-Z]{2}$')),
    ('Secretary of State', re.compile(r'^(KX)?SECSTATE[A-Z]{2}$')),
    ('Lieutenant Governor', re.compile(r'^(KX)?LTGOV[A-Z]{2}$|^KX[A-Z]{2}LTGOV$')),
]
HOUSE_SERIES = 'KXHOUSERACE'
SEATS_SERIES, SEATS_EVENT = 'KXDSENATESEATS', 'KXDSENATESEATS-27'
EVENT_2026 = re.compile(r'-26(NOV03|NOV)?$')


def get(path, **params):
    url = f'{API}{path}?' + urllib.parse.urlencode(params)
    for attempt in range(8):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt == 7:
                raise RuntimeError(f'{url}: {e}') from e
            time.sleep(2 * (attempt + 1))


def events(series):
    out, cursor = [], ''
    while True:
        q = dict(series_ticker=series, limit=200, with_nested_markets='true')
        if cursor:
            q['cursor'] = cursor
        d = get('/events', **q)
        out += d['events']
        cursor = d.get('cursor')
        if not cursor:
            return out


def snapshot_price(series, ticker):
    d = get(f'/series/{series}/markets/{ticker}/candlesticks',
            start_ts=SNAP_TS - LOOKBACK, end_ts=SNAP_TS, period_interval=60)
    candles = [c for c in d.get('candlesticks', []) if c['end_period_ts'] <= SNAP_TS]
    for c in reversed(candles):
        p = c['price'].get('close_dollars') or c['price'].get('previous_dollars')
        if p is not None:
            return float(p), 'last'
    if candles:
        bid, ask = candles[-1]['yes_bid'].get('close_dollars'), candles[-1]['yes_ask'].get('close_dollars')
        if bid and ask:
            return (float(bid) + float(ask)) / 2, 'mid'
    return None, ''


def party(ticker):
    suffix = ticker.rsplit('-', 1)[-1]
    return {'D': 'D', 'DEM': 'D', 'R': 'R', 'GOP': 'R', 'REP': 'R'}.get(suffix, '')


def race_events():
    series = get('/series', category='Elections')['series']
    picked = []
    for s in series:
        for office, pat in OFFICE_PATTERNS:
            if pat.match(s['ticker']):
                picked.append((office, s['ticker']))
                break
    picked.append(('House', HOUSE_SERIES))
    with ThreadPoolExecutor(4) as ex:
        found = list(ex.map(lambda p: [(p[0], e) for e in events(p[1])], picked))
    races = {}
    for office, e in (x for batch in found for x in batch):
        if EVENT_2026.search(e['event_ticker']):
            races.setdefault(e['event_ticker'], (office, e))
    return list(races.values())


def rows_for(office, e):
    rows = []
    for m in e.get('markets', []):
        price, basis = snapshot_price(e['series_ticker'], m['ticker'])
        rows.append(dict(
            office=office, event_ticker=e['event_ticker'], race=e['title'].replace(' winner?', ''),
            market_ticker=m['ticker'], candidate=m.get('yes_sub_title') or '', party=party(m['ticker']),
            price_nov2='' if price is None else f'{price:.3f}', price_basis=basis,
            result=m.get('result') or '',
        ))
    return rows


def main():
    print('Kalshi prices at', SNAPSHOT.isoformat())
    races = race_events()
    print(f'  {len(races)} races')
    seats = get(f'/events/{SEATS_EVENT}', with_nested_markets='true')['event']
    seats['series_ticker'] = SEATS_SERIES
    jobs = races + [('Senate seat count', seats)]
    with ThreadPoolExecutor(4) as ex:
        rows = [r for batch in ex.map(lambda j: rows_for(*j), jobs) for r in batch]
    rows.sort(key=lambda r: (r['office'], r['event_ticker'], r['market_ticker']))
    os.makedirs('data', exist_ok=True)
    with open(OUT, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f'  [OK] {OUT}: {len(rows)} markets')


if __name__ == '__main__':
    main()
