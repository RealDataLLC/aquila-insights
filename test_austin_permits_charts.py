"""
TEST VERSION - Austin Site Plan Permits Analysis
Uses sample data to verify chart generation works correctly
"""
import pandas as pd
import numpy as np
import os
import sys

try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError as e:
    print(f"Error importing plotly: {e}")
    sys.exit(1)

from aquila_graphing_tools import AQUILA_COLORS, AQUILA_FONT

print("=" * 80)
print("TEST: AUSTIN SITE PLAN PERMITS - DEVELOPMENT PIPELINE ANALYSIS")
print("=" * 80)
print("\nUsing sample data for testing chart generation...")

# Load sample data
df = pd.read_csv('sample_austin_permits_data.csv')
print(f"  OK - Loaded {len(df):,} sample records")

# Parse dates
df['application_start_date'] = pd.to_datetime(df['application_start_date'], errors='coerce')
df['approval_date'] = pd.to_datetime(df['approval_date'], errors='coerce')

# Convert numeric fields
df['proposed_bldg_sq_footage'] = pd.to_numeric(df['proposed_bldg_sq_footage'], errors='coerce')
df['gross_site_area_acres'] = pd.to_numeric(df['gross_site_area_acres'], errors='coerce')
df['day_approved'] = pd.to_numeric(df['day_approved'], errors='coerce')

# Filter: 2015 onward
df = df[df['application_start_date'] >= '2015-01-01'].copy()
df_with_sf = df[df['proposed_bldg_sq_footage'].notna() & (df['proposed_bldg_sq_footage'] > 0)].copy()

print(f"  - Records with valid SF data: {len(df_with_sf):,}")
print(f"  - Date range: {df['application_start_date'].min()} to {df['application_start_date'].max()}")
print(f"  - Total proposed SF: {df_with_sf['proposed_bldg_sq_footage'].sum() / 1_000_000:.1f}M SF")

# Land use categorization
def categorize_land_use(land_use_str):
    if pd.isna(land_use_str):
        return 'Other'
    land_use_lower = str(land_use_str).lower()
    if any(word in land_use_lower for word in ['mixed', 'multi-use', 'mixed-use']):
        return 'Mixed-Use'
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

# Create output directory
os.makedirs('charts/development', exist_ok=True)

# CHART 1: Pipeline Volume by Quarter
print("\nChart 1: Pipeline Volume by Quarter...")
df_with_sf['quarter'] = df_with_sf['application_start_date'].dt.to_period('Q').dt.to_timestamp()
pipeline_by_quarter = df_with_sf.groupby(['quarter', 'status'])['proposed_bldg_sq_footage'].sum().reset_index()

fig1 = px.area(
    pipeline_by_quarter,
    x='quarter',
    y='proposed_bldg_sq_footage',
    color='status',
    title='Austin Development Pipeline Volume by Quarter (2015-Present)',
    labels={'quarter': 'Quarter', 'proposed_bldg_sq_footage': 'Proposed Building SF', 'status': 'Permit Status'},
    color_discrete_sequence=AQUILA_COLORS
)
fig1.update_layout(
    height=650, plot_bgcolor='white', paper_bgcolor='white',
    font=dict(family=AQUILA_FONT, color='#172344'),
    legend=dict(orientation='h', yanchor='bottom', y=-0.25, xanchor='center', x=0.5),
    xaxis=dict(showline=True, linecolor='#e9e9ea', linewidth=0.5, showgrid=False),
    yaxis=dict(showline=True, linecolor='#e9e9ea', linewidth=0.5, showgrid=True, gridcolor='#e9e9ea', tickformat=',')
)
fig1.write_html('charts/development/pipeline_volume_by_quarter.html')
print("  ✓ Saved")

# CHART 2: Pipeline by Land Use
print("\nChart 2: Pipeline by Land Use Type...")
pipeline_by_use = df_with_sf.groupby(['quarter', 'land_use_category'])['proposed_bldg_sq_footage'].sum().reset_index()

fig2 = px.area(
    pipeline_by_use,
    x='quarter',
    y='proposed_bldg_sq_footage',
    color='land_use_category',
    title='Austin Development Activity by Land Use Type (2015-Present)',
    labels={'quarter': 'Quarter', 'proposed_bldg_sq_footage': 'Proposed Building SF', 'land_use_category': 'Land Use Category'},
    color_discrete_sequence=AQUILA_COLORS
)
fig2.update_layout(
    height=650, plot_bgcolor='white', paper_bgcolor='white',
    font=dict(family=AQUILA_FONT, color='#172344'),
    legend=dict(orientation='h', yanchor='bottom', y=-0.25, xanchor='center', x=0.5),
    xaxis=dict(showline=True, linecolor='#e9e9ea', linewidth=0.5, showgrid=False),
    yaxis=dict(showline=True, linecolor='#e9e9ea', linewidth=0.5, showgrid=True, gridcolor='#e9e9ea', tickformat=',')
)
fig2.write_html('charts/development/pipeline_by_land_use_type.html')
print("  ✓ Saved")

# CHART 3: Top Neighborhoods
print("\nChart 3: Pipeline by Neighborhood...")
neighborhood_totals = df_with_sf.groupby('neighborhood_plan_name').agg({
    'proposed_bldg_sq_footage': 'sum',
    'case_id': 'count'
}).reset_index()
neighborhood_totals.columns = ['neighborhood_plan_name', 'total_sf', 'project_count']
neighborhood_totals = neighborhood_totals.sort_values('total_sf', ascending=True).tail(10)  # Top 10 for sample

fig3 = go.Figure()
fig3.add_trace(go.Bar(
    y=neighborhood_totals['neighborhood_plan_name'],
    x=neighborhood_totals['total_sf'],
    orientation='h',
    marker=dict(color=AQUILA_COLORS[0]),
    text=neighborhood_totals['project_count'],
    texttemplate='%{text} projects',
    textposition='outside'
))
fig3.update_layout(
    title='Top Neighborhoods by Development Activity (2015-Present)',
    xaxis_title='Total Proposed Building SF',
    yaxis_title='Neighborhood Plan',
    height=600, plot_bgcolor='white', paper_bgcolor='white',
    font=dict(family=AQUILA_FONT, color='#172344'),
    xaxis=dict(showline=True, linecolor='#e9e9ea', linewidth=0.5, showgrid=True, gridcolor='#e9e9ea', tickformat=','),
    yaxis=dict(showline=True, linecolor='#e9e9ea', linewidth=0.5, showgrid=False)
)
fig3.write_html('charts/development/pipeline_by_neighborhood.html')
print("  ✓ Saved")

# CHART 4: Size Distribution
print("\nChart 4: Project Size Distribution...")
size_bins = [0, 50000, 250000, 500000, float('inf')]
size_labels = ['Small (<50k SF)', 'Medium (50k-250k SF)', 'Large (250k-500k SF)', 'Mega (500k+ SF)']
df_with_sf['size_category'] = pd.cut(df_with_sf['proposed_bldg_sq_footage'], bins=size_bins, labels=size_labels, include_lowest=True)
size_distribution = df_with_sf['size_category'].value_counts().reindex(size_labels)

fig4 = go.Figure()
fig4.add_trace(go.Bar(
    x=size_distribution.index,
    y=size_distribution.values,
    marker=dict(color=AQUILA_COLORS[:4]),
    text=size_distribution.values,
    texttemplate='%{text:,}',
    textposition='outside'
))
fig4.update_layout(
    title='Austin Development Projects by Size Category (2015-Present)',
    xaxis_title='Project Size Category',
    yaxis_title='Number of Projects',
    height=600, plot_bgcolor='white', paper_bgcolor='white',
    font=dict(family=AQUILA_FONT, color='#172344'),
    xaxis=dict(showline=True, linecolor='#e9e9ea', linewidth=0.5, showgrid=False),
    yaxis=dict(showline=True, linecolor='#e9e9ea', linewidth=0.5, showgrid=True, gridcolor='#e9e9ea', tickformat=',')
)
fig4.write_html('charts/development/project_size_distribution.html')
print("  ✓ Saved")

# CHART 5: Approval Timelines
print("\nChart 5: Approval Timeline Trends...")
df_approved = df_with_sf[df_with_sf['day_approved'].notna() & (df_with_sf['day_approved'] > 0)].copy()
df_approved = df_approved[df_approved['day_approved'] <= 1000]
timeline_by_quarter = df_approved.groupby('quarter')['day_approved'].agg(['median', 'count']).reset_index()
timeline_by_quarter.columns = ['quarter', 'median_days', 'project_count']
timeline_by_quarter = timeline_by_quarter[timeline_by_quarter['project_count'] >= 2]  # Lowered for sample

fig5 = go.Figure()
fig5.add_trace(go.Scatter(
    x=timeline_by_quarter['quarter'],
    y=timeline_by_quarter['median_days'],
    mode='lines+markers',
    line=dict(color=AQUILA_COLORS[0], width=3),
    marker=dict(size=8, color=AQUILA_COLORS[0])
))
fig5.update_layout(
    title='Austin Development Approval Timeline Trends (2015-Present)',
    xaxis_title='Quarter',
    yaxis_title='Median Days to Approval',
    height=600, plot_bgcolor='white', paper_bgcolor='white',
    font=dict(family=AQUILA_FONT, color='#172344'),
    showlegend=False,
    xaxis=dict(showline=True, linecolor='#e9e9ea', linewidth=0.5, showgrid=False),
    yaxis=dict(showline=True, linecolor='#e9e9ea', linewidth=0.5, showgrid=True, gridcolor='#e9e9ea', tickformat=',')
)
fig5.write_html('charts/development/approval_timeline_trends.html')
print("  ✓ Saved")

# CHART 6: FAR Trends
print("\nChart 6: Density Trends (FAR)...")
df_far = df_with_sf[(df_with_sf['gross_site_area_acres'].notna()) & (df_with_sf['gross_site_area_acres'] > 0)].copy()
df_far['far'] = df_far['proposed_bldg_sq_footage'] / (df_far['gross_site_area_acres'] * 43560)
df_far = df_far[(df_far['far'] > 0) & (df_far['far'] <= 20)]
far_by_quarter = df_far.groupby('quarter')['far'].agg(['median', 'count']).reset_index()
far_by_quarter.columns = ['quarter', 'median_far', 'project_count']
far_by_quarter = far_by_quarter[far_by_quarter['project_count'] >= 2]

fig6 = go.Figure()
fig6.add_trace(go.Scatter(
    x=far_by_quarter['quarter'],
    y=far_by_quarter['median_far'],
    mode='lines+markers',
    line=dict(color=AQUILA_COLORS[2], width=3),
    marker=dict(size=8, color=AQUILA_COLORS[2])
))
fig6.update_layout(
    title='Austin Development Density Trends - Floor Area Ratio (2015-Present)',
    xaxis_title='Quarter',
    yaxis_title='Median Floor Area Ratio (FAR)',
    height=600, plot_bgcolor='white', paper_bgcolor='white',
    font=dict(family=AQUILA_FONT, color='#172344'),
    showlegend=False,
    xaxis=dict(showline=True, linecolor='#e9e9ea', linewidth=0.5, showgrid=False),
    yaxis=dict(showline=True, linecolor='#e9e9ea', linewidth=0.5, showgrid=True, gridcolor='#e9e9ea', tickformat='.2f')
)
fig6.write_html('charts/development/density_trends_far.html')
print("  ✓ Saved")

print("\n" + "=" * 80)
print("TEST COMPLETE: All 6 charts generated successfully!")
print("=" * 80)
print("\nTo generate charts with real data:")
print("  1. Run create_austin_permits_charts.py in your local environment")
print("  2. Ensure you have network access to data.austintexas.gov")
print()
