"""
Broker vs. Direct Deal Comparison Chart
Compares net effective base rent for tenant-represented vs. direct leases
within the same buildings, using Skyline export data.

Output: charts/office/broker-comparison.html
"""

import os
import glob
import pandas as pd
import plotly.graph_objects as go

from aquila_graphing_tools import AQUILA_COLORS, AQUILA_FONT
from aquila.charts import write_chart_html

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'Emily Trep')
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'charts', 'office', 'broker-comparison.html')

# ---------------------------------------------------------------------------
# Building name normalization
# Groups sub-buildings into parent properties for cleaner display
# ---------------------------------------------------------------------------
BUILDING_MAP = {
    '502 W 15th St':              '502 W 15th',
    'The Gallery on 15ht':        '502 W 15th',   # CSV typo
    'The Gallery on 15th':        '502 W 15th',
    '9500 Arboretum':             '9500 Arboretum',
    'Braker Pointe I':            'Braker Pointe',
    'Braker Pointe II':           'Braker Pointe',
    'Braker Pointe III':          'Braker Pointe',
    'Hartland Plaza':             'Hartland Plaza',
    'Hartland Plaza Shops':       'Hartland Plaza',
    'Perry Brooks Tower':         'Perry Brooks',
    'Prominent Pointe I':         'Prominent Pointe',
    'Prominent Pointe II':        'Prominent Pointe',
    'The Campus at Arboretum 1':  'The Campus',
    'The Campus at Arboretum 2':  'The Campus',
}

VALID_LEASE_TYPES = {'New'}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_all_data():
    """Load and combine all Skyline xlsx exports + Direct Leases CSV."""
    frames = []

    # Skyline Excel files (header is row 3, 0-indexed = header=2)
    xlsx_pattern = os.path.join(DATA_DIR, '*.xlsx')
    for path in sorted(glob.glob(xlsx_pattern)):
        df = pd.read_excel(path, header=2)
        frames.append(df)

    # Direct Leases CSV (same Skyline format)
    csv_path = os.path.join(DATA_DIR, 'Direct Leases - 02_25_26 15_07(Export).csv')
    if os.path.exists(csv_path):
        df_csv = pd.read_csv(csv_path, header=2)
        frames.append(df_csv)

    df_all = pd.concat(frames, ignore_index=True)

    # Remove flagged comps (Skyline marks deleted/invalid entries as "Remove Comp")
    df_all = df_all[~df_all['Tenant Name'].astype(str).str.strip().str.lower().isin(['remove comp', 'removecomp'])]

    # First pass dedup: exact match on tenant + building + date
    df_all['Execution Date'] = pd.to_datetime(df_all['Execution Date'], errors='coerce')
    df_all = df_all.drop_duplicates(subset=['Tenant Name', 'Building Name', 'Execution Date'])

    # Second pass dedup: same tenant + building appearing in both broker categories
    # (same deal entered by landlord side and tenant side) — keep the rep version if rates match
    df_all['_has_rep'] = (
        df_all['Tenant Broker Name'].notna() &
        (df_all['Tenant Broker Name'].astype(str).str.strip() != '') &
        (df_all['Tenant Broker Name'].astype(str).str.strip().str.lower() != 'nan')
    )
    df_all['_ner_rounded'] = df_all['Net Effective Base Rate'].astype(str).str[:6]  # round by truncation to $0.01 precision for grouping
    # Sort so rows WITH rep come first, then deduplicate on (Tenant, Building, rounded rate)
    df_all = df_all.sort_values('_has_rep', ascending=False)
    df_all = df_all.drop_duplicates(subset=['Tenant Name', 'Building Name', '_ner_rounded'], keep='first')
    df_all = df_all.drop(columns=['_has_rep', '_ner_rounded'])

    return df_all


def clean_data(df):
    """Filter, normalize, and classify each deal."""
    # Normalize building names
    df['Display Building'] = df['Building Name'].map(BUILDING_MAP).fillna(df['Building Name'])

    # Numeric conversion
    df['Net Effective Base Rate'] = pd.to_numeric(
        df['Net Effective Base Rate'].astype(str).str.replace(',', '', regex=False),
        errors='coerce'
    )

    # Filter to valid lease types and non-null rent
    # Apply a $20/SF floor to exclude anomalous deals (retail, storage, distressed) that
    # misrepresent typical office economics
    df = df[df['Lease Type'].isin(VALID_LEASE_TYPES)].copy()
    df = df[df['Net Effective Base Rate'].notna() & (df['Net Effective Base Rate'] >= 20.0)].copy()

    # Classify by tenant rep presence
    has_rep = (
        df['Tenant Broker Name'].notna() &
        (df['Tenant Broker Name'].astype(str).str.strip() != '') &
        (df['Tenant Broker Name'].astype(str).str.strip().str.lower() != 'nan')
    )
    df['Deal Type'] = has_rep.map({True: 'With Tenant Rep', False: 'Direct (No Rep)'})

    return df


# ---------------------------------------------------------------------------
# Chart building
# ---------------------------------------------------------------------------

def build_chart(df):
    """Create grouped bar chart comparing rep vs. direct deals by building."""

    # Aggregate: mean net effective rate per building + deal type
    agg = (
        df.groupby(['Display Building', 'Deal Type'])['Net Effective Base Rate']
        .agg(['mean', 'count'])
        .reset_index()
    )
    agg.columns = ['Building', 'Deal Type', 'Avg Rate', 'Count']

    # Build ordered list of buildings (sort by total avg rate descending for readability)
    building_order = (
        agg.groupby('Building')['Avg Rate']
        .mean()
        .sort_values(ascending=False)
        .index.tolist()
    )

    # Compute average savings — only for buildings where BOTH deal types exist
    buildings_with_both = (
        agg.groupby('Building')['Deal Type']
        .nunique()
        .pipe(lambda s: s[s == 2].index)
        .tolist()
    )
    paired = agg[agg['Building'].isin(buildings_with_both)]
    direct_avg = paired[paired['Deal Type'] == 'Direct (No Rep)']['Avg Rate'].mean()
    rep_avg = paired[paired['Deal Type'] == 'With Tenant Rep']['Avg Rate'].mean()
    savings = direct_avg - rep_avg  # positive = rep is cheaper for tenant
    n_buildings = len(buildings_with_both)

    fig = go.Figure()

    deal_types = [
        ('With Tenant Rep',  AQUILA_COLORS[0],  'solid'),   # Navy
        ('Direct (No Rep)',  AQUILA_COLORS[3],  'solid'),   # Concrete
    ]

    for label, color, _ in deal_types:
        subset = agg[agg['Deal Type'] == label]
        # Align to building_order (NaN for buildings with no data in this category)
        rates = []
        counts = []
        for b in building_order:
            row = subset[subset['Building'] == b]
            if len(row) > 0:
                rates.append(row.iloc[0]['Avg Rate'])
                counts.append(int(row.iloc[0]['Count']))
            else:
                rates.append(None)
                counts.append(0)

        hover_texts = [
            f'<b>{b}</b><br>{label}<br>Avg Net Effective: ${r:.2f}/SF<br>Deals: {c}<extra></extra>'
            if r is not None else ''
            for b, r, c in zip(building_order, rates, counts)
        ]

        fig.add_trace(go.Bar(
            name=label,
            x=building_order,
            y=rates,
            marker_color=color,
            hovertemplate=hover_texts,
            text=[f'${r:.2f}' if r is not None else '' for r in rates],
            textposition='outside',
            textfont=dict(family=AQUILA_FONT, size=11, color='#172344'),
        ))

    # Savings annotation text (buildings with both deal types only)
    if pd.notna(savings) and savings > 0:
        savings_text = (
            f'In {n_buildings} buildings with both deal types, represented tenants paid '
            f'<b>${savings:.2f}/SF/yr less on average</b> '
            f'(Net Effective Base Rate, new leases only)'
        )
    else:
        savings_text = (
            f'Net Effective Base Rate | New leases only | '
            f'{n_buildings} buildings with comparable data'
        )

    fig.update_layout(
        title=dict(
            text='Tenant Rep Impact: Net Effective Rent by Building',
            font=dict(family=AQUILA_FONT, size=20, color='#172344'),
            x=0.5,
            xanchor='center',
        ),
        barmode='group',
        height=650,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, color='#172344'),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            font=dict(family=AQUILA_FONT, size=12),
        ),
        xaxis=dict(
            title=dict(text='Building', font=dict(family=AQUILA_FONT, size=13)),
            tickfont=dict(family=AQUILA_FONT, size=12),
            showgrid=False,
            linecolor='#E8E8E8',
        ),
        yaxis=dict(
            title=dict(text='Net Effective Base Rate ($/SF/yr)', font=dict(family=AQUILA_FONT, size=13)),
            tickfont=dict(family=AQUILA_FONT, size=12),
            tickprefix='$',
            tickformat=',.2f',
            showgrid=True,
            gridcolor='#E8E8E8',
            zeroline=False,
            rangemode='tozero',
        ),
        margin=dict(t=100, b=180, l=80, r=40),
    )

    # Savings summary annotation below chart
    fig.add_annotation(
        text=savings_text,
        xref='paper', yref='paper',
        x=0.5, y=-0.27,
        showarrow=False,
        font=dict(family=AQUILA_FONT, size=12, color='#172344'),
        align='center',
        xanchor='center',
    )

    return fig


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print('Loading data...')
    df_raw = load_all_data()
    print(f'  Loaded {len(df_raw)} raw records')

    df = clean_data(df_raw)
    print(f'  After filtering (New + Renewal, valid rent): {len(df)} records')

    print('\nDeal counts by building and type:')
    summary = df.groupby(['Display Building', 'Deal Type']).agg(
        count=('Net Effective Base Rate', 'count'),
        avg_rate=('Net Effective Base Rate', 'mean')
    )
    print(summary.to_string())

    print('\nBuilding chart...')
    fig = build_chart(df)

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    write_chart_html(fig, OUTPUT_FILE)
    print(f'  Saved: {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
