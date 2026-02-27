import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402
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
COPPER = AQUILA_COLORS[4]   # #AB6D3A
BRASS  = AQUILA_COLORS[5]   # #DEB76D
GREEN  = AQUILA_COLORS[6]   # #556B30
CONCRETE = AQUILA_COLORS[3] # #AAA9A8
SIGNAL = AQUILA_COLORS[11]  # #BF4040
PENNY  = AQUILA_COLORS[8]   # #D6B69C
SUN    = AQUILA_COLORS[9]   # #FFD899
ZILKER = AQUILA_COLORS[10]  # #B2C48C

# One color per industry (10 industries), assigned in hierarchy order
INDUSTRY_COLORS = {
    "Semiconductors & Electronics":           AQUILA_COLORS[0],   # Navy
    "Energy, Battery & Materials":            AQUILA_COLORS[1],   # Glass Blue
    "Corporate / Office HQ":                  AQUILA_COLORS[2],   # Glass Blue Alt
    "Aerospace & Defense":                    AQUILA_COLORS[3],   # Concrete
    "Software, AI & Technology":              AQUILA_COLORS[4],   # Copper
    "Logistics, Distribution & Supply Chain": AQUILA_COLORS[5],   # Brass
    "Advanced Manufacturing":                 AQUILA_COLORS[6],   # Greenspace
    "Construction & Building Products":       AQUILA_COLORS[7],   # Mopac Gray
    "Healthcare & Life Sciences":             AQUILA_COLORS[8],   # Pennybacker
    "Food & Beverage Manufacturing":          AQUILA_COLORS[9],   # Texas Sun
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
        margin=dict(t=130, b=80, l=60, r=60),
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
    full = text if not subtitle else f"{text}<br><br><sup style='color:#555'>{subtitle}</sup>"
    return dict(
        text=full,
        font=dict(family=AQUILA_FONT, size=18, color=NAVY),
        x=0.5,
        xanchor="center",
    )


# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def main():
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
            .sort_values(ascending=True)  # ascending so largest appears at top
        )

        colors = [INDUSTRY_COLORS.get(ind, NAVY) for ind in by_industry.index]
        total = by_industry.sum()

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
                    f"Source: Austin Chamber of Commerce Relocations & Expansions Log · {total:,} total jobs announced"
                ),
                height=520,
                margin=dict(t=130, b=60, l=260, r=120),
                showlegend=False,
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
            )
        )

        path = f"{OUTPUT_DIR}/austin_2025_jobs_by_industry.html"
        fig.write_html(path)
        print(f"  Saved: {path}")


    # ---------------------------------------------------------------------------
    # Chart 2 — New Relocations vs. Expansions (pie chart, total jobs by action type)
    # ---------------------------------------------------------------------------
    def chart_new_vs_expanded(df):
        by_action = df.groupby("Type of Action")["Jobs Created"].sum()
        new_jobs = by_action.get("New", 0)
        expanded_jobs = by_action.get("Expanded", 0)
        total = new_jobs + expanded_jobs
        new_pct = new_jobs / total * 100 if total > 0 else 0

        fig = go.Figure()
        fig.add_trace(go.Pie(
            labels=["New Operations", "Expansions"],
            values=[new_jobs, expanded_jobs],
            marker=dict(
                colors=[NAVY, GLASS],
                line=dict(color="white", width=2),
            ),
            texttemplate="<b>%{label}</b><br>%{value:,} jobs<br>%{percent}",
            textposition="outside",
            textfont=dict(family=AQUILA_FONT, size=12, color=NAVY),
            hovertemplate="<b>%{label}</b><br>Jobs: %{value:,}<br>Share: %{percent}<extra></extra>",
            hole=0,
            sort=False,
        ))

        fig.update_layout(
            title=chart_title(
                "New Relocations vs. Expansions — Austin 2025",
                f"Source: Austin Chamber of Commerce · {new_pct:.0f}% of jobs from new operations"
            ),
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family=AQUILA_FONT, size=12, color=NAVY),
            height=520,
            margin=dict(t=130, b=60, l=60, r=60),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.08,
                xanchor="center",
                x=0.5,
                font=dict(family=AQUILA_FONT, size=12, color=NAVY),
            ),
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

        # Colors reversed so top bar (largest) gets hierarchy [0] Navy, descending
        n = len(by_loc)
        bar_colors = [AQUILA_COLORS[(n - 1 - i) % len(AQUILA_COLORS)] for i in range(n)]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=by_loc.values,
            y=by_loc.index,
            orientation="h",
            marker_color=bar_colors,
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
                margin=dict(t=130, b=60, l=160, r=120),
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
    # Chart 4 — HQ vs. Branch/Production Jobs (pie chart, total jobs only)
    # ---------------------------------------------------------------------------
    def chart_hq_activity(df):
        by_hq = df.groupby("HQ?")["Jobs Created"].sum()
        hq_jobs = by_hq.get("Yes", 0)
        branch_jobs = by_hq.get("No", 0)
        hq_companies = (df["HQ?"] == "Yes").sum()
        total_companies = len(df)

        fig = go.Figure()
        fig.add_trace(go.Pie(
            labels=["Headquarters", "Branch / Production"],
            values=[hq_jobs, branch_jobs],
            marker=dict(
                colors=[NAVY, GLASS],
                line=dict(color="white", width=2),
            ),
            texttemplate="<b>%{label}</b><br>%{value:,} jobs<br>%{percent}",
            textposition="outside",
            textfont=dict(family=AQUILA_FONT, size=12, color=NAVY),
            hovertemplate="<b>%{label}</b><br>Jobs: %{value:,}<br>Share: %{percent}<extra></extra>",
            hole=0,
            sort=False,
        ))

        fig.update_layout(
            title=chart_title(
                "Headquarters vs. Branch/Production — Austin 2025",
                f"Source: Austin Chamber of Commerce · {hq_companies} of {total_companies} companies designated as headquarters operations"
            ),
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family=AQUILA_FONT, size=12, color=NAVY),
            height=520,
            margin=dict(t=130, b=60, l=60, r=60),
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.08,
                xanchor="center",
                x=0.5,
                font=dict(family=AQUILA_FONT, size=12, color=NAVY),
            ),
        )

        path = f"{OUTPUT_DIR}/austin_2025_hq_activity.html"
        fig.write_html(path)
        print(f"  Saved: {path}")


    # ---------------------------------------------------------------------------
    # Chart 5 — Monthly Jobs Trend (line chart)
    # ---------------------------------------------------------------------------
    def chart_jobs_by_month(df):
        by_month = df.groupby("Month")["Jobs Created"].sum()

        # Sort chronologically
        present_months = [m for m in MONTH_ORDER if m in by_month.index]
        by_month = by_month.reindex(present_months)
        abbrev_labels = [MONTH_ABBREV[m] for m in present_months]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=abbrev_labels,
            y=by_month.values,
            mode="lines+markers+text",
            line=dict(color=NAVY, width=2.5),
            marker=dict(color=NAVY, size=8),
            text=[f"{v:,}" for v in by_month.values],
            textposition="top center",
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
                margin=dict(t=130, b=80, l=80, r=60),
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
                    range=[0, by_month.max() * 1.22],
                ),
            )
        )

        path = f"{OUTPUT_DIR}/austin_2025_jobs_by_month.html"
        fig.write_html(path)
        print(f"  Saved: {path}")


    # ---------------------------------------------------------------------------
    # Chart 6 — Top 10 Companies by Jobs (Plotly table)
    # ---------------------------------------------------------------------------
    def chart_top_companies(df):
        top10 = (
            df[["Company", "Jobs Created", "Type of Action", "Industry", "Location"]]
            .sort_values("Jobs Created", ascending=False)
            .head(10)
            .reset_index(drop=True)
        )
        top10.index += 1  # 1-based rank

        # Alternate row shading: light gray / white
        fill_colors = []
        for i in range(len(top10)):
            fill_colors.append("#F5F7FA" if i % 2 == 0 else "white")

        # Format jobs with commas
        jobs_formatted = [f"{v:,}" for v in top10["Jobs Created"]]

        fig = go.Figure(data=[go.Table(
            columnwidth=[40, 200, 100, 220, 140],
            header=dict(
                values=["#", "Company", "Jobs Created", "Industry", "Location"],
                fill_color=NAVY,
                font=dict(family=AQUILA_FONT, size=13, color="white"),
                align=["center", "left", "center", "left", "left"],
                height=36,
                line_color=NAVY,
            ),
            cells=dict(
                values=[
                    list(top10.index),
                    top10["Company"].tolist(),
                    jobs_formatted,
                    top10["Industry"].tolist(),
                    top10["Location"].tolist(),
                ],
                fill_color=[fill_colors] * 5,
                font=dict(family=AQUILA_FONT, size=12, color=NAVY),
                align=["center", "left", "center", "left", "left"],
                height=32,
                line_color="#e9e9ea",
            ),
        )])

        fig.update_layout(
            title=chart_title(
                "Top 10 Companies by Jobs Created — Austin 2025",
                "Source: Austin Chamber of Commerce · Top 10 companies account for 70% of all announced jobs"
            ),
            plot_bgcolor="white",
            paper_bgcolor="white",
            font=dict(family=AQUILA_FONT, size=12, color=NAVY),
            height=480,
            margin=dict(t=130, b=40, l=40, r=40),
        )

        path = f"{OUTPUT_DIR}/austin_2025_top_companies.html"
        # Inject CSS to vertically center text in Plotly SVG table cells
        html = fig.to_html(full_html=True, include_plotlyjs=True)
        css_fix = "<style>g.table g.cells text { dominant-baseline: central !important; }</style>"
        html = html.replace('</head>', css_fix + '\n</head>', 1)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"  Saved: {path}")


    # ---------------------------------------------------------------------------
    # Run all charts
    # ---------------------------------------------------------------------------
    print("\nGenerating Austin 2025 charts...")
    chart_jobs_by_industry(df)
    chart_new_vs_expanded(df)
    chart_jobs_by_location(df)
    chart_hq_activity(df)
    chart_jobs_by_month(df)
    chart_top_companies(df)
    print("\nDone. 6 charts saved to", OUTPUT_DIR)



if __name__ == '__main__':
    main()
