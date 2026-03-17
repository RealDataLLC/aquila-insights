"""
Aquila Benefit tab -- NER analysis comparing AQUILA-brokered deals vs peers.

Provides layout builder and callback registration for the main dashboard.
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, Input, Output, State, callback_context, no_update, MATCH, ALL

# Brand constants (local stub or parent package)
try:
    from aquila.brand import AQUILA_COLORS, AQUILA_FONT
except ImportError:
    from aquila_graphing_tools import AQUILA_COLORS, AQUILA_FONT

try:
    from aquila.connectors.skyline import fetch_all_leases
except ImportError:
    # Vercel deployment: aquila package not available — inline Skyline fetch logic
    import os as _os
    import requests as _requests

    _SKYLINE_BASE_URL = "https://api.withskyline.com/external/v1"

    def fetch_all_leases(lease_type=None, start_date=None, end_date=None):
        api_key = _os.getenv("SKYLINE_API_KEY", "")
        headers = {"Authorization": f"Bearer {api_key}"}
        params = {"pageSize": 100, "sortBy": "executionDate", "sortOrder": "desc"}
        if lease_type:
            params["leaseType"] = lease_type
        if start_date:
            params["executionDate_gte"] = start_date
        if end_date:
            params["executionDate_lte"] = end_date
        all_leases, page = [], 1
        while True:
            params["page"] = page
            try:
                resp = _requests.get(
                    f"{_SKYLINE_BASE_URL}/leases", headers=headers, params=params
                )
                resp.raise_for_status()
                body = resp.json()
            except Exception as e:
                print(f"    [ERROR] Skyline API page {page}: {e}")
                break
            data = body.get("data", [])
            pagination = body.get("pagination", {})
            all_leases.extend(data)
            if not pagination.get("hasNextPage", False):
                break
            page += 1
        return all_leases



# ---------------------------------------------------------------------------
# Chart config (matches main dashboard)
# ---------------------------------------------------------------------------
_CHART_CONFIG = {
    "displayModeBar": "hover",
    "modeBarButtonsToRemove": [
        "select2d", "lasso2d", "autoScale2d",
        "toggleSpikelines", "hoverCompareCartesian",
    ],
    "displaylogo": False,
    "toImageButtonOptions": {"format": "png", "scale": 2},
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_skyline_leases():
    """Fetch Skyline leases and return a flat DataFrame."""
    raw = fetch_all_leases()
    if not raw:
        return pd.DataFrame()

    rows = []
    for r in raw:
        tenant = r.get("tenant") or {}
        tb = r.get("tenantBroker") or {}
        tbk = r.get("tenantBrokerage") or {}
        lb = r.get("landlordBroker") or {}
        lbk = r.get("landlordBrokerage") or {}
        prop = r.get("property") or {}

        rows.append({
            "lease_id": r.get("id"),
            "execution_date": r.get("executionDate"),
            "lease_type": r.get("leaseType"),
            "financial_type": r.get("financialType"),
            "size_sf": r.get("sizeSf"),
            "base_rate": r.get("baseRate"),
            "ti_allowance": r.get("tiAllowance"),
            "free_months": r.get("freeMonths"),
            "opex": r.get("opex"),
            "ner": r.get("netEffectiveBaseRate"),
            "lease_term": r.get("leaseTerm"),
            "full_service_rate": r.get("fullServiceRate"),
            "tenant_name": tenant.get("name"),
            "tenant_broker": tb.get("name"),
            "tenant_brokerage": tbk.get("name"),
            "landlord_broker": lb.get("name"),
            "landlord_brokerage": lbk.get("name"),
            "property_id": prop.get("id"),
            "building_name": prop.get("name"),
            "address": prop.get("address"),
            "city": prop.get("city"),
            "state": prop.get("state"),
            "submarket": prop.get("submarket"),
            "property_type": prop.get("propertyType"),
            "building_class": prop.get("buildingClass"),
        })

    df = pd.DataFrame(rows)
    df["property_id"] = df["property_id"].astype(str)
    df["execution_date"] = pd.to_datetime(df["execution_date"], errors="coerce")
    df["year"] = df["execution_date"].dt.year.astype("Int64")

    # Identify AQUILA deals
    df["is_aquila"] = (
        df["tenant_brokerage"]
        .fillna("")
        .str.upper()
        .str.contains("AQUILA")
    )

    # Numeric columns
    for col in ["size_sf", "base_rate", "ti_allowance", "free_months",
                "opex", "ner", "lease_term", "full_service_rate"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# ---------------------------------------------------------------------------
# NER comparison logic
# ---------------------------------------------------------------------------

def build_ner_comparison(df, lease_types=None, years=None):
    """
    Compare AQUILA deals vs peers in the same building/year.

    Returns a DataFrame with one row per AQUILA deal that has peer comps,
    including peer_avg_ner, savings, and win flag.
    """
    work = df.copy()

    if lease_types:
        work = work[work["lease_type"].isin(lease_types)]
    if years:
        work = work[work["year"].isin(years)]

    # Need valid NER
    work = work.dropna(subset=["ner", "property_id", "year"])

    results = []
    for (pid, yr), grp in work.groupby(["property_id", "year"]):
        aquila = grp[grp["is_aquila"]]
        peers = grp[~grp["is_aquila"]]
        if aquila.empty or peers.empty:
            continue

        peer_avg_ner = peers["ner"].mean()
        for _, deal in aquila.iterrows():
            savings = peer_avg_ner - deal["ner"]
            results.append({
                **deal.to_dict(),
                "peer_avg_ner": peer_avg_ner,
                "peer_count": len(peers),
                "savings": savings,
                "win": savings > 0,
            })

    return pd.DataFrame(results) if results else pd.DataFrame()


def get_peer_comps(df, property_id, year, lease_types=None):
    """Return peer (non-AQUILA) deals for a given building and year."""
    mask = (
        (df["property_id"].astype(str) == str(property_id))
        & (df["year"] == year)
        & (~df["is_aquila"])
        & (df["ner"].notna())
    )
    if lease_types:
        mask &= df["lease_type"].isin(lease_types)
    return df[mask]


def compute_kpis(comp_df):
    """Return dict of KPI values from a comparison DataFrame."""
    if comp_df.empty:
        return {"deals": 0, "win_rate": 0, "median_savings": 0, "total_sf": 0}
    return {
        "deals": len(comp_df),
        "win_rate": comp_df["win"].mean() * 100,
        "median_savings": comp_df["savings"].median(),
        "total_sf": comp_df["size_sf"].sum(),
    }


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------

def _build_avg_ner_chart(comp_df):
    """Grouped bar chart: avg NER by year -- AQUILA vs Peers."""
    if comp_df.empty:
        fig = go.Figure()
        fig.update_layout(title="Average NER by Year", font=dict(family=AQUILA_FONT))
        return fig

    yearly = comp_df.groupby("year").agg(
        aquila_ner=("ner", "mean"),
        peer_ner=("peer_avg_ner", "mean"),
    ).reset_index()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=yearly["year"].astype(str), y=yearly["aquila_ner"],
        name="AQUILA", marker_color=AQUILA_COLORS[0],
    ))
    fig.add_trace(go.Bar(
        x=yearly["year"].astype(str), y=yearly["peer_ner"],
        name="Market Peers", marker_color=AQUILA_COLORS[3],
    ))
    fig.update_layout(
        barmode="group",
        title=dict(text="Average NER by Year", x=0.5, xanchor="center"),
        yaxis=dict(title="NER ($/SF)", tickprefix="$", tickformat=",.2f"),
        xaxis=dict(title="Year"),
        font=dict(family=AQUILA_FONT, color="#172344"),
        plot_bgcolor="white",
        legend=dict(orientation="h", yanchor="top", y=-0.25,
                    xanchor="center", x=0.5),
        margin=dict(t=60, b=100),
    )
    fig.update_yaxes(gridcolor="#E8E8E8")
    return fig


def _build_savings_chart(comp_df):
    """Horizontal bar chart: NER savings per AQUILA deal."""
    if comp_df.empty:
        fig = go.Figure()
        fig.update_layout(title="NER Savings Per Deal", font=dict(family=AQUILA_FONT))
        return fig

    plot_df = comp_df.sort_values("savings", ascending=True).copy()
    plot_df["label"] = (
        plot_df["building_name"].fillna("Unknown")
        + " (" + plot_df["year"].astype(str) + ")"
    )
    colors = [AQUILA_COLORS[6] if s > 0 else AQUILA_COLORS[11] for s in plot_df["savings"]]

    fig = go.Figure(go.Bar(
        y=plot_df["label"],
        x=plot_df["savings"],
        orientation="h",
        marker_color=colors,
        customdata=plot_df[["property_id", "year", "lease_id"]].values,
        hovertemplate="%{y}<br>Savings: $%{x:,.2f}/SF<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="NER Savings Per Deal", x=0.5, xanchor="center"),
        xaxis=dict(title="Savings ($/SF)", tickprefix="$", tickformat=",.2f"),
        yaxis=dict(title=""),
        font=dict(family=AQUILA_FONT, color="#172344"),
        plot_bgcolor="white",
        height=max(400, len(plot_df) * 30 + 120),
        margin=dict(t=60, b=60, l=200),
    )
    fig.update_xaxes(gridcolor="#E8E8E8")
    return fig


# ---------------------------------------------------------------------------
# Detail panel builders
# ---------------------------------------------------------------------------

def _build_deal_card(deal, title="AQUILA Deal", color=AQUILA_COLORS[0]):
    """Build a card for a single deal."""
    def _fmt(val, prefix="", suffix="", fmt=",.2f"):
        if pd.isna(val) or val is None:
            return "N/A"
        return f"{prefix}{val:{fmt}}{suffix}"

    return dbc.Card([
        dbc.CardHeader(title, style={"backgroundColor": color, "color": "white",
                                     "fontWeight": "bold", "fontFamily": AQUILA_FONT}),
        dbc.CardBody([
            html.P([html.Strong("Tenant: "), deal.get("tenant_name", "N/A")]),
            html.P([html.Strong("NER: "), _fmt(deal.get("ner"), "$", "/SF")]),
            html.P([html.Strong("Base Rate: "), _fmt(deal.get("base_rate"), "$", "/SF")]),
            html.P([html.Strong("TI Allowance: "), _fmt(deal.get("ti_allowance"), "$", "/SF")]),
            html.P([html.Strong("Free Months: "), _fmt(deal.get("free_months"), fmt=".0f")]),
            html.P([html.Strong("Size: "), _fmt(deal.get("size_sf"), suffix=" SF", fmt=",.0f")]),
            html.P([html.Strong("Term: "), _fmt(deal.get("lease_term"), suffix=" mo", fmt=".0f")]),
            html.P([html.Strong("Type: "), deal.get("lease_type", "N/A")]),
            html.P([html.Strong("Broker: "), deal.get("tenant_broker", "N/A")]),
        ], style={"fontFamily": AQUILA_FONT, "fontSize": "13px"}),
    ], className="mb-2")


def _build_detail_panel(aquila_deal, peer_comps):
    """Build the expandable detail panel for a clicked deal."""
    header_text = (
        f"{aquila_deal.get('building_name', 'Unknown')} "
        f"({aquila_deal.get('year', '')})"
    )
    address = aquila_deal.get("address", "")
    submarket = aquila_deal.get("submarket", "")

    peer_cards = []
    for _, p in peer_comps.iterrows():
        peer_cards.append(dbc.Col(
            _build_deal_card(p.to_dict(), title="Peer Comp", color=AQUILA_COLORS[3]),
            md=4, sm=6, xs=12,
        ))

    return dbc.Card([
        dbc.CardHeader([
            html.H5(header_text, className="mb-1"),
            html.Small(f"{address} | {submarket}", className="text-muted"),
        ], style={"fontFamily": AQUILA_FONT}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col(
                    _build_deal_card(aquila_deal, title="AQUILA Deal",
                                     color=AQUILA_COLORS[0]),
                    md=4, sm=6, xs=12,
                ),
                dbc.Col([
                    html.H6("Peer Comps", style={"fontFamily": AQUILA_FONT}),
                    dbc.Row(peer_cards) if peer_cards else html.P("No peer comps."),
                ], md=8),
            ]),
        ]),
    ], className="mt-3", style={"border": f"2px solid {AQUILA_COLORS[0]}"})


# ---------------------------------------------------------------------------
# Broker list builder (static, full dataset)
# ---------------------------------------------------------------------------

def _build_broker_list_content(df_leases):
    """Build horizontal bar broker list from full dataset (all years, all types)."""
    if df_leases.empty:
        return html.P("No data available.", style={"padding": "20px"})

    aquila_deals = df_leases[df_leases["is_aquila"]]
    broker_counts = (
        aquila_deals
        .groupby("tenant_broker", dropna=False)
        .size()
        .reset_index(name="deals")
    )
    broker_counts = broker_counts.dropna(subset=["tenant_broker"])
    broker_counts = broker_counts[broker_counts["tenant_broker"].str.strip() != ""]
    broker_counts = broker_counts.sort_values("deals", ascending=False)

    num_brokers = len(broker_counts)
    max_deals = broker_counts["deals"].max() if not broker_counts.empty else 1

    items = []
    for _, row in broker_counts.iterrows():
        bar_pct = (row["deals"] / max_deals) * 100
        items.append(html.Div([
            html.Div(
                row["tenant_broker"],
                style={
                    "fontWeight": "bold", "color": AQUILA_COLORS[0],
                    "width": "200px", "flexShrink": "0",
                    "fontFamily": AQUILA_FONT, "fontSize": "14px",
                },
            ),
            html.Div(
                style={
                    "width": f"{bar_pct}%", "height": "10px",
                    "backgroundColor": AQUILA_COLORS[0],
                    "borderRadius": "5px", "flexGrow": "1",
                    "maxWidth": "400px", "minWidth": "4px",
                },
            ),
            html.Span(
                f"{row['deals']} deals",
                style={
                    "marginLeft": "12px", "color": "#666",
                    "whiteSpace": "nowrap", "fontFamily": AQUILA_FONT,
                    "fontSize": "13px",
                },
            ),
        ], style={
            "display": "flex", "alignItems": "center",
            "padding": "10px 20px",
            "borderBottom": f"1px solid {AQUILA_COLORS[7]}",
        }))

    return html.Div([
        html.Div([
            html.H5("AQUILA Tenant Rep Brokers", style={
                "color": "white", "marginBottom": "4px",
                "fontFamily": AQUILA_FONT, "fontWeight": "bold",
            }),
            html.P(
                f"{num_brokers} confirmed brokers "
                f"- deal counts across full dataset (all years, all deal types)",
                style={
                    "color": AQUILA_COLORS[5], "fontSize": "13px",
                    "marginBottom": "0", "fontFamily": AQUILA_FONT,
                },
            ),
        ], style={
            "backgroundColor": AQUILA_COLORS[0],
            "padding": "16px 20px",
            "borderRadius": "8px 8px 0 0",
        }),
        html.Div(items, style={
            "border": f"1px solid {AQUILA_COLORS[7]}",
            "borderTop": "none",
            "borderRadius": "0 0 8px 8px",
            "maxHeight": "600px", "overflowY": "auto",
            "backgroundColor": "white",
        }),
    ], style={"maxWidth": "700px"})


# ---------------------------------------------------------------------------
# Building list for Deal Browser
# ---------------------------------------------------------------------------

def _build_building_list(comp_df):
    """Build scrollable building list from comparison results."""
    if comp_df.empty:
        return html.Div(
            html.P("No buildings match current filters.",
                   style={"color": "#999", "padding": "20px", "textAlign": "center"}),
        )

    # Group by building + year
    grouped = comp_df.groupby(
        ["property_id", "building_name", "year"], dropna=False
    ).agg(
        deal_count=("lease_id", "count"),
        avg_savings=("savings", "mean"),
        any_win=("win", "any"),
    ).reset_index()
    grouped = grouped.sort_values(["year", "building_name"], ascending=[True, True])

    items = []
    for _, row in grouped.iterrows():
        savings = row["avg_savings"]
        is_win = savings > 0
        indicator_color = AQUILA_COLORS[6] if is_win else AQUILA_COLORS[11]
        indicator_symbol = "V" if is_win else "X"
        savings_text = f"${abs(savings):,.2f}/SF"
        if not is_win:
            savings_text = f"-{savings_text}"

        pid = row["property_id"] or ""
        yr = int(row["year"]) if pd.notna(row["year"]) else 0
        card_key = f"{pid}|{yr}"
        deal_word = "deal" if row["deal_count"] == 1 else "deals"

        items.append(html.Div(
            [
                html.Div([
                    html.Div(
                        row["building_name"] or "Unknown",
                        style={
                            "fontWeight": "bold", "color": AQUILA_COLORS[0],
                            "fontSize": "14px", "fontFamily": AQUILA_FONT,
                        },
                    ),
                    html.Div(
                        f"{yr} - {row['deal_count']} {deal_word}",
                        style={
                            "fontSize": "12px", "color": "#888",
                            "fontFamily": AQUILA_FONT,
                        },
                    ),
                ], style={"flex": "1"}),
                html.Div([
                    html.Span(
                        indicator_symbol,
                        style={
                            "fontWeight": "bold", "color": indicator_color,
                            "marginRight": "4px",
                        },
                    ),
                    html.Span(
                        savings_text,
                        style={
                            "fontWeight": "bold", "color": indicator_color,
                            "fontFamily": AQUILA_FONT, "fontSize": "13px",
                        },
                    ),
                ], style={"textAlign": "right", "whiteSpace": "nowrap"}),
            ],
            id={"type": "benefit-building-card", "index": card_key},
            n_clicks=0,
            style={
                "display": "flex", "alignItems": "center",
                "padding": "12px 16px", "cursor": "pointer",
                "borderBottom": f"1px solid {AQUILA_COLORS[7]}",
            },
        ))

    count = len(grouped)
    return html.Div([
        html.Div(
            f"BUILDINGS ({count})",
            style={
                "backgroundColor": AQUILA_COLORS[0], "color": "white",
                "padding": "10px 16px", "fontWeight": "bold",
                "fontFamily": AQUILA_FONT, "fontSize": "13px",
                "borderRadius": "8px 8px 0 0",
                "letterSpacing": "0.5px",
            },
        ),
        html.Div(items, style={
            "maxHeight": "550px", "overflowY": "auto",
            "border": f"1px solid {AQUILA_COLORS[7]}",
            "borderTop": "none",
            "borderRadius": "0 0 8px 8px",
            "backgroundColor": "white",
        }),
    ])


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

def build_benefit_layout(df_leases):
    """Build the complete Aquila Benefit tab layout."""
    lease_types = sorted(df_leases["lease_type"].dropna().unique().tolist()) if not df_leases.empty else []
    years = sorted(df_leases["year"].dropna().unique().tolist()) if not df_leases.empty else []
    year_range = f"{min(years)}-{max(years)}" if years else "N/A"

    # Year filter pill buttons
    year_buttons = [dbc.Button(
        "All", id={"type": "benefit-year-btn", "index": "all"},
        color="primary", size="sm", className="me-1 mb-1", outline=False,
    )]
    for yr in years:
        year_buttons.append(dbc.Button(
            str(yr), id={"type": "benefit-year-btn", "index": str(yr)},
            color="primary", size="sm", className="me-1 mb-1", outline=True,
        ))

    # Broker list (static, computed once from full data)
    broker_content = _build_broker_list_content(df_leases)

    # ---- Header bar (navy, shared across all sub-tabs) ----
    header_bar = html.Div([
        # Left: title info
        html.Div([
            html.Div(
                "AQUILA COMMERCIAL - BENEFIT ANALYSIS",
                style={
                    "color": AQUILA_COLORS[5], "fontSize": "12px",
                    "fontWeight": "bold", "letterSpacing": "2px",
                    "fontFamily": AQUILA_FONT, "marginBottom": "4px",
                },
            ),
            html.H4(
                "Tenant Rep NER Analysis",
                style={
                    "color": "white", "fontFamily": AQUILA_FONT,
                    "fontWeight": "bold", "marginBottom": "6px",
                },
            ),
            html.P(
                f"New deals only - Same building - Same year - {year_range} - Duplicates removed",
                style={
                    "color": AQUILA_COLORS[1], "fontSize": "13px",
                    "fontFamily": AQUILA_FONT, "marginBottom": "8px",
                },
            ),
            html.Div(
                "Lower NER = tenant pays less = better deal",
                style={
                    "display": "inline-block",
                    "backgroundColor": "rgba(255,255,255,0.15)",
                    "color": AQUILA_COLORS[5], "fontSize": "12px",
                    "padding": "4px 12px", "borderRadius": "12px",
                    "fontFamily": AQUILA_FONT,
                },
            ),
        ], style={"flex": "1"}),
        # Right: KPI cards
        html.Div(id="benefit-kpi-row", style={
            "display": "flex", "gap": "24px", "alignItems": "center",
        }),
    ], style={
        "display": "flex", "alignItems": "center",
        "backgroundColor": AQUILA_COLORS[0],
        "padding": "20px 24px",
        "borderRadius": "8px 8px 0 0",
    })

    # ---- Filter row: year pills ----
    filter_row = html.Div([
        html.Div([
            html.Span("Year:", style={
                "fontWeight": "bold", "fontFamily": AQUILA_FONT,
                "marginRight": "8px", "fontSize": "13px",
            }),
            html.Div(year_buttons, className="d-flex flex-wrap"),
        ], style={"flex": "1", "display": "flex", "alignItems": "center"}),
    ], style={
        "padding": "12px 24px",
        "borderBottom": f"1px solid {AQUILA_COLORS[7]}",
        "backgroundColor": "#FAFAFA",
    })

    # ---- Charts sub-tab ----
    charts_tab = dbc.Tab(label="Charts", tab_id="benefit-charts", children=[
        dbc.Container([
            dbc.Row([
                dbc.Col(dcc.Graph(id="benefit-ner-chart", config=_CHART_CONFIG), md=6),
                dbc.Col(dcc.Graph(id="benefit-savings-chart", config=_CHART_CONFIG), md=6),
            ], className="mt-3"),
            html.Div(id="benefit-detail-panel"),
        ], fluid=True),
    ])

    # ---- Deal Browser sub-tab ----
    deal_browser_tab = dbc.Tab(label="Deal Browser", tab_id="benefit-deals", children=[
        dbc.Container([
            dbc.Row([
                dbc.Col(
                    html.Div(id="benefit-building-list"),
                    md=4, style={"paddingRight": "0"},
                ),
                dbc.Col(
                    html.Div(id="benefit-building-detail", children=[
                        html.Div([
                            html.Div(
                                "<-",
                                style={
                                    "fontSize": "32px", "color": "#CCC",
                                    "marginBottom": "8px",
                                },
                            ),
                            html.P(
                                "Select a building to view deal terms",
                                style={
                                    "color": "#999", "fontFamily": AQUILA_FONT,
                                    "fontSize": "14px",
                                },
                            ),
                        ], style={
                            "textAlign": "center", "paddingTop": "120px",
                        }),
                    ]),
                    md=8, style={
                        "borderLeft": f"1px solid {AQUILA_COLORS[7]}",
                        "minHeight": "400px",
                    },
                ),
            ], className="mt-3"),
        ], fluid=True),
    ])

    # ---- Broker List sub-tab ----
    broker_tab = dbc.Tab(label="Broker List", tab_id="benefit-brokers", children=[
        dbc.Container([
            html.Div(broker_content, className="mt-3"),
        ], fluid=True),
    ])

    return html.Div([
        header_bar,
        filter_row,
        dbc.Tabs(
            [charts_tab, deal_browser_tab, broker_tab],
            id="benefit-sub-tabs", active_tab="benefit-charts",
        ),

        # Hidden stores
        dcc.Store(id="benefit-selected-year", data="all"),
    ])


# ---------------------------------------------------------------------------
# Callback registration
# ---------------------------------------------------------------------------

def register_callbacks(app, df_leases):
    """Register all Aquila Benefit callbacks on the Dash app."""

    # ---- Year pill click -> update store ----
    @app.callback(
        Output("benefit-selected-year", "data"),
        Input({"type": "benefit-year-btn", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def _on_year_click(n_clicks_list):
        if not n_clicks_list or all(
            n is None or n == 0 for n in n_clicks_list
        ):
            return no_update

        ctx = callback_context
        if not ctx.triggered:
            return no_update

        prop_id_str = ctx.triggered[0]["prop_id"]
        import json as _json
        try:
            btn_id = _json.loads(prop_id_str.rsplit(".", 1)[0])
            return btn_id["index"]
        except (ValueError, KeyError, TypeError):
            return no_update

    # ---- Year pill styling ----
    @app.callback(
        Output({"type": "benefit-year-btn", "index": MATCH}, "outline"),
        Input("benefit-selected-year", "data"),
        State({"type": "benefit-year-btn", "index": MATCH}, "id"),
    )
    def _style_year_btn(selected_year, btn_id):
        return btn_id["index"] != (selected_year or "all")

    # Default placeholder for building detail panel
    _default_building_detail = html.Div([
        html.Div(
            "\u2190",
            style={"fontSize": "32px", "color": "#CCC", "marginBottom": "8px"},
        ),
        html.P(
            "Select a building to view deal terms",
            style={"color": "#999", "fontFamily": AQUILA_FONT, "fontSize": "14px"},
        ),
    ], style={"textAlign": "center", "paddingTop": "120px"})

    # ---- Main update: KPIs + charts + building list ----
    @app.callback(
        [
            Output("benefit-kpi-row", "children"),
            Output("benefit-ner-chart", "figure"),
            Output("benefit-savings-chart", "figure"),
            Output("benefit-building-list", "children"),
            Output("benefit-building-detail", "children", allow_duplicate=True),
            Output("benefit-detail-panel", "children", allow_duplicate=True),
        ],
        [
            Input("benefit-selected-year", "data"),
        ],
    )
    def _update_benefit(selected_year):
        try:
            years = None
            if selected_year and selected_year != "all":
                try:
                    years = [int(selected_year)]
                except (ValueError, TypeError):
                    years = None

            # Always filter to New deals for comparison
            lease_types = ["New"]

            comp_df = build_ner_comparison(df_leases, lease_types=lease_types, years=years)
            kpis = compute_kpis(comp_df)

            # KPI cards (styled for navy header)
            deals_str = f"{kpis['deals']:,}"
            win_str = f"{kpis['win_rate']:.0f}%" if pd.notna(kpis['win_rate']) else "0%"
            sav_val = kpis['median_savings']
            sav_str = f"+${sav_val:,.2f}" if pd.notna(sav_val) else "+$0.00"
            sf_val = kpis['total_sf']
            sf_str = f"{sf_val:,.0f}" if pd.notna(sf_val) else "0"

            kpi_items = [
                (deals_str, "DEALS"),
                (win_str, "WIN RATE"),
                (sav_str, "MEDIAN SAVINGS"),
                (sf_str, "TOTAL SF"),
            ]
            kpi_cards = []
            for value, label in kpi_items:
                kpi_cards.append(html.Div([
                    html.Div(value, style={
                        "fontSize": "22px", "fontWeight": "bold",
                        "color": AQUILA_COLORS[5], "fontFamily": AQUILA_FONT,
                        "lineHeight": "1.1",
                    }),
                    html.Div(label, style={
                        "fontSize": "10px", "color": AQUILA_COLORS[1],
                        "fontFamily": AQUILA_FONT, "letterSpacing": "1px",
                    }),
                ], style={"textAlign": "center"}))

            # Charts
            ner_fig = _build_avg_ner_chart(comp_df)
            savings_fig = _build_savings_chart(comp_df)

            # Building list for Deal Browser
            building_list = _build_building_list(comp_df)

            return (kpi_cards, ner_fig, savings_fig, building_list,
                    _default_building_detail, [])
        except Exception as exc:
            import traceback
            traceback.print_exc()
            empty_fig = go.Figure()
            empty_fig.update_layout(font=dict(family=AQUILA_FONT))
            return (
                [html.Div(f"Error: {exc}", style={"color": "red"})],
                empty_fig,
                empty_fig,
                html.P(f"Error loading data: {exc}", style={"color": "red"}),
                _default_building_detail,
                [],
            )

    # ---- Savings chart click -> detail panel ----
    @app.callback(
        Output("benefit-detail-panel", "children"),
        Input("benefit-savings-chart", "clickData"),
        prevent_initial_call=True,
    )
    def _on_savings_click(click_data):
        try:
            if not click_data or not click_data.get("points"):
                return no_update

            point = click_data["points"][0]
            custom = point.get("customdata")
            if custom is None or len(custom) < 3:
                return no_update

            prop_id, year, lease_id = custom[0], custom[1], custom[2]

            mask = df_leases["lease_id"] == lease_id
            if not mask.any():
                return html.P("Deal not found.")

            deal = df_leases[mask].iloc[0].to_dict()
            peers = get_peer_comps(df_leases, prop_id, year, lease_types=["New"])
            return _build_detail_panel(deal, peers)
        except Exception:
            return no_update

    # ---- Building card click -> detail panel in Deal Browser ----
    @app.callback(
        Output("benefit-building-detail", "children"),
        Input({"type": "benefit-building-card", "index": ALL}, "n_clicks"),
        State("benefit-selected-year", "data"),
        prevent_initial_call=True,
    )
    def _on_building_click(n_clicks_list, selected_year):
        try:
            # Guard: no clicks yet (initial render / year change re-render)
            if not n_clicks_list or all(
                n is None or n == 0 for n in n_clicks_list
            ):
                return no_update

            # Use callback_context for broader Dash version compatibility
            ctx = callback_context
            if not ctx.triggered:
                return no_update

            # Guard: triggered value must be > 0 (not a re-render with n_clicks=0)
            triggered_value = ctx.triggered[0].get("value", 0)
            if not triggered_value or triggered_value == 0:
                return no_update

            # Find which button was clicked
            prop_id_str = ctx.triggered[0]["prop_id"]  # e.g. '{"index":"pid|2023","type":"benefit-building-card"}.n_clicks'
            import json as _json
            try:
                btn_id = _json.loads(prop_id_str.rsplit(".", 1)[0])
                card_key = btn_id["index"]
            except (ValueError, KeyError, TypeError):
                return no_update

            parts = card_key.split("|", 1)
            if len(parts) != 2:
                return no_update

            prop_id, yr_str = parts
            try:
                yr = int(yr_str)
            except (ValueError, TypeError):
                return no_update

            # Get AQUILA deals for this building+year
            years_filter = None
            if selected_year and selected_year != "all":
                try:
                    years_filter = [int(selected_year)]
                except (ValueError, TypeError):
                    pass

            comp_df = build_ner_comparison(
                df_leases, lease_types=["New"], years=years_filter
            )
            if comp_df.empty:
                return html.P("No comparison data.", style={"padding": "20px"})

            building_deals = comp_df[
                (comp_df["property_id"] == prop_id) & (comp_df["year"] == yr)
            ]
            if building_deals.empty:
                return html.P("No deals found for this building.",
                              style={"padding": "20px"})

            # Build detail cards for each AQUILA deal + peers
            panels = []
            for _, deal_row in building_deals.iterrows():
                deal = deal_row.to_dict()
                peers = get_peer_comps(df_leases, prop_id, yr, lease_types=["New"])
                panels.append(_build_detail_panel(deal, peers))

            return html.Div(panels)
        except Exception:
            return no_update
