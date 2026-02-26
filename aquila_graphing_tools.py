import os
import subprocess

# Plotly styling module for Aquila-style charts
import plotly.express as px
from datetime import datetime

# Aquila Brand Colors (2026 Updated Palette)
# Use colors in hierarchy order: Navy first, then Glass Blue, Glass Blue Alt, etc.
AQUILA_COLORS = [
    "#172344",  # 1. AQUILA Navy (primary)
    "#C2DAF1",  # 2. Glass Blue
    "#88ABC8",  # 3. Glass Blue Alt
    "#AAA9A8",  # 4. Concrete
    "#AB6D3A",  # 5. Copper
    "#DEB76D",  # 6. Brass
    "#556B30",  # 7. Greenspace
    "#E8E8E8",  # 8. Mopac Gray
    "#D6B69C",  # 9. Pennybacker
    "#FFD899",  # 10. Texas Sun
    "#B2C48C",  # 11. Zilker
    "#BF4040",  # 12. Signal
    "#F2ACAC",  # 13. SoCo
]
AQUILA_FONT = "Futura LT Pro, Futura, Arial, sans-serif"

def initialize_supabase_connection():
    """
    Initialize connection to Supabase database.
    Returns a Supabase client for querying data.

    Requires environment variables:
    - SUPABASE_URL: Your Supabase project URL
    - SUPABASE_KEY: Your Supabase API key (anon or service_role)

    Returns
    -------
    supabase.Client
        Authenticated Supabase client for database operations

    Example
    -------
    >>> from dotenv import load_dotenv
    >>> load_dotenv('aquila_graph.env')
    >>> supabase = initialize_supabase_connection()
    >>>
    >>> # Query data
    >>> response = supabase.table('your_table').select('*').execute()
    >>> df = pd.DataFrame(response.data)
    """
    from supabase import create_client, Client
    from dotenv import load_dotenv
    # Always load aquila_graph.env from the folder containing this module file
    import os

    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "aquila_graph.env")
    load_dotenv(env_path)

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_PUBLIC_KEY")
    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY must be set in aquila_graph.env"
        )

    supabase: Client = create_client(url, key)
    return supabase
    
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