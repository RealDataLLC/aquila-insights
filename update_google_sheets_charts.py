#!/usr/bin/env python3
"""
Update Google Sheets Charts
Regenerates all tenant demand charts from Google Sheets data

Usage:
    python3 update_google_sheets_charts.py
    python3 update_google_sheets_charts.py --update-readme
"""

import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import plotly.express as px
import plotly.graph_objects as go
import os
from dotenv import load_dotenv
from datetime import datetime
import sys

# Load environment
load_dotenv('aquila_graph.env')

# Colors
COLORS = {
    'background': '#FFFFFF',
    'text': '#2C3E50',
    'blue': '#00008B',
    'orange': '#DAA520',
    'light_gray': '#F8F9F9'
}

AQUILA_COLORS = [
    "#002A5C", "#005BAB", "#69A3D2", "#F2B134", "#FFD166", "#EDC87A",
    "#184D82", "#33658A", "#F6D266", "#114477", "#E7A932", "#DA993A"
]

def get_google_credentials():
    """Build Google credentials from environment variables"""
    credentials_dict = {
        "type": os.getenv("GOOGLE_SERVICE_ACCOUNT_TYPE"),
        "project_id": os.getenv("GOOGLE_PROJECT_ID"),
        "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("GOOGLE_PRIVATE_KEY"),
        "client_email": os.getenv("GOOGLE_CLIENT_EMAIL"),
        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
        "auth_uri": os.getenv("GOOGLE_AUTH_URI"),
        "token_uri": os.getenv("GOOGLE_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv("GOOGLE_AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.getenv("GOOGLE_CLIENT_X509_CERT_URL"),
        "universe_domain": os.getenv("GOOGLE_UNIVERSE_DOMAIN")
    }

    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]

    return ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)

def fetch_google_sheets_data():
    """Fetch tenant requirements data from Google Sheets"""
    print("Connecting to Google Sheets...")

    creds = get_google_credentials()
    client = gspread.authorize(creds)

    # Open spreadsheet
    spreadsheet_id = '1bzpRnUrpBH6l_zX7DtTypczZf5bpYVwqPUG3tzg2vec'
    sheet = client.open_by_key(spreadsheet_id).get_worksheet(0)

    print("Fetching data...")
    records = sheet.get_all_records()
    df = pd.DataFrame(records)

    print(f"✓ Loaded {len(df)} records")

    # Parse dates
    df['DATE OF REQUIREMENT'] = pd.to_datetime(df['DATE OF REQUIREMENT'], format='mixed', errors='coerce')
    df['DATE UPDATED'] = pd.to_datetime(df['DATE UPDATED'], format='mixed', errors='coerce')
    df['EFFECTIVE_DATE'] = df['DATE OF REQUIREMENT']

    # Parse numeric columns
    df['REQUIRED SF (LOW)'] = pd.to_numeric(df['REQUIRED SF (LOW)'], errors='coerce')
    df['REQUIRED SF (HIGH)'] = pd.to_numeric(df['REQUIRED SF (HIGH)'], errors='coerce')
    df['REQUIRED SF (AVG)'] = (df['REQUIRED SF (LOW)'] + df['REQUIRED SF (HIGH)']) / 2

    # Filter to recent data (since 2024-12-31)
    df = df[df['EFFECTIVE_DATE'] >= pd.Timestamp('2024-12-31')]

    print(f"✓ Filtered to {len(df)} records since 2024-12-31")

    return df

def generate_chart_1_total_sf(df):
    """Chart 1: Monthly Total Square Footage Requirements"""
    print("\n[1/4] Generating: Monthly Total SF Requirements...")

    # Monthly aggregation
    monthly_data = df.groupby(pd.Grouper(key='EFFECTIVE_DATE', freq='ME')).agg({
        'REQUIRED SF (LOW)': ['sum', 'count'],
        'REQUIRED SF (HIGH)': 'sum',
        'REQUIRED SF (AVG)': ['mean', 'median']
    }).reset_index()

    monthly_data.columns = [
        'EFFECTIVE_DATE', 'REQUIRED SF (LOW)', 'REQUIRED SF (COUNT)',
        'REQUIRED SF (HIGH)', 'REQUIRED SF (AVG)', 'REQUIRED SF (MEDIAN)'
    ]

    # Create chart
    fig = px.line(
        monthly_data,
        x='EFFECTIVE_DATE',
        y=['REQUIRED SF (LOW)', 'REQUIRED SF (HIGH)'],
        title='Monthly Total Square Footage Requirements',
        labels={'value': 'Square Footage', 'EFFECTIVE_DATE': 'Date'},
        color_discrete_sequence=[COLORS['orange'], COLORS['blue']]
    )

    fig.update_layout(
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['background'],
        font=dict(family='Segoe UI', size=12),
        title={'font': dict(family='Segoe UI', size=24)},
        xaxis=dict(
            gridcolor=COLORS['light_gray'],
            tickformat='%b %Y',
            showgrid=True,
            dtick="M1"
        ),
        yaxis=dict(gridcolor=COLORS['light_gray']),
        margin=dict(t=100, b=50, l=50, r=50)
    )

    os.makedirs("charts", exist_ok=True)
    fig.write_html("charts/requirements_sf_total.html")
    print("  ✓ Saved: charts/requirements_sf_total.html")

    return monthly_data

def generate_chart_2_avg_sf(monthly_data):
    """Chart 2: Monthly Average Square Footage Metrics (dual axis)"""
    print("\n[2/4] Generating: Monthly Average SF Metrics...")

    fig = go.Figure()

    # Lines for Mean and Median
    fig.add_trace(go.Scatter(
        x=monthly_data['EFFECTIVE_DATE'],
        y=monthly_data['REQUIRED SF (AVG)'],
        mode='lines+markers',
        name='Avg SF (Mean)',
        line=dict(color=COLORS['orange'])
    ))

    fig.add_trace(go.Scatter(
        x=monthly_data['EFFECTIVE_DATE'],
        y=monthly_data['REQUIRED SF (MEDIAN)'],
        mode='lines+markers',
        name='Avg SF (Median)',
        line=dict(color=COLORS['blue'])
    ))

    # Bars for COUNT (secondary y-axis)
    fig.add_trace(go.Bar(
        x=monthly_data['EFFECTIVE_DATE'],
        y=monthly_data['REQUIRED SF (COUNT)'],
        name='Record Count',
        yaxis='y2',
        marker_color=COLORS['text'],
        opacity=0.3
    ))

    fig.update_layout(
        title={
            'text': 'Monthly Average Square Footage Metrics',
            'font': dict(family='Segoe UI', size=24)
        },
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['background'],
        font=dict(family='Segoe UI', size=12),
        xaxis=dict(
            title='Date',
            gridcolor=COLORS['light_gray'],
            tickformat='%b %Y',
            dtick="M1",
            showgrid=True
        ),
        yaxis=dict(
            title="Square Footage",
            gridcolor=COLORS['light_gray']
        ),
        yaxis2=dict(
            title="Count",
            overlaying='y',
            side='right',
            titlefont=dict(family='Segoe UI', size=12, color=COLORS['text']),
            tickfont=dict(family='Segoe UI', size=12, color=COLORS['text'])
        ),
        legend=dict(orientation="h", y=-0.2),
        margin=dict(t=100, b=50, l=50, r=50)
    )

    fig.write_html("charts/requirements_sf_avg.html")
    print("  ✓ Saved: charts/requirements_sf_avg.html")

def generate_chart_3_by_industry(df):
    """Chart 3: Tenant Demand by Industry (donut chart)"""
    print("\n[3/4] Generating: Tenant Demand by Industry...")

    # Aggregate by industry
    industry_data = (
        df.dropna(subset=['REQUIRED SF (AVG)'])
          .groupby('INDUSTRY')['REQUIRED SF (AVG)']
          .sum()
          .reset_index()
    )

    # Clean data
    industry_data = industry_data[industry_data['REQUIRED SF (AVG)'] != 0]
    industry_data = industry_data[industry_data['INDUSTRY'].astype(str).str.strip() != '']

    # Top 7, rest as "Other"
    industry_data_sorted = industry_data.sort_values(by='REQUIRED SF (AVG)', ascending=False)
    top_n = 7
    largest = industry_data_sorted.iloc[:top_n]
    other = industry_data_sorted.iloc[top_n:]

    if not other.empty:
        other_row = {
            'INDUSTRY': 'Other',
            'REQUIRED SF (AVG)': other['REQUIRED SF (AVG)'].sum()
        }
        pie_data = pd.concat([largest, pd.DataFrame([other_row])], ignore_index=True)
    else:
        pie_data = largest

    # Colors
    industry_colors = (AQUILA_COLORS * ((len(pie_data) // len(AQUILA_COLORS)) + 1))[:len(pie_data)]

    fig = go.Figure(
        data=[
            go.Pie(
                labels=pie_data['INDUSTRY'],
                values=pie_data['REQUIRED SF (AVG)'],
                textinfo='label+percent',
                insidetextorientation='radial',
                hole=0.55,
                marker=dict(
                    line=dict(color=COLORS['background'], width=2),
                    colors=industry_colors
                )
            )
        ]
    )

    fig.update_layout(
        title={
            'text': 'Tenant Demand by Industry',
            'font': dict(family='Futura LT Pro', size=24)
        },
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['background'],
        font=dict(family='Futura LT Pro', size=12),
        showlegend=False,
        width=820,
        height=650,
        margin=dict(t=100, b=80, l=50, r=50)
    )

    fig.write_html("charts/requirements_sf_avg_by_industry.html")
    print("  ✓ Saved: charts/requirements_sf_avg_by_industry.html")

def generate_chart_4_by_size_range(df):
    """Chart 4: Total Cumulative SF Requested by Size Range"""
    print("\n[4/4] Generating: SF Requested by Size Range...")

    # Define size bins
    bins = [0, 14000, 40000, 100000, float('inf')]
    labels = ['0-14k', '15k-39k', '40k-99k', '100k+']

    df['SIZE RANGE'] = pd.cut(df['REQUIRED SF (AVG)'], bins=bins, labels=labels, right=False)

    # Group by size range
    size_group = df.groupby('SIZE RANGE', observed=True).agg(
        **{
            'Total SF Requested': ('REQUIRED SF (AVG)', 'sum'),
            'Number of Requirements': ('REQUIRED SF (AVG)', 'count')
        }
    ).reset_index()

    # Ensure all bins present
    size_group['SIZE RANGE'] = pd.Categorical(size_group['SIZE RANGE'], categories=labels, ordered=True)
    size_group = size_group.sort_values('SIZE RANGE').reset_index(drop=True)

    # Create chart
    fig = go.Figure(
        data=[
            go.Bar(
                y=size_group['SIZE RANGE'],
                x=size_group['Total SF Requested'],
                orientation='h',
                marker_color=AQUILA_COLORS[:len(size_group)],
                text=size_group['Number of Requirements'],
                textposition='inside',
                insidetextanchor='middle',
                hovertemplate=(
                    'Size Range: %{y}<br>'
                    'Total SF Requested: %{x:,.0f}<br>'
                    'Number of Requirements: %{text}<extra></extra>'
                ),
            )
        ]
    )

    fig.update_layout(
        title={
            'text': 'Total Cumulative SF Requested by Size Range',
            'font': dict(family='Segoe UI', size=22)
        },
        xaxis=dict(
            title='Total Cumulative Requested SF',
            showgrid=True,
            zeroline=True,
            showline=True,
            linecolor='lightgrey',
            linewidth=2,
            mirror=False,
            ticks='outside'
        ),
        yaxis=dict(
            title='Requirement Size Range (SF)',
            tickmode='array',
            tickvals=labels,
            ticktext=labels,
            showline=True,
            linecolor='lightgrey',
            linewidth=2,
            mirror=False,
            ticks='outside'
        ),
        font=dict(family='Futura LT Pro', size=12),
        plot_bgcolor=COLORS['background'],
        paper_bgcolor=COLORS['background'],
        width=820,
        height=500,
        margin=dict(t=80, b=80, l=120, r=50)
    )

    fig.update_traces(
        texttemplate='%{text} reqs',
        textfont=dict(family='Futura LT Pro', size=14)
    )

    fig.write_html("charts/requirements_by_size_range.html")
    print("  ✓ Saved: charts/requirements_by_size_range.html")

def update_readme_dates():
    """Update README.md with today's date for Google Sheets charts"""
    print("\nUpdating README.md dates...")

    today = datetime.now().strftime('%Y-%m-%d')

    # Read README
    with open('README.md', 'r') as f:
        content = f.read()

    # Update dates for Google Sheets charts
    replacements = {
        'Requirements Total SF': f'Requirements Total SF [{today}]',
        'Requirements Average SF': f'Requirements Average SF [{today}]',
        'Tenant Demand by Industry': f'Tenant Demand by Industry [{today}]',
        'Tenant Demand by Size Range and Number': f'Tenant Demand by Size Range and Number [{today}]'
    }

    for old, new in replacements.items():
        # Replace only if date exists (preserve existing format)
        import re
        pattern = re.escape(old) + r' \[\d{4}-\d{2}-\d{2}\]'
        if re.search(pattern, content):
            content = re.sub(pattern, new, content)

    # Write back
    with open('README.md', 'w') as f:
        f.write(content)

    print(f"  ✓ Updated README.md dates to {today}")

def main():
    """Main execution"""
    print("=" * 70)
    print("UPDATING GOOGLE SHEETS CHARTS")
    print("=" * 70)

    try:
        # Fetch data
        df = fetch_google_sheets_data()

        # Generate all charts
        monthly_data = generate_chart_1_total_sf(df)
        generate_chart_2_avg_sf(monthly_data)
        generate_chart_3_by_industry(df)
        generate_chart_4_by_size_range(df)

        print("\n" + "=" * 70)
        print("✓ SUCCESS: All Google Sheets charts updated")
        print("=" * 70)

        # Update README if requested
        if '--update-readme' in sys.argv:
            update_readme_dates()

        print("\nGenerated charts:")
        print("  • requirements_sf_total.html")
        print("  • requirements_sf_avg.html")
        print("  • requirements_sf_avg_by_industry.html")
        print("  • requirements_by_size_range.html")
        print("\nNext steps:")
        print("  1. Review charts in browser")
        print("  2. Commit: git add charts/ README.md && git commit -m 'Update Google Sheets charts'")
        print("  3. Push to GitHub")
        print("")

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
