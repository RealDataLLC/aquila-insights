#!/usr/bin/env python3
"""
Election 2026 -- LinkedIn Research Series
11 charts tying Austin CRE data to the November 3, 2026 midterms.

Charts (all in charts/economic-indicators/):
  Leasing hesitation (office requirements, Google Sheets)
    1. election_requirements_seasonal.html   -- Monthly requirement index, election vs non-election years
    2. election_requirements_yearend.html    -- Nov-Dec requirement index by year
  Tax policy and wealth migration (IRS SOI state-to-state migration)
    3. election_migration_top_states.html    -- Net AGI migration by state, latest year
    4. election_migration_no_tax_trend.html  -- Net AGI gained by no-wage-tax states, by year
  Government jobs (BLS via FRED)
    5. election_austin_government_jobs.html  -- Austin MSA federal / state / local employment
    6. election_government_share.html        -- Government share of jobs: Austin vs Texas vs US
    7. election_federal_jobs_index.html      -- Federal jobs indexed to Jan 2025: Austin vs US
  Housing supply (Census permits + Realtor.com via FRED)
    8. election_austin_housing_permits.html  -- Austin MSA permits, single-family vs multifamily
    9. election_austin_price_inventory.html  -- Austin median list price vs active listings
  Rates around midterms (FRED daily)
   10. election_10y_treasury_midterms.html   -- 10Y Treasury path around midterm elections
   11. election_credit_spread_midterms.html  -- Baa corporate spread path around midterms

Usage:
    python -m generators.economic.election
"""

import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
from dotenv import load_dotenv

from aquila.brand import AQUILA_COLORS, AQUILA_FONT, NAVY, GLASS_BLUE, CONCRETE, COPPER, BRASS
from aquila.charts import write_chart_html
from aquila.connectors.fred import fetch_fred_series
from aquila.connectors.gsheets import get_gsheets_client

load_dotenv('aquila_graph.env')

OUT_DIR = os.path.join('charts', 'economic-indicators')
GLASS_ALT = AQUILA_COLORS[2]
GREENSPACE = AQUILA_COLORS[6]
SIGNAL = AQUILA_COLORS[11]
GRID = '#E8E8E8'

REQUIREMENTS_SHEET_ID = '1bzpRnUrpBH6l_zX7DtTypczZf5bpYVwqPUG3tzg2vec'
HISTORICAL_TAB = 'DITM & Crab Trap MASTER Report (Through 2024)'

ELECTION_YEARS = [2018, 2020, 2022, 2024]
MIDTERMS = {
    2010: '2010-11-02',
    2014: '2014-11-04',
    2018: '2018-11-06',
    2022: '2022-11-08',
    2026: '2026-11-03',
}

# States with no tax on wage income (2023). NH taxed interest/dividends through 2024;
# WA added a capital-gains tax in 2022 -- neither taxes wages.
NO_WAGE_TAX_STATES = {'AK', 'FL', 'NV', 'NH', 'SD', 'TN', 'TX', 'WA', 'WY'}
IRS_YEARS = ['1617', '1718', '1819', '1920', '2021', '2122', '2223']


def _style(fig, title, subtitle=None, source=None, **overrides):
    """Apply shared Aquila layout (centered title + subtitle) and a source note."""
    text = title if not subtitle else f'{title}<br><sup>{subtitle}</sup>'
    layout = dict(
        title=dict(text=text, x=0.5, xanchor='center',
                   font=dict(family=AQUILA_FONT, size=20, color=NAVY)),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, color=NAVY, size=13),
        margin=dict(l=80, r=40, t=110, b=150),
        legend=dict(orientation='h', yanchor='top', y=-0.12, xanchor='center', x=0.5),
        xaxis=dict(showgrid=False, linecolor=GRID),
        yaxis=dict(gridcolor=GRID, zeroline=False),
        hovermode='x unified',
    )
    layout.update(overrides)
    fig.update_layout(**layout)
    if source:
        # Added (not set via layout) so chart annotations from add_hline etc. survive
        fig.add_annotation(
            text=f'Source: {source}', xref='paper', yref='paper', x=0, y=-0.24,
            xanchor='left', yanchor='top', showarrow=False,
            font=dict(size=10, color=CONCRETE),
        )


def _save(fig, name):
    write_chart_html(fig, os.path.join(OUT_DIR, name))
    print(f'  [OK] {name}')


# ── 1. Leasing hesitation: office requirements ───────────────────────────────

def _num(series):
    return pd.to_numeric(series.astype(str).str.replace(',', '').str.replace('$', ''), errors='coerce')


def _standardize_requirements(df):
    """Office-only rows with date + average SF. Handles both date column names."""
    date_col = 'DATE OF REQUIREMENT' if 'DATE OF REQUIREMENT' in df.columns else 'DATE'
    df = df[df['USE'].astype(str).str.lower().str.contains('office', na=False)]
    out = pd.DataFrame({
        'date': pd.to_datetime(df[date_col], errors='coerce', format='mixed'),
        'sf': (_num(df['REQUIRED SF (LOW)']) + _num(df['REQUIRED SF (HIGH)'])) / 2,
    })
    return out.dropna()


def load_requirements():
    """Combine historical + current requirement tabs (2017 onward)."""
    sheet = get_gsheets_client().open_by_key(REQUIREMENTS_SHEET_ID)
    current = pd.DataFrame(sheet.get_worksheet(0).get_all_records())
    rows = sheet.worksheet(HISTORICAL_TAB).get_all_values()
    historical = pd.DataFrame(rows[1:], columns=rows[0])
    df = pd.concat([_standardize_requirements(historical), _standardize_requirements(current)])
    df = df[df['date'] >= '2017-01-01']
    print(f'  [OK] {len(df)} office requirements, {df.date.min():%b %Y} - {df.date.max():%b %d, %Y}')
    return df


def requirement_index(df):
    """Monthly requirement count indexed to each year's Jan-Aug monthly average."""
    monthly = df.groupby(pd.Grouper(key='date', freq='MS')).size().rename('count').to_frame()
    monthly['year'] = monthly.index.year
    monthly['month'] = monthly.index.month
    base = monthly[monthly.month <= 8].groupby('year')['count'].mean()
    monthly['index'] = monthly['count'] / monthly['year'].map(base)
    return monthly


def chart_requirements_seasonal(monthly, last_date):
    print('\n[1] Requirements seasonal profile...')
    full_years = monthly[monthly.year < last_date.year]
    elec = full_years[full_years.year.isin(ELECTION_YEARS)].groupby('month')['index'].mean()
    non = full_years[~full_years.year.isin(ELECTION_YEARS)].groupby('month')['index'].mean()
    cur = monthly[(monthly.year == last_date.year) & (monthly.index <= last_date)]
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    fig = go.Figure()
    fig.add_vrect(x0='Oct', x1='Dec', fillcolor=GLASS_BLUE, opacity=0.25, line_width=0,
                  annotation_text='Election season', annotation_position='top left',
                  annotation_font=dict(size=11, color=NAVY))
    fig.add_hline(y=1, line=dict(color=CONCRETE, width=1, dash='dot'))
    fig.add_trace(go.Scatter(x=months, y=non.values, name='Non-election years (2017-2025 odd)',
                             line=dict(color=CONCRETE, width=3),
                             hovertemplate='%{y:.2f}x<extra>Non-election</extra>'))
    fig.add_trace(go.Scatter(x=months, y=elec.values, name='Election years (2018-2024)',
                             line=dict(color=NAVY, width=4),
                             hovertemplate='%{y:.2f}x<extra>Election</extra>'))
    fig.add_trace(go.Scatter(x=[months[m - 1] for m in cur.month], y=cur['index'].values,
                             name=f'{last_date.year} (through {last_date:%b %d})',
                             line=dict(color=COPPER, width=3, dash='dash'), mode='lines+markers',
                             hovertemplate='%{y:.2f}x<extra>' + str(last_date.year) + '</extra>'))
    _style(
        fig,
        'Do Austin Office Tenants Wait Out Elections?',
        "New office requirements by month, indexed to each year's Jan-Aug average (1.0 = normal pace)",
        'AQUILA office requirements database (tenants actively in the market), 2017-2026.',
    )
    fig.update_yaxes(title='Requirement Index (x)', tickformat='.1f')
    _save(fig, 'election_requirements_seasonal.html')


def chart_requirements_yearend(monthly, last_date):
    print('\n[2] Requirements year-end index by year...')
    full_years = monthly[monthly.year < last_date.year]
    yearend = full_years[full_years.month >= 11].groupby('year')['index'].mean()
    is_elec = [y in ELECTION_YEARS for y in yearend.index]
    elec_avg = yearend[is_elec].mean()
    non_avg = yearend[[not e for e in is_elec]].mean()
    ex2020 = yearend[[y in ELECTION_YEARS and y != 2020 for y in yearend.index]].mean()

    print(f'    Nov-Dec index -- election: {elec_avg:.2f}  non-election: {non_avg:.2f}  '
          f'election ex-2020: {ex2020:.2f}  gap: {elec_avg / non_avg - 1:+.0%}')

    fig = go.Figure(go.Bar(
        x=[str(y) for y in yearend.index], y=yearend.values,
        marker_color=[NAVY if e else CONCRETE for e in is_elec],
        text=[f'{v:.2f}x' for v in yearend.values], textposition='outside',
        hovertemplate='%{x}: %{y:.2f}x<extra></extra>',
    ))
    for avg, label, color in [(non_avg, 'Non-election avg', CONCRETE), (elec_avg, 'Election avg', NAVY)]:
        fig.add_hline(y=avg, line=dict(color=color, width=1.5, dash='dash'),
                      annotation_text=f'{label}: {avg:.2f}x', annotation_position='top right',
                      annotation_font=dict(size=11, color=color))
    _style(
        fig,
        'The Year-End Slowdown Runs Deeper in Election Years',
        "Nov-Dec new office requirements vs. that year's Jan-Aug pace | Navy = election year",
        'AQUILA office requirements database. 2020 also reflects COVID-19.',
        hovermode='closest', showlegend=False,
    )
    fig.update_yaxes(title='Nov-Dec Requirement Index (x)', tickformat='.1f',
                     range=[0, yearend.max() * 1.25])
    _save(fig, 'election_requirements_yearend.html')


# ── 2. Tax policy: IRS state-to-state migration ───────────────────────────────

def _read_irs(kind, yy):
    url = f'https://www.irs.gov/pub/irs-soi/state{kind}{yy}.csv'
    resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=60)
    resp.raise_for_status()
    return pd.read_csv(io.StringIO(resp.content.decode('latin-1')))


def load_irs_net_agi():
    """Net domestic AGI migration ($B) and net returns by state and tax year."""
    frames = []
    for yy in IRS_YEARS:
        try:
            inflow = _read_irs('inflow', yy)
            outflow = _read_irs('outflow', yy)
        except Exception as e:
            print(f'  [SKIP] IRS {yy}: {e}')
            continue
        inflow.columns = [c.lower() for c in inflow.columns]
        outflow.columns = [c.lower() for c in outflow.columns]
        # Code 97 covers both "Total Migration-US" (domestic) and "Same State" rows
        inn = inflow[(inflow['y1_statefips'] == 97)
                     & inflow['y1_state_name'].str.contains('Total Migration-US$', regex=True)]
        out = outflow[(outflow['y2_statefips'] == 97)
                      & outflow['y2_state_name'].str.contains('Total Migration-US$', regex=True)]
        inn = inn.set_index('y2_statefips')
        out = out.set_index('y1_statefips')
        state = inn['y1_state']
        df = pd.DataFrame({
            'state': state,
            'net_agi_b': (inn['agi'] - out['agi'].reindex(inn.index)) / 1e6,  # AGI in $000s
            'net_returns': inn['n1'] - out['n1'].reindex(inn.index),
        }).dropna()
        df['year'] = f'20{yy[:2]}-{yy[2:]}'
        frames.append(df)
        print(f'  [OK] IRS {yy}: {len(df)} states')
    return pd.concat(frames, ignore_index=True)


def chart_migration_top_states(irs):
    print('\n[3] Net AGI migration by state...')
    latest = irs['year'].max()
    df = irs[irs.year == latest].sort_values('net_agi_b')
    df = pd.concat([df.head(10), df.tail(10)])
    colors = [BRASS if s in NO_WAGE_TAX_STATES else NAVY for s in df.state]

    fig = go.Figure(go.Bar(
        x=df.net_agi_b, y=df.state, orientation='h', marker_color=colors,
        text=[f"{'+' if v >= 0 else '-'}${abs(v):.1f}B" for v in df.net_agi_b], textposition='outside',
        hovertemplate='%{y}: %{x:$,.2f}B net AGI<extra></extra>', showlegend=False,
    ))
    # Legend proxies
    for name, color in [('No tax on wage income', BRASS), ('Taxes wage income', NAVY)]:
        fig.add_trace(go.Bar(x=[None], y=[None], name=name, marker_color=color, showlegend=True))
    _style(
        fig,
        'Tax Policy Is on the Ballot. Income Is Already Voting With Its Feet.',
        f'Net domestic adjusted gross income migration, top and bottom 10 states, tax year {latest}',
        'IRS Statistics of Income, state-to-state migration data. Net = inflow AGI - outflow AGI.',
        hovermode='closest', height=720, barmode='overlay',
        margin=dict(l=60, r=60, t=110, b=150),
    )
    fig.update_xaxes(title='Net AGI Migration ($ Billions)', tickprefix='$', ticksuffix='B',
                     gridcolor=GRID, zeroline=True, zerolinecolor=NAVY)
    fig.update_yaxes(showgrid=False, categoryorder='array', categoryarray=list(df.state))
    _save(fig, 'election_migration_top_states.html')


def chart_migration_no_tax_trend(irs):
    print('\n[4] No-wage-tax states net AGI trend...')
    irs = irs.copy()
    irs['group'] = np.where(irs.state.isin(NO_WAGE_TAX_STATES), 'no_tax', 'tax')
    no_tax = irs[irs.group == 'no_tax'].groupby('year')['net_agi_b'].sum()
    tx = irs[irs.state == 'TX'].set_index('year')['net_agi_b']
    fl = irs[irs.state == 'FL'].set_index('year')['net_agi_b']
    rest = no_tax - tx - fl

    fig = go.Figure()
    for series, name, color in [(fl, 'Florida', BRASS), (tx, 'Texas', NAVY),
                                (rest, 'Other 7 no-wage-tax states', GLASS_ALT)]:
        fig.add_trace(go.Bar(x=series.index, y=series.values, name=name, marker_color=color,
                             hovertemplate='%{y:$,.1f}B<extra>' + name + '</extra>'))
    fig.add_trace(go.Scatter(
        x=no_tax.index, y=no_tax.values, mode='text', text=[f'${v:.0f}B' for v in no_tax.values],
        textposition='top center', showlegend=False, hoverinfo='skip',
        textfont=dict(size=12, color=NAVY),
    ))
    _style(
        fig,
        'Net Income Gained by States With No Wage Tax',
        'Net domestic AGI migration into AK, FL, NV, NH, SD, TN, TX, WA, WY by tax year',
        'IRS Statistics of Income, state-to-state migration data.',
        barmode='relative',
    )
    fig.update_yaxes(title='Net AGI Migration ($ Billions)', tickprefix='$', ticksuffix='B',
                     range=[min(0, rest.min() * 1.2), no_tax.max() * 1.15])
    _save(fig, 'election_migration_no_tax_trend.html')
    print(f'    Latest year: no-wage-tax states ${no_tax.iloc[-1]:.1f}B, TX ${tx.iloc[-1]:.1f}B')


# ── 3. Government jobs ───────────────────────────────────────────────────────

def chart_austin_government_jobs():
    print('\n[5] Austin government jobs by level...')
    levels = [('SMU48124209093000001', 'Local', NAVY),
              ('SMU48124209092000001', 'State', GLASS_ALT),
              ('SMU48124209091000001', 'Federal', COPPER)]
    fig = go.Figure()
    for sid, name, color in levels:
        df = fetch_fred_series(sid, name)
        if df.empty:
            continue
        df = df.set_index('date')[name].rolling(12).mean().dropna()
        df = df[df.index >= '2015-01-01']
        fig.add_trace(go.Scatter(x=df.index, y=df.values, name=name, line=dict(color=color, width=3),
                                 hovertemplate='%{y:,.1f}K<extra>' + name + '</extra>'))
        print(f'    {name}: {df.iloc[-1]:.1f}K (12M avg, {df.index[-1]:%b %Y})')
    _style(
        fig,
        'Austin Government Payrolls: Local and State Grow, Federal Slips',
        'Austin MSA government employment by level, 12-month moving average (thousands)',
        'BLS Current Employment Statistics via FRED (not seasonally adjusted; smoothed).',
    )
    fig.update_yaxes(title='Jobs (Thousands)', ticksuffix='K', rangemode='tozero')
    _save(fig, 'election_austin_government_jobs.html')


def chart_government_share():
    print('\n[6] Government share of jobs...')
    pairs = [('AUST448GOVT', 'AUST448NA', 'Austin MSA', NAVY),
             ('TXGOVT', 'TXNA', 'Texas', BRASS),
             ('USGOVT', 'PAYEMS', 'United States', CONCRETE)]
    fig = go.Figure()
    for gov_id, total_id, name, color in pairs:
        gov = fetch_fred_series(gov_id, 'gov')
        total = fetch_fred_series(total_id, 'total')
        if gov.empty or total.empty:
            continue
        df = gov.merge(total, on='date')
        df = df[df.date >= '2010-01-01']
        share = df['gov'] / df['total']
        fig.add_trace(go.Scatter(x=df.date, y=share, name=name, line=dict(color=color, width=3),
                                 hovertemplate='%{y:.1%}<extra>' + name + '</extra>'))
        print(f'    {name}: {share.iloc[-1]:.1%}')
    _style(
        fig,
        'Austin Has Grown Out of Being a Government Town',
        'Government employment (federal + state + local) as a share of total nonfarm jobs',
        'BLS Current Employment Statistics via FRED (seasonally adjusted).',
    )
    fig.update_yaxes(title='Share of Total Jobs', tickformat='.0%')
    _save(fig, 'election_government_share.html')


def chart_federal_jobs_index():
    print('\n[7] Federal jobs indexed to Jan 2025...')
    series = [('SMU48124209091000001', 'Austin MSA', NAVY),
              ('CES9091000001', 'United States', CONCRETE)]
    fig = go.Figure()
    fig.add_hline(y=100, line=dict(color=CONCRETE, width=1, dash='dot'))
    for sid, name, color in series:
        df = fetch_fred_series(sid, name)
        if df.empty:
            continue
        df = df[df.date >= '2024-07-01'].set_index('date')[name]
        idx = df / df.loc['2025-01-01'] * 100
        fig.add_trace(go.Scatter(x=idx.index, y=idx.values, name=name, line=dict(color=color, width=3),
                                 hovertemplate='%{y:.1f}<extra>' + name + '</extra>'))
        print(f'    {name}: {idx.iloc[-1]:.1f} ({df.iloc[-1] - df.loc["2025-01-01"]:+,.1f}K since Jan 2025)')
    _style(
        fig,
        'Federal Payrolls Since January 2025',
        'Federal government employment indexed to January 2025 = 100',
        'BLS Current Employment Statistics via FRED. Austin not seasonally adjusted; US seasonally adjusted.',
    )
    fig.update_yaxes(title='Index (Jan 2025 = 100)')
    _save(fig, 'election_federal_jobs_index.html')


# ── 4. Housing supply ────────────────────────────────────────────────────────

def chart_housing_permits():
    print('\n[8] Austin housing permits...')
    total = fetch_fred_series('AUST448BPPRIV', 'total')
    single = fetch_fred_series('AUST448BP1FH', 'single')
    if total.empty or single.empty:
        print('  [SKIP] permit data unavailable')
        return
    df = total.merge(single, on='date').set_index('date')
    df['multi'] = df['total'] - df['single']
    roll = df.rolling(12).sum().dropna()
    roll = roll[roll.index >= '2015-01-01']

    fig = go.Figure()
    for col, name, color in [('single', 'Single-family (1 unit)', NAVY), ('multi', 'Multifamily (2+ units)', GLASS_ALT)]:
        fig.add_trace(go.Scatter(x=roll.index, y=roll[col], name=name, stackgroup='one',
                                 line=dict(color=color, width=0.5), fillcolor=color,
                                 hovertemplate='%{y:,.0f} units<extra>' + name + '</extra>'))
    peak = roll['total'].idxmax()
    fig.add_annotation(x=peak, y=roll['total'].max(), text=f'Peak: {roll["total"].max():,.0f}<br>{peak:%b %Y}',
                       showarrow=True, arrowhead=0, ay=-35, font=dict(size=11, color=NAVY))
    _style(
        fig,
        'Housing Affordability Is on Every Ballot. Austin Ran the Supply Experiment.',
        'Austin MSA residential building permits, trailing 12-month total units',
        'U.S. Census Bureau Building Permits Survey via FRED.',
    )
    fig.update_yaxes(title='Permitted Units (Trailing 12M)', tickformat=',')
    _save(fig, 'election_austin_housing_permits.html')
    print(f'    Peak {roll["total"].max():,.0f} ({peak:%b %Y}); latest {roll["total"].iloc[-1]:,.0f}')


def chart_price_inventory():
    print('\n[9] Austin list price vs inventory...')
    price = fetch_fred_series('MEDLISPRI12420', 'price')
    listings = fetch_fred_series('ACTLISCOU12420', 'listings')
    if price.empty or listings.empty:
        print('  [SKIP] Realtor.com data unavailable')
        return
    df = price.merge(listings, on='date')
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df.date, y=df.listings, name='Active listings', marker_color=GLASS_BLUE,
                         hovertemplate='%{y:,.0f}<extra>Active listings</extra>'))
    fig.add_trace(go.Scatter(x=df.date, y=df.price, name='Median list price', line=dict(color=NAVY, width=3), yaxis='y2',
                             hovertemplate='%{y:$,.0f}<extra>Median list price</extra>'))
    peak = df.loc[df.price.idxmax()]
    last = df.iloc[-1]
    print(f'    Price peak ${peak.price:,.0f} ({peak.date:%b %Y}) -> ${last.price:,.0f} '
          f'({last.price / peak.price - 1:+.0%}); listings {last.listings:,.0f}')
    _style(
        fig,
        'More Supply, Lower Prices: Austin Housing Since the Peak',
        'Austin MSA median home list price (line) vs. active for-sale listings (bars)',
        'Realtor.com Housing Inventory via FRED.',
        # Price on y2 (overlay) so the line draws above the listing bars
        yaxis=dict(title='Active Listings', side='right', showgrid=False,
                   tickformat=',', rangemode='tozero'),
        yaxis2=dict(title='Median List Price', overlaying='y', side='left', tickprefix='$',
                    tickformat=',', gridcolor=GRID, zeroline=False, rangemode='tozero'),
        margin=dict(l=90, r=90, t=110, b=150),
    )
    _save(fig, 'election_austin_price_inventory.html')


# ── 5. Rates around midterms ─────────────────────────────────────────────────

def midterm_paths(series_id, window=180):
    """Change in bps from T-window days, for each midterm, on a calendar-day axis."""
    df = fetch_fred_series(series_id, 'v')
    s = df.set_index('date')['v'].asfreq('D').ffill()
    paths = {}
    for year, date in MIDTERMS.items():
        e = pd.Timestamp(date)
        seg = s[e - pd.Timedelta(days=window): e + pd.Timedelta(days=window)]
        if seg.empty:
            continue
        paths[year] = pd.Series((seg.values - seg.iloc[0]) * 100,
                                index=(seg.index - e).days)
    return paths


def chart_midterm_paths(series_id, filename, title, subtitle, source):
    paths = midterm_paths(series_id)
    history = [y for y in paths if y != 2026]
    avg = pd.concat([paths[y] for y in history], axis=1).mean(axis=1)
    shades = [CONCRETE, GLASS_ALT, GLASS_BLUE, BRASS]

    fig = go.Figure()
    fig.add_vline(x=0, line=dict(color=NAVY, width=1, dash='dot'))
    fig.add_annotation(x=0, y=1.02, yref='paper', text='Election Day', showarrow=False,
                       font=dict(size=11, color=NAVY))
    fig.add_hline(y=0, line=dict(color=GRID, width=1))
    for year, color in zip(history, shades):
        fig.add_trace(go.Scatter(x=paths[year].index, y=paths[year].values, name=str(year),
                                 line=dict(color=color, width=1.5),
                                 hovertemplate='%{y:+.0f} bps<extra>' + str(year) + '</extra>'))
    fig.add_trace(go.Scatter(x=avg.index, y=avg.values, name='Average (2010-2022)',
                             line=dict(color=NAVY, width=4),
                             hovertemplate='%{y:+.0f} bps<extra>Average</extra>'))
    if 2026 in paths:
        fig.add_trace(go.Scatter(x=paths[2026].index, y=paths[2026].values, name='2026',
                                 line=dict(color=SIGNAL, width=3),
                                 hovertemplate='%{y:+.0f} bps<extra>2026</extra>'))
        print(f'    2026 so far: {paths[2026].iloc[-1]:+.0f} bps at T{paths[2026].index[-1]}d; '
              f'avg at same point {avg.loc[paths[2026].index[-1]]:+.0f}, avg at T+180 {avg.iloc[-1]:+.0f}')
    for y in history:
        print(f'    {y}: T0 {paths[y].loc[0]:+.0f}  T+90 {paths[y].loc[90]:+.0f}  T+180 {paths[y].iloc[-1]:+.0f}')
    _style(fig, title, subtitle, source)
    fig.update_xaxes(title='Days From Election Day', zeroline=False)
    fig.update_yaxes(title='Change Since 6 Months Before (bps)', ticksuffix=' bps')
    _save(fig, filename)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print('=' * 80)
    print('ELECTION 2026 RESEARCH SERIES')
    print('=' * 80)

    print('\nLoading office requirements...')
    try:
        req = load_requirements()
        monthly = requirement_index(req)
        chart_requirements_seasonal(monthly, req.date.max())
        chart_requirements_yearend(monthly, req.date.max())
    except Exception as e:
        print(f'  [ERROR] Requirements charts skipped: {e}')

    print('\nLoading IRS migration data...')
    irs = load_irs_net_agi()
    if not irs.empty:
        chart_migration_top_states(irs)
        chart_migration_no_tax_trend(irs)

    chart_austin_government_jobs()
    chart_government_share()
    chart_federal_jobs_index()

    chart_housing_permits()
    chart_price_inventory()

    print('\n[10] 10Y Treasury around midterms...')
    chart_midterm_paths(
        'DGS10', 'election_10y_treasury_midterms.html',
        'What Midterms Have Meant for the 10-Year Treasury',
        '10-year Treasury yield change from 6 months before each midterm election (bps)',
        'Federal Reserve H.15 via FRED (DGS10).',
    )
    print('\n[11] Credit spread around midterms...')
    chart_midterm_paths(
        'BAA10Y', 'election_credit_spread_midterms.html',
        'Credit Spreads Around Midterm Elections',
        'Moody\'s Baa corporate yield minus 10-year Treasury, change from 6 months before (bps)',
        'Moody\'s and Federal Reserve via FRED (BAA10Y).',
    )

    print('\nDone.')


if __name__ == '__main__':
    main()
