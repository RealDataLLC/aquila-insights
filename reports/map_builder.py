"""
Submarket map builder for AQUILA Office Quarterly Report.

Parses KMZ/KML polygon boundaries and renders Plotly Scattermapbox maps
as PNG images for embedding in the report PDF.

Maps:
  - Citywide: all 13 polygons colored with AQUILA brand colors + labels
  - CBD / Northwest / Southwest / East: highlighted polygons, others gray
"""
import os
import math
import zipfile
import xml.etree.ElementTree as ET

import plotly.graph_objects as go
from dotenv import load_dotenv

from aquila.brand import AQUILA_COLORS

# -- Load Mapbox token from environment
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "aquila_graph.env"))
MAPBOX_TOKEN = os.environ.get("MAPBOX_API_KEY", "")

# -- Default KMZ path
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_KMZ = os.path.join(_REPO_ROOT, "data", "Final AQUILA Submarket Map.kmz")

# -- Submarket groupings (report submarket -> KML polygon names)
SUBMARKET_GROUPS = {
    "CBD":       ["CBD"],
    "Northwest": ["Northwest", "Far NW/Round Rock", "Round Rock",
                  "Arboretum Market", "Shepherd Mountain", "North"],
    "Southwest": ["Southwest", "Near SW", "Far Southwest"],
    "East":      ["East/ Northeast"],
}

# -- Per-polygon brand colors (for citywide map)
POLYGON_COLORS = {
    "CBD":               AQUILA_COLORS[0],   # Navy
    "Northwest":         AQUILA_COLORS[1],   # Glass Blue
    "Southwest":         AQUILA_COLORS[2],   # Glass Blue Alt
    "East/ Northeast":   AQUILA_COLORS[4],   # Copper
    "Near SW":           AQUILA_COLORS[5],   # Brass
    "Far Southwest":     AQUILA_COLORS[6],   # Greenspace
    "Far NW/Round Rock": AQUILA_COLORS[8],   # Pennybacker
    "Round Rock":        AQUILA_COLORS[9],   # Texas Sun
    "Arboretum Market":  AQUILA_COLORS[10],  # Zilker
    "Shepherd Mountain": AQUILA_COLORS[3],   # Concrete
    "Central":           AQUILA_COLORS[11],  # Signal
    "North":             AQUILA_COLORS[12],  # SoCo
    "South/ Southeast":  AQUILA_COLORS[7],   # Mopac Gray
}

_KML_NS = {"kml": "http://www.opengis.net/kml/2.2"}


def parse_kmz(kmz_path=None):
    """Extract polygon coordinates from a KMZ file.

    Returns dict of {name: [(lon, lat), ...]} for each Polygon placemark.
    Points and other geometry types are skipped.
    """
    kmz_path = kmz_path or DEFAULT_KMZ
    polygons = {}

    with zipfile.ZipFile(kmz_path, "r") as zf:
        kml_names = [n for n in zf.namelist() if n.endswith(".kml")]
        if not kml_names:
            raise ValueError(f"No KML file found in {kmz_path}")
        kml_data = zf.read(kml_names[0])

    root = ET.fromstring(kml_data)

    for pm in root.iter("{http://www.opengis.net/kml/2.2}Placemark"):
        name_el = pm.find("kml:name", _KML_NS)
        if name_el is None or not name_el.text:
            continue
        name = name_el.text.strip()

        polygon_el = pm.find(".//kml:Polygon", _KML_NS)
        if polygon_el is None:
            continue

        coords_el = polygon_el.find(
            ".//kml:outerBoundaryIs/kml:LinearRing/kml:coordinates", _KML_NS
        )
        if coords_el is None or not coords_el.text:
            continue

        coords = []
        for triplet in coords_el.text.strip().split():
            parts = triplet.split(",")
            if len(parts) >= 2:
                lon, lat = float(parts[0]), float(parts[1])
                coords.append((lon, lat))

        if coords:
            polygons[name] = coords

    return polygons

def _rgba(hex_color, opacity=0.45):
    r = int(hex_color[1:3], 16)
    g = int(hex_color[3:5], 16)
    b = int(hex_color[5:7], 16)
    return f"rgba({r},{g},{b},{opacity})"


def _compute_centroid(coords):
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return sum(lons) / len(lons), sum(lats) / len(lats)


def _compute_bounds(polygons, names=None):
    all_lons, all_lats = [], []
    for name, coords in polygons.items():
        if names and name not in names:
            continue
        all_lons.extend(c[0] for c in coords)
        all_lats.extend(c[1] for c in coords)
    return {
        "min_lon": min(all_lons), "max_lon": max(all_lons),
        "min_lat": min(all_lats), "max_lat": max(all_lats),
    }


def _auto_zoom(bounds, width_px=1100, height_px=500):
    lat_range = bounds["max_lat"] - bounds["min_lat"]
    lon_range = bounds["max_lon"] - bounds["min_lon"]
    lat_zoom = math.log2(180 / lat_range) if lat_range > 0 else 15
    lon_zoom = math.log2(360 / lon_range) if lon_range > 0 else 15
    zoom = min(lat_zoom, lon_zoom) + 0.3
    return max(7, min(zoom, 14))

def _add_mapbox_polygon(fig, name, coords, fill_color, line_color,
                        line_width=1.5, opacity=0.5, show_legend=False):
    lons = [c[0] for c in coords] + [coords[0][0]]
    lats = [c[1] for c in coords] + [coords[0][1]]
    fig.add_trace(go.Scattermapbox(
        lon=lons, lat=lats,
        mode="lines",
        fill="toself",
        fillcolor=_rgba(fill_color, opacity),
        line=dict(color=line_color, width=line_width),
        name=name,
        showlegend=show_legend,
        hoverinfo="skip",
    ))


# -- Label display name mapping (line breaks for long names)
_DISPLAY_NAMES = {
    "Far NW/Round Rock": "Far NW/\nRound Rock",
    "East/ Northeast":   "East/\nNortheast",
    "South/ Southeast":  "South/\nSoutheast",
    "Arboretum Market":  "Arboretum\nMarket",
    "Shepherd Mountain":  "Shepherd\nMountain",
}


def _display_name(name):
    return _DISPLAY_NAMES.get(name, name)


def _add_mapbox_label(fig, name, coords, font_size=10, font_color="#172344"):
    clon, clat = _compute_centroid(coords)
    fig.add_trace(go.Scattermapbox(
        lon=[clon], lat=[clat],
        mode="text",
        text=[_display_name(name)],
        textfont=dict(size=font_size, color=font_color, family="Arial Black"),
        showlegend=False,
        hoverinfo="skip",
    ))


def _mapbox_layout(bounds, width=1100, height=500):
    center_lat = (bounds["min_lat"] + bounds["max_lat"]) / 2
    center_lon = (bounds["min_lon"] + bounds["max_lon"]) / 2
    zoom = _auto_zoom(bounds, width, height)
    return go.Layout(
        mapbox=dict(
            accesstoken=MAPBOX_TOKEN,
            style="light",
            center=dict(lat=center_lat, lon=center_lon),
            zoom=zoom,
        ),
        width=width,
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        paper_bgcolor="white",
    )


def build_citywide_map(polygons, width=1100, height=500):
    """Build citywide map with all polygons colored by brand palette."""
    fig = go.Figure()

    for name, coords in polygons.items():
        color = POLYGON_COLORS.get(name, AQUILA_COLORS[3])
        _add_mapbox_polygon(fig, name, coords,
                            fill_color=color, line_color=color,
                            line_width=2, opacity=0.55)
        _add_mapbox_label(fig, name, coords, font_size=9, font_color="#172344")

    bounds = _compute_bounds(polygons)
    pad_lat = (bounds["max_lat"] - bounds["min_lat"]) * 0.05
    pad_lon = (bounds["max_lon"] - bounds["min_lon"]) * 0.05
    bounds["min_lat"] -= pad_lat
    bounds["max_lat"] += pad_lat
    bounds["min_lon"] -= pad_lon
    bounds["max_lon"] += pad_lon
    fig.update_layout(_mapbox_layout(bounds, width, height))
    return fig


def build_submarket_map(polygons, highlight_names, width=1100, height=500):
    """Build submarket map: highlighted polygons in Navy, others light gray."""
    fig = go.Figure()

    highlight_set = set(highlight_names)

    for name, coords in polygons.items():
        if name not in highlight_set:
            _add_mapbox_polygon(fig, name, coords,
                                fill_color="#D0D0D0", line_color="#B0B0B0",
                                line_width=1, opacity=0.35)

    for name, coords in polygons.items():
        if name in highlight_set:
            _add_mapbox_polygon(fig, name, coords,
                                fill_color=AQUILA_COLORS[0], line_color=AQUILA_COLORS[0],
                                line_width=2.5, opacity=0.55)
            _add_mapbox_label(fig, name, coords, font_size=11, font_color="#FFFFFF")

    # Zoom to highlighted polygons only, with padding
    bounds = _compute_bounds(polygons, names=highlight_set)
    pad_lat = (bounds["max_lat"] - bounds["min_lat"]) * 0.05
    pad_lon = (bounds["max_lon"] - bounds["min_lon"]) * 0.05
    bounds["min_lat"] -= pad_lat
    bounds["max_lat"] += pad_lat
    bounds["min_lon"] -= pad_lon
    bounds["max_lon"] += pad_lon
    fig.update_layout(_mapbox_layout(bounds, width, height))
    return fig


def export_map(fig, output_path, width=1100, height=500, scale=3):
    """Export map figure to PNG via Kaleido."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.write_image(output_path, width=width, height=height, scale=scale,
                    format="png", engine="kaleido")
    print(f"    Map saved: {os.path.basename(output_path)}")


def generate_submarket_maps(charts_dir, kmz_path=None, width=1100, height=500, scale=3):
    """Generate all submarket map PNGs for the office report.

    Returns dict of {submarket_name: png_path}.
    """
    if not MAPBOX_TOKEN:
        print('  WARNING: MAPBOX_API_KEY not set -- skipping map generation')
        return {}
    print('\n  Generating submarket maps...')
    polygons = parse_kmz(kmz_path)
    print(f"    Parsed {len(polygons)} polygons from KMZ")

    maps = {}

    fig = build_citywide_map(polygons, width, height)
    path = os.path.join(charts_dir, "map_citywide.png")
    export_map(fig, path, width, height, scale)
    maps["Citywide"] = path

    for submarket, poly_names in SUBMARKET_GROUPS.items():
        fig = build_submarket_map(polygons, poly_names, width, height)
        fname = "map_" + submarket.lower().replace(" ", "_") + ".png"
        path = os.path.join(charts_dir, fname)
        export_map(fig, path, width, height, scale)
        maps[submarket] = path

    print(f"    Generated {len(maps)} maps")
    return maps
