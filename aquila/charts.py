"""
Plotly chart helpers with Aquila brand styling.
All chart titles are centered by default.
"""

import base64
from pathlib import Path

import plotly.express as px
from .brand import AQUILA_COLORS, AQUILA_FONT

# ── Logo watermark ─────────────────────────────────────────────────────────────
_LOGO_PATH = Path(__file__).parent.parent / "data" / "Aquila_Logo2.png"
_LOGO_B64: str | None = None


def _get_logo_b64() -> str:
    """Lazy-load and cache the Aquila logo as a base64 string."""
    global _LOGO_B64
    if _LOGO_B64 is None:
        with open(_LOGO_PATH, "rb") as f:
            _LOGO_B64 = base64.b64encode(f.read()).decode()
    return _LOGO_B64


def add_aquila_logo(fig, sizex: float = 0.12, opacity: float = 0.7):
    """Add Aquila logo above the chart area, aligned to the top-right margin.

    The logo is placed above the plot area (not overlaying chart data) by
    anchoring the bottom of the image to y=1.02 (slightly above the top edge
    of the plot). The top margin is expanded to at least 60 px so the logo
    is fully visible.

    Layout positions (paper coordinates, where y=1 = plot top):
      Logo  : y=1.02 → extends up ~12% of plot height into the top margin

    Parameters
    ----------
    fig : plotly.graph_objects.Figure
    sizex : float
        Width of the logo as a fraction of the figure width (default 0.12 = 12%).
    opacity : float
        Logo opacity from 0 (transparent) to 1 (opaque).

    Returns
    -------
    plotly.graph_objects.Figure  (same object, modified in place)
    """
    # Ensure enough top margin for logo (~12% of plot height).
    current_t = (fig.layout.margin.t or 0) if fig.layout.margin else 0
    if current_t < 60:
        fig.update_layout(margin=dict(t=60))

    fig.add_layout_image(dict(
        source=f"data:image/png;base64,{_get_logo_b64()}",
        xref="paper",
        yref="paper",
        x=1.0,
        y=1.02,      # Slightly above the plot area top edge
        sizex=sizex,
        sizey=sizex,
        xanchor="right",
        yanchor="bottom",  # bottom of logo at y=1.02; extends upward into margin
        opacity=opacity,
        layer="above",
    ))
    return fig


def write_chart_html(fig, path, sizex: float = 0.12, opacity: float = 0.7):
    """Add Aquila logo watermark and write the figure as a standalone HTML file.

    Use this instead of ``fig.write_html(path)`` in all chart generators.

    Parameters
    ----------
    fig : plotly.graph_objects.Figure
    path : str | Path
        Destination HTML file path.
    sizex : float
        Logo width as a fraction of figure width (default 0.12).
    opacity : float
        Logo opacity (default 0.7).
    """
    add_aquila_logo(fig, sizex=sizex, opacity=opacity)
    fig.write_html(path)


def aquila_styled_line_chart(
    df,
    x,
    y,
    color=None,
    facet_row=None,
    title="",
    height=800,
):
    """
    Build a Plotly line chart with Aquila style settings.

    Parameters
    ----------
    df : pd.DataFrame
        Source data.
    x, y : str
        Column names.
    color : str, optional
        Name of column to group/color lines.
    facet_row : str, optional
        Row facet column.
    title : str
        Chart title (centered by default).
    height : int
        Chart height in pixels.

    Returns
    -------
    plotly.graph_objects.Figure
    """
    fig = px.line(
        df,
        x=x,
        y=y,
        color=color,
        facet_row=facet_row,
        title=title,
        color_discrete_sequence=AQUILA_COLORS,
    )

    layout_dict = dict(
        height=height,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family=AQUILA_FONT, color="#172344"),
        title_font_family=AQUILA_FONT,
        title_x=0.5,
        title_xanchor="center",
        legend=dict(
            title_font_family=AQUILA_FONT,
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
        ),
        margin=dict(b=80),
        xaxis_tickangle=90,
        xaxis=dict(
            showline=True,
            linecolor="#e9e9ea",
            linewidth=0.5,
            mirror=False,
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            showline=True,
            linecolor="#e9e9ea",
            linewidth=0.5,
            mirror=False,
            showgrid=True,
            gridcolor="#e9e9ea",
            zeroline=True,
        ),
        shapes=[],
    )

    fig.update_layout(**layout_dict)
    return fig
