#!/usr/bin/env python3
"""
Money vs. Movers -- Migration Analysis Charts
4 charts visualizing U-Haul migration volume vs. IRS wealth migration data.

Charts:
  1. migration_divergence.html        -- Indexed U-Haul rank vs IRS AGI (grouped bar)
  2. migration_dollars_per_door.html   -- Net AGI per net inbound household
  3. migration_capital_per_mover.html  -- US choropleth: net AGI per inbound mover
  4. migration_austin_split.html       -- Austin MSA counties vs TX/FL comps

Data: Hardcoded from IRS SOI 2022-2023, U-Haul Growth Index 2025.

Usage:
    python -m generators.economic.migration
"""

import base64
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from aquila.brand import AQUILA_COLORS, AQUILA_FONT, NAVY, GLASS_BLUE, CONCRETE, COPPER, BRASS
from aquila.charts import write_chart_html, add_aquila_logo

OUT_DIR = os.path.join('charts', 'economic-indicators')


def _base_layout(**overrides):
    """Shared Aquila layout defaults."""
    layout = dict(
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, color='#172344', size=13),
        title_x=0.5,
        title_xanchor='center',
        margin=dict(l=160, r=40, t=80, b=60),
    )
    layout.update(overrides)
    return layout


# ── Chart 1: The Divergence ──────────────────────────────────────────────────

def chart_divergence():
    """U-Haul 2023 rank (on y-axis) vs actual IRS Net AGI inflow in $ billions."""
    # Ordered bottom-to-top so #1 renders at top with categoryorder
    # 2023 U-Haul Growth Index: TX #1, FL #2, NC #3, SC #4, TN #5, AZ #8
    states_raw   = ['Arizona', 'Tennessee', 'South Carolina', 'North Carolina', 'Florida', 'Texas']
    uhaul_rank   = ['#8', '#5', '#4', '#3', '#2', '#1']
    agi_billions = [1.5, 2.8, 4.1, 3.9, 20.65, 5.5]

    # Show U-Haul rank inline with state name on y-axis
    states = [f'{s}  (U-Haul {r})' for s, r in zip(states_raw, uhaul_rank)]

    fig = go.Figure()

    # IRS AGI bars -- actual dollar values
    fig.add_trace(go.Bar(
        y=states, x=agi_billions, orientation='h',
        marker_color=NAVY,
        text=[f'${v:.1f}B' if v < 10 else f'${v:.2f}B' for v in agi_billions],
        textposition='outside',
        textfont=dict(size=12, color=NAVY),
    ))

    fig.update_layout(
        **_base_layout(margin=dict(l=240, r=80, t=80, b=60)),
        title=dict(text='The Divergence: Movers vs. Dollars',
                   font=dict(family=AQUILA_FONT, size=18, color=NAVY)),
        height=450,
        showlegend=False,
        xaxis=dict(
            title='IRS Net AGI Inflow, 2023 ($ billions)',
            tickprefix='$', ticksuffix='B',
            range=[0, 24],
            showgrid=True, gridcolor='#e9e9ea',
            zeroline=False,
        ),
        yaxis=dict(showgrid=False, categoryorder='array', categoryarray=states),
    )

    write_chart_html(fig, os.path.join(OUT_DIR, 'migration_divergence.html'))
    print('  [1/4] migration_divergence.html')
    return fig


# ── Chart 2: Dollars per Door ────────────────────────────────────────────────

def chart_dollars_per_door():
    """Net AGI per net inbound household, 2023."""
    states = ['Arizona', 'Texas', 'Tennessee', 'North Carolina',
              'South Carolina', 'Florida']
    values = [60, 66, 88, 95, 108, 163]

    # Color: Florida = Copper (wealth leader), Texas = Navy, rest = Glass Blue
    colors = []
    for s in states:
        if s == 'Florida':
            colors.append(COPPER)
        elif s == 'Texas':
            colors.append(NAVY)
        else:
            colors.append(GLASS_BLUE)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=states, x=values, orientation='h',
        marker_color=colors,
        text=[f'${v}K' for v in values],
        textposition='outside',
        textfont=dict(size=12),
    ))

    # US median HH income reference line
    fig.add_vline(x=75, line_dash='dot', line_color=CONCRETE, line_width=1.5,
                  annotation_text='US median HH income ~ $75K',
                  annotation_position='top',
                  annotation_font=dict(size=10, color=CONCRETE))

    fig.update_layout(
        **_base_layout(),
        title=dict(text='Net AGI per Net Inbound Household, 2023',
                   font=dict(family=AQUILA_FONT, size=18, color=NAVY)),
        height=450,
        showlegend=False,
        xaxis=dict(
            title='$ thousands per net return',
            range=[0, 190],
            tickprefix='$', ticksuffix='K',
            showgrid=True, gridcolor='#e9e9ea',
            zeroline=False,
        ),
        yaxis=dict(showgrid=False),
    )

    # Legend annotations for color coding
    fig.add_annotation(x=0.02, y=-0.18, xref='paper', yref='paper',
                       text=('<span style="color:' + COPPER + '">&#9632;</span> Florida -- wealth leader'
                             '&nbsp;&nbsp;&nbsp;'
                             '<span style="color:' + NAVY + '">&#9632;</span> Texas -- volume leader'
                             '&nbsp;&nbsp;&nbsp;'
                             '<span style="color:' + GLASS_BLUE + '">&#9632;</span> Other Sun Belt'),
                       showarrow=False, font=dict(size=11))

    write_chart_html(fig, os.path.join(OUT_DIR, 'migration_dollars_per_door.html'))
    print('  [2/4] migration_dollars_per_door.html')
    return fig


# ── Chart 3: US Choropleth -- Capital per Mover ──────────────────────────────

def chart_capital_per_mover():
    """Choropleth map: net AGI per inbound mover by state, 2023."""
    data = {
        'AK': -8.2, 'ME': 15.9, 'VT': 5.5, 'NH': 18.5, 'WA': -1.4,
        'MT': 14.2, 'ND': -6.2, 'MN': -17.3, 'IL': -33.4, 'WI': -0.843,
        'MI': -8.0, 'NY': -36.9, 'MA': -34.4, 'ID': 14.9, 'WY': 6.8,
        'SD': 9.5, 'IA': -4.7, 'IN': -2.7, 'OH': -10.5, 'PA': -11.0,
        'NJ': -14.7, 'CT': -6.0, 'RI': 1.4, 'OR': -4.8, 'NV': 13.6,
        'CO': 3.8, 'NE': -6.4, 'MO': -1.7, 'KY': -1.3, 'WV': 0.295,
        'VA': -4.0, 'MD': -13.5, 'DE': 15.8, 'CA': -30.6, 'UT': 6.0,
        'NM': -1.8, 'KS': -5.1, 'AR': 6.5, 'TN': 13.9, 'NC': 13.2,
        'SC': 23.2, 'DC': -20.0, 'AZ': 13.6, 'OK': 3.1, 'LA': -12.1,
        'MS': -1.2, 'AL': 5.2, 'GA': 2.8, 'HI': -0.075, 'TX': 10.0,
        'FL': 34.1,
    }

    df = pd.DataFrame(list(data.items()), columns=['state', 'net_agi_per_mover'])

    # Custom color scale matching the PDF's 7-bucket diverging scheme
    # Navy/dark for negative, Aquila brand tones for positive
    colorscale = [
        [0.0,  '#172344'],   # < -$20K  (Navy)
        [0.2,  '#88ABC8'],   # -$20K to -$10K  (Glass Alt)
        [0.35, '#C2DAF1'],   # -$10K to -$2.5K (Glass Blue)
        [0.45, '#E8E8E8'],   # +/- $2.5K (Mopac Gray)
        [0.55, '#DEB76D'],   # +$2.5K to +$10K (Brass)
        [0.7,  '#AB6D3A'],   # +$10K to +$20K (Copper)
        [1.0,  '#556B30'],   # > +$20K (Greenspace)
    ]

    fig = go.Figure(go.Choropleth(
        locations=df['state'],
        z=df['net_agi_per_mover'],
        locationmode='USA-states',
        colorscale=colorscale,
        zmin=-37, zmax=35,
        colorbar=dict(
            title=dict(text='Net AGI / mover ($K)', font=dict(size=12)),
            tickprefix='$', ticksuffix='K',
            len=0.7,
        ),
        text=df.apply(lambda r: f"{r['state']}: {'+'if r['net_agi_per_mover']>0 else ''}${r['net_agi_per_mover']:.1f}K", axis=1),
        hoverinfo='text',
    ))

    fig.update_layout(
        **_base_layout(margin=dict(l=20, r=20, t=80, b=40)),
        title=dict(text='Net AGI per Inbound Mover, 2023',
                   font=dict(family=AQUILA_FONT, size=18, color=NAVY)),
        height=550,
        geo=dict(
            scope='usa',
            bgcolor='white',
            lakecolor='white',
            landcolor='white',
            showlakes=True,
            showframe=False,
        ),
    )

    # Subtitle annotation
    fig.add_annotation(
        x=0.5, y=1.06, xref='paper', yref='paper',
        text='IRS SOI 2022-2023 net AGI / total inbound individuals -- dollars per person who moved in',
        showarrow=False, font=dict(size=11, color=CONCRETE),
    )

    write_chart_html(fig, os.path.join(OUT_DIR, 'migration_capital_per_mover.html'))
    print('  [3/4] migration_capital_per_mover.html')
    return fig


# ── Chart 4: The Austin Split ────────────────────────────────────────────────

def chart_austin_split():
    """Austin MSA counties vs major TX and FL comps -- net AGI per inbound mover."""
    counties = [
        'Dallas', 'Harris (Houston)', 'Bexar (San Antonio)',
        'Travis *', 'Tarrant (Fort Worth)',
        'Broward, FL', 'Miami-Dade, FL',
        'Collin (Plano)', 'Caldwell *', 'Bastrop *',
        'Pinellas, FL (St. Pete)',
        'Williamson *', 'Hays *',
        'Palm Beach, FL', 'Collier, FL (Naples)',
    ]
    values = [
        -10.6, -7.8, -2.6,
        -1.8, -0.4,
        4.2, 7.6,
        9.7, 10.9, 11.6,
        15.4,
        17.1, 19.8,
        47.5, 97.7,
    ]

    # Color buckets matching the PDF
    def _color(v, name):
        if v > 20:
            return COPPER        # Wealth magnet
        elif v >= 10:
            return BRASS         # Strong positive
        elif v >= 2.5:
            return AQUILA_COLORS[9]  # Texas Sun -- modest positive
        elif v >= -2.5:
            return CONCRETE      # Slightly negative
        else:
            return NAVY          # Net loss

    colors = [_color(v, n) for v, n in zip(values, counties)]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=counties, x=values, orientation='h',
        marker_color=colors,
        text=[f'{"+" if v > 0 else ""}${v:.1f}K' for v in values],
        textposition='outside',
        textfont=dict(size=11),
    ))

    # Austin MSA weighted average reference line
    fig.add_vline(x=8.3, line_dash='dot', line_color=CONCRETE, line_width=1.5,
                  annotation_text='Austin MSA weighted avg +$8.3K',
                  annotation_position='top right',
                  annotation_font=dict(size=10, color=CONCRETE))

    fig.update_layout(
        **_base_layout(margin=dict(l=190, r=60, t=80, b=80)),
        title=dict(text='Net AGI per Inbound Mover, by County, 2023',
                   font=dict(family=AQUILA_FONT, size=18, color=NAVY)),
        height=650,
        showlegend=False,
        xaxis=dict(
            title='Net AGI captured per inbound individual (thousands of dollars)',
            tickprefix='$', ticksuffix='K',
            showgrid=True, gridcolor='#e9e9ea',
            zeroline=True, zerolinecolor='#AAA9A8', zerolinewidth=1,
        ),
        yaxis=dict(showgrid=False),
    )

    # Subtitle
    fig.add_annotation(
        x=0.5, y=1.06, xref='paper', yref='paper',
        text='Austin MSA counties vs. major Texas and Florida comps -- IRS SOI county migration data',
        showarrow=False, font=dict(size=11, color=CONCRETE),
    )

    # Color legend
    legend_items = [
        (COPPER, 'Wealth magnet (>$20K/mover)'),
        (BRASS, 'Strong positive ($10-20K)'),
        (AQUILA_COLORS[9], 'Modest positive ($2.5-10K)'),
        (CONCRETE, 'Slightly negative'),
        (NAVY, 'Net loss (<-$5K)'),
    ]
    legend_text = '&nbsp;&nbsp;'.join(
        f'<span style="color:{c}">&#9632;</span> {lbl}' for c, lbl in legend_items
    )
    fig.add_annotation(
        x=0.5, y=-0.16, xref='paper', yref='paper',
        text=legend_text, showarrow=False, font=dict(size=10),
    )

    # Star footnote
    fig.add_annotation(
        x=0.5, y=-0.21, xref='paper', yref='paper',
        text='* = Austin MSA county',
        showarrow=False, font=dict(size=10, color=CONCRETE),
    )

    write_chart_html(fig, os.path.join(OUT_DIR, 'migration_austin_split.html'))
    print('  [4/4] migration_austin_split.html')
    return fig


# ── Combined Pages ───────────────────────────────────────────────────────────

PAGES = [
    {
        'num': '01',
        'title': 'The Divergence',
        'body': (
            '<p>Texas has topped U-Haul\'s Growth Index 7 of the last 10 years. '
            'But the IRS tells a different story.</p>'
            '<p>Florida captured $20.65B in net adjusted gross income in 2023. '
            'Texas: $5.5B. That\'s roughly <strong>$3.75 of net wealth flowing into '
            'Florida for every $1 into Texas</strong> &mdash; despite Texas leading '
            'in raw household count.</p>'
            '<p>One is a volume story. The other is a wealth story. '
            'Hustlers vs. retirees. They underwrite very differently.</p>'
        ),
        'source': 'U-Haul Growth Index 2025, IRS SOI Migration Data 2022&ndash;2023.',
    },
    {
        'num': '02',
        'title': 'Dollars per Door',
        'body': (
            '<p>Strip away total volume and ask: what does the average inbound '
            'household actually earn?</p>'
            '<ul>'
            '<li>Florida: <strong>$163K</strong> per net inbound household</li>'
            '<li>South Carolina: $108K</li>'
            '<li>Texas: $66K</li>'
            '</ul>'
            '<p>The US median household income is ~$75K. Texas is pulling movers '
            '<em>below</em> that line. Florida and South Carolina are pulling movers '
            'well above it.</p>'
            '<p>Same Sun Belt. Very different tenant profiles. Very different rent ceilings.</p>'
        ),
        'source': 'IRS SOI Migration Data 2022&ndash;2023.',
    },
    {
        'num': '03',
        'title': 'Flow of Capital, per Mover',
        'body': (
            '<p>Florida captures <strong>$34,100 in net AGI for every person who moves in</strong>. '
            'Texas: $10,000. That puts Texas in the same tier as Idaho and Nevada &mdash; '
            'not leading the pack.</p>'
            '<p>On the other end: New York loses $36.9K per mover. California: $30.6K. '
            'Massachusetts: $34.4K. The people arriving in those states bring materially '
            'less income than the people leaving.</p>'
            '<p>The second tier is worth watching. New Hampshire, Maine, Delaware, Idaho, '
            'and Montana are all capturing $14K&ndash;$19K per mover without ever making '
            'U-Haul\'s top 10. Selective wealth capture, not volume.</p>'
        ),
        'source': 'IRS SOI State Migration Data 2022&ndash;2023.',
    },
    {
        'num': '04',
        'title': 'The Austin Split',
        'body': (
            '<p>Zoom from state to county and the finding flips.</p>'
            '<p>Within the Austin MSA, wealth migration is a suburban story:</p>'
            '<ul>'
            '<li>Hays County: <strong>+$19.8K</strong> per mover (higher than Florida\'s state average)</li>'
            '<li>Williamson County: <strong>+$17.1K</strong> per mover</li>'
            '<li>Travis County: <strong>&minus;$1.8K</strong> per mover</li>'
            '</ul>'
            '<p>Travis isn\'t declining &mdash; it\'s sorting. High earners are moving '
            'to Leander, Lakeway, Dripping Springs, Kyle, and Buda. That shows up as '
            'Travis outflow and Williamson/Hays inflow.</p>'
            '<p>For context: Dallas is at &minus;$10.6K per mover. Harris (Houston) is at '
            '&minus;$7.8K. The same suburban wealth migration is happening across Texas metros.</p>'
            '<p>The Austin MSA weighted average is still +$8.3K &mdash; the suburbs are '
            'doing the heavy lifting.</p>'
        ),
        'source': 'IRS SOI County Migration Data 2022&ndash;2023.',
    },
]


def build_combined_html(figs):
    """Build a single branded HTML document with 4 page sections."""
    # Logo as base64 for header
    logo_path = Path(__file__).parent.parent.parent / 'data' / 'Aquila_Logo2.png'
    with open(logo_path, 'rb') as f:
        logo_b64 = base64.b64encode(f.read()).decode()

    # Convert each figure to an embedded HTML div (no full page wrapper)
    chart_divs = []
    for fig in figs:
        div = pio.to_html(fig, full_html=False, include_plotlyjs=False)
        chart_divs.append(div)

    # Build page sections
    sections = []
    for i, (page, div) in enumerate(zip(PAGES, chart_divs)):
        sections.append(f'''
        <section class="page">
            <div class="page-header">
                <span class="page-num">{page['num']}</span>
                <h2>{page['title']}</h2>
            </div>
            <div class="chart-container">
                {div}
            </div>
            <div class="post-body">
                {page['body']}
            </div>
            <div class="source">
                <strong>Source:</strong> {page['source']}
            </div>
        </section>''')

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Money vs. Movers &mdash; Migration Analysis &middot; AQUILA Research</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: 'Inter', {AQUILA_FONT};
    color: {NAVY};
    background: #f5f5f5;
    line-height: 1.6;
  }}

  .doc-header {{
    background: {NAVY};
    color: white;
    padding: 28px 48px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }}
  .doc-header img {{ height: 36px; }}
  .doc-header .label {{
    font-size: 12px;
    letter-spacing: 2px;
    text-transform: uppercase;
    opacity: 0.7;
  }}
  .doc-header h1 {{
    font-size: 28px;
    font-weight: 700;
    margin: 4px 0 0;
  }}
  .doc-header .subtitle {{
    font-size: 14px;
    opacity: 0.8;
    margin-top: 2px;
  }}

  .page {{
    background: white;
    max-width: 900px;
    margin: 32px auto;
    padding: 40px 48px;
    border-radius: 4px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    page-break-after: always;
  }}

  .page-header {{
    display: flex;
    align-items: baseline;
    gap: 14px;
    margin-bottom: 24px;
    border-bottom: 2px solid {NAVY};
    padding-bottom: 10px;
  }}
  .page-num {{
    font-size: 32px;
    font-weight: 700;
    color: {COPPER};
    line-height: 1;
  }}
  .page-header h2 {{
    font-size: 22px;
    font-weight: 600;
  }}

  .chart-container {{
    margin: 0 -16px 24px;
  }}

  .post-body {{
    font-size: 15px;
    color: #333;
  }}
  .post-body p {{ margin-bottom: 12px; }}
  .post-body ul {{
    margin: 8px 0 12px 24px;
  }}
  .post-body li {{ margin-bottom: 4px; }}
  .post-body strong {{ color: {NAVY}; }}

  .source {{
    margin-top: 20px;
    padding-top: 12px;
    border-top: 1px solid #e9e9ea;
    font-size: 12px;
    color: #888;
  }}

  @media print {{
    body {{ background: white; }}
    .doc-header {{ position: static; }}
    .page {{
      box-shadow: none;
      margin: 0;
      border-radius: 0;
      page-break-after: always;
    }}
  }}
</style>
</head>
<body>

<div class="doc-header">
    <div>
        <div class="label">AQUILA Research &middot; Market Intelligence &middot; April 2026</div>
        <h1>Money vs. Movers</h1>
        <div class="subtitle">Migration Analysis &mdash; U-Haul Growth Index vs. IRS Wealth Migration</div>
    </div>
    <img src="data:image/png;base64,{logo_b64}" alt="AQUILA">
</div>

{''.join(sections)}

<div style="text-align:center; padding: 24px; font-size: 12px; color: #888;">
    AQUILA Research &middot; realdatallc.github.io/aquila-insights
</div>

</body>
</html>'''

    out_path = os.path.join(OUT_DIR, 'migration_money_vs_movers.html')
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'  [+] migration_money_vs_movers.html (combined)')


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print('Generating Money vs. Movers migration charts...')
    os.makedirs(OUT_DIR, exist_ok=True)
    fig1 = chart_divergence()
    fig2 = chart_dollars_per_door()
    fig3 = chart_capital_per_mover()
    fig4 = chart_austin_split()
    build_combined_html([fig1, fig2, fig3, fig4])
    print('Done -- 4 charts + combined page written.')


if __name__ == '__main__':
    main()
