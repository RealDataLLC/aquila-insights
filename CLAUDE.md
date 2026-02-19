# CLAUDE.md - AI Assistant Guide for Aquila Insights

## Project Overview

**Aquila Insights** generates branded, interactive HTML charts from real estate data and publishes them via GitHub Pages.

**Workflow:** Notebooks for development → Export HTML to `charts/` → Link in README.md → Auto-publish to GitHub Pages

**Maintained by:** Nelson Lin (nelson@subtlerealestate.com)
**Repository:** https://github.com/realdatallc/aquila-insights
**Deployment:** https://realdatallc.github.io/aquila-insights/
**Active Branch:** Feature branches merge to main

---

## Technology Stack

**Languages:** Python 3, SQL, JavaScript/HTML (Plotly-generated)

**Core Libraries:**
- Data: `pandas`, `numpy`
- Visualization: `plotly.express`, `plotly.graph_objects`
- APIs: `requests`, `gspread`, `oauth2client`, `supabase`
- Files: `openpyxl`, `python-dotenv`

**Data Sources:**
1. **Supabase** - PostgreSQL database (market data)
2. **Google Sheets** - Office tenant requirements (ID: `1bzpRnUrpBH6l_zX7DtTypczZf5bpYVwqPUG3tzg2vec`)
3. **Google Sheets** - Industrial TITM (ID: `1natA0ALaQnX3U_vGC5Vrchy1QqmbW8k0zvTKwuE2wys`)
4. **FRED API** - Economic indicators
5. **Excel Files** - Property management & transaction data

---

## Repository Structure

```
/home/user/aquila-insights/
├── charts/                                  # Published HTML charts (organized by category)
│   ├── property-management/                 # 1 chart: AMS KPIs
│   ├── office/                              # 17 charts: Requirements, transactions, market metrics
│   ├── industrial/                          # 9 charts: TITM demand, vacancy, NNN rent, market metrics
│   └── economic-indicators/                 # 8 charts: Employment, wages, housing, financial
│
├── dashboards/                              # Interactive Dash apps (local, not published)
│   ├── office_requirements_dashboard.py     # Austin office requirements interactive dashboard
│   ├── office_requirements_dashboard_v1_backup.py  # Pre-v2 backup
│   └── requirements.txt                     # Dashboard-specific dependencies
│
├── data/                                    # Input data files
│   ├── AMS- Property Split List.xlsx
│   └── TransactionRequestForm_Data_*.xlsx
│
├── NOTEBOOKS (Development)
│   ├── office_requirements_combined.ipynb         # Office: 7 requirements charts (Google Sheets)
│   ├── industrial_vacancy_supabase.ipynb          # Industrial: 1 vacancy chart (Supabase)
│   ├── building-performance-by-size.ipynb         # Both: 4 size-based charts (Supabase)
│   ├── fred-economic-indicators.ipynb             # Economic: 7 indicator charts (FRED API)
│   └── supabase-graphs.ipynb                      # Example/documentation
│
├── UPDATE SCRIPTS (Automation)
│   ├── update_all_charts.py                       # Master: Runs all 5 update scripts
│   ├── update_office_combined_requirements.py     # Office: 7 charts (Google Sheets)
│   ├── update_industrial_vacancy.py               # Industrial: 1 chart (Supabase)
│   ├── update_building_performance_charts.py      # Both: 4 charts (Supabase)
│   ├── update_fred_housing_chart.py               # Economic: 1 chart (FRED)
│   └── update_fred_economic_indicators.py         # Economic: 7 charts (FRED)
│
├── GENERATOR SCRIPTS (On-demand)
│   ├── create_ams_kpi_chart.py                    # Property management KPIs
│   ├── create_office_transaction_charts.py        # Office transaction volume (2 charts)
│   ├── create_office_demand_by_market.py          # Office demand by submarket (5 charts)
│   ├── create_industrial_demand_charts.py         # Industrial TITM charts (5 charts)
│   └── create_industrial_nnn_rent_chart.py        # Industrial NNN rent by submarket (1 chart)
│
├── DEPRECATED
│   └── DEPRECATED_update_office_requirements.py   # Old single-tab Google Sheets (replaced by combined)
│
├── aquila_graphing_tools.py                 # Shared utilities (styling, Supabase, git)
├── aquila_graph.env                         # CREDENTIALS (gitignored)
├── .gitignore                               # Excludes: aquila_graph.env, *.json
└── README.md                                # Public chart index
```

---

## Key Files & Functions

### aquila_graphing_tools.py

**Core Functions:**
```python
# Supabase connection
initialize_supabase_connection() → supabase.Client

# Git automation
commit_and_push_all(commit_message)

# Styled charts
aquila_styled_line_chart(df, x, y, color=None, facet_row=None, title="", height=800)
```

**Brand Colors (2026 Palette):**
```python
AQUILA_COLORS = [
    "#172344",  # AQUILA Navy (primary)
    "#C2DAF1",  # Glass Blue (secondary)
    "#AB6D3A",  # Copper (tertiary)
    "#DEB76D",  # Brass (tertiary)
    "#556B30",  # Greenspace (tertiary)
    "#AAA9A8",  # Concrete (tertiary)
    "#BF4040",  # Signal (extended)
    "#D6B69C",  # Pennybacker (extended)
    "#FFDB99",  # Texas Sun (extended)
    "#B2C48C",  # Zilker (extended)
    "#E8E8E8",  # Mopac Gray (extended)
    "#F2ACAC",  # SoCo (extended)
]
```

**Font:** `AQUILA_FONT = "Futura LT Pro, Futura, Arial, sans-serif"`

---

## Data Sources & Chart Outputs

### 1. Office Requirements (Google Sheets)

**Notebook:** `office_requirements_combined.ipynb`
**Script:** `update_office_combined_requirements.py`

**Data Source:**
- Spreadsheet ID: `1bzpRnUrpBH6l_zX7DtTypczZf5bpYVwqPUG3tzg2vec`
- Tab 0: "2025 +" (current data)
- Tab 2: "Through 2024" (historical, office-only filtered)

**Key Features:**
- Combines historical & current data from 2018+
- Compares requirements vs absorption (Supabase)
- Market mapping: Flexible/Citywide counts toward all markets
- **2026 annualized projection** on demand-by-tenant-size chart (see below)

**Outputs (7 charts):**
```
charts/office/
├── requirements_sf_total.html
├── requirements_sf_avg.html
├── requirements_sf_avg_by_industry.html
├── requirements_by_size_range.html
├── requirements_vs_absorption_office.html
├── requirements_yoy_rolling_12m.html
└── requirements_demand_by_tenant_size.html   ← Annual bars + 2026 projection
```

**Size Bins:** Sub 10k, 10k-25k, 25k-50k, 50k-100k, Mega (100k+)

**2026 Annualized Projection (`requirements_demand_by_tenant_size.html`):**
- Chart aggregates by **year** (not quarter)
- Current year bar is **projected full-year** demand, not YTD actuals
- Projection formula: `projected_2026 = ytd_2026 × (full_2025 / ytd_2025_same_period)`
- Size distribution uses 2025's annual size-category mix
- Visual distinction: projected bar rendered at 45% opacity with diagonal hatch pattern; total demand marker is open circle on a dashed connector
- Caption in chart subtitle shows pace factor and as-of date, e.g. *"8.4x pace factor vs. 2025"*

---

### 2. Industrial Vacancy (Supabase)

**Notebook:** `industrial_vacancy_supabase.ipynb`
**Script:** `update_industrial_vacancy.py`

**Data Source:** Supabase table `market_tables_industrial`

**Outputs (1 chart):**
```
charts/industrial/
└── vacancy_rate_industrial.html
```

---

### 3. Industrial Demand (Google Sheets TITM)

**Script:** `create_industrial_demand_charts.py`

**Data Source:**
- Spreadsheet ID: `1natA0ALaQnX3U_vGC5Vrchy1QqmbW8k0zvTKwuE2wys`
- Tab index 1: "TITM" (Tenants in the Market)

**Outputs (5 charts):**
```
charts/industrial/
├── industrial_demand_by_tenant_size.html
├── industrial_demand_by_use_type.html
├── industrial_requirements_by_size_range.html
├── industrial_requirements_sf_total.html
└── industrial_requirements_sf_avg.html
```

**Size Bins:** Sub 25k, 25k-50k, 50k-100k, 100k-250k, Mega (250k+)
*(Larger than office bins due to industrial scale)*

---

### 4. Industrial NNN Rental Rates (Supabase)

**Script:** `create_industrial_nnn_rent_chart.py`

**Data Source:** Supabase table `market_tables_industrial`

**Filters:** `property_type = 'Industrial'`, submarkets: Northeast, Southeast, Williamson County

**Date Range:** 2022 Q1 → configurable `END_QUARTER` constant (update as new quarters arrive)

**Outputs (1 chart):**
```
charts/industrial/
└── industrial_nnn_rent_by_submarket.html
```

**Colors:** Navy (Northeast), Brass (Southeast), Concrete (Williamson County)

---

### 5. Building Performance (Supabase)

**Notebook:** `building-performance-by-size.ipynb`
**Script:** `update_building_performance_charts.py`

**Data Source:**
- `quarterly_report_data_office` (12,000+ records)
- `quarterly_report_data_industrial` (26,000+ records)

**Filters:**
- `aquila_competitive_set = True`
- `building_status = 'Existing'`

**Processing:**
- Parses quarter strings ("2025 Q4" → datetime)
- Auto-creates 5 size bins per property type using quintiles
- Weighted calculations by `rentable_building_area`
- Uses pagination for large datasets

**Outputs (4 charts):**
```
charts/office/
├── office_occupancy_by_size.html
└── office_rent_by_size.html

charts/industrial/
├── industrial_occupancy_by_size.html
└── industrial_rent_by_size.html
```

---

### 6. Economic Indicators (FRED API)

**Notebook:** `fred-economic-indicators.ipynb`
**Scripts:**
- `update_fred_housing_chart.py` (1 chart)
- `update_fred_economic_indicators.py` (7 charts)

**Data Source:** Federal Reserve Economic Data API

**Key Technique:** Base 100 indexing for cross-series comparison

**Outputs (8 charts):**
```
charts/economic-indicators/
├── austin_housing_starts.html                    # Series: AUST448BPPRIV
├── austin_employment_office_sectors.html         # 3 series
├── austin_employment_industrial.html             # 2 series
├── austin_employment_retail.html
├── austin_vs_national_tech_employment.html
├── austin_vs_dallas_vs_national_wage_growth.html # 3 metros
├── interest_rates_treasury_mortgage.html         # 2 series
└── inflation_cpi_ppi_office.html                 # 5 series
```

---

### 7. Property Management (Excel)

**Script:** `create_ams_kpi_chart.py`

**Data Source:** `data/AMS- Property Split List (Updated 1.9.26).xlsx`

**Outputs (1 chart):**
```
charts/property-management/
└── ams_managed_properties_kpi.html
```

**Metrics:** Total SF & building count by property type (dual bar chart)

---

### 8. Office Transactions (Excel)

**Script:** `create_office_transaction_charts.py`

**Data Source:** `data/TransactionRequestForm_Data_*.xlsx`

**Processing:** Robust SF cleaning (handles acres, suites, totals)

**Outputs (2 charts):**
```
charts/office/
├── transaction_sf_by_quarter.html
└── transaction_count_by_quarter.html
```

**Data Range:** 2022 Q1+ (stacked by platform)

---

### 9. Office Demand by Market (Google Sheets)

**Script:** `create_office_demand_by_market.py`

**Inclusive Market Mapping:**
- **Citywide/Flexible** → All markets (CBD, SW, NW, E, C)
- **Urban Core** → CBD + C
- **Far NW/Domain** → NW
- **Multi-market strings** → Each listed market

**Outputs (5 charts):**
```
charts/office/
├── requirements_demand_by_tenant_size_cbd.html
├── requirements_demand_by_tenant_size_sw.html
├── requirements_demand_by_tenant_size_nw.html
├── requirements_demand_by_tenant_size_e.html
└── requirements_demand_by_tenant_size_c.html
```

**2026 Annualized Projection (all 5 submarket charts):**
- Same annual aggregation and projection methodology as the main demand chart (Section 1)
- Global pace factor computed from all-market 2025 vs 2026 YTD, then applied per submarket
- Market-specific 2026 projected total distributed by that submarket's 2025 size mix (falls back to YTD 2026 mix if no 2025 data exists for that market)
- Identical visual treatment: hatched/faded projected bar + dashed connector to open-circle marker on total line
- Caption subtitle on each chart shows pace factor and as-of date

---

## Interactive Dashboards (Local)

Dashboards live in `dashboards/` and run locally via Dash. They are NOT published to GitHub Pages.

**Run any dashboard:**
```bash
cd dashboards
python office_requirements_dashboard.py
# Opens at http://127.0.0.1:8050/
```

**Dependencies (install once):**
```bash
pip install dash dash-bootstrap-components plotly pandas gspread oauth2client python-dotenv
```

---

### Office Requirements Dashboard

**File:** `dashboards/office_requirements_dashboard.py`
**Data Source:** Google Sheets `1bzpRnUrpBH6l_zX7DtTypczZf5bpYVwqPUG3tzg2vec` (same as static charts)

**Features:**
- **Submarket filter** – multi-select: CBD, SW, NW, E, C (or All)
- **Industry filter** – multi-select from all industries in dataset
- **Size Range filter** – Sub 10k SF, 10k-25k SF, 25k-50k SF, 50k-100k SF, Mega Requirements
- **Date Range Picker** – controls graph display range only (data is never date-filtered)
- **Metric Cards** – Total SF, Requirement Count, Avg SF per Req, YoY Growth (color-coded)
- **SF Range Chart** – SF Low/High lines for current + prior year, plus 3-month rolling avg on Avg SF
- **Count Bar Chart** – Grouped bars current vs prior year
- **Data Table** – sortable monthly detail, 20 rows/page
- **CSV Export** – downloads current view with rolling averages

**Key Architecture Decisions:**
- Data is **never filtered by date** — date range only slices the display. This ensures prior year comparison data is always available regardless of selected range.
- Rolling averages are calculated on the **full dataset first**, then split into current/prior periods. This prevents edge effects at period boundaries.
- Prior year period = exact same date range shifted back 12 months (not calendar year).
- YoY alignment: prior year months are relabeled to current year ticks (e.g., "Feb 2024" data displays under "Feb 2025" label).
- Orphaned prior-year rows (no matching current month) are filtered out after the merge to prevent stray dates appearing on the x-axis.

**Rolling Average:**
- Window: 3 months, `min_periods=1`
- Calculated on `sf_avg = (sf_low + sf_high) / 2` — NOT separate low/high lines
- Rendered as dotted Copper line (current) and dash-dot Brass line (prior year)

**Size Bins (office-specific):**
```python
bins   = [0, 10000, 25000, 50000, 100000, float('inf')]
labels = ['Sub 10k SF', '10k-25k SF', '25k-50k SF', '50k-100k SF', 'Mega Requirements']
df['size_category'] = pd.cut(df['sf_avg'], bins=bins, labels=labels, right=False)
```

**Known Gotchas:**
| Issue | Cause | Fix |
|-------|-------|-----|
| Stray old date at end of chart (e.g. "Dec 2024" after "Dec 2025") | Outer merge creates orphaned rows with `NaN` sort key | Filter `df_plot[df_plot['sort_order_current'].notna()]` after merge |
| Prior year month missing from bar chart | Date filtering applied before aggregation excluded that month | Never date-filter `df_global`; only split into current/prior after aggregating |
| `app.run_server` error | Obsolete in newer Dash | Use `app.run()` |
| `font` key error on axis | Plotly changed API | Use `tickfont=dict(...)` inside `xaxis`/`yaxis`, not `font=dict(...)` |
| Unicode print error on Windows | CP1252 can't encode checkmarks | Use plain ASCII in `print()` statements |

---

## Standard Workflow

### Chart Generation

1. **Load environment**
```python
from dotenv import load_dotenv
load_dotenv('aquila_graph.env')
```

2. **Fetch & process data**
```python
# Supabase
from aquila_graphing_tools import initialize_supabase_connection
supabase = initialize_supabase_connection()
response = supabase.table('table_name').select('*').execute()
df = pd.DataFrame(response.data)

# Google Sheets
import gspread
from oauth2client.service_account import ServiceAccountCredentials
# ... (build credentials from env vars) ...
client = gspread.authorize(creds)
sheet = client.open_by_key('sheet_id')
df = pd.DataFrame(sheet.get_worksheet(0).get_all_records())

# FRED API
import requests
url = "https://api.stlouisfed.org/fred/series/observations"
params = {"series_id": "SERIES_ID", "api_key": fred_api_key, "file_type": "json"}
response = requests.get(url, params=params)
df = pd.DataFrame(response.json()['observations'])
```

3. **Generate chart**
```python
from aquila_graphing_tools import aquila_styled_line_chart
fig = aquila_styled_line_chart(df, x='date', y='value', color='category', title='Chart Title')

# Or custom chart
import plotly.express as px
from aquila_graphing_tools import AQUILA_COLORS, AQUILA_FONT
fig = px.bar(df, x='x', y='y', color_discrete_sequence=AQUILA_COLORS)
fig.update_layout(plot_bgcolor='white', font=dict(family=AQUILA_FONT, color='#172344'))
```

4. **Export to categorized subdirectory**
```python
fig.write_html('charts/category/chart_name.html')
# Categories: property-management, office, industrial, economic-indicators
```

5. **Update README.md** (REQUIRED)
```markdown
## Category
[Descriptive Name [YYYY-MM-DD]](https://realdatallc.github.io/aquila-insights/charts/category/chart_name.html)
```

6. **Commit & push**
```python
from aquila_graphing_tools import commit_and_push_all
commit_and_push_all("Update chart description")
```

---

## Common Patterns

### Date Handling
```python
# Parse mixed formats
df['date'] = pd.to_datetime(df['date'], errors='coerce')

# Parse quarter strings ("2025 Q4")
import re
def parse_quarter(q_str):
    m = re.match(r'(\d{4})\s*[Qq](\d)', str(q_str))
    if m:
        year, q = int(m.group(1)), int(m.group(2))
        return pd.Timestamp(f"{year}-{(q-1)*3+1:02d}-01")
    return pd.NaT

# Monthly aggregation
monthly = df.groupby(pd.Grouper(key='date', freq='ME')).sum()
```

### Data Cleaning
```python
# Remove commas, convert to numeric
df['value'] = pd.to_numeric(df['value'].astype(str).str.replace(',', ''), errors='coerce')

# Filter dates
df = df[df['date'] >= '2018-01-01']

# Size binning
df['size_bin'] = pd.cut(df['sf'], bins=[0, 10000, 25000, 50000, 100000, float('inf')],
                        labels=['Sub 10k', '10k-25k', '25k-50k', '50k-100k', 'Mega'])
```

### Chart Formatting
```python
# Percentages
fig.update_yaxes(tickformat='.1%')

# Currency
fig.update_yaxes(tickprefix='$', tickformat=',')

# Height
fig.update_layout(height=650)
```

---

## Automation

### Update All Charts
```bash
python3 update_all_charts.py                    # Generate 20 charts
python3 update_all_charts.py --update-readme    # + Update README dates
```

**Runs 5 scripts:**
1. `update_office_combined_requirements.py` (7 Office charts)
2. `update_industrial_vacancy.py` (1 Industrial chart)
3. `update_fred_housing_chart.py` (1 Economic chart)
4. `update_building_performance_charts.py` (4 Office & Industrial charts)
5. `update_fred_economic_indicators.py` (7 Economic charts)

### Individual Updates
```bash
python3 update_office_combined_requirements.py
python3 update_industrial_vacancy.py
python3 update_building_performance_charts.py
python3 update_fred_housing_chart.py
python3 update_fred_economic_indicators.py
```

### On-Demand Generators
```bash
python3 create_ams_kpi_chart.py
python3 create_office_transaction_charts.py
python3 create_office_demand_by_market.py
python3 create_industrial_demand_charts.py
```

---

## Configuration

### aquila_graph.env
```bash
# FRED API
FRED_API_KEY=your_key

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_key

# Google Service Account (JSON credentials as env vars)
GOOGLE_SERVICE_ACCOUNT_TYPE=service_account
GOOGLE_PROJECT_ID=project_id
GOOGLE_PRIVATE_KEY_ID=key_id
GOOGLE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
GOOGLE_CLIENT_EMAIL=service_account@project.iam.gserviceaccount.com
GOOGLE_CLIENT_ID=client_id
GOOGLE_AUTH_URI=https://accounts.google.com/o/oauth2/auth
GOOGLE_TOKEN_URI=https://oauth2.googleapis.com/token
GOOGLE_AUTH_PROVIDER_X509_CERT_URL=https://www.googleapis.com/oauth2/v1/certs
GOOGLE_CLIENT_X509_CERT_URL=https://www.googleapis.com/robot/v1/metadata/x509/service_account%40project.iam.gserviceaccount.com
GOOGLE_UNIVERSE_DOMAIN=googleapis.com
```

**Security:**
- `.gitignore` excludes `aquila_graph.env` and `*.json`
- Verify credentials NOT committed: `git log --all --full-history -- aquila_graph.env`

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Google Sheets 403** | Verify service account has spreadsheet access; check credentials |
| **Supabase 403** | Use `service_role` key OR adjust RLS policies for `anon` key |
| **FRED API Error** | Verify API key at https://fred.stlouisfed.org/ |
| **Empty DataFrame** | Check query/API response; print `df.shape` and `df.head()` |
| **Date Parsing** | Use `pd.to_datetime(..., errors='coerce')` and check for NaTs |
| **Git Push Failed** | Check branch format: `claude/*-{sessionId}`; retry with backoff |
| **Chart No Data** | Verify date filters didn't remove all records |
| **Projection factor looks wrong** | Check that `date` column has 2025 records; fallback is `365/day_of_year` |
| **Submarket projection is 0** | Market may have no 2026 YTD data; chart still renders historical bars |
| **`titlefont` ValueError (Plotly)** | Use `title=dict(text=..., font=dict(...))` syntax instead |
| **Dash `app.run_server` error** | Obsolete in Dash 2.x — use `app.run()` instead |
| **Dash axis `font` ValueError** | Use `tickfont=dict(...)` inside `xaxis`/`yaxis`, not `font=dict(...)` |
| **Stray date at end of chart** | Outer merge creates orphaned NaN rows — filter `df_plot[df_plot['sort_order_current'].notna()]` |
| **Prior year month missing** | Data was filtered by date before aggregation — aggregate ALL data first, split into periods after |
| **Unicode error on Windows (print)** | CP1252 encoding can't print `✓` — use plain ASCII in `print()` statements |

---

## DO's and DON'Ts

### ✓ DO:
- Use Aquila brand colors/fonts (`AQUILA_COLORS`, `AQUILA_FONT`)
- Export charts to categorized subdirectories (`charts/category/`)
- Update README.md with format: `[Name [YYYY-MM-DD]](url)`
- Use descriptive commit messages
- Handle date/numeric parsing errors (`errors='coerce'`)
- Check DataFrame not empty before charting
- Test chart renders before committing

### ✗ DON'T:
- Commit credentials (`aquila_graph.env`, `*.json`)
- Use random colors (always `AQUILA_COLORS`)
- Skip README.md updates
- Create generic filenames (`chart1.html`)
- Hardcode credentials in notebooks
- Push to main directly (use feature branches)
- Include PII in published charts

---

## Quick Reference

**Chart Categories:**
```
property-management/ → AMS KPIs
office/              → Requirements, transactions, market metrics
industrial/          → TITM demand, vacancy, market metrics
economic-indicators/ → Employment, wages, housing, financial
```

**Data Sources:**
```
Supabase:       PostgreSQL market data
Google Sheets:  Office requirements (1bzpRnUrpBH6l_zX7DtTypczZf5bpYVwqPUG3tzg2vec)
Google Sheets:  Industrial TITM (1natA0ALaQnX3U_vGC5Vrchy1QqmbW8k0zvTKwuE2wys)
FRED API:       Economic indicators
Excel:          AMS data, Transaction forms
```

**Public URLs:**
```
Repository: https://github.com/realdatallc/aquila-insights
Pages:      https://realdatallc.github.io/aquila-insights/
Charts:     https://realdatallc.github.io/aquila-insights/charts/{category}/{filename}.html
```

---

**Last Updated:** 2026-02-19
**Document Version:** 2.3.0

---

## Changelog

### Version 2.3.0 (2026-02-19)
- Added `create_industrial_nnn_rent_chart.py` — Industrial NNN Rental Rates line chart
  - Submarkets: Northeast, Southeast, Williamson County; property type: Industrial
  - Date range: 2022 Q1 → configurable `END_QUARTER` constant
  - Output: `charts/industrial/industrial_nnn_rent_by_submarket.html`
- Updated industrial chart count: 8 → 9
- Renumbered data source sections 4–8 to 5–9 to accommodate new section

### Version 2.2.0 (2026-02-19)
- Added `dashboards/` directory and Office Requirements Dashboard documentation
- Dashboard features: submarket/industry/size filters, date range picker, metric cards, YoY comparison, 3-month rolling avg, data table, CSV export
- Documented key architecture decisions: no date filtering on global data, rolling avg computed before period split, outer merge orphan filter
- Added dashboard-specific troubleshooting entries (Dash API changes, stray dates, missing prior year data, Windows Unicode)
- Added "Interactive Dashboards (Local)" section with run instructions and known gotchas

### Version 2.1.0 (2026-02-19)
- Added 2026 annualized projection to `requirements_demand_by_tenant_size.html` (main demand chart)
  - Chart changed from quarterly to **annual** aggregation (years on x-axis)
  - Current-year bar shows projected full-year demand; historical bars unchanged
  - Projection: `ytd_2026 × (full_2025 / ytd_2025_same_period)`, distributed by 2025 size mix
  - Visual: 45% opacity + diagonal hatch for projected bar; dashed connector + open-circle marker on total line
  - Subtitle caption shows pace factor and as-of date dynamically
- Applied identical projection logic to all 5 submarket charts (`create_office_demand_by_market.py`)
  - Global pace factor from all-market 2025 vs 2026 YTD applied per submarket
  - Market-specific size distribution from 2025 annual mix (falls back to YTD 2026 mix)
- `calculate_2026_annual_projection()` helper function embedded in `update_office_combined_requirements.py`

### Version 2.0.0 (2026-02-10)
- **MAJOR:** Condensed from 2869 to 587 lines (80% reduction)
- **BREAKING:** Renamed files for clarity:
  - `googlesheets_combined.ipynb` → `office_requirements_combined.ipynb`
  - `SQL.ipynb` → `industrial_vacancy_supabase.ipynb`
  - `update_combined_requirements_charts.py` → `update_office_combined_requirements.py`
  - `update_supabase_charts.py` → `update_industrial_vacancy.py`
  - `update_fred_charts.py` → `update_fred_housing_chart.py`
  - `create_demand_by_tenant_size_by_market.py` → `create_office_demand_by_market.py`
  - `create_transaction_form_chart.py` → `create_office_transaction_charts.py`
  - `update_google_sheets_charts.py` → `DEPRECATED_update_office_requirements.py`
- Removed detailed duplicate documentation for deprecated single-tab Google Sheets charts
- Consolidated repetitive chart generation patterns
- Merged similar data processing sections
- Updated all script references to new names
- Organized by data source with clear input/output mapping

### Version 1.4.0 (2026-02-09)
- Added Industrial Demand charts from TITM Google Sheet
- Industrial-scaled size bins documented

### Version 1.3.0 (2026-01-30)
- Added Office Demand by Tenant Size chart

### Version 1.2.0 (2026-01-23)
- Updated Aquila brand color palette (2026 rebrand)

### Version 1.1.0 (2026-01-23)
- Added FRED economic indicators notebook & script
- Reorganized charts into categorized subdirectories

### Version 1.0.0 (2026-01-15)
- Initial comprehensive documentation
