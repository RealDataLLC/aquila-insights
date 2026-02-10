"""
Austin Site Plan Permits Analysis - Development Pipeline Charts
Generates 6 interactive charts analyzing Austin's commercial development pipeline (2015-present)

Data Source: Austin Open Data Portal - Site Plan Cases
Charts: Pipeline volume, land use trends, geography, size distribution, approval timelines, density (FAR)
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

from aquila_graphing_tools import AQUILA_COLORS, AQUILA_FONT

print("=" * 80)
print("AUSTIN SITE PLAN PERMITS - DEVELOPMENT PIPELINE ANALYSIS")
print("=" * 80)

# ============================================================================
# STEP 1: Data Fetching
# ============================================================================
print("\nStep 1: Fetching data from Austin Open Data API...")

url = "https://data.austintexas.gov/resource/mavg-96ck.csv?$limit=25000"

try:
    # Use requests with headers to avoid 403 errors
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()

    # Parse CSV from response
    from io import StringIO
    df = pd.read_csv(StringIO(response.text))
    print(f"  OK - Fetched {len(df):,} records")
except Exception as e:
    print(f"  ERROR - Failed to fetch data: {e}")
    sys.exit(1)

# ============================================================================
# STEP 2: Data Cleaning
# ============================================================================
print("\nStep 2: Cleaning and processing data...")

# Parse dates
df['application_start_date'] = pd.to_datetime(df['application_start_date'], errors='coerce')
df['approval_date'] = pd.to_datetime(df['approval_date'], errors='coerce')

# Convert numeric fields
df['proposed_bldg_sq_footage'] = pd.to_numeric(df['proposed_bldg_sq_footage'], errors='coerce')
df['gross_site_area_acres'] = pd.to_numeric(df['gross_site_area_acres'], errors='coerce')
df['day_approved'] = pd.to_numeric(df['day_approved'], errors='coerce')

print(f"  - Total records before filtering: {len(df):,}")

# Filter: 2015 onward (live development market view)
df = df[df['application_start_date'] >= '2015-01-01'].copy()
print(f"  - Records from 2015+: {len(df):,}")

# Create dataset with SF data (needed for most charts)
df_with_sf = df[df['proposed_bldg_sq_footage'].notna() & (df['proposed_bldg_sq_footage'] > 0)].copy()
print(f"  - Records with valid SF data: {len(df_with_sf):,}")

# Print date range
print(f"  - Date range: {df['application_start_date'].min()} to {df['application_start_date'].max()}")
print(f"  - Total proposed SF: {df_with_sf['proposed_bldg_sq_footage'].sum() / 1_000_000:.1f}M SF")

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
    if any(word in land_use_lower for word in ['retail', 'restaurant', 'shopping', 'store']):
        return 'Retail'
    if any(word in land_use_lower for word in ['warehouse', 'industrial', 'manufacturing', 'distribution']):
        return 'Industrial'
    if any(word in land_use_lower for word in ['apartment', 'residential', 'condo', 'townhome', 'housing', 'dwelling']):
        return 'Residential'
    if any(word in land_use_lower for word in ['hotel', 'lodging', 'hospitality']):
        return 'Hospitality'

    return 'Other'

df_with_sf['land_use_category'] = df_with_sf['proposed_land_use'].apply(categorize_land_use)

# Show category distribution
category_counts = df_with_sf['land_use_category'].value_counts()
print(f"  - Land use categories:")
for cat, count in category_counts.items():
    print(f"    {cat}: {count:,} projects ({count/len(df_with_sf)*100:.1f}%)")

# Create output directory if needed
os.makedirs('charts/development', exist_ok=True)

# ============================================================================
# CHART 1: Development Pipeline Volume Over Time
# ============================================================================
print("\nChart 1: Generating Pipeline Volume by Quarter...")

# Group by quarter and status
df_with_sf['quarter'] = df_with_sf['application_start_date'].dt.to_period('Q').dt.to_timestamp()
pipeline_by_quarter = df_with_sf.groupby(['quarter', 'status'])['proposed_bldg_sq_footage'].sum().reset_index()

# Create stacked area chart
fig1 = px.area(
    pipeline_by_quarter,
    x='quarter',
    y='proposed_bldg_sq_footage',
    color='status',
    title='Austin Development Pipeline Volume by Quarter (2015-Present)',
    labels={
        'quarter': 'Quarter',
        'proposed_bldg_sq_footage': 'Proposed Building SF',
        'status': 'Permit Status'
    },
    color_discrete_sequence=AQUILA_COLORS
)

fig1.update_layout(
    height=650,
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(family=AQUILA_FONT, color='#172344'),
    legend=dict(
        title_font_family=AQUILA_FONT,
        orientation='h',
        yanchor='bottom',
        y=-0.25,
        xanchor='center',
        x=0.5
    ),
    xaxis=dict(
        showline=True,
        linecolor='#e9e9ea',
        linewidth=0.5,
        showgrid=False
    ),
    yaxis=dict(
        showline=True,
        linecolor='#e9e9ea',
        linewidth=0.5,
        showgrid=True,
        gridcolor='#e9e9ea',
        tickformat=','
    )
)

output_file = 'charts/development/pipeline_volume_by_quarter.html'
fig1.write_html(output_file)
print(f"  ✓ Saved to {output_file}")

# ============================================================================
# CHART 2: Development Activity by Land Use Type
# ============================================================================
print("\nChart 2: Generating Pipeline by Land Use Type...")

# Group by quarter and land use category
pipeline_by_use = df_with_sf.groupby(['quarter', 'land_use_category'])['proposed_bldg_sq_footage'].sum().reset_index()

fig2 = px.area(
    pipeline_by_use,
    x='quarter',
    y='proposed_bldg_sq_footage',
    color='land_use_category',
    title='Austin Development Activity by Land Use Type (2015-Present)',
    labels={
        'quarter': 'Quarter',
        'proposed_bldg_sq_footage': 'Proposed Building SF',
        'land_use_category': 'Land Use Category'
    },
    color_discrete_sequence=AQUILA_COLORS
)

fig2.update_layout(
    height=650,
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(family=AQUILA_FONT, color='#172344'),
    legend=dict(
        title_font_family=AQUILA_FONT,
        orientation='h',
        yanchor='bottom',
        y=-0.25,
        xanchor='center',
        x=0.5
    ),
    xaxis=dict(
        showline=True,
        linecolor='#e9e9ea',
        linewidth=0.5,
        showgrid=False
    ),
    yaxis=dict(
        showline=True,
        linecolor='#e9e9ea',
        linewidth=0.5,
        showgrid=True,
        gridcolor='#e9e9ea',
        tickformat=','
    )
)

output_file = 'charts/development/pipeline_by_land_use_type.html'
fig2.write_html(output_file)
print(f"  ✓ Saved to {output_file}")

# ============================================================================
# CHART 3: Development Activity by Geography (Top 15 Neighborhoods)
# ============================================================================
print("\nChart 3: Generating Pipeline by Neighborhood (Top 15)...")

# Group by neighborhood, get totals
neighborhood_totals = df_with_sf.groupby('neighborhood_plan_name').agg({
    'proposed_bldg_sq_footage': 'sum',
    'case_id': 'count'
}).reset_index()
neighborhood_totals.columns = ['neighborhood_plan_name', 'total_sf', 'project_count']

# Sort and take top 15
neighborhood_totals = neighborhood_totals.sort_values('total_sf', ascending=True).tail(15)

# Create horizontal bar chart
fig3 = go.Figure()

fig3.add_trace(go.Bar(
    y=neighborhood_totals['neighborhood_plan_name'],
    x=neighborhood_totals['total_sf'],
    orientation='h',
    marker=dict(color=AQUILA_COLORS[0]),
    text=neighborhood_totals['project_count'],
    texttemplate='%{text} projects',
    textposition='outside',
    hovertemplate='<b>%{y}</b><br>Total SF: %{x:,.0f}<br>Projects: %{text}<extra></extra>'
))

fig3.update_layout(
    title='Top 15 Neighborhoods by Development Activity (2015-Present)',
    xaxis_title='Total Proposed Building SF',
    yaxis_title='Neighborhood Plan',
    height=700,
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(family=AQUILA_FONT, color='#172344'),
    xaxis=dict(
        showline=True,
        linecolor='#e9e9ea',
        linewidth=0.5,
        showgrid=True,
        gridcolor='#e9e9ea',
        tickformat=','
    ),
    yaxis=dict(
        showline=True,
        linecolor='#e9e9ea',
        linewidth=0.5,
        showgrid=False
    )
)

output_file = 'charts/development/pipeline_by_neighborhood.html'
fig3.write_html(output_file)
print(f"  ✓ Saved to {output_file}")

# ============================================================================
# CHART 4: Project Size Distribution
# ============================================================================
print("\nChart 4: Generating Project Size Distribution...")

# Create size bins
size_bins = [0, 50000, 250000, 500000, float('inf')]
size_labels = ['Small (<50k SF)', 'Medium (50k-250k SF)', 'Large (250k-500k SF)', 'Mega (500k+ SF)']

df_with_sf['size_category'] = pd.cut(
    df_with_sf['proposed_bldg_sq_footage'],
    bins=size_bins,
    labels=size_labels,
    include_lowest=True
)

# Count projects by size category
size_distribution = df_with_sf['size_category'].value_counts().reindex(size_labels)

fig4 = go.Figure()

fig4.add_trace(go.Bar(
    x=size_distribution.index,
    y=size_distribution.values,
    marker=dict(color=AQUILA_COLORS[:4]),
    text=size_distribution.values,
    texttemplate='%{text:,}',
    textposition='outside',
    hovertemplate='<b>%{x}</b><br>Projects: %{y:,}<br>% of Total: %{customdata:.1f}%<extra></extra>',
    customdata=(size_distribution.values / size_distribution.sum() * 100)
))

fig4.update_layout(
    title='Austin Development Projects by Size Category (2015-Present)',
    xaxis_title='Project Size Category',
    yaxis_title='Number of Projects',
    height=600,
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(family=AQUILA_FONT, color='#172344'),
    xaxis=dict(
        showline=True,
        linecolor='#e9e9ea',
        linewidth=0.5,
        showgrid=False
    ),
    yaxis=dict(
        showline=True,
        linecolor='#e9e9ea',
        linewidth=0.5,
        showgrid=True,
        gridcolor='#e9e9ea',
        tickformat=','
    )
)

output_file = 'charts/development/project_size_distribution.html'
fig4.write_html(output_file)
print(f"  ✓ Saved to {output_file}")

# ============================================================================
# CHART 5: Approval Timeline Trends
# ============================================================================
print("\nChart 5: Generating Approval Timeline Trends...")

# Filter to projects with approval data
df_approved = df_with_sf[df_with_sf['day_approved'].notna() & (df_with_sf['day_approved'] > 0)].copy()

# Remove extreme outliers (>1000 days = ~2.7 years)
df_approved = df_approved[df_approved['day_approved'] <= 1000]

print(f"  - Projects with approval data: {len(df_approved):,}")
print(f"  - Median approval time: {df_approved['day_approved'].median():.0f} days")

# Group by quarter and calculate median
timeline_by_quarter = df_approved.groupby('quarter')['day_approved'].agg(['median', 'count']).reset_index()
timeline_by_quarter.columns = ['quarter', 'median_days', 'project_count']

# Filter quarters with at least 5 projects for statistical significance
timeline_by_quarter = timeline_by_quarter[timeline_by_quarter['project_count'] >= 5]

fig5 = go.Figure()

fig5.add_trace(go.Scatter(
    x=timeline_by_quarter['quarter'],
    y=timeline_by_quarter['median_days'],
    mode='lines+markers',
    line=dict(color=AQUILA_COLORS[0], width=3),
    marker=dict(size=8, color=AQUILA_COLORS[0]),
    name='Median Approval Days',
    hovertemplate='<b>%{x|%Y Q%q}</b><br>Median Days: %{y:.0f}<br>Projects: %{customdata}<extra></extra>',
    customdata=timeline_by_quarter['project_count']
))

fig5.update_layout(
    title='Austin Development Approval Timeline Trends (2015-Present)',
    xaxis_title='Quarter',
    yaxis_title='Median Days to Approval',
    height=600,
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(family=AQUILA_FONT, color='#172344'),
    showlegend=False,
    xaxis=dict(
        showline=True,
        linecolor='#e9e9ea',
        linewidth=0.5,
        showgrid=False
    ),
    yaxis=dict(
        showline=True,
        linecolor='#e9e9ea',
        linewidth=0.5,
        showgrid=True,
        gridcolor='#e9e9ea',
        tickformat=','
    )
)

output_file = 'charts/development/approval_timeline_trends.html'
fig5.write_html(output_file)
print(f"  ✓ Saved to {output_file}")

# ============================================================================
# CHART 6: Density Trends (FAR - Floor Area Ratio)
# ============================================================================
print("\nChart 6: Generating Density Trends (FAR)...")

# Filter to projects with both SF and acreage data
df_far = df_with_sf[
    (df_with_sf['gross_site_area_acres'].notna()) &
    (df_with_sf['gross_site_area_acres'] > 0)
].copy()

# Calculate FAR: Building SF / (Acres * 43,560 SF/acre)
df_far['far'] = df_far['proposed_bldg_sq_footage'] / (df_far['gross_site_area_acres'] * 43560)

# Filter outliers: FAR should be between 0 and 20 (20 is very dense, like downtown high-rise)
df_far = df_far[(df_far['far'] > 0) & (df_far['far'] <= 20)]

print(f"  - Projects with FAR data: {len(df_far):,}")
print(f"  - Median FAR: {df_far['far'].median():.2f}")

# Group by quarter and calculate median FAR
far_by_quarter = df_far.groupby('quarter')['far'].agg(['median', 'count']).reset_index()
far_by_quarter.columns = ['quarter', 'median_far', 'project_count']

# Filter quarters with at least 5 projects
far_by_quarter = far_by_quarter[far_by_quarter['project_count'] >= 5]

fig6 = go.Figure()

fig6.add_trace(go.Scatter(
    x=far_by_quarter['quarter'],
    y=far_by_quarter['median_far'],
    mode='lines+markers',
    line=dict(color=AQUILA_COLORS[2], width=3),
    marker=dict(size=8, color=AQUILA_COLORS[2]),
    name='Median FAR',
    hovertemplate='<b>%{x|%Y Q%q}</b><br>Median FAR: %{y:.2f}<br>Projects: %{customdata}<extra></extra>',
    customdata=far_by_quarter['project_count']
))

fig6.update_layout(
    title='Austin Development Density Trends - Floor Area Ratio (2015-Present)',
    xaxis_title='Quarter',
    yaxis_title='Median Floor Area Ratio (FAR)',
    height=600,
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(family=AQUILA_FONT, color='#172344'),
    showlegend=False,
    xaxis=dict(
        showline=True,
        linecolor='#e9e9ea',
        linewidth=0.5,
        showgrid=False
    ),
    yaxis=dict(
        showline=True,
        linecolor='#e9e9ea',
        linewidth=0.5,
        showgrid=True,
        gridcolor='#e9e9ea',
        tickformat='.2f'
    )
)

output_file = 'charts/development/density_trends_far.html'
fig6.write_html(output_file)
print(f"  ✓ Saved to {output_file}")

# ============================================================================
# Summary
# ============================================================================
print("\n" + "=" * 80)
print("CHART GENERATION COMPLETE")
print("=" * 80)
print(f"\n✓ Generated 6 charts in charts/development/")
print(f"✓ Data period: 2015-{df['application_start_date'].max().year}")
print(f"✓ Total records analyzed: {len(df):,}")
print(f"✓ Total proposed SF: {df_with_sf['proposed_bldg_sq_footage'].sum() / 1_000_000:.1f}M SF")
print(f"\nNext steps:")
print(f"  1. Review charts in charts/development/")
print(f"  2. Update README.md with chart links")
print(f"  3. Commit and push to feature branch")
print()
