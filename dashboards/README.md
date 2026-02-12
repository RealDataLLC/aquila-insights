# Austin Office Requirements Dashboard

Interactive Dash dashboard for exploring Austin office requirement trends with year-over-year comparison.

## Features

- **Submarket Filter**: Select one or more submarkets (CBD, SW, NW, E, C) or view all markets
- **Industry Filter**: Filter requirements by tenant industry
- **Time Window**: Choose lookback period (6, 12, or 24 months)
- **SF Range Chart**: Line chart showing low/high SF ranges with YoY comparison
- **Count Chart**: Bar chart showing number of requirements with YoY comparison
- **CSV Export**: Download filtered data for further analysis

## Installation

1. Install dependencies:
```bash
cd dashboards
pip install -r requirements.txt
```

2. Ensure `aquila_graph.env` is configured in the parent directory with:
   - Google Service Account credentials (for Google Sheets access)
   - OR place `aquilacommercialsheets-923494a59a4b.json` in parent directory

## Running the Dashboard

```bash
cd dashboards
python office_requirements_dashboard.py
```

The dashboard will be available at: http://127.0.0.1:8050/

Press `Ctrl+C` to stop the server.

## Data Source

- **Google Sheets**: Office Requirements Spreadsheet (ID: `1bzpRnUrpBH6l_zX7DtTypczZf5bpYVwqPUG3tzg2vec`)
  - Tab 0: "2025 +" (current data)
  - Tab 1: "DITM & Crab Trap MASTER Report (Through 2024)" (historical data)

Data is filtered to:
- Office use only
- Date range: 2018-01-01 to present
- Records with valid SF (low & high)
- **Most recent month excluded** (incomplete data collection)

## How It Works

### Market Mapping
Requirements can apply to multiple submarkets:
- **Citywide/Flexible** → All markets (CBD, SW, NW, E, C)
- **Urban Core** → CBD + C
- **Far NW/Domain** → NW
- Direct market names → Their respective markets

### Year-over-Year Comparison
- **Current Period**: Data from selected time window (e.g., last 6 months)
- **Prior Year**: Data from same months one year earlier
- Prior year data is shifted forward 12 months for visual alignment

### Monthly Aggregation
- **SF Low/High**: Sum of all requirements in that month
- **Count**: Number of requirements in that month

### Data Exclusion
The dashboard automatically excludes the most recent month from all calculations because requirement data collection is typically incomplete for the current month.

## Chart Details

### SF Range Line Chart
- **Solid lines**: Current period (Navy = Low, Glass Blue = High)
- **Dashed lines**: Prior year (same colors, reduced opacity)
- **Height**: 400px
- **Hover**: Shows exact values and month

### Count Bar Chart
- **Solid bars**: Current period (Copper)
- **Transparent bars**: Prior year (Brass, 70% opacity)
- **Layout**: Grouped bars for side-by-side comparison
- **Height**: 300px
- **Hover**: Shows exact counts and month

## Aquila Branding

The dashboard uses Aquila's 2026 brand colors and fonts:
- **Primary**: Aquila Navy (#172344)
- **Secondary**: Glass Blue (#C2DAF1)
- **Tertiary**: Copper (#AB6D3A), Brass (#DEB76D)
- **Font**: Futura LT Pro, Futura, Arial, sans-serif

## Troubleshooting

### Google Sheets Connection Error
- Verify `aquila_graph.env` contains valid Google Service Account credentials
- OR ensure `aquilacommercialsheets-923494a59a4b.json` exists in parent directory
- Check service account has access to the spreadsheet

### No Data Shown
- Check date filters (data starts from 2018)
- Verify selected submarkets/industries have data
- Check console for error messages

### Port Already in Use
If port 8050 is already in use, edit `office_requirements_dashboard.py` and change:
```python
app.run_server(debug=True, host='127.0.0.1', port=8051)  # Use different port
```

## Future Enhancements

Potential features for future versions:
- Micromarket filter (when data becomes available)
- Size range filter (Sub 10k, 10k-25k, etc.)
- Deal status filter
- Moving averages
- Metric cards showing % change
- Submarket comparison mode
- Custom date range picker

## File Structure

```
dashboards/
├── office_requirements_dashboard.py    # Main Dash application
├── requirements.txt                    # Python dependencies
└── README.md                           # This file
```

## Dependencies

- `dash>=2.14.0` - Dashboard framework
- `dash-bootstrap-components>=1.5.0` - Bootstrap styling
- `plotly>=5.18.0` - Interactive charts
- `pandas>=2.1.0` - Data manipulation
- `gspread>=5.12.0` - Google Sheets API
- `oauth2client>=4.1.3` - Google authentication
- `python-dotenv>=1.0.0` - Environment variables

## Last Updated

2026-02-12
