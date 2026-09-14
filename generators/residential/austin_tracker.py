#!/usr/bin/env python3
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402
"""
Austin Residential Tracker

Story 10 — "Asking is not achieved" (4 charts)
  Chart 25 — Asking vs achieved price, both indexed to 2019 Q1
  Chart 26 — Active inventory vs new listings
  Chart 27 — Share of listings with a price cut
  Chart 28 — Housing permits, 12-month rolling

Story 11 — "How Austin rents actually changed" (2 charts, Zillow ZORI)
  Chart 29 — Austin vs US rent growth, year over year
  Chart 30 — The gap between them, in percentage points

RENT IS PLOTTED AS CHANGE, NEVER LEVEL. Four vendors publish a current Austin
rent and they span $1,328 (Apartment List, city, all units) to $1,425
(RealPage, professionally managed effective) to $1,500 (CoStar, metro asking)
to $1,653 (Zillow ZORI) -- a 24% spread, because each measures a different
slice. Rates of change are comparable where levels are not.

THE HEADLINE IS THE DIVERGENCE. Median LISTING price is down 28.5% from its
May 2022 peak; the FHFA repeat-sales index, which measures actual closings, is
down 11.3% from its 2022 Q2 peak and has been flat for two and a half years
(509.9 in 2024 Q1 to 506.3 in 2026 Q2). Year over year the two series point in
opposite directions: listings -9.8%, FHFA +0.3%. Anyone quoting "Austin home
prices are down 28%" is quoting asks, not sales.

WHAT THESE SERIES ARE. Everything except the FHFA index is Realtor.com listing
data for CBSA 12420 (Austin-Round Rock-San Marcos), served through FRED. They
describe the properties ON the market, not the ones that sold, so they move
with listing MIX as well as with price -- median listed square footage has
drifted 2,065 -> 2,003 SF over the last year, which is part of why the median
list price falls faster than price per square foot. The FHFA index is
repeat-sales on the same homes, so it is mix-free; it is also quarterly and
lags. Use FHFA for "what happened to prices" and the listing series for "what
is happening in the market right now".

CBSA 12420 is the five-county metro, so Williamson and Hays are in these
numbers -- the same footprint caveat that applies to the retail submarket work.

SEASONALITY IS SEVERE. Active listings, new listings and days on market all
swing hard within a year (new listings ran 1,632 in Dec 2025 and 4,408 in Apr
2026). Compare year over year or use the rolling series; never read a
month-over-month move as a trend.

Usage:
    PYTHONUTF8=1 python -m generators.residential.austin_tracker
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from dotenv import load_dotenv

from aquila.brand import AQUILA_FONT, NAVY, CONCRETE, COPPER, GLASS_ALT
from aquila.charts import write_chart_html
from aquila.connectors.fred import fetch_fred_series

load_dotenv('aquila_graph.env')

OUTPUT_DIR = 'charts/residential'

# CBSA 12420 = Austin-Round Rock-San Marcos, TX
SERIES = {
    'active': 'ACTLISCOU12420',           # active listing count
    'new_list': 'NEWLISCOU12420',         # new listings
    'price_cut': 'PRIREDCOU12420',        # listings with a price reduction
    'med_price': 'MEDLISPRI12420',        # median listing price
    'permits': 'AUST448BPPRIV',           # private housing units authorized
}
HPI_SERIES = 'ATNHPIUS12420Q'             # FHFA all-transactions index, quarterly

INDEX_BASE = '2019Q1'

# Zillow Observed Rent Index -- free public CSV, smoothed, all home types.
# Metro rows; we take Austin against the national line as a benchmark.
ZORI_URL = ('https://files.zillowstatic.com/research/public_csvs/zori/'
            'Metro_zori_uc_sfrcondomfr_sm_month.csv')
ZORI_METRO = 'Austin, TX'
ZORI_BENCHMARK = 'United States'


# -- Helpers -------------------------------------------------------------------

def _shared_layout(title_text, y_title, height=580, subtitle=None):
    """Title centred per brand; subtitle left-aligned, legend below the plot.

    add_aquila_logo() parks the watermark in the top-right margin at y=1.02, so
    the subtitle sits at y=1.075 and is left-aligned to stay clear of it. Keep
    each subtitle line under ~55 characters or it runs under the logo.
    """
    annotations = []
    if subtitle:
        annotations.append(dict(
            text=subtitle, xref='paper', yref='paper', x=0, xanchor='left', y=1.075, yanchor='bottom',
            showarrow=False, align='left', font=dict(family=AQUILA_FONT, size=12, color=CONCRETE)))

    return dict(
        title=dict(text=title_text, font=dict(family=AQUILA_FONT, size=18, color=NAVY),
                   x=0.5, xanchor='center', y=0.965, yanchor='top'),
        annotations=annotations,
        xaxis=dict(title='', tickfont=dict(family=AQUILA_FONT, size=11, color=NAVY), showgrid=False,
                   linecolor='#E8E8E8'),
        yaxis=dict(title=y_title, title_font=dict(family=AQUILA_FONT, size=12, color=NAVY),
                   tickfont=dict(family=AQUILA_FONT, size=11, color=NAVY), gridcolor='#E8E8E8',
                   zeroline=False),
        legend=dict(font=dict(family=AQUILA_FONT, size=11, color=NAVY), bgcolor='rgba(0,0,0,0)',
                    orientation='h', yanchor='top', y=-0.16, x=0.5, xanchor='center'),
        plot_bgcolor='white', paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, color=NAVY),
        height=height, margin=dict(l=80, r=130, t=125, b=95),
        hovermode='x unified',
    )


def _label(fig, x, y, text, color, size=11):
    """Direct label just past the final point."""
    fig.add_annotation(x=x, y=y, text=f"  {text}", showarrow=False, xanchor='left',
                       font=dict(family=AQUILA_FONT, size=size, color=color))


# -- Data Loading --------------------------------------------------------------

def load_data():
    """Monthly listing series plus the quarterly FHFA index."""
    cols = {}
    for name, sid in SERIES.items():
        print(f"  fetching {sid} ({name})...")
        df = fetch_fred_series(sid, name)
        if df.empty:
            raise RuntimeError(f"FRED returned no data for {sid}")
        s = df.set_index(pd.to_datetime(df['date']))[name]
        cols[name] = pd.to_numeric(s, errors='coerce').dropna()
    monthly = pd.DataFrame(cols)
    monthly['cut_share'] = monthly['price_cut'] / monthly['active']

    print(f"  fetching {HPI_SERIES} (FHFA index)...")
    h = fetch_fred_series(HPI_SERIES, 'hpi')
    hpi = pd.to_numeric(h.set_index(pd.to_datetime(h['date']))['hpi'], errors='coerce').dropna()

    print(f"  [OK] monthly {monthly.index[0]:%b %Y} -> {monthly.index[-1]:%b %Y}, "
          f"FHFA -> {hpi.index[-1]:%Y}Q{(hpi.index[-1].month - 1) // 3 + 1}")
    return monthly, hpi


def load_zori():
    """Austin and national Zillow Observed Rent Index, monthly.

    Returned as CHANGE, not level. Rent levels are not comparable across
    vendors -- Apartment List, RealPage, CoStar and Zillow all publish a
    current "Austin rent" spanning $1,328 to $1,653, because each measures a
    different slice of the stock. Rates of change are comparable, so that is
    what these charts plot.
    """
    print(f"  downloading ZORI...")
    raw = pd.read_csv(ZORI_URL)
    date_cols = [c for c in raw.columns if c[:4].isdigit()]

    def one(region):
        match = raw[raw['RegionName'] == region]
        if match.empty:
            raise RuntimeError(f"ZORI has no row for {region!r}")
        row = match.iloc[0]
        s = pd.Series({pd.to_datetime(c): pd.to_numeric(row[c], errors='coerce') for c in date_cols})
        return s.dropna().sort_index()

    d = pd.DataFrame({'austin': one(ZORI_METRO), 'us': one(ZORI_BENCHMARK)}).dropna()
    d['austin_yoy'] = d['austin'].pct_change(12)
    d['us_yoy'] = d['us'].pct_change(12)
    d['gap_pp'] = (d['austin_yoy'] - d['us_yoy']) * 100
    print(f"  [OK] ZORI {d.index[0]:%b %Y} -> {d.index[-1]:%b %Y}")
    return d


def _negative_run(yoy):
    """Length in months of the unbroken run of negative YoY ending at the last point."""
    run = 0
    for v in yoy.dropna()[::-1] < 0:
        if not v:
            break
        run += 1
    return run


# -- Charts --------------------------------------------------------------------

def chart_rent_change(z):
    """Chart 29: Austin rent growth against the national rate.

    Year over year, NOT a shorter window. A 3-month annualised rate currently
    reads +4.6% for Austin and would look like a decisive recovery, but ZORI is
    smoothed and not seasonally adjusted -- the national series swings the same
    way over the same months (-1.9% in Dec 2025 to +6.6% in May 2026), so most
    of that is spring. Year over year cancels the season by construction.
    """
    d = z.dropna(subset=['austin_yoy']).loc['2016':]
    fig = go.Figure()
    fig.add_hline(y=0, line=dict(color=CONCRETE, width=1))
    fig.add_trace(go.Scatter(x=d.index, y=d['us_yoy'], mode='lines', name='United States',
                             line=dict(color=CONCRETE, width=2),
                             hovertemplate='%{y:+.1%}<extra>US</extra>'))
    fig.add_trace(go.Scatter(x=d.index, y=d['austin_yoy'], mode='lines', name='Austin metro',
                             line=dict(color=NAVY, width=2),
                             hovertemplate='%{y:+.1%}<extra>Austin</extra>'))

    y = z['austin_yoy'].dropna()
    run = _negative_run(y)
    subtitle = (f"Austin peaked at {y.max():+.1%} in {y.idxmax():%b %Y} and bottomed at "
                f"{y.min():+.1%} in {y.idxmin():%b %Y}<br>"
                f"Now {y.iloc[-1]:+.1%} — negative for {run} straight months, but closing on the US")
    layout = _shared_layout('Austin Rent Growth Went From First to Last',
                            'Rent change, year over year', subtitle=subtitle)
    layout['yaxis']['tickformat'] = '+.0%'
    fig.update_layout(**layout)
    # CONCRETE sits under 3:1 against white, so both series are direct-labelled.
    _label(fig, d.index[-1], d['us_yoy'].iloc[-1], f"US {d['us_yoy'].iloc[-1]:+.1%}", CONCRETE)
    _label(fig, d.index[-1], d['austin_yoy'].iloc[-1], f"Austin {d['austin_yoy'].iloc[-1]:+.1%}", NAVY)
    return fig


def chart_rent_gap(z):
    """Chart 30: Austin's rent growth minus the national rate, in points.

    Strips out whatever national rent conditions are doing and leaves only
    Austin-specific performance. Also immune to the seasonality problem, since
    both series carry the same season.
    """
    d = z.dropna(subset=['gap_pp']).loc['2016':]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d.index, y=d['gap_pp'], mode='lines', name='Austin minus US',
                             line=dict(color=NAVY, width=2), fill='tozeroy',
                             fillcolor='rgba(23,35,68,0.08)',
                             hovertemplate='%{y:+.1f} pp<extra></extra>', showlegend=False))
    fig.add_hline(y=0, line=dict(color=CONCRETE, width=1))

    g = d['gap_pp']
    subtitle = (f"Worst gap {g.min():+.1f} points in {g.idxmin():%b %Y}; now {g.iloc[-1]:+.1f}<br>"
                f"Austin still trails the national rate, by less than half as much")
    layout = _shared_layout('How Far Austin Rent Growth Trails the Nation',
                            'Percentage points vs US', subtitle=subtitle)
    fig.update_layout(**layout)
    _label(fig, d.index[-1], g.iloc[-1], f"{g.iloc[-1]:+.1f} pp", NAVY)
    return fig


def chart_asking_vs_achieved(monthly, hpi):
    """Chart 25: the divergence between what sellers ask and what homes fetch.

    Both series are resampled to quarterly and indexed to the same base so they
    share one axis. Mixing a monthly asking price against a quarterly index on
    two y-scales would be the dual-axis mistake and would also hide that the
    two disagree about direction.
    """
    # Align on quarters where BOTH series exist. `monthly` spans back to 1988
    # because the permits series does, while the listing data starts 2016 Q3 --
    # an index intersection alone leaves ~110 empty quarters on the axis.
    ask_q = monthly['med_price'].resample('QS').mean()
    hpi_q = hpi.resample('QS').mean()
    both = pd.concat([ask_q.rename('ask'), hpi_q.rename('hpi')], axis=1).dropna()
    ask_q, hpi_q, idx = both['ask'], both['hpi'], both.index

    base = pd.Period(INDEX_BASE, freq='Q').to_timestamp()
    ask_i = ask_q / ask_q.loc[base] * 100
    hpi_i = hpi_q / hpi_q.loc[base] * 100
    labels = [f"{d:%Y}Q{(d.month - 1) // 3 + 1}" for d in idx]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=labels, y=hpi_i, mode='lines', name='Achieved — FHFA repeat-sales index',
                             line=dict(color=NAVY, width=2),
                             hovertemplate='%{y:.0f}<extra>Achieved</extra>'))
    fig.add_trace(go.Scatter(x=labels, y=ask_i, mode='lines', name='Asking — median listing price',
                             line=dict(color=COPPER, width=2),
                             hovertemplate='%{y:.0f}<extra>Asking</extra>'))

    ask_pk, hpi_pk = monthly['med_price'].max(), hpi.max()
    subtitle = (f"Asking is {monthly['med_price'].iloc[-1] / ask_pk - 1:+.0%} from its peak; "
                f"achieved is {hpi.iloc[-1] / hpi_pk - 1:+.0%}<br>"
                f"Over the last year asking fell 9.8% while achieved rose 0.3%")
    layout = _shared_layout('Austin Housing: Asking Prices Are Not Sale Prices',
                            f'Index ({INDEX_BASE} = 100)', subtitle=subtitle)
    fig.update_layout(**layout)
    _label(fig, labels[-1], hpi_i.iloc[-1], f"Achieved {hpi_i.iloc[-1]:.0f}", NAVY)
    _label(fig, labels[-1], ask_i.iloc[-1], f"Asking {ask_i.iloc[-1]:.0f}", COPPER)
    return fig


def chart_inventory(monthly):
    """Chart 26: how much is for sale against how much arrives each month."""
    d = monthly.loc['2019':]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d.index, y=d['active'], mode='lines', name='Active listings',
                             line=dict(color=NAVY, width=2),
                             hovertemplate='%{y:,.0f}<extra>Active</extra>'))
    fig.add_trace(go.Scatter(x=d.index, y=d['new_list'], mode='lines', name='New listings that month',
                             line=dict(color=COPPER, width=2),
                             hovertemplate='%{y:,.0f}<extra>New</extra>'))

    a, n = d['active'], d['new_list']
    subtitle = (f"Active {a.iloc[-1]:,.0f}, {a.iloc[-1] / a.iloc[-13] - 1:+.1%} year over year — "
                f"essentially flat<br>Both series swing seasonally; compare like month to like month")
    layout = _shared_layout('Austin For-Sale Inventory Has Stopped Building', 'Listings',
                            subtitle=subtitle)
    layout['yaxis']['tickformat'] = ','
    fig.update_layout(**layout)
    _label(fig, d.index[-1], a.iloc[-1], f"Active {a.iloc[-1]:,.0f}", NAVY)
    _label(fig, d.index[-1], n.iloc[-1], f"New {n.iloc[-1]:,.0f}", COPPER)
    return fig


def chart_price_cuts(monthly):
    """Chart 27: share of what is listed that has already been marked down."""
    d = monthly.loc['2019':]
    roll = d['cut_share'].rolling(12).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d.index, y=d['cut_share'], mode='lines', name='Monthly',
                             line=dict(color=GLASS_ALT, width=2),
                             hovertemplate='%{y:.1%}<extra>Monthly</extra>'))
    fig.add_trace(go.Scatter(x=d.index, y=roll, mode='lines', name='12-month average',
                             line=dict(color=NAVY, width=2),
                             hovertemplate='%{y:.1%}<extra>12-mo avg</extra>'))

    cur, pk = d['cut_share'].iloc[-1], monthly['cut_share'].max()
    subtitle = (f"{cur:.0%} of active listings carry a price cut, against a "
                f"{pk:.0%} peak in {monthly['cut_share'].idxmax():%b %Y}<br>"
                f"Elevated versus 2019, but well off the 2022 repricing")
    layout = _shared_layout('Two in Five Austin Listings Have Cut Their Price',
                            'Share of active listings', subtitle=subtitle)
    layout['yaxis']['tickformat'] = '.0%'
    fig.update_layout(**layout)
    # GLASS_ALT sits under 3:1 against white, so both series are direct-labelled.
    _label(fig, d.index[-1], cur, f"Monthly {cur:.0%}", GLASS_ALT)
    _label(fig, d.index[-1], roll.iloc[-1], f"12-mo {roll.iloc[-1]:.0%}", NAVY)
    return fig


def chart_permits(monthly):
    """Chart 28: the supply response, as a rolling year to remove seasonality."""
    roll = monthly['permits'].rolling(12).sum().dropna()
    roll = roll.loc['2015':]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=roll.index, y=roll, mode='lines', name='Units authorized',
                             line=dict(color=NAVY, width=2), fill='tozeroy',
                             fillcolor='rgba(23,35,68,0.08)',
                             hovertemplate='%{y:,.0f} units<extra></extra>', showlegend=False))

    pk = roll.max()
    subtitle = (f"{roll.iloc[-1]:,.0f} units in the year to {roll.index[-1]:%b %Y}, "
                f"{roll.iloc[-1] / pk - 1:+.0%} from the<br>{roll.idxmax():%b %Y} peak of {pk:,.0f} — "
                f"the supply response has more than halved")
    layout = _shared_layout('Austin Housing Permits Have More Than Halved',
                            'Units authorized, trailing 12 months', subtitle=subtitle)
    layout['yaxis']['tickformat'] = ','
    layout['yaxis']['rangemode'] = 'tozero'
    fig.update_layout(**layout)
    _label(fig, roll.index[-1], roll.iloc[-1], f"{roll.iloc[-1]:,.0f}", NAVY)
    return fig


# -- Main ----------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Loading FRED series...")
    monthly, hpi = load_data()
    z = load_zori()

    charts = [
        (chart_rent_change(z), 'austin_rent_change.html'),
        (chart_rent_gap(z), 'austin_rent_gap_vs_us.html'),
        (chart_asking_vs_achieved(monthly, hpi), 'austin_asking_vs_achieved.html'),
        (chart_inventory(monthly), 'austin_for_sale_inventory.html'),
        (chart_price_cuts(monthly), 'austin_listing_price_cuts.html'),
        (chart_permits(monthly), 'austin_housing_permits.html'),
    ]
    print()
    for fig, name in charts:
        path = f'{OUTPUT_DIR}/{name}'
        write_chart_html(fig, path)
        print(f"  [OK] {path}")
    print(f"\n{len(charts)} charts written to {OUTPUT_DIR}/")


if __name__ == '__main__':
    main()
