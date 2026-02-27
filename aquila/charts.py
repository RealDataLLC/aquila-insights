"""
Plotly chart helpers with Aquila brand styling.
All chart titles are centered by default.
"""

import plotly.express as px
from .brand import AQUILA_COLORS, AQUILA_FONT


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
        margin=dict(b=100),
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
