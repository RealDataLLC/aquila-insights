import os
import subprocess

# Plotly styling module for Aquila-style charts
import plotly.express as px
from datetime import datetime

AQUILA_COLORS = ["#00325a", "#e6b40a", "#8c8c8c", "#18a0CF", "#D05325"]
AQUILA_FONT = "Futura LT Pro, Futura, Arial, sans-serif"
def commit_and_push_all(commit_message="Update readme instructions"):
    """
    Stages all changes, commits with the provided message,
    and pushes to 'main'. If 'main' doesn't exist, tries 'master'.
    """
    # Make sure we're in the notebook's directory
    notebook_dir = os.path.dirname(os.path.abspath("__file__"))
    os.chdir(notebook_dir)

    # Stage all changes
    subprocess.run(["git", "add", "."])

    # Commit with the provided message
    subprocess.run(["git", "commit", "-m", commit_message])

    # Push to default remote (origin) and branch (main or master)
    try:
        subprocess.run(["git", "push", "origin", "main"], check=True)
    except subprocess.CalledProcessError:
        # If main branch doesn't exist, try master
        subprocess.run(["git", "push", "origin", "master"])

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
        Chart title.
    height : int
        Chart height.
    date_annotation : bool
        If True, adds an annotation with today's date.
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
    # No vertical lines: skip vline_shapes and related logic
    vline_shapes = []

    # Borders: Only show left and bottom (x and y axis lines), hide others
    layout_dict = dict(
        height=height,
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(family=AQUILA_FONT, color="#00325a"),
        title_font_family=AQUILA_FONT,
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
            linewidth=.5,
            mirror=False,
            showgrid=False,   # Hide background grid
            zeroline=False,
        ),
        yaxis=dict(
            showline=True,
            linecolor="#e9e9ea",
            linewidth=.5,
            mirror=False,
            showgrid=True,
            gridcolor="#e9e9ea",
            zeroline=True,
        ),
        shapes=vline_shapes,
    )

    fig.update_layout(**layout_dict)
    return fig