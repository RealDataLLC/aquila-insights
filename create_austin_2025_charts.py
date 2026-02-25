"""
Austin 2025 Industries & Companies Charts
==========================================
Generates 6 Plotly HTML charts from the Austin Chamber relocations/expansions data.
Charts support the article: "The Industries and Companies That Came to Austin in 2025"

Output: charts/economic-indicators/austin_2025_*.html
Run:    python create_austin_2025_charts.py
"""

import os
import pandas as pd
import plotly.graph_objects as go

from aquila_graphing_tools import AQUILA_COLORS, AQUILA_FONT

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
EXCEL_PATH = os.path.join("data", "Industries and Companies 2025.xlsx")
OUTPUT_DIR = "charts/economic-indicators"

NAVY   = AQUILA_COLORS[0]   # #172344
GLASS  = AQUILA_COLORS[1]   # #C2DAF1
COPPER = AQUILA_COLORS[2]   # #AB6D3A
BRASS  = AQUILA_COLORS[3]   # #DEB76D
GREEN  = AQUILA_COLORS[4]   # #556B30
CONCRETE = AQUILA_COLORS[5] # #AAA9A8
SIGNAL = AQUILA_COLORS[6]   # #BF4040
PENNY  = AQUILA_COLORS[7]   # #D6B69C
SUN    = AQUILA_COLORS[8]   # #FFDB99
ZILKER = AQUILA_COLORS[9]   # #B2C48C

# One color per industry (10 industries, 10 colors)
INDUSTRY_COLORS = {
    "Semiconductors & Electronics":           NAVY,
    "Energy, Battery & Materials":            COPPER,
    "Corporate / Office HQ":                  BRASS,
    "Aerospace & Defense":                    GREEN,
    "Software, AI & Technology":              GLASS,
    "Logistics, Distribution & Supply Chain": CONCRETE,
    "Advanced Manufacturing":                 SIGNAL,
    "Construction & Building Products":       PENNY,
    "Healthcare & Life Sciences":             SUN,
    "Food & Beverage Manufacturing":          ZILKER,
}

MONTH_ORDER = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]
MONTH_ABBREV = {
    "January": "Jan", "February": "Feb", "March": "Mar", "April": "Apr",
    "May": "May", "June": "Jun", "July": "Jul", "August": "Aug",
    "September": "Sep", "October": "Oct", "November": "Nov", "December": "Dec",
}

# ---------------------------------------------------------------------------
# Shared layout helper
# ---------------------------------------------------------------------------
def base_layout(**kwargs):
    """Base Plotly layout with Aquila brand styling."""
    defaults = dict(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family=AQUILA_FONT, size=13, color=NAVY),
        margin=dict(t=110, b=80, l=60, r=60),
        xaxis=dict(
            gridcolor="#e9e9ea",
            linecolor="#cccccc",
            tickfont=dict(family=AQUILA_FONT, size=12, color=NAVY),
            title_font=dict(family=AQUILA_FONT, size=13, color=NAVY),
        ),
        yaxis=dict(
            gridcolor="#e9e9ea",
            linecolor="#cccccc",
            tickfont=dict(family=AQUILA_FONT, size=12, color=NAVY),
            title_font=dict(family=AQUILA_FONT, size=13, color=NAVY),
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.18,
            xanchor="center",
            x=0.5,
            font=dict(family=AQUILA_FONT, size=12, color=NAVY),
        ),
    )
    defaults.update(kwargs)
    return defaults


def chart_title(text, subtitle=None):
    full = text if not subtitle else f"{text}<br><sup style='color:#555'>{subtitle}</sup>"
    return dict(
        text=full,
        font=dict(family=AQUILA_FONT, size=18, color=NAVY),
        x=0.0,
        xanchor="left",
        pad=dict(l=0),
    )


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
print("Loading data...")
df = pd.read_excel(EXCEL_PATH, sheet_name="2025")
print(f"  Loaded {len(df)} rows from 2025 sheet. Total jobs: {df['Jobs Created'].sum():,}")

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Chart 1 — Jobs by Industry (horizontal bar)
# ---------------------------------------------------------------------------
def chart_jobs_by_industry(df):
    by_industry = (
        df.groupby("Industry")["Jobs Created"]
        .sum()
        .sort_values(ascending=True)  # ascending for horizontal bar (largest at top)
    )

    colors = [INDUSTRY_COLORS.get(ind, NAVY) for ind in by_industry.index]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=by_industry.values,
        y=by_industry.index,
        orientation="h",
        marker_color=colors,
        text=[f"{v:,}" for v in by_industry.values],
        textposition="outside",
        textfont=dict(family=AQUILA_FONT, size=12, color=NAVY),
        hovertemplate="<b>%{y}</b><br>Jobs: %{x:,}<extra></extra>",
    ))

    fig.update_layout(
        **base_layout(
            title=chart_title(
                "Jobs Created by Industry — Austin Region 2025",
                "Source: Austin Chamber of Commerce Relocations & Expansions Log · 10,621 total jobs announced"
            ),
            height=520,
            margin=dict(t=110, b=60, l=260, r=120),
            xaxis=dict(
                title="Jobs Announced",
                tickformat=",",
                gridcolor="#e9e9ea",
                linecolor="#cccccc",
                tickfont=dict(family=AQUILA_FONT, size=12, color=NAVY),
                title_font=dict(family=AQUILA_FONT, size=13, color=NAVY),
                range=[0, by_industry.max() * 1.18],
            ),
            yaxis=dict(
                gridcolor="#e9e9ea",
                linecolor="#cccccc",
                tickfont=dict(family=AQUILA_FONT, size=12, color=NAVY),
            ),
            showlegend=False,
        )
    )

    path = f"{OUTPUT_DIR}/austin_2025_jobs_by_industry.html"
    fig.write_html(path)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Chart 2 — New Relocations vs. Expansions by Industry (stacked vertical bar)
# ---------------------------------------------------------------------------
def chart_new_vs_expanded(df):
    pivot = (
        df.groupby(["Industry", "Type of Action"])["Jobs Created"]
        .sum()
        .unstack(fill_value=0)
    )
    # Sort by total descending
    pivot["_total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("_total", ascending=False).drop(columns="_total")

    fig = go.Figure()
    action_colors = {"New": NAVY, "Expanded": BRASS}

    for action in ["New", "Expanded"]:
        if action not in pivot.columns:
            continue
        fig.add_trace(go.Bar(
            name=f"{action} Operation",
            x=pivot.index,
            y=pivot[action],
            marker_color=action_colors[action],
            hovertemplate=f"<b>%{{x}}</b><br>{action}: %{{y:,}} jobs<extra></extra>",
        ))

    fig.update_layout(
        **base_layout(
            title=chart_title(
                "New Relocations vs. Expansions by Industry — Austin 2025",
                "Source: Austin Chamber of Commerce · New operations = 62% of jobs announced"
            ),
            barmode="stack",
            height=520,
            margin=dict(t=110, b=140, l=60, r=60),
            xaxis=dict(
                tickangle=-35,
                tickfont=dict(family=AQUILA_FONT, size=11, color=NAVY),
                linecolor="#cccccc",
                gridcolor="#e9e9ea",
            ),
            yaxis=dict(
                title="Jobs Announced",
                tickformat=",",
                gridcolor="#e9e9ea",
                linecolor="#cccccc",
                tickfont=dict(family=AQUILA_FONT, size=12, color=NAVY),
                title_font=dict(family=AQUILA_FONT, size=13, color=NAVY),
            ),
        )
    )

    path = f"{OUTPUT_DIR}/austin_2025_new_vs_expanded.html"
    fig.write_html(path)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Chart 3 — Jobs by Location (top 10, horizontal bar)
# ---------------------------------------------------------------------------
def chart_jobs_by_location(df):
    by_loc = (
        df.groupby("Location")["Jobs Created"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .sort_values(ascending=True)  # flip for horizontal bar (largest at top)
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=by_loc.values,
        y=by_loc.index,
        orientation="h",
        marker_color=NAVY,
        text=[f"{v:,}" for v in by_loc.values],
        textposition="outside",
        textfont=dict(family=AQUILA_FONT, size=12, color=NAVY),
        hovertemplate="<b>%{y}</b><br>Jobs: %{x:,}<extra></extra>",
    ))

    fig.update_layout(
        **base_layout(
            title=chart_title(
                "Jobs by Location — Austin Region 2025 (Top 10)",
                "Source: Austin Chamber of Commerce Relocations & Expansions Log"
            ),
            height=480,
            margin=dict(t=110, b=60, l=160, r=120),
            showlegend=False,
            xaxis=dict(
                title="Jobs Announced",
                tickformat=",",
                gridcolor="#e9e9ea",
                linecolor="#cccccc",
                tickfont=dict(family=AQUILA_FONT, size=12, color=NAVY),
                title_font=dict(family=AQUILA_FONT, size=13, color=NAVY),
                range=[0, by_loc.max() * 1.18],
            ),
            yaxis=dict(
                gridcolor="#e9e9ea",
                linecolor="#cccccc",
                tickfont=dict(family=AQUILA_FONT, size=12, color=NAVY),
            ),
        )
    )

    path = f"{OUTPUT_DIR}/austin_2025_jobs_by_location.html"
    fig.write_html(path)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Chart 4 — HQ vs. Non-HQ Jobs by Industry (grouped bar)
# ---------------------------------------------------------------------------
def chart_hq_activity(df):
    pivot = (
        df.groupby(["Industry", "HQ?"])["Jobs Created"]
        .sum()
        .unstack(fill_value=0)
    )
    # Only industries with at least some HQ activity
    pivot = pivot[pivot.get("Yes", pd.Series(0, index=pivot.index)) > 0]
    # Sort by total HQ jobs descending
    if "Yes" in pivot.columns:
        pivot = pivot.sort_values("Yes", ascending=False)

    fig = go.Figure()

    if "Yes" in pivot.columns:
        fig.add_trace(go.Bar(
            name="Headquarters",
            x=pivot.index,
            y=pivot["Yes"],
            marker_color=COPPER,
            hovertemplate="<b>%{x}</b><br>HQ Jobs: %{y:,}<extra></extra>",
        ))
    if "No" in pivot.columns:
        fig.add_trace(go.Bar(
            name="Branch / Production",
            x=pivot.index,
            y=pivot["No"],
            marker_color=NAVY,
            hovertemplate="<b>%{x}</b><br>Non-HQ Jobs: %{y:,}<extra></extra>",
        ))

    fig.update_layout(
        **base_layout(
            title=chart_title(
                "Headquarters vs. Branch/Production Jobs by Industry — Austin 2025",
                "Source: Austin Chamber of Commerce · Headquarters operations = 41 of 71 companies"
            ),
            barmode="group",
            height=520,
            margin=dict(t=110, b=160, l=60, r=60),
            xaxis=dict(
                tickangle=-35,
                tickfont=dict(family=AQUILA_FONT, size=11, color=NAVY),
                linecolor="#cccccc",
                gridcolor="#e9e9ea",
            ),
            yaxis=dict(
                title="Jobs Announced",
                tickformat=",",
                gridcolor="#e9e9ea",
                linecolor="#cccccc",
                tickfont=dict(family=AQUILA_FONT, size=12, color=NAVY),
                title_font=dict(family=AQUILA_FONT, size=13, color=NAVY),
            ),
        )
    )

    path = f"{OUTPUT_DIR}/austin_2025_hq_activity.html"
    fig.write_html(path)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Chart 5 — Monthly Jobs Trend (bar chart)
# ---------------------------------------------------------------------------
def chart_jobs_by_month(df):
    by_month = df.groupby("Month")["Jobs Created"].sum()

    # Sort chronologically
    present_months = [m for m in MONTH_ORDER if m in by_month.index]
    by_month = by_month.reindex(present_months)
    abbrev_labels = [MONTH_ABBREV[m] for m in present_months]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=abbrev_labels,
        y=by_month.values,
        marker_color=NAVY,
        text=[f"{v:,}" for v in by_month.values],
        textposition="outside",
        textfont=dict(family=AQUILA_FONT, size=11, color=NAVY),
        hovertemplate="<b>%{x}</b><br>Jobs: %{y:,}<extra></extra>",
    ))

    fig.update_layout(
        **base_layout(
            title=chart_title(
                "Monthly Jobs Announced — Austin Region 2025",
                "Source: Austin Chamber of Commerce Relocations & Expansions Log"
            ),
            height=480,
            margin=dict(t=110, b=80, l=60, r=60),
            showlegend=False,
            xaxis=dict(
                tickfont=dict(family=AQUILA_FONT, size=12, color=NAVY),
                linecolor="#cccccc",
                gridcolor="rgba(0,0,0,0)",
            ),
            yaxis=dict(
                title="Jobs Announced",
                tickformat=",",
                gridcolor="#e9e9ea",
                linecolor="#cccccc",
                tickfont=dict(family=AQUILA_FONT, size=12, color=NAVY),
                title_font=dict(family=AQUILA_FONT, size=13, color=NAVY),
                range=[0, by_month.max() * 1.18],
            ),
        )
    )

    path = f"{OUTPUT_DIR}/austin_2025_jobs_by_month.html"
    fig.write_html(path)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Chart 6 — Top 10 Companies by Jobs (horizontal bar, colored by New/Expanded)
# ---------------------------------------------------------------------------
def chart_top_companies(df):
    top10 = (
        df[["Company", "Jobs Created", "Type of Action", "Industry"]]
        .sort_values("Jobs Created", ascending=False)
        .head(10)
        .sort_values("Jobs Created", ascending=True)  # flip for horizontal bar
    )

    colors = [NAVY if t == "New" else BRASS for t in top10["Type of Action"]]

    # Build custom hover text
    hover = [
        f"<b>{row.Company}</b><br>Jobs: {row['Jobs Created']:,}<br>"
        f"Industry: {row.Industry}<br>Type: {row['Type of Action']}"
        for _, row in top10.iterrows()
    ]

    fig = go.Figure()

    # Add invisible traces just for the legend
    fig.add_trace(go.Bar(
        x=[None], y=[None], orientation="h",
        marker_color=NAVY, name="New Operation",
    ))
    fig.add_trace(go.Bar(
        x=[None], y=[None], orientation="h",
        marker_color=BRASS, name="Expanded Operation",
    ))

    # Main bars
    fig.add_trace(go.Bar(
        x=top10["Jobs Created"].values,
        y=top10["Company"].values,
        orientation="h",
        marker_color=colors,
        text=[f"{v:,}" for v in top10["Jobs Created"].values],
        textposition="outside",
        textfont=dict(family=AQUILA_FONT, size=12, color=NAVY),
        hovertext=hover,
        hoverinfo="text",
        showlegend=False,
    ))

    fig.update_layout(
        **base_layout(
            title=chart_title(
                "Top 10 Companies by Jobs Created — Austin 2025",
                "Source: Austin Chamber of Commerce · Top 10 = 70% of all announced jobs"
            ),
            height=500,
            margin=dict(t=110, b=100, l=180, r=130),
            barmode="overlay",
            xaxis=dict(
                title="Jobs Announced",
                tickformat=",",
                gridcolor="#e9e9ea",
                linecolor="#cccccc",
                tickfont=dict(family=AQUILA_FONT, size=12, color=NAVY),
                title_font=dict(family=AQUILA_FONT, size=13, color=NAVY),
                range=[0, top10["Jobs Created"].max() * 1.22],
            ),
            yaxis=dict(
                gridcolor="#e9e9ea",
                linecolor="#cccccc",
                tickfont=dict(family=AQUILA_FONT, size=12, color=NAVY),
            ),
        )
    )

    path = f"{OUTPUT_DIR}/austin_2025_top_companies.html"
    fig.write_html(path)
    print(f"  Saved: {path}")


# ---------------------------------------------------------------------------
# Run all charts
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("\nGenerating Austin 2025 charts...")
    chart_jobs_by_industry(df)
    chart_new_vs_expanded(df)
    chart_jobs_by_location(df)
    chart_hq_activity(df)
    chart_jobs_by_month(df)
    chart_top_companies(df)
    print("\nDone. 6 charts saved to", OUTPUT_DIR)
