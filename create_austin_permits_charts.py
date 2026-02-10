"""
Austin Site Plan Permits Analysis - Development Pipeline Charts
Generates 6 interactive charts analyzing Austin's commercial development pipeline (2015-present)

Data Source: Austin Open Data Portal - Site Plan Cases (mavg-96ck)
Available fields: permit counts, proposed_land_use, council_district, status, dates
Note: This dataset does NOT include square footage data, so all charts use permit counts.

Charts:
1. Pipeline volume by quarter (permit count by status)
2. Development activity by land use type
3. Top council districts by permit activity
4. Permit status distribution
5. Approval timeline trends (days from application to status change)
6. Year-over-year permit trends
"""
import pandas as pd
import numpy as np
import requests
import os
import sys

try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError as e:
    print(f"Error importing plotly: {e}")
    print("Please ensure plotly is installed: pip install plotly")
    sys.exit(1)

import time

from aquila_graphing_tools import AQUILA_COLORS, AQUILA_FONT

# Base directory for output (absolute path avoids OneDrive sync issues)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, 'charts', 'development')


def save_chart(fig, filename):
    """Save chart with retry logic to handle OneDrive file locks"""
    filepath = os.path.join(OUTPUT_DIR, filename)
    for attempt in range(3):
        try:
            fig.write_html(filepath)
            print(f"  [OK] Saved to charts/development/{filename}")
            return
        except OSError as e:
            if attempt < 2:
                print(f"  [RETRY] Write failed ({e}), retrying in 2s...")
                time.sleep(2)
            else:
                raise


print("=" * 80)
print("AUSTIN SITE PLAN PERMITS - DEVELOPMENT PIPELINE ANALYSIS")
print("=" * 80)

# ============================================================================
# STEP 1: Data Fetching (JSON API - CSV endpoint not supported for this dataset)
# ============================================================================
print("\nStep 1: Fetching data from Austin Open Data API...")

base_url = "https://data.austintexas.gov/resource/mavg-96ck.json"
all_records = []
offset = 0
batch_size = 5000

try:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    while True:
        params = {
            '$limit': batch_size,
            '$offset': offset,
            '$order': 'application_start_date DESC'
        }
        response = requests.get(base_url, headers=headers, params=params, timeout=60)
        response.raise_for_status()
        batch = response.json()
        if not batch:
            break
        all_records.extend(batch)
        offset += batch_size
        print(f"  Fetched {len(all_records):,} records so far...")

    df = pd.DataFrame(all_records)
    print(f"  OK - Total: {len(df):,} records")
except Exception as e:
    print(f"  ERROR - Failed to fetch data: {e}")
    sys.exit(1)

# ============================================================================
# STEP 2: Data Cleaning
# ============================================================================
print("\nStep 2: Cleaning and processing data...")

# Parse dates
df['application_start_date'] = pd.to_datetime(df['application_start_date'], errors='coerce')
df['status_date'] = pd.to_datetime(df['status_date'], errors='coerce')

print(f"  - Total records before filtering: {len(df):,}")

# Filter: 2015 onward
df = df[df['application_start_date'] >= '2015-01-01'].copy()
print(f"  - Records from 2015+: {len(df):,}")

# Print date range
print(f"  - Date range: {df['application_start_date'].min().date()} to {df['application_start_date'].max().date()}")

# Calculate days to status change (approval/closure/etc.)
df['days_to_status'] = (df['status_date'] - df['application_start_date']).dt.days

# Create quarter column
df['quarter'] = df['application_start_date'].dt.to_period('Q').dt.to_timestamp()

# ============================================================================
# STEP 3: Land Use Categorization
# ============================================================================
print("\nStep 3: Categorizing land uses...")

def categorize_land_use(land_use_str):
    """Map proposed_land_use to CRE categories"""
    if pd.isna(land_use_str):
        return 'Other'
    land_use_lower = str(land_use_str).lower()

    # Check for mixed-use indicators (check first, most specific)
    if any(word in land_use_lower for word in ['mixed', 'multi-use', 'mixed-use']):
        return 'Mixed-Use'

    # Check specific categories
    if any(word in land_use_lower for word in ['office', 'medical office']):
        return 'Office'
    if any(word in land_use_lower for word in ['retail', 'restaurant', 'shopping', 'store', 'commercial']):
        return 'Retail/Commercial'
    if any(word in land_use_lower for word in ['warehouse', 'industrial', 'manufacturing', 'distribution']):
        return 'Industrial'
    if any(word in land_use_lower for word in ['apartment', 'residential', 'condo', 'townhome',
                                                 'housing', 'dwelling', 'single family', 'duplex',
                                                 'multifamily', 'multi-family']):
        return 'Residential'
    if any(word in land_use_lower for word in ['hotel', 'lodging', 'hospitality']):
        return 'Hospitality'

    return 'Other'

df['land_use_category'] = df['proposed_land_use'].apply(categorize_land_use)

# Show category distribution
category_counts = df['land_use_category'].value_counts()
print("  - Land use categories:")
for cat, count in category_counts.items():
    print(f"    {cat}: {count:,} permits ({count/len(df)*100:.1f}%)")

# Create output directory if needed
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================================
# Shared layout helper
# ============================================================================
def aquila_layout(title, xaxis_title='', yaxis_title='', height=650, show_legend=True):
    """Return standard Aquila layout dict"""
    layout = dict(
        title=title,
        height=height,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, color='#172344'),
        xaxis=dict(
            title=xaxis_title,
            showline=True,
            linecolor='#e9e9ea',
            linewidth=0.5,
            showgrid=False
        ),
        yaxis=dict(
            title=yaxis_title,
            showline=True,
            linecolor='#e9e9ea',
            linewidth=0.5,
            showgrid=True,
            gridcolor='#e9e9ea',
            tickformat=','
        )
    )
    if show_legend:
        layout['legend'] = dict(
            title_font_family=AQUILA_FONT,
            orientation='h',
            yanchor='bottom',
            y=-0.25,
            xanchor='center',
            x=0.5
        )
    else:
        layout['showlegend'] = False
    return layout

# ============================================================================
# CHART 1: Development Pipeline Volume Over Time (Permit Counts by Status)
# ============================================================================
print("\nChart 1: Generating Pipeline Volume by Quarter...")

pipeline_by_quarter = df.groupby(['quarter', 'status']).size().reset_index(name='permit_count')

fig1 = px.area(
    pipeline_by_quarter,
    x='quarter',
    y='permit_count',
    color='status',
    title='Austin Site Plan Permits by Quarter (2015-Present)',
    labels={
        'quarter': 'Quarter',
        'permit_count': 'Number of Permits',
        'status': 'Permit Status'
    },
    color_discrete_sequence=AQUILA_COLORS
)
fig1.update_layout(**aquila_layout(
    'Austin Site Plan Permits by Quarter (2015-Present)',
    'Quarter', 'Number of Permits'
))

save_chart(fig1, 'pipeline_volume_by_quarter.html')

# ============================================================================
# CHART 2: Development Activity by Land Use Type
# ============================================================================
print("\nChart 2: Generating Pipeline by Land Use Type...")

pipeline_by_use = df.groupby(['quarter', 'land_use_category']).size().reset_index(name='permit_count')

fig2 = px.area(
    pipeline_by_use,
    x='quarter',
    y='permit_count',
    color='land_use_category',
    title='Austin Development Activity by Land Use Type (2015-Present)',
    labels={
        'quarter': 'Quarter',
        'permit_count': 'Number of Permits',
        'land_use_category': 'Land Use Category'
    },
    color_discrete_sequence=AQUILA_COLORS
)
fig2.update_layout(**aquila_layout(
    'Austin Development Activity by Land Use Type (2015-Present)',
    'Quarter', 'Number of Permits'
))

save_chart(fig2, 'pipeline_by_land_use_type.html')

# ============================================================================
# CHART 3: Top Council Districts by Permit Activity
# ============================================================================
print("\nChart 3: Generating Pipeline by Council District...")

# Filter to records with council district data
df_with_district = df[df['council_district'].notna()].copy()

district_totals = df_with_district.groupby('council_district').size().reset_index(name='permit_count')
district_totals = district_totals.sort_values('permit_count', ascending=True)

# Format district labels
district_totals['district_label'] = 'District ' + district_totals['council_district'].astype(str)

fig3 = go.Figure()

fig3.add_trace(go.Bar(
    y=district_totals['district_label'],
    x=district_totals['permit_count'],
    orientation='h',
    marker=dict(color=AQUILA_COLORS[0]),
    text=district_totals['permit_count'],
    texttemplate='%{text:,} permits',
    textposition='outside',
    hovertemplate='<b>%{y}</b><br>Permits: %{x:,}<extra></extra>'
))

fig3.update_layout(**aquila_layout(
    'Austin Site Plan Permits by Council District (2015-Present)',
    'Number of Permits', 'Council District',
    height=700, show_legend=False
))

save_chart(fig3, 'pipeline_by_council_district.html')

# ============================================================================
# CHART 4: Permit Status Distribution
# ============================================================================
print("\nChart 4: Generating Permit Status Distribution...")

status_counts = df['status'].value_counts().reset_index()
status_counts.columns = ['status', 'count']
status_counts = status_counts.sort_values('count', ascending=True)

fig4 = go.Figure()

fig4.add_trace(go.Bar(
    y=status_counts['status'],
    x=status_counts['count'],
    orientation='h',
    marker=dict(color=AQUILA_COLORS[0]),
    text=status_counts['count'],
    texttemplate='%{text:,}',
    textposition='outside',
    hovertemplate='<b>%{y}</b><br>Permits: %{x:,}<br>% of Total: %{customdata:.1f}%<extra></extra>',
    customdata=(status_counts['count'] / status_counts['count'].sum() * 100)
))

fig4.update_layout(**aquila_layout(
    'Austin Site Plan Permit Status Distribution (2015-Present)',
    'Number of Permits', 'Permit Status',
    height=600, show_legend=False
))

save_chart(fig4, 'permit_status_distribution.html')

# ============================================================================
# CHART 5: Approval Timeline Trends
# ============================================================================
print("\nChart 5: Generating Approval Timeline Trends...")

# Filter to permits with valid timeline data (positive days, not extreme outliers)
df_with_timeline = df[
    (df['days_to_status'].notna()) &
    (df['days_to_status'] > 0) &
    (df['days_to_status'] <= 1500)
].copy()

print(f"  - Permits with timeline data: {len(df_with_timeline):,}")
if len(df_with_timeline) > 0:
    print(f"  - Median days to status change: {df_with_timeline['days_to_status'].median():.0f} days")

    timeline_by_quarter = df_with_timeline.groupby('quarter')['days_to_status'].agg(['median', 'count']).reset_index()
    timeline_by_quarter.columns = ['quarter', 'median_days', 'permit_count']

    # Filter quarters with at least 10 permits for statistical significance
    timeline_by_quarter = timeline_by_quarter[timeline_by_quarter['permit_count'] >= 10]

    fig5 = go.Figure()

    fig5.add_trace(go.Scatter(
        x=timeline_by_quarter['quarter'],
        y=timeline_by_quarter['median_days'],
        mode='lines+markers',
        line=dict(color=AQUILA_COLORS[0], width=3),
        marker=dict(size=8, color=AQUILA_COLORS[0]),
        name='Median Days',
        hovertemplate='<b>%{x|%Y Q%q}</b><br>Median Days: %{y:.0f}<br>Permits: %{customdata}<extra></extra>',
        customdata=timeline_by_quarter['permit_count']
    ))

    fig5.update_layout(**aquila_layout(
        'Austin Site Plan Approval Timeline Trends (2015-Present)',
        'Quarter', 'Median Days to Status Change',
        height=600, show_legend=False
    ))

    save_chart(fig5, 'approval_timeline_trends.html')
else:
    print("  [SKIP] No timeline data available")

# ============================================================================
# CHART 6: Year-over-Year Permit Trends
# ============================================================================
print("\nChart 6: Generating Year-over-Year Permit Trends...")

df['year'] = df['application_start_date'].dt.year

# Exclude current year if incomplete (less than 3 months of data)
current_year = pd.Timestamp.now().year
latest_month = df[df['year'] == current_year]['application_start_date'].dt.month.max()
if pd.notna(latest_month) and latest_month < 3:
    yoy_df = df[df['year'] < current_year].copy()
    print(f"  - Excluding {current_year} (only {int(latest_month)} month(s) of data)")
else:
    yoy_df = df.copy()

yoy_counts = yoy_df.groupby(['year', 'land_use_category']).size().reset_index(name='permit_count')

fig6 = px.bar(
    yoy_counts,
    x='year',
    y='permit_count',
    color='land_use_category',
    title='Austin Site Plan Permits Year-over-Year by Land Use (2015-Present)',
    labels={
        'year': 'Year',
        'permit_count': 'Number of Permits',
        'land_use_category': 'Land Use Category'
    },
    color_discrete_sequence=AQUILA_COLORS,
    barmode='stack'
)

fig6.update_layout(**aquila_layout(
    'Austin Site Plan Permits Year-over-Year by Land Use (2015-Present)',
    'Year', 'Number of Permits'
))
fig6.update_xaxes(dtick=1)

save_chart(fig6, 'permits_yoy_by_land_use.html')

# ============================================================================
# Summary
# ============================================================================
print("\n" + "=" * 80)
print("CHART GENERATION COMPLETE")
print("=" * 80)
print(f"\n  Generated 6 charts in charts/development/")
print(f"  Data period: 2015-{df['application_start_date'].max().year}")
print(f"  Total records analyzed: {len(df):,}")
print(f"\nNext steps:")
print(f"  1. Review charts in charts/development/")
print(f"  2. Update README.md with chart links")
print(f"  3. Commit and push to feature branch")
print()
