# Brand constants stub for Vercel deployment.
# On local runs the parent directory's aquila_graphing_tools.py takes precedence
# (added to sys.path[0] by the dashboard). On Vercel the parent directory is not
# deployed, so Python falls through to this file in the dashboards/ root.

AQUILA_COLORS = [
    "#172344",  # [0]  Navy (primary)
    "#C2DAF1",  # [1]  Glass Blue (secondary)
    "#88ABC8",  # [2]  Glass Blue Alt (secondary)
    "#AAA9A8",  # [3]  Concrete (tertiary)
    "#AB6D3A",  # [4]  Copper (tertiary)
    "#DEB76D",  # [5]  Brass (tertiary)
    "#556B30",  # [6]  Greenspace (tertiary)
    "#E8E8E8",  # [7]  Mopac Gray (extended)
    "#D6B69C",  # [8]  Pennybacker (extended)
    "#FFD899",  # [9]  Texas Sun (extended)
    "#B2C48C",  # [10] Zilker (extended)
    "#BF4040",  # [11] Signal (extended)
    "#F2ACAC",  # [12] SoCo (extended)
]

AQUILA_FONT = "Futura LT Pro, Futura, Arial, sans-serif"
