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
        (df["property_id"] == property_id)
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


def compute_broker_leaderboard(comp_df):
    """Aggregate comparison results by AQUILA tenant broker."""
    if comp_df.empty:
        return pd.DataFrame()

    grouped = comp_df.groupby("tenant_broker", dropna=False).agg(
        deals=("lease_id", "count"),
        wins=("win", "sum"),
        total_sf=("size_sf", "sum"),
        median_savings=("savings", "median"),
        avg_savings=("savings", "mean"),
    ).reset_index()
    grouped["win_rate"] = (grouped["wins"] / grouped["deals"] * 100).round(1)
    grouped = grouped.sort_values("deals", ascending=False)
    grouped.columns = ["Broker", "Deals", "Wins", "Total SF",
                       "Median Savings", "Avg Savings", "Win Rate"]
    return grouped


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
# Layout
# ---------------------------------------------------------------------------

def build_benefit_layout(df_leases):
    """Build the complete Aquila Benefit tab layout."""
    lease_types = sorted(df_leases["lease_type"].dropna().unique().tolist()) if not df_leases.empty else []
    years = sorted(df_leases["year"].dropna().unique().tolist()) if not df_leases.empty else []

    # Year filter pills
    year_buttons = [dbc.Button(
        "All", id={"type": "benefit-year-btn", "index": "all"},
        color="primary", size="sm", className="me-1 mb-1", outline=False,
    )]
    for yr in years:
        year_buttons.append(dbc.Button(
            str(yr), id={"type": "benefit-year-btn", "index": str(yr)},
            color="primary", size="sm", className="me-1 mb-1", outline=True,
        ))

    # -- Charts sub-tab --
    charts_tab = dbc.Tab(label="Charts", tab_id="benefit-charts", children=[
        dbc.Container([
            # Filters row
            dbc.Row([
                dbc.Col([
                    html.Label("Year", style={"fontWeight": "bold", "fontFamily": AQUILA_FONT}),
                    html.Div(year_buttons, className="d-flex flex-wrap"),
                ], md=8),
                dbc.Col([
                    html.Label("Lease Type", style={"fontWeight": "bold", "fontFamily": AQUILA_FONT}),
                    dcc.Dropdown(
                        id="benefit-lease-type",
                        options=[{"label": t, "value": t} for t in lease_types],
                        value=["New"] if "New" in lease_types else [],
                        multi=True,
                        placeholder="All types",
                    ),
                ], md=4),
            ], className="mb-3 mt-3"),

            # KPI row
            dbc.Row(id="benefit-kpi-row", className="mb-3"),

            # Charts
            dbc.Row([
                dbc.Col(dcc.Graph(id="benefit-ner-chart", config=_CHART_CONFIG), md=6),
                dbc.Col(dcc.Graph(id="benefit-savings-chart", config=_CHART_CONFIG), md=6),
            ]),

            # Detail panel (hidden until click)
            html.Div(id="benefit-detail-panel"),

            # Hidden store for selected year
            dcc.Store(id="benefit-selected-year", data="all"),
        ], fluid=True),
    ])

    # -- Deal Browser sub-tab --
    deal_columns = [
        {"name": "Building", "id": "building_name"},
        {"name": "Tenant", "id": "tenant_name"},
        {"name": "Year", "id": "year"},
        {"name": "NER", "id": "ner", "type": "numeric",
         "format": dash_table.FormatTemplate.money(2)},
        {"name": "Base Rate", "id": "base_rate", "type": "numeric",
         "format": dash_table.FormatTemplate.money(2)},
        {"name": "TI", "id": "ti_allowance", "type": "numeric",
         "format": dash_table.FormatTemplate.money(2)},
        {"name": "Free Mo", "id": "free_months", "type": "numeric"},
        {"name": "Size SF", "id": "size_sf", "type": "numeric",
         "format": dash_table.FormatTemplate.money(0)},
        {"name": "Term", "id": "lease_term", "type": "numeric"},
        {"name": "Type", "id": "lease_type"},
        {"name": "Broker", "id": "tenant_broker"},
        {"name": "Peer Avg NER", "id": "peer_avg_ner", "type": "numeric",
         "format": dash_table.FormatTemplate.money(2)},
        {"name": "Savings", "id": "savings", "type": "numeric",
         "format": dash_table.FormatTemplate.money(2)},
    ]

    deal_browser_tab = dbc.Tab(label="Deal Browser", tab_id="benefit-deals", children=[
        dbc.Container([
            dash_table.DataTable(
                id="benefit-deal-table",
                columns=deal_columns,
                data=[],
                sort_action="native",
                filter_action="native",
                page_size=20,
                style_table={"overflowX": "auto"},
                style_header={
                    "backgroundColor": AQUILA_COLORS[0],
                    "color": "white",
                    "fontWeight": "bold",
                    "fontFamily": AQUILA_FONT,
                },
                style_cell={
                    "fontFamily": AQUILA_FONT,
                    "fontSize": "13px",
                    "padding": "6px 10px",
                },
                style_data_conditional=[{
                    "if": {"row_index": "odd"},
                    "backgroundColor": "#F9F9F9",
                }],
            ),
        ], fluid=True, className="mt-3"),
    ])

    # -- Broker List sub-tab --
    broker_columns = [
        {"name": "Broker", "id": "Broker"},
        {"name": "Deals", "id": "Deals", "type": "numeric"},
        {"name": "Wins", "id": "Wins", "type": "numeric"},
        {"name": "Win Rate", "id": "Win Rate", "type": "numeric"},
        {"name": "Total SF", "id": "Total SF", "type": "numeric",
         "format": dash_table.FormatTemplate.money(0)},
        {"name": "Median Savings", "id": "Median Savings", "type": "numeric",
         "format": dash_table.FormatTemplate.money(2)},
        {"name": "Avg Savings", "id": "Avg Savings", "type": "numeric",
         "format": dash_table.FormatTemplate.money(2)},
    ]

    broker_tab = dbc.Tab(label="Broker List", tab_id="benefit-brokers", children=[
        dbc.Container([
            dash_table.DataTable(
                id="benefit-broker-table",
                columns=broker_columns,
                data=[],
                sort_action="native",
                page_size=20,
                style_table={"overflowX": "auto"},
                style_header={
                    "backgroundColor": AQUILA_COLORS[0],
                    "color": "white",
                    "fontWeight": "bold",
                    "fontFamily": AQUILA_FONT,
                },
                style_cell={
                    "fontFamily": AQUILA_FONT,
                    "fontSize": "13px",
                    "padding": "6px 10px",
                },
                style_data_conditional=[{
                    "if": {"row_index": "odd"},
                    "backgroundColor": "#F9F9F9",
                }],
            ),
        ], fluid=True, className="mt-3"),
    ])

    return html.Div([
        html.H4("Aquila Benefit -- Tenant Rep NER Analysis",
                style={"fontFamily": AQUILA_FONT, "color": AQUILA_COLORS[0],
                       "textAlign": "center", "marginTop": "15px"}),
        dbc.Tabs([charts_tab, deal_browser_tab, broker_tab],
                 id="benefit-sub-tabs", active_tab="benefit-charts"),
    ])


# ---------------------------------------------------------------------------
# Callback registration
# ---------------------------------------------------------------------------

def register_callbacks(app, df_leases):
    """Register all Aquila Benefit callbacks on the Dash app."""

    # ---- Year pill click ----
    # Must use ALL (not MATCH) because the Output is a plain component, not pattern-matched.
    @app.callback(
        Output("benefit-selected-year", "data"),
        Input({"type": "benefit-year-btn", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def _on_year_click(n_clicks_list):
        ctx = callback_context
        if not ctx.triggered:
            return no_update
        prop_id = ctx.triggered[0]["prop_id"]
        import json
        btn_id = json.loads(prop_id.split(".")[0])
        return btn_id["index"]

    # ---- Main update: KPIs + charts + tables ----
    @app.callback(
        [
            Output("benefit-kpi-row", "children"),
            Output("benefit-ner-chart", "figure"),
            Output("benefit-savings-chart", "figure"),
            Output("benefit-deal-table", "data"),
            Output("benefit-broker-table", "data"),
        ],
        [
            Input("benefit-selected-year", "data"),
            Input("benefit-lease-type", "value"),
            Input("benefit-sub-tabs", "active_tab"),
        ],
    )
    def _update_benefit(selected_year, lease_types, active_tab):
        years = None
        if selected_year and selected_year != "all":
            try:
                years = [int(selected_year)]
            except (ValueError, TypeError):
                years = None

        comp_df = build_ner_comparison(df_leases, lease_types=lease_types or None, years=years)
        kpis = compute_kpis(comp_df)

        # KPI cards
        kpi_items = [
            ("Deals Analyzed", f"{kpis['deals']:,}"),
            ("Win Rate", f"{kpis['win_rate']:.1f}%"),
            ("Median Savings", f"${kpis['median_savings']:,.2f}/SF"),
            ("Total SF", f"{kpis['total_sf']:,.0f}"),
        ]
        kpi_cards = []
        for label, value in kpi_items:
            kpi_cards.append(dbc.Col(dbc.Card(dbc.CardBody([
                html.H6(label, className="text-muted mb-1",
                         style={"fontFamily": AQUILA_FONT, "fontSize": "12px"}),
                html.H4(value, style={"fontFamily": AQUILA_FONT,
                                       "color": AQUILA_COLORS[0], "marginBottom": 0}),
            ]), className="text-center"), md=3, sm=6, xs=6, className="mb-2"))

        # Charts
        ner_fig = _build_avg_ner_chart(comp_df)
        savings_fig = _build_savings_chart(comp_df)

        # Deal browser data
        deal_data = []
        if not comp_df.empty:
            show_cols = ["building_name", "tenant_name", "year", "ner",
                         "base_rate", "ti_allowance", "free_months", "size_sf",
                         "lease_term", "lease_type", "tenant_broker",
                         "peer_avg_ner", "savings"]
            for c in show_cols:
                if c not in comp_df.columns:
                    comp_df[c] = None
            deal_data = comp_df[show_cols].to_dict("records")

        # Broker leaderboard
        broker_df = compute_broker_leaderboard(comp_df)
        broker_data = broker_df.to_dict("records") if not broker_df.empty else []

        return kpi_cards, ner_fig, savings_fig, deal_data, broker_data

    # ---- Year pill styling ----
    @app.callback(
        Output({"type": "benefit-year-btn", "index": MATCH}, "outline"),
        Input("benefit-selected-year", "data"),
        State({"type": "benefit-year-btn", "index": MATCH}, "id"),
    )
    def _style_year_btn(selected_year, btn_id):
        return btn_id["index"] != (selected_year or "all")

    # ---- Savings chart click -> detail panel ----
    @app.callback(
        Output("benefit-detail-panel", "children"),
        Input("benefit-savings-chart", "clickData"),
        State("benefit-lease-type", "value"),
        prevent_initial_call=True,
    )
    def _on_savings_click(click_data, lease_types):
        if not click_data or not click_data.get("points"):
            return no_update

        point = click_data["points"][0]
        custom = point.get("customdata")
        if custom is None or len(custom) < 3:
            return no_update

        prop_id, year, lease_id = custom[0], custom[1], custom[2]

        # Find the AQUILA deal
        mask = df_leases["lease_id"] == lease_id
        if not mask.any():
            return html.P("Deal not found.")

        deal = df_leases[mask].iloc[0].to_dict()

        # Get peer comps
        peers = get_peer_comps(df_leases, prop_id, year,
                               lease_types=lease_types or None)

        return _build_detail_panel(deal, peers)
