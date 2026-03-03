#!/usr/bin/env python3
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402
"""
Generate AMS Property Management KPI chart from property split list
Shows number of buildings and combined square footage by property type
for properties managed by Aquila Management Services (AMS)
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from aquila_graphing_tools import AQUILA_COLORS, AQUILA_FONT
from aquila.charts import write_chart_html


def main():
    # Read the Excel file (headers start at row 3, which is index 2)
    file_path = 'data/AMS- Property Split List (Updated 1.9.26).xlsx'
    df = pd.read_excel(file_path, header=2)

    # Clean the data
    # Remove leading/trailing spaces from column names
    df.columns = df.columns.str.strip()

    # Get the two columns we need
    property_col = 'Type of              Property'
    sqft_col = 'Square \nFootage'

    # Remove rows with missing values in either column
    df_clean = df[[property_col, sqft_col]].dropna()

    # Clean property type names (remove extra spaces, standardize)
    df_clean[property_col] = df_clean[property_col].str.strip().str.replace(r'\s+', ' ', regex=True)

    # Calculate metrics by property type
    metrics = df_clean.groupby(property_col).agg({
        sqft_col: ['sum', 'count']
    }).reset_index()

    # Flatten column names
    metrics.columns = ['Property Type', 'Total Square Footage', 'Number of Buildings']

    # Sort by total square footage for better visualization
    metrics = metrics.sort_values('Total Square Footage', ascending=True)

    # Create figure with subplots (2 columns for the two metrics)
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Total Square Footage', 'Number of Buildings'),
        horizontal_spacing=0.15
    )

    # Add bar for Total Square Footage (left subplot)
    fig.add_trace(
        go.Bar(
            y=metrics['Property Type'],
            x=metrics['Total Square Footage'],
            orientation='h',
            marker_color=AQUILA_COLORS[0],  # Navy blue
            text=metrics['Total Square Footage'].apply(lambda x: f'{x:,.0f}'),
            textposition='auto',
            hovertemplate='<b>%{y}</b><br>Total SF: %{x:,.0f}<extra></extra>',
            showlegend=False
        ),
        row=1, col=1
    )

    # Add bar for Number of Buildings (right subplot)
    fig.add_trace(
        go.Bar(
            y=metrics['Property Type'],
            x=metrics['Number of Buildings'],
            orientation='h',
            marker_color=AQUILA_COLORS[1],  # Gold
            text=metrics['Number of Buildings'],
            textposition='auto',
            hovertemplate='<b>%{y}</b><br>Buildings: %{x}<extra></extra>',
            showlegend=False
        ),
        row=1, col=2
    )

    # Update layout with Aquila styling
    fig.update_layout(
        title={
            'text': 'AMS Property Management KPIs',
            'font': {'size': 24, 'family': AQUILA_FONT, 'color': '#172344'},
            'x': 0.5, 'xanchor': 'center'
        },
        height=600,
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, color='#172344', size=12),
        margin=dict(l=150, r=50, t=100, b=80)
    )

    # Update all x-axes
    fig.update_xaxes(
        showgrid=True,
        gridcolor='#e9e9ea',
        showline=True,
        linecolor='#172344',
        linewidth=1
    )

    # Update all y-axes
    fig.update_yaxes(
        showgrid=False,
        showline=True,
        linecolor='#172344',
        linewidth=1
    )

    # Update subplot titles styling
    fig.update_annotations(font=dict(size=14, family=AQUILA_FONT, color='#172344'))

    # Save to charts directory
    output_file = 'charts/property-management/ams_managed_properties_kpi.html'
    write_chart_html(fig, output_file)
    print(f"OK: Chart saved to {output_file}")

    # Print summary
    print("\n" + "="*60)
    print("AQUILA KPI SUMMARY")
    print("="*60)
    print(metrics.to_string(index=False))
    print("\n" + "="*60)
    print(f"Total Properties: {metrics['Number of Buildings'].sum()}")
    print(f"Total Square Footage: {metrics['Total Square Footage'].sum():,.0f}")
    print("="*60)



if __name__ == '__main__':
    main()
