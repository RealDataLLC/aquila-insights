#!/usr/bin/env python3
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))  # noqa: E402
"""
TI Allowance Charts -- Differences by Size, Lease Term, and Lease Type

Data Source: Skyline API (AQUILA Comp Database)

Charts Generated:
1. office_ti_by_size.html        -- Avg TI by space size (Small/Medium/Large)
2. office_ti_by_lease_term.html  -- Avg TI by lease term (Short/Medium/Long)
3. office_ti_by_lease_type.html  -- Avg TI by lease type (New/Renewal/Expansion/Sublease)

Usage:
    python -m generators.office.ti_allowance
"""

import pandas as pd
import plotly.graph_objects as go
from dotenv import load_dotenv

from aquila.brand import AQUILA_COLORS, AQUILA_FONT
from aquila.charts import write_chart_html
from aquila.connectors.skyline import fetch_all_leases

load_dotenv("aquila_graph.env")

# ---------------------------------------------------------------------------
# Brand colors
# ---------------------------------------------------------------------------
BRASS  = AQUILA_COLORS[5]   # "#DEB76D"  gold/yellow  -- Large / Long / New Lease
NAVY   = AQUILA_COLORS[0]   # "#172344"  dark navy     -- Medium / Medium / Expansion
GRAY   = AQUILA_COLORS[3]   # "#AAA9A8"  concrete gray -- Small / Short / Renewal
SIGNAL = AQUILA_COLORS[11]  # "#BF4040"  signal red    -- Sublease (chart 3 only)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_data() -> pd.DataFrame:
    """Fetch Skyline leases and return a flat DataFrame with key TI fields."""
    raw = fetch_all_leases()
    rows = []
    for r in raw:
        prop = r.get("property") or {}
        rows.append({
            "execution_date": r.get("executionDate"),
            "lease_type":     r.get("leaseType"),
            "size_sf":        r.get("sizeSf"),
            "ti_allowance":   r.get("tiAllowance"),
            "lease_term":     r.get("leaseTerm"),
            "property_type":  prop.get("propertyType"),
            "city":           prop.get("city"),
            "state":          prop.get("state"),
        })

    df = pd.DataFrame(rows)
    df["execution_date"] = pd.to_datetime(df["execution_date"], errors="coerce")
    df["year"] = df["execution_date"].dt.year

    for col in ["size_sf", "ti_allowance", "lease_term"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Office only
    df = df[df["property_type"].str.upper().str.contains("OFFICE", na=False)]

    # Keep only rows with TI data and reasonable years
    df = df[df["ti_allowance"].notna() & df["ti_allowance"].gt(0)]
    df = df[df["year"].between(2005, 2030)]
    return df


def _avg_ti_by_year(df: pd.DataFrame, group_col: str) -> pd.DataFrame:
    """Return pivot of SF-weighted average TI per year × group_col (columns = groups)."""
    df2 = df[df["size_sf"].notna() & df["size_sf"].gt(0)].copy()

    def _wavg(g):
        return (g["ti_allowance"] * g["size_sf"]).sum() / g["size_sf"].sum()

    agg = (
        df2.groupby(["year", group_col])
        .apply(_wavg, include_groups=False)
        .reset_index(name="ti_allowance")
    )
    pivot = agg.pivot(index="year", columns=group_col, values="ti_allowance")
    return pivot


def _chart_layout(title: str, ymax: float) -> dict:
    return dict(
        title=dict(
            text=f"<b>{title}</b>",
            x=0.5,
            xanchor="center",
            font=dict(family=AQUILA_FONT, size=16, color="#172344"),
        ),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family=AQUILA_FONT, color="#172344"),
        xaxis=dict(
            showgrid=False,
            tickfont=dict(family=AQUILA_FONT, size=12),
            dtick=1,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#E8E8E8",
            tickprefix="$",
            tickformat=",.2f",
            rangemode="tozero",
            range=[0, ymax * 1.15],
            tickfont=dict(family=AQUILA_FONT, size=12),
        ),
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.15,
            xanchor="left",
            x=0,
            font=dict(family=AQUILA_FONT, size=11),
        ),
        margin=dict(t=70, b=100, l=60, r=80),
        annotations=[
            dict(
                text="Source: AQUILA Comp Database",
                xref="paper", yref="paper",
                x=0, y=-0.10,
                showarrow=False,
                font=dict(family=AQUILA_FONT, size=10, color="#888888"),
                align="left",
            )
        ],
    )


def _add_end_label(fig: go.Figure, series: pd.Series, color: str):
    """Add a text annotation at the last non-null value of a series."""
    valid = series.dropna()
    if valid.empty:
        return
    last_x = valid.index[-1]
    last_y = valid.iloc[-1]
    fig.add_annotation(
        x=last_x,
        y=last_y,
        text=f"  <b>${last_y:,.2f}</b>",
        showarrow=False,
        xanchor="left",
        font=dict(family=AQUILA_FONT, size=11, color=color),
    )


def _line(x, y, name, color, dash="solid"):
    return go.Scatter(
        x=x,
        y=y,
        mode="lines",
        name=name,
        line=dict(color=color, width=2.5, dash=dash),
        connectgaps=True,
    )


# ---------------------------------------------------------------------------
# Chart 1 -- By Size of Space
# ---------------------------------------------------------------------------

def chart_ti_by_size(df: pd.DataFrame):
    df2 = df[df["size_sf"].notna()].copy()
    df2["size_bin"] = pd.cut(
        df2["size_sf"],
        bins=[0, 5_000, 20_000, float("inf")],
        labels=["Small (0 - 5,000)", "Medium (5,000 - 20,000)", "Large (20,000+)"],
    )

    pivot = _avg_ti_by_year(df2, "size_bin")

    fig = go.Figure()
    specs = [
        ("Large (20,000+)",        BRASS,  "Large (20,000+)"),
        ("Medium (5,000 - 20,000)", NAVY,   "Medium (5,000 - 20,000)"),
        ("Small (0 - 5,000)",       GRAY,   "Small (0 - 5,000)"),
    ]
    for col, color, label in specs:
        if col in pivot.columns:
            s = pivot[col]
            fig.add_trace(_line(s.index.tolist(), s.values.tolist(), label, color))
            _add_end_label(fig, s, color)

    ymax = pivot.max().max() if not pivot.empty else 50
    fig.update_layout(**_chart_layout("Differences by Size of Space", ymax))
    write_chart_html(fig, "charts/office/office_ti_by_size.html")
    print("    [OK] charts/office/office_ti_by_size.html")


# ---------------------------------------------------------------------------
# Chart 2 -- By Lease Term
# ---------------------------------------------------------------------------

def chart_ti_by_lease_term(df: pd.DataFrame):
    df2 = df[df["lease_term"].notna()].copy()
    df2["term_bin"] = pd.cut(
        df2["lease_term"],
        bins=[0, 24, 60, float("inf")],
        labels=["Short (1 - 24 Months)", "Medium (25 - 60 Months)", "Long (61+ Months)"],
    )

    pivot = _avg_ti_by_year(df2, "term_bin")

    fig = go.Figure()
    specs = [
        ("Long (61+ Months)",       BRASS, "Long (61+ Months)"),
        ("Medium (25 - 60 Months)", NAVY,  "Medium (25 - 60 Months)"),
        ("Short (1 - 24 Months)",   GRAY,  "Short (1 - 24 Months)"),
    ]
    for col, color, label in specs:
        if col in pivot.columns:
            s = pivot[col]
            fig.add_trace(_line(s.index.tolist(), s.values.tolist(), label, color))
            _add_end_label(fig, s, color)

    ymax = pivot.max().max() if not pivot.empty else 50
    fig.update_layout(**_chart_layout("Differences by Lease Term", ymax))
    write_chart_html(fig, "charts/office/office_ti_by_lease_term.html")
    print("    [OK] charts/office/office_ti_by_lease_term.html")


# ---------------------------------------------------------------------------
# Chart 3 -- By Lease Type
# ---------------------------------------------------------------------------

def chart_ti_by_lease_type(df: pd.DataFrame):
    df2 = df[df["lease_type"].notna()].copy()

    # Normalize lease_type casing
    df2["lease_type"] = df2["lease_type"].str.strip().str.title()

    pivot = _avg_ti_by_year(df2, "lease_type")

    fig = go.Figure()
    specs = [
        ("New Lease",  BRASS,  "New Lease"),
        ("Expansion",  NAVY,   "Expansion"),
        ("Renewal",    GRAY,   "Renewal"),
        ("Sublease",   SIGNAL, "Sublease"),
    ]
    # Also try alternate capitalizations from API
    _alt = {
        "New Lease": ["New"],
        "Expansion": ["Expansion"],
        "Renewal":   ["Renewal"],
        "Sublease":  ["Sublease"],
    }

    for label, color, display in specs:
        candidates = [label] + _alt.get(label, [])
        col = next((c for c in candidates if c in pivot.columns), None)
        if col is not None:
            s = pivot[col]
            fig.add_trace(_line(s.index.tolist(), s.values.tolist(), display, color))
            _add_end_label(fig, s, color)

    ymax = pivot.max().max() if not pivot.empty else 50
    fig.update_layout(**_chart_layout("Differences by Type of Lease", ymax))
    write_chart_html(fig, "charts/office/office_ti_by_lease_type.html")
    print("    [OK] charts/office/office_ti_by_lease_type.html")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print("Fetching Skyline lease data...")
    df = _load_data()
    print(f"    {len(df)} leases with TI data, years {int(df['year'].min())}-{int(df['year'].max())}")

    print("Generating TI charts...")
    chart_ti_by_size(df)
    chart_ti_by_lease_term(df)
    chart_ti_by_lease_type(df)
    print("Done.")


if __name__ == "__main__":
    main()
