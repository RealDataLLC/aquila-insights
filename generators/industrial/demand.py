import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402
"""
Industrial Demand by Tenant Size - TITM (Tenants in the Market)
Generates industrial demand charts from the Industrial Google Sheet TITM tab.
"""
import pandas as pd
import numpy as np
import sys
import os

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please ensure gspread and oauth2client are installed")
    sys.exit(1)

import plotly.graph_objects as go
from datetime import datetime
from dotenv import load_dotenv
from aquila_graphing_tools import AQUILA_COLORS, AQUILA_FONT
from aquila.charts import write_chart_html


def main():
    # Load environment variables
    load_dotenv('aquila_graph.env')

    # Check if we should use JSON file or environment variables
    json_file = 'aquilacommercialsheets-923494a59a4b.json'
    use_json = os.path.exists(json_file)

    print("=" * 80)
    print("INDUSTRIAL DEMAND BY TENANT SIZE - TITM")
    print("=" * 80)

    # ============================================================================
    # STEP 1: Connect to Google Sheets
    # ============================================================================
    print("\nStep 1: Connecting to Google Sheets...")

    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]

    if use_json:
        print("  Using JSON credentials file")
        credentials = ServiceAccountCredentials.from_json_keyfile_name(json_file, scope)
    else:
        print("  Using environment variables for credentials")

        def get_env_stripped(key):
            val = os.getenv(key)
            if val:
                return val.strip('"').strip("'")
            return val

        credentials_dict = {
            "type": get_env_stripped("GOOGLE_SERVICE_ACCOUNT_TYPE"),
            "project_id": get_env_stripped("GOOGLE_PROJECT_ID"),
            "private_key_id": get_env_stripped("GOOGLE_PRIVATE_KEY_ID"),
            "private_key": get_env_stripped("GOOGLE_PRIVATE_KEY").replace('\\n', '\n') if get_env_stripped("GOOGLE_PRIVATE_KEY") else None,
            "client_email": get_env_stripped("GOOGLE_CLIENT_EMAIL"),
            "client_id": get_env_stripped("GOOGLE_CLIENT_ID"),
            "auth_uri": get_env_stripped("GOOGLE_AUTH_URI"),
            "token_uri": get_env_stripped("GOOGLE_TOKEN_URI"),
            "auth_provider_x509_cert_url": get_env_stripped("GOOGLE_AUTH_PROVIDER_X509_CERT_URL"),
            "client_x509_cert_url": get_env_stripped("GOOGLE_CLIENT_X509_CERT_URL"),
            "universe_domain": get_env_stripped("GOOGLE_UNIVERSE_DOMAIN")
        }
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)

    client = gspread.authorize(credentials)
    spreadsheet_id = '1natA0ALaQnX3U_vGC5Vrchy1QqmbW8k0zvTKwuE2wys'
    sheet = client.open_by_key(spreadsheet_id)

    print("  OK - Connected successfully")

    # ============================================================================
    # STEP 2: Read TITM tab
    # ============================================================================
    print("\nStep 2: Reading data from TITM tab...")

    titm_ws = sheet.get_worksheet(1)  # Index 1 is TITM
    rows = titm_ws.get_all_values()
    headers = rows[0]
    df = pd.DataFrame(rows[1:], columns=headers)

    print(f"    - Raw rows loaded: {len(df)}")

    # Remove completely empty rows
    df = df[df.apply(lambda row: any(str(v).strip() != '' for v in row), axis=1)]
    print(f"    - Non-empty rows: {len(df)}")

    # Remove section header rows (e.g., "Dead or Done Deals" with no date/SF)
    df = df[df['Date'].astype(str).str.strip() != ''].copy()
    print(f"    - Rows with dates: {len(df)}")

    # ============================================================================
    # STEP 3: Standardize data
    # ============================================================================
    print("\nStep 3: Standardizing data...")

    # Parse dates
    df['date'] = pd.to_datetime(df['Date'], errors='coerce')

    # Parse SF values (remove commas)
    df['sf_low'] = pd.to_numeric(
        df['Size (SF) Low'].astype(str).str.replace(',', '').str.strip(),
        errors='coerce'
    )
    df['sf_high'] = pd.to_numeric(
        df['Size (SF) High'].astype(str).str.replace(',', '').str.strip(),
        errors='coerce'
    )

    # Calculate average SF
    df['sf_avg'] = (df['sf_low'] + df['sf_high']) / 2

    # Normalize status
    df['status_clean'] = df['Status'].astype(str).str.strip().str.lower()

    # Filter out rows with no valid data
    df = df[df['date'].notna() & df['sf_avg'].notna()].copy()

    # Restrict to deals after 2021
    df = df[df['date'] >= pd.Timestamp('2022-01-01')].copy()

    print(f"    - Valid rows (with date and SF) after 2021: {len(df)}")
    print(f"    - Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"    - SF range: {df['sf_avg'].min():,.0f} to {df['sf_avg'].max():,.0f}")
    print(f"    - Median SF: {df['sf_avg'].median():,.0f}")

    # Show status breakdown
    print(f"\n    Status breakdown:")
    for status, count in df['status_clean'].value_counts().items():
        print(f"      {status}: {count}")

    # Show use type breakdown
    print(f"\n    Use type breakdown:")
    for use, count in df['Use'].str.strip().value_counts().head(10).items():
        print(f"      {use}: {count}")

    # ============================================================================
    # STEP 4: Generate Industrial Demand by Tenant Size chart
    # ============================================================================
    print("\nStep 4: Generating Industrial Demand by Tenant Size chart...")

    # Create output directory
    os.makedirs('charts/industrial', exist_ok=True)

    # Add quarter column
    df['quarter'] = df['date'].dt.to_period('Q').dt.to_timestamp()

    # Industrial-scaled size bins (5 categories)
    demand_bins = [0, 25000, 50000, 100000, 250000, float('inf')]
    demand_labels = ['Sub 25k SF', '25k-50k SF', '50k-100k SF', '100k-250k SF', 'Mega (250k+)']

    df['size_category'] = pd.cut(
        df['sf_avg'],
        bins=demand_bins,
        labels=demand_labels,
        right=False
    )

    # Aggregate by quarter and size category
    quarterly_by_size = df.groupby(['quarter', 'size_category'], observed=False).agg(
        segment_demand=('sf_avg', 'sum'),
        count=('sf_avg', 'count')
    ).reset_index()

    # Total demand per quarter
    quarterly_total = df.groupby('quarter').agg(
        total_demand=('sf_avg', 'sum')
    ).reset_index()

    quarters = sorted(quarterly_by_size['quarter'].unique())

    if len(quarters) == 0:
        print("  WARNING: No quarter data found, exiting")
        sys.exit(1)

    print(f"    - Quarters: {len(quarters)} ({quarters[0].to_period('Q')} to {quarters[-1].to_period('Q')})")

    # Colors for each size category
    category_colors = {
        'Mega (250k+)':  AQUILA_COLORS[0],   # Navy
        '100k-250k SF':  AQUILA_COLORS[1],   # Glass Blue
        '50k-100k SF':   AQUILA_COLORS[2],   # Glass Blue Alt
        '25k-50k SF':    AQUILA_COLORS[3],   # Concrete
        'Sub 25k SF':    AQUILA_COLORS[4],   # Copper
    }

    category_order = ['Mega (250k+)', '100k-250k SF', '50k-100k SF', '25k-50k SF', 'Sub 25k SF']

    # Create figure
    fig = go.Figure()

    # Grouped bars for each size category
    for category in category_order:
        cat_data = quarterly_by_size[quarterly_by_size['size_category'] == category]
        cat_data = cat_data[['quarter', 'segment_demand', 'count']].set_index('quarter').reindex(quarters).reset_index()
        cat_data['segment_demand'] = cat_data['segment_demand'].fillna(0)
        cat_data['count'] = cat_data['count'].fillna(0)

        # Format quarter labels as "YYYY Qn"
        cat_data['quarter_label'] = cat_data['quarter'].dt.to_period('Q').astype(str)

        fig.add_trace(go.Bar(
            x=cat_data['quarter_label'],
            y=cat_data['segment_demand'],
            name=category,
            marker_color=category_colors[category],
            hovertemplate=(
                f'<b>{category}</b><br>'
                'Quarter: %{x}<br>'
                'Demand: %{y:,.0f} SF<br>'
                '<extra></extra>'
            ),
        ))

    # Total demand line on secondary y-axis
    total_data = quarterly_total.set_index('quarter').reindex(quarters).reset_index()
    total_data['total_demand'] = total_data['total_demand'].fillna(0)
    total_data['quarter_label'] = total_data['quarter'].dt.to_period('Q').astype(str)

    fig.add_trace(go.Scatter(
        x=total_data['quarter_label'],
        y=total_data['total_demand'],
        mode='lines+markers',
        name='Total Demand',
        line=dict(color=AQUILA_COLORS[0], width=3, dash='dash'),
        marker=dict(size=10, color=AQUILA_COLORS[0], symbol='line-ew-open', line=dict(width=3)),
        yaxis='y2',
        hovertemplate=(
            '<b>Total Demand</b><br>'
            'Quarter: %{x}<br>'
            'Total: %{y:,.0f} SF<br>'
            '<extra></extra>'
        ),
    ))

    min_quarter = quarters[0]
    max_quarter = quarters[-1]

    fig.update_layout(
        title={
            'text': f'Industrial Demand by Tenant Size (Quarterly: {min_quarter.to_period("Q")}-{max_quarter.to_period("Q")})',
            'font': dict(family=AQUILA_FONT, size=24, color=AQUILA_COLORS[0]),
            'x': 0.5,
            'xanchor': 'center',
        },
        barmode='group',
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, size=12, color=AQUILA_COLORS[0]),
        xaxis=dict(
            title='',
            showgrid=False,
            showline=True,
            linecolor='lightgrey',
            linewidth=1,
            tickfont=dict(size=10),
            tickangle=-45,
        ),
        yaxis=dict(
            title=dict(text='Segment Demand (SF)', font=dict(size=14)),
            showgrid=True,
            gridcolor='#e9e9ea',
            showline=True,
            linecolor='lightgrey',
            linewidth=1,
            tickformat=',',
            rangemode='tozero',
        ),
        yaxis2=dict(
            title=dict(text='Total Demand (SF)', font=dict(size=14)),
            overlaying='y',
            side='right',
            showgrid=False,
            showline=True,
            linecolor='lightgrey',
            linewidth=1,
            tickformat=',',
            rangemode='tozero',
        ),
        legend=dict(
            orientation='h',
            yanchor='top',
            y=-0.2,
            xanchor='center',
            x=0.5,
            font=dict(size=12),
            traceorder='normal',
        ),
        height=650,
        width=1400,
        margin=dict(t=80, b=140, l=80, r=80),
        hovermode='x unified',
    )

    chart_path = 'charts/industrial/industrial_demand_by_tenant_size.html'
    write_chart_html(fig, chart_path)
    print(f"    OK: Saved {chart_path}")

    # ============================================================================
    # CHART 2: Industrial Demand by Use Type (donut chart)
    # ============================================================================
    print("\nStep 5: Generating Industrial Demand by Use Type chart...")

    use_data = (
        df.dropna(subset=['sf_avg'])
        .assign(use_clean=lambda x: x['Use'].str.strip())
        .groupby('use_clean')['sf_avg']
        .sum()
        .reset_index()
    )
    use_data = use_data[use_data['sf_avg'] > 0]
    use_data = use_data[use_data['use_clean'].astype(str).str.strip() != '']

    # Date range for title
    min_date = df['date'].min()
    max_date = df['date'].max()
    date_range_note = f"(Data from {min_date:%b %Y} to {max_date:%b %Y})"

    # Top 7 + Other
    use_data_sorted = use_data.sort_values(by='sf_avg', ascending=False)
    top_n = 7
    largest = use_data_sorted.iloc[:top_n]
    other = use_data_sorted.iloc[top_n:]

    if not other.empty:
        other_row = pd.DataFrame([{
            'use_clean': 'Other',
            'sf_avg': other['sf_avg'].sum()
        }])
        pie_data = pd.concat([largest, other_row], ignore_index=True)
    else:
        pie_data = largest

    # Extend color palette
    use_colors = (AQUILA_COLORS * ((len(pie_data) // len(AQUILA_COLORS)) + 1))[:len(pie_data)]

    fig2 = go.Figure(
        data=[
            go.Pie(
                labels=pie_data['use_clean'],
                values=pie_data['sf_avg'],
                textinfo='label+percent',
                insidetextorientation='radial',
                hole=0.55,
                marker=dict(
                    line=dict(color='white', width=2),
                    colors=use_colors
                )
            )
        ]
    )
    fig2.update_layout(
        title={
            'text': f'Industrial Tenant Demand by Use Type {date_range_note}',
            'font': dict(family=AQUILA_FONT, size=24, color=AQUILA_COLORS[0]),
            'x': 0.5, 'xanchor': 'center'
        },
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family=AQUILA_FONT, size=12, color=AQUILA_COLORS[0]),
        showlegend=False,
        width=1000,
        height=650,
        margin=dict(t=100, b=80, l=50, r=50)
    )

    chart2_path = 'charts/industrial/industrial_demand_by_use_type.html'
    write_chart_html(fig2, chart2_path)
    print(f"    OK: Saved {chart2_path}")

    # ============================================================================
    # CHART 3: Industrial Requirements by Size Range (horizontal bars)
    # ============================================================================
    print("\nStep 6: Generating Industrial Requirements by Size Range chart...")

    size_group = df.groupby('size_category', observed=False).agg(
        total_sf=('sf_avg', 'sum'),
        count=('sf_avg', 'count')
    ).reset_index()

    size_group['size_category'] = pd.Categorical(
        size_group['size_category'],
        categories=demand_labels,
        ordered=True
    )
    size_group = size_group.sort_values('size_category').reset_index(drop=True)

    fig3 = go.Figure(
        data=[
            go.Bar(
                y=size_group['size_category'].astype(str),
                x=size_group['total_sf'],
                orientation='h',
                marker_color=[category_colors[cat] for cat in size_group['size_category']],
                text=size_group['count'],
                texttemplate='%{text} reqs',
                textposition='inside',
                textfont=dict(family=AQUILA_FONT, size=14),
                hovertemplate=(
                    'Size Range: %{y}<br>'
                    'Total SF: %{x:,.0f}<br>'
                    'Count: %{text}<extra></extra>'
                ),
            )
        ]
    )
    fig3.update_layout(
        title={
            'text': f'Industrial: Total Cumulative SF Requested by Size Range {date_range_note}',
            'font': dict(family=AQUILA_FONT, size=22, color=AQUILA_COLORS[0]),
            'x': 0.5, 'xanchor': 'center'
        },
        xaxis=dict(
            title='Total Cumulative Requested SF',
            showgrid=True,
            showline=True,
            linecolor='lightgrey',
            linewidth=2,
            tickformat=',',
        ),
        yaxis=dict(
            title='Requirement Size Range (SF)',
            showline=True,
            linecolor='lightgrey',
            linewidth=2
        ),
        font=dict(family=AQUILA_FONT, size=12, color=AQUILA_COLORS[0]),
        plot_bgcolor='white',
        paper_bgcolor='white',
        width=1000,
        height=500,
        margin=dict(t=80, b=80, l=140, r=50)
    )

    chart3_path = 'charts/industrial/industrial_requirements_by_size_range.html'
    write_chart_html(fig3, chart3_path)
    print(f"    OK: Saved {chart3_path}")

    # ============================================================================
    # CHART 4: Monthly Total SF Requirements (Low/High lines)
    # ============================================================================
    print("\nStep 7: Generating Industrial Monthly Total SF Requirements chart...")

    import plotly.express as px

    monthly_data = df.groupby(pd.Grouper(key='date', freq='ME')).agg({
        'sf_low': ['sum', 'count'],
        'sf_high': 'sum',
        'sf_avg': ['mean', 'median']
    }).reset_index()

    monthly_data.columns = [
        'date', 'sf_low_sum', 'count', 'sf_high_sum', 'sf_avg_mean', 'sf_avg_median'
    ]

    COLORS = {
        'background': '#FFFFFF',
        'text': '#172344',
        'blue': AQUILA_COLORS[0],    # Navy
        'orange': AQUILA_COLORS[4],  # Copper
        'gridcolor': '#e9e9ea',
        'light_gray': '#F8F9F9'
    }

    fig4 = px.line(
        monthly_data,
        x='date',
        y=['sf_low_sum', 'sf_high_sum'],
        title='Industrial: Monthly Total Square Footage Requirements',
        labels={
            'value': 'Square Footage',
            'date': 'Date',
        },
        color_discrete_sequence=[COLORS['orange'], COLORS['blue']]
    )

    for i, trace_name in enumerate(['Low Requirement (sqft)', 'High Requirement (sqft)']):
        fig4.data[i].name = trace_name

    fig4.update_layout(
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['background'],
        font=dict(family=AQUILA_FONT, size=12, color=AQUILA_COLORS[0]),
        title={'font': dict(family=AQUILA_FONT, size=24, color=AQUILA_COLORS[0]), 'x': 0.5, 'xanchor': 'center'},
        xaxis=dict(
            gridcolor=COLORS['light_gray'],
            showgrid=True,
            showline=True,
            linecolor='lightgrey'
        ),
        yaxis=dict(
            gridcolor=COLORS['light_gray'],
            showline=True,
            linecolor='lightgrey',
            tickformat=','
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5
        ),
        margin=dict(t=100, b=50, l=50, r=50),
        height=550
    )

    chart4_path = 'charts/industrial/industrial_requirements_sf_total.html'
    write_chart_html(fig4, chart4_path)
    print(f"    OK: Saved {chart4_path}")

    # ============================================================================
    # CHART 5: Monthly Average SF Metrics (dual-axis)
    # ============================================================================
    print("\nStep 8: Generating Industrial Monthly Average SF Metrics chart...")

    fig5 = go.Figure()

    fig5.add_trace(go.Scatter(
        x=monthly_data['date'],
        y=monthly_data['sf_avg_mean'],
        mode='lines+markers',
        name='Avg SF (Mean)',
        line=dict(color=COLORS['orange'])
    ))
    fig5.add_trace(go.Scatter(
        x=monthly_data['date'],
        y=monthly_data['sf_avg_median'],
        mode='lines+markers',
        name='Avg SF (Median)',
        line=dict(color=COLORS['blue'])
    ))

    fig5.add_trace(go.Bar(
        x=monthly_data['date'],
        y=monthly_data['count'],
        name='Record Count',
        yaxis='y2',
        marker_color=COLORS['text'],
        opacity=0.3
    ))

    fig5.update_layout(
        title={
            'text': 'Industrial: Monthly Average Square Footage Metrics',
            'font': dict(family=AQUILA_FONT, size=24, color=AQUILA_COLORS[0]),
            'x': 0.5,
            'xanchor': 'center',
        },
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['background'],
        font=dict(family=AQUILA_FONT, size=12, color=AQUILA_COLORS[0]),
        xaxis=dict(
            title='Date',
            gridcolor=COLORS['light_gray'],
            showgrid=True,
            showline=True,
            linecolor='lightgrey'
        ),
        yaxis=dict(
            title="Square Footage",
            gridcolor=COLORS['light_gray'],
            showline=True,
            linecolor='lightgrey',
            tickformat=','
        ),
        yaxis2=dict(
            title=dict(text="Count", font=dict(family=AQUILA_FONT, size=12, color=COLORS['text'])),
            overlaying='y',
            side='right',
            tickfont=dict(family=AQUILA_FONT, size=12, color=COLORS['text'])
        ),
        legend=dict(orientation="h", y=-0.2),
        margin=dict(t=100, b=50, l=50, r=50)
    )

    chart5_path = 'charts/industrial/industrial_requirements_sf_avg.html'
    write_chart_html(fig5, chart5_path)
    print(f"    OK: Saved {chart5_path}")

    # ============================================================================
    # SUMMARY
    # ============================================================================
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"\nDataset:")
    print(f"  - Total records: {len(df)}")
    print(f"  - Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"  - Total SF (avg): {df['sf_avg'].sum():,.0f}")
    print(f"  - Unique use types: {df['Use'].str.strip().nunique()}")
    print(f"  - Unique submarkets: {df['Submarket'].str.strip().nunique()}")

    print(f"\nCharts generated:")
    print(f"  OK: {chart_path}")
    print(f"  OK: {chart2_path}")
    print(f"  OK: {chart3_path}")
    print(f"  OK: {chart4_path}")
    print(f"  OK: {chart5_path}")

    print("\n" + "=" * 80)
    print("OK: Complete!")
    print("=" * 80)



if __name__ == '__main__':
    main()
