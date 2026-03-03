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
- PDF Reports: `jinja2`, `weasyprint`, `kaleido`
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
aquila-insights/
├── aquila/                          # Shared Python package
│   ├── __init__.py                  #   Re-exports AQUILA_COLORS, AQUILA_FONT
│   ├── brand.py                     #   13-color palette, AQUILA_FONT, named aliases
│   ├── charts.py                    #   aquila_styled_line_chart()
│   ├── dateutil.py                  #   parse_quarter(), quarter_sort_key()
│   ├── git.py                       #   commit_and_push_all()
│   └── connectors/                  #   Data source clients (auto-loads aquila_graph.env)
│       ├── __init__.py
│       ├── supabase.py              #     get_supabase_client(use_service_role=True)
│       ├── gsheets.py               #     get_gsheets_client()
│       └── fred.py                  #     fetch_fred_series()
│
├── generators/                      # Chart generators (organized by domain)
│   ├── __init__.py                  #   Adds repo root to sys.path
│   ├── office/                      #   5 generators -> 29 charts
│   │   ├── requirements.py          #     7 requirement charts (Google Sheets)
│   │   ├── demand_by_market.py      #     5 submarket demand charts (Google Sheets)
│   │   ├── transactions.py          #     2 transaction charts (Excel)
│   │   ├── market_metrics.py        #     12 vacancy/rent/opex charts (Supabase)
│   │   └── building_performance.py  #     4 occupancy/rent by size (Supabase)
│   ├── industrial/                  #   3 generators -> 9 charts
│   │   ├── vacancy.py               #     1 vacancy chart (Supabase)
│   │   ├── demand.py                #     5 TITM demand charts (Google Sheets)
│   │   └── nnn_rent.py              #     1 NNN rent chart (Supabase)
│   ├── economic/                    #   3 generators -> 14 charts
│   │   ├── fred_indicators.py       #     7 FRED indicator charts
│   │   ├── fred_housing.py          #     1 housing starts chart
│   │   └── austin_economy.py        #     6 Austin 2025 economy charts (Excel)
│   ├── property_mgmt/               #   1 generator -> 1 chart
│   │   └── ams_kpi.py               #     AMS managed properties KPI (Excel)
│   └── development/                 #   1 generator -> 6 charts
│       └── permits.py               #     Development pipeline charts (API)
│
├── charts/                          # Published HTML charts (GitHub Pages)
│   ├── property-management/         # 1 chart: AMS KPIs
│   ├── office/                      # 29 charts: Requirements, transactions, market metrics
│   ├── industrial/                  # 9 charts: TITM demand, vacancy, NNN rent
│   ├── economic-indicators/         # 14 charts: Employment, wages, housing, Austin economy
│   └── development/                 # 6 charts: Pipeline, permitting
│
├── reports/                         # Quarterly Report generators (PDF)
│   ├── office/{YEAR}_{QN}/          # Office output per quarter
│   ├── industrial/{YEAR}_{QN}/      # Industrial output per quarter
│   ├── templates/                   # Jinja2 HTML page templates (14 office + 9 industrial)
│   ├── static/                      # CSS: report.css, tables.css
│   ├── generate_office_report.py    # Office report orchestrator (CLI)
│   ├── generate_industrial_report.py# Industrial report orchestrator (CLI)
│   ├── cleanup_quarterly_data.py    # Pre-report data cleanup
│   ├── data_loader.py              # Office: Supabase + Excel -> DataFrames
│   ├── industrial_data_loader.py   # Industrial: Supabase + Excel -> DataFrames
│   ├── chart_builder.py            # Office: Plotly -> PNG via Kaleido
│   ├── industrial_chart_builder.py # Industrial: Plotly -> PNG via Kaleido
│   ├── report_assembler.py         # Office: Jinja2 render + WeasyPrint -> PDF
│   └── industrial_report_assembler.py # Industrial: Jinja2 render + WeasyPrint -> PDF
│
├── dashboards/                      # Interactive Dash apps (local, not published)
│   ├── office_requirements_dashboard.py
│   └── requirements.txt
│
├── data/                            # Input data files (Excel, CSV)
├── notebooks/                       # Jupyter development notebooks
├── archive/                         # Deprecated/test scripts
│
├── update_all_charts.py             # Master orchestrator (runs all generators)
├── aquila_graphing_tools.py         # Backward-compat shim (imports from aquila/)
├── aquila_graph.env                 # CREDENTIALS (gitignored)
├── .gitignore
├── README.md                        # Public chart index
└── CLAUDE.md                        # This file
```

---

## Key Files & Functions

### aquila/ Package

The `aquila/` package consolidates shared utilities. All generators and reports import from here.

```python
# Brand constants
from aquila.brand import AQUILA_COLORS, AQUILA_FONT, NAVY, GLASS_BLUE, COPPER, BRASS

# Data connectors (auto-loads aquila_graph.env)
from aquila.connectors.supabase import get_supabase_client
from aquila.connectors.gsheets import get_gsheets_client
from aquila.connectors.fred import fetch_fred_series

# Utilities
from aquila.dateutil import parse_quarter, quarter_sort_key
from aquila.charts import aquila_styled_line_chart
from aquila.git import commit_and_push_all
```

### aquila_graphing_tools.py (Backward-Compat Shim)

Re-exports from `aquila/` package. Existing code using old imports continues to work:
```python
# These still work via the shim:
from aquila_graphing_tools import AQUILA_COLORS, AQUILA_FONT
from aquila_graphing_tools import initialize_supabase_connection
from aquila_graphing_tools import aquila_styled_line_chart, commit_and_push_all
```

**Brand Colors (2026 Palette):**
```python
AQUILA_COLORS = [
    "#172344",  # [0]  AQUILA Navy (primary)
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
```

**Color Usage Guidelines:**
- All chart titles must be **centered** (`x=0.5, xanchor='center'` in title dict, or `title_x=0.5, title_xanchor='center'` in layout)
- Use colors in **hierarchy order** for categorical series (index [0] first, [1] second, etc.)
- Named aliases for common colors: Navy=[0], Glass=[1], GlassAlt=[2], Concrete=[3], Copper=[4], Brass=[5], Greenspace=[6], MopacGray=[7], Pennybacker=[8], TexasSun=[9], Zilker=[10], Signal=[11], SoCo=[12]
- On Windows (CP1252 shell), use `PYTHONUTF8=1 python script.py` or replace Unicode chars (✓, →, ⚠) with ASCII equivalents ([OK], ->, [WARN]) in print statements

**Font:** `AQUILA_FONT = "Futura LT Pro, Futura, Arial, sans-serif"`

---

## Data Sources & Chart Outputs

### 1. Office Requirements (Google Sheets)

**Notebook:** `notebooks/office_requirements_combined.ipynb`
**Script:** `generators/office/requirements.py`

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

**Notebook:** `notebooks/industrial_vacancy_supabase.ipynb`
**Script:** `generators/industrial/vacancy.py`

**Data Source:** Supabase table `market_tables_industrial`

**Outputs (1 chart):**
```
charts/industrial/
└── vacancy_rate_industrial.html
```

---

### 3. Industrial Demand (Google Sheets TITM)

**Script:** `generators/industrial/demand.py`

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

**Script:** `generators/industrial/nnn_rent.py`

**Data Source:** Supabase table `market_tables_industrial`

**Filters:** `property_type = 'Industrial'`, submarkets: Northeast, Southeast, Williamson County

**Date Range:** 2022 Q1 → configurable `END_QUARTER` constant (update as new quarters arrive)

**Outputs (1 chart):**
```
charts/industrial/
└── industrial_nnn_rent_by_submarket.html
```

**Colors:** Navy (Northeast), Glass Blue (Southeast), Copper (Williamson County)

---

### 5. Building Performance (Supabase)

**Notebook:** `notebooks/building-performance-by-size.ipynb`
**Script:** `generators/office/building_performance.py`

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

**Notebook:** `notebooks/fred-economic-indicators.ipynb`
**Scripts:**
- `generators/economic/fred_housing.py` (1 chart)
- `generators/economic/fred_indicators.py` (7 charts)

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

### 7. Austin Economy — Relocations & Expansions (Excel)

**Script:** `generators/economic/austin_economy.py`

**Data Source:** `data/Industries and Companies 2025.xlsx`
- Sheet `"2025"`: 71 rows — Company, Type of Operation, Jobs Created, Location, Type of Action (New/Expanded), Month, Industry, HQ?
- Sheet `"2024"`: 72 rows — prior-year comparison (no Industry/HQ? columns)

**Outputs (6 charts):**
```
charts/economic-indicators/
├── austin_2025_jobs_by_industry.html       # Jobs by industry (horizontal bar, 10 categories, distinct colors)
├── austin_2025_new_vs_expanded.html        # New relocations vs. expansions by industry (stacked bar)
├── austin_2025_jobs_by_location.html       # Top 10 cities by jobs (horizontal bar)
├── austin_2025_hq_activity.html            # HQ vs. branch/production total jobs (pie chart, 2 slices)
├── austin_2025_jobs_by_month.html          # Monthly job announcements Jan–Dec (line chart with markers)
└── austin_2025_top_companies.html          # Top 10 companies (Plotly table: Company, Jobs, Industry, Location)
```

**Key Stats (2025):** 10,621 total jobs · 10 industries · 71 companies · 62% new operations · 41 HQ designations

---

### 8. Property Management (Excel)

**Script:** `generators/property_mgmt/ams_kpi.py`

**Data Source:** `data/AMS- Property Split List (Updated 1.9.26).xlsx`

**Outputs (1 chart):**
```
charts/property-management/
└── ams_managed_properties_kpi.html
```

**Metrics:** Total SF & building count by property type (dual bar chart)

---

### 9. Office Transactions (Excel)

**Script:** `generators/office/transactions.py`

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

### 10. Office Demand by Market (Google Sheets)

**Script:** `generators/office/demand_by_market.py`

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

### 11. Office Market Metrics Charts (Supabase)

**Script:** `generators/office/market_metrics.py`

**Data Source:** Supabase table `market_tables_office`

**Filters:**
- CBD, Northwest, Southwest: `table_type = "competitive set"`
- The Domain: `table_type = "micromarket"` (Domain is a micromarket subdivision of Northwest)

**Date Range:** All available history (2018 Q1 → current quarter)

**Outputs (12 charts):**
```
charts/office/
├── office_vacancy_rate_cbd.html         # Vacancy rate % over time (line chart)
├── office_vacancy_rate_northwest.html
├── office_vacancy_rate_southwest.html
├── office_vacancy_rate_domain.html
├── office_rental_rate_cbd.html          # Base Rent + Opex stacked bar
├── office_rental_rate_northwest.html
├── office_rental_rate_southwest.html
├── office_rental_rate_domain.html
├── office_opex_cbd.html                 # Operating expenses $/SF/yr (line chart)
├── office_opex_northwest.html
├── office_opex_southwest.html
└── office_opex_domain.html
```

**Chart types:**
- Vacancy Rate: line chart, `total_vacancy_rate` as %, no markers
- Rental Rate: stacked bar — Base Rent (Navy, bottom) + Opex (Glass Blue, top)
- Operating Expenses: line chart, `average_opex` in $/SF/yr, no markers

**Colors (vacancy/opex line charts):** CBD=Navy, Northwest=Glass Blue, Southwest=Glass Blue Alt, The Domain=Concrete

**Supabase auth:** Uses `aquila.connectors.supabase.get_supabase_client(use_service_role=True)` — the anon key lacks RLS access to `market_tables_office`.

---

### 12. Office Quarterly Report (PDF Generator)

**Directory:** `reports/`
**Entry point:** `reports/generate_office_report.py`

Programmatically recreates the AQUILA Office Quarterly Report (previously a 56-page PDF built manually in InDesign). Uses Plotly for charts, Jinja2 HTML templates for layout, and WeasyPrint for HTML-to-PDF conversion.

**Data Sources:**
- **Primary:** Supabase `market_tables_office` (544 rows, 32 quarters, 13 micromarkets x 3 table types)
- **Secondary:** Excel/CSV files on `Q:\0-Quarterly Reports\0-Office\{YEAR} Q{N}\`
  - `Major Leases and Sales {YEAR} {Q}Q.xlsx` — Leases + Sales
  - `Office Avail.xlsx` — Large availability per submarket + subleases
  - `{Q}Q {YEAR} Building List.xlsx` — 18 regional building sheets
  - `Citywide Pipeline {YEAR} Q{Q}.xlsx` — Under construction + proposed (parsed into year/quarter groups)
  - `Availability Tables.xlsx` — Direct/sublease availability matrices
  - `Quarterly Changes [Q{N}]/` — CSV files: `NRA_Changes`, `Status_Changes`, `Vacancy_Changes`

**Key Architecture:**
- `report_config.py` — Single file to update per quarter (year, quarter, paths, submarket lists)
- `cleanup_quarterly_data.py` — Pre-report data cleanup; runs automatically as Step 0 of both `generate_office_report.py` and `generate_industrial_report.py`. Auto-detects report type (office vs industrial) from config module. Features: abbreviation standardization, Vertical Format tab creation, Major Leases sort/format/name-matching (via Supabase inventory), Major Sales portfolio consolidation, pipeline UC verification (warnings), Proposed sorting
- `data_loader.py` — Loads Supabase (service role key) + Excel into nested dict
- `chart_builder.py` — 3 dual-axis Plotly charts per performance page (vacancy SF, absorption, rental rates), exported as PNG via Kaleido
- `report_assembler.py` — Jinja2 template rendering + WeasyPrint PDF conversion
- **Citywide mapping:** Uses `table_type="overall"` (not "competitive set") in Supabase
- **Supabase auth:** Uses `SUPABASE_KEY` (service role, `sb_secret_*`) since `SUPABASE_PUBLIC_KEY` (anon JWT) lacks RLS access to `market_tables_office`

**Page Sequence (matches InDesign report order):**
1. Title page
2. Quarterly Changes (NRA, Status, Vacancy — from CSV files)
3. Citywide KPI + competitive set performance
4. Major Leases table
5. Major Sales mini-table cards
6. Development Pipeline — Under Construction (page 1) + Planned/Proposed (page 2)
7. Submarket sections (CBD, NW, SW, E): KPI header → competitive set → large availability
8. Micromarket performance pages (Domain, Shepherd Mountain, Near NW, Far NW, Near SW, Far SW)
9. Overall performance pages (CBD, NW, SW, E)
10. Sublease report (paginated at 30 rows/page)
11. Building lists (18 regional sheets)

**Run Commands:**
```bash
# Full PDF generation (cleanup + charts + PDF)
python reports/generate_office_report.py

# HTML-only preview (no WeasyPrint needed)
python reports/generate_office_report.py --html-only

# Reuse existing chart PNGs (faster iteration on CSS/layout)
python reports/generate_office_report.py --html-only --skip-charts

# Full PDF with existing charts
python reports/generate_office_report.py --skip-charts

# Skip the data cleanup step
python reports/generate_office_report.py --skip-cleanup

# Run cleanup standalone (preview changes without writing)
python reports/cleanup_quarterly_data.py --dry-run

# Run cleanup standalone (apply changes)
python reports/cleanup_quarterly_data.py
```

**Output:**
```
reports/office/{YEAR}_{QN}/
├── charts/                                    # 55 PNG chart images
├── AQUILA_Office_Report_{YEAR}_{QN}.html      # Intermediate HTML
└── AQUILA_Office_Report_{YEAR}_{QN}.pdf       # Final ~50-page report
```

**Templates (14 Jinja2 HTML files):**

| Template | Type | Instances | Data Source |
|----------|------|-----------|-------------|
| `page_title.html` | Cover | 1 | Config only |
| `page_toc.html` | Table of Contents (2-column + city photo) | 1 | Auto-generated from page_map |
| `page_quarterly_changes.html` | Tables (NRA/Status/Vacancy) | 1 | CSV files (`Quarterly Changes [QN]/`) |
| `page_kpi_header.html` | KPI header | 5 | Supabase (latest quarter) |
| `page_performance.html` | Table + 3 charts | 15 | Supabase (last 8 quarters) |
| `page_major_leases.html` | Table | 1 | Excel |
| `page_major_sales.html` | 2-column table grid of mini-cards | 1 | Excel |
| `page_pipeline.html` | Under Construction + Planned/Proposed | 2 | Excel (`Citywide Pipeline`) |
| `page_large_availability.html` | Table | 4 | Excel |
| `page_long_term_submarkets.html` | 2×3 chart grid (Of Submarkets) | 1 | Supabase (all quarters) |
| `page_long_term_cbd_suburban.html` | 2×2 chart grid (CBD vs Suburban) | 1 | Supabase (all quarters) |
| `page_sublease_report.html` | Table (paginated) | 2 | Excel |
| `page_building_list.html` | Table + totals | 18 | Excel |

**TOC Architecture:**
- Built via two-pass: all content pages rendered first to record anchor → page number mappings
- TOC inserts after title page (page 2), content starts at page 3
- Anchors: `citywide-performance`, `major-leases`, `development-pipeline`, `cbd-kpi`, `nw-kpi`, `sw-kpi`, `east-kpi`, `micromarket-performance`, `long-term-performance`, `overall-performance`, `sublease-report`
- Pipeline counts as 2 physical PDF pages in the page counter (`pdf_pages=2`)
- City photo: place `austin_skyline.jpg` in `reports/static/` to populate the TOC photo; falls back to gray placeholder
- TOC page number is suppressed via `@page toc-page` named rule

**Performance Charts (3 per page, 15 pages = 45 charts + 3 Citywide = 48 total):**
1. **Vacancy SF** — Stacked bar (Direct + Sublease Vacant) + line (Vacancy Rate %). Navy/Glass Blue bars, Copper line.
2. **Net Absorption** — Bar (Net Absorption) + line (Occupancy Rate). Navy bars, Brass line.
3. **Rental Rates** — Stacked bar (Base Rent + Opex) + line (Vacancy Rate %). Navy/Concrete bars, Copper line.

Charts 1 & 2 render side-by-side at 520x300px. Chart 3 renders at 520x300px in a half-width column with blank space for layout symmetry.

**Long-term Charts (2 pages, 10 charts total, placed after micromarket/before overall):**
- **Page 1 — Of Submarkets** (`page_long_term_submarkets.html`): 2×3 grid
  - Citywide vacant SF vs vacancy rate (overall table_type)
  - CBD, Northwest, Southwest vacant SF vs vacancy rate (competitive set)
  - Citywide Class A & B asking rates line chart
  - Citywide absorption & occupancy rate
- **Page 2 — CBD vs Suburban** (`page_long_term_cbd_suburban.html`): 2×2 grid
  - Average Class A asking rates: CBD (Navy) vs Suburban (Brass) lines
  - Vacant SF vs Vacancy Rate: CBD and Suburban stacked bars + combined vacancy rate line (Copper). Stack order (bottom→top): CBD Sublease (Glass Blue), CBD Direct (Navy), Suburban Sublease (Brass), Suburban Direct (Brass + hatch `/`)
  - Direct & Sublease Vacancy: fully stacked bars (`barmode='stack'`). Same color scheme as vacancy chart — CBD Sublease (Glass Blue), CBD Direct (Navy), Suburban Sublease (Brass), Suburban Direct (Brass + `/` hatch). Quarters aligned via `set_index`
  - SF Under Construction: stacked bars CBD (Navy) / Suburban (Brass) / East (Glass Blue)
  - **Suburban = NW + SW** competitive set combined (SF summed; rent/rate NRA-weighted average)
- **Absorption chart** uses `barmode='relative'` (not `'stack'`) to correctly handle negative absorption values below zero; CBD (Navy) / Northwest (Glass Blue) / Southwest (Brass) bars + Citywide occupancy rate line (Copper) on secondary y-axis
- **Citywide asking rates** chart shows two lines: Class A (Navy) and Class B (Brass)

**Dependencies (Windows):**
```bash
pip install weasyprint kaleido jinja2
# GTK3 runtime for WeasyPrint on Windows:
# Install MSYS2 → pacman -S mingw-w64-ucrt-x86_64-pango mingw-w64-ucrt-x86_64-gtk3
# Add C:\msys64\ucrt64\bin to PATH
```

**Quarterly Update Process:**
1. Update `reports/report_config.py` with new `REPORT_YEAR` and `REPORT_QUARTER` (all paths auto-derive)
2. Ensure all source files are in the expected `Q:` drive folder structure:
   - `Major Leases and Sales [Q{N}]/`
   - `Large Availabilities & Maps [Q{N}]/`
   - `Building Lists [Q{N}]/`
   - `Citywide Pipeline [Q{N}]/`
   - `Quarterly Changes [Q{N}]/` ← CSV exports: NRA_Changes, Status_Changes, Vacancy_Changes
3. Run `python reports/generate_office_report.py`
4. Compare output PDF against InDesign reference

---

### 13. Industrial Quarterly Report (PDF Generator)

**Directory:** `reports/`
**Entry point:** `reports/generate_industrial_report.py`

Programmatically recreates the AQUILA Industrial Quarterly Report (previously a ~52-page PDF built manually in InDesign). Parallel architecture to the office report but with industrial-specific data structures: dual property types (Industrial + Flex), different submarkets, and unique page types (regional comparison, generation-based large availabilities).

**Data Sources:**
- **Primary:** Supabase `market_tables_industrial` (keyed by `submarket_name` + `property_type`)
- **Secondary:** Excel/CSV files on `Q:\0-Quarterly Reports\0-Industrial\{YEAR} Q{N}\`
  - `Tables and Graphs [Q{N}]/Tables/{YEAR}Q{N}_submarket_tables_industrial.xlsx` — 18 sheets (8 submarkets × 2 types + Regional)
  - `Major Sales and Leases [Q{N}]/{YEAR} Q{N} Industrial Major Sales and Leases.xlsx` — Leases + Sales
  - `Large Availabilities [Q{N}]/{YEAR} Q{N} Large Availabilities.xlsx` — First Gen + Second Gen sheets
  - `Development Pipeline [Q{N}]/{YEAR} Q{N} Development Pipeline.xlsx` — Under Construction + Proposed
  - `Building Lists [Q{N}]/{N}Q {YEAR} - building_list_industrial.xlsx` — 16 sheets (8 submarkets × 2 types)
  - `Quarterly Changes [Q{N}]/` — CSV files: `Existing Supply NRA Changes`, `Status_Changes`, `Vacancy_Changes`

**Key Architecture:**
- `industrial_report_config.py` — Single file to update per quarter (year, quarter, paths, submarket lists)
- `industrial_data_loader.py` — Loads Supabase (primary) + Excel (fallback) into nested dict; includes `load_quarterly_changes()` for CSV data
- `industrial_chart_builder.py` — 3 performance charts per page (vacancy SF, absorption, rental) + regional comparison multi-line charts; imports shared primitives from `chart_builder.py`
- `industrial_report_assembler.py` — Jinja2 template rendering + WeasyPrint PDF conversion
- **Dual property types:** Every submarket generates 2 performance pages (Industrial + Flex)
- **Supabase keying:** Uses `(submarket_name, property_type)` — different from office's `(aquila_micromarket, table_type)`
- **No opex:** Industrial uses "Average Base Rent" (single bar), not office's "Full Service Rent" (Base + Opex stacked)

**Page Sequence (matches InDesign report order):**
1. Title page
2. Table of Contents (two-pass, computed page numbers)
3. By the Numbers (Industrial + Flex KPIs: Net Absorption, Avg Base Rent, Vacancy Rate, Market Size Change + Pipeline totals)
4. Quarterly Changes (NRA, Status, Vacancy — from CSV files)
5. Major Leases table
6. Major Sales card grid
7-8. Development Pipeline — Under Construction (page 1) + Planned/Proposed (page 2)
9. Large Availabilities — First Generation
10. Large Availabilities — Second Generation
11. Regional Overall — Industrial (performance table + 3 charts)
12. Regional Overall — Flex (performance table + 3 charts)
13-16. Regional Comparison (Vacancy Rate + Avg Rent × 2 property types)
17-30. Submarket sections (7 submarkets × 2 pages each: Industrial + Flex)
31-46. Building Lists (16 sheets: 8 submarkets × 2 types)

**Run Commands:**
```bash
# Full PDF generation (cleanup + charts + PDF)
python reports/generate_industrial_report.py

# HTML-only preview (no WeasyPrint needed)
python reports/generate_industrial_report.py --html-only

# Reuse existing chart PNGs (faster iteration on CSS/layout)
python reports/generate_industrial_report.py --html-only --skip-charts

# Full PDF with existing charts
python reports/generate_industrial_report.py --skip-charts

# Skip the data cleanup step
python reports/generate_industrial_report.py --skip-cleanup
```

**Output:**
```
reports/industrial/{YEAR}_{QN}/
├── charts/                                        # 52 PNG chart images
├── AQUILA_Industrial_Report_{YEAR}_{QN}.html      # Intermediate HTML
└── AQUILA_Industrial_Report_{YEAR}_{QN}.pdf       # Final ~45-page report
```

**Industrial-Specific Templates (9 Jinja2 HTML files):**

| Template | Type | Instances | Data Source |
|----------|------|-----------|-------------|
| `page_industrial_title.html` | Cover | 1 | Config only |
| `page_industrial_toc.html` | Table of Contents | 1 | Auto-generated from page_map |
| `page_industrial_kpi.html` | By the Numbers (Industrial + Flex + Pipeline) | 1 | Supabase (latest quarter) |
| `page_industrial_performance.html` | Table + 3 charts | 16 | Supabase (last 8 quarters) |
| `page_industrial_major_leases.html` | Table | 1 | Excel |
| `page_industrial_major_sales.html` | 2-column card grid with subtitle | 1 | Excel |
| `page_industrial_pipeline.html` | Under Construction + Planned/Proposed | 2 | Excel (named columns) |
| `page_industrial_large_avail.html` | Table by generation | 2 | Excel |
| `page_regional_comparison.html` | Cross-submarket table + multi-line chart | 4 | Supabase |

**Shared Templates (reused from office, read-only):**
- `base.html` — outer HTML shell
- `page_building_list.html` — building list table
- `page_quarterly_changes.html` — quarterly changes tables

**Performance Charts (3 per page, 52 total):**
1. **Vacancy SF** — Stacked bar (Direct + Sublease Vacant) + line (Vacancy Rate %). Navy/Glass Blue bars, Copper line.
2. **Net Absorption** — Bar (Net Absorption) + line (Occupancy Rate). Navy bars, Brass line.
3. **Average Base Rent** — Single bar (Base Rent) + line (Vacancy Rate %). Navy bar, Copper line. *(No opex stacking — differs from office)*

**Regional Comparison Charts (4 total):**
- Multi-line chart with one line per submarket (7 colored lines from AQUILA_COLORS)
- Last 8 quarters only
- 2 metrics (Vacancy Rate, Avg Base Rent) × 2 property types (Industrial, Flex)

**Chart Count Breakdown:**

| Category | Count |
|----------|-------|
| Regional Industrial: vacancy_sf + absorption + rental | 3 |
| Regional Flex: vacancy_sf + absorption + rental | 3 |
| 7 submarkets × Industrial × 3 charts | 21 |
| 7 submarkets × Flex × 3 charts | 21 |
| Regional Comparison (vacancy + rent) × 2 types | 4 |
| **Total** | **52** |

**Submarkets & Property Types:**
```python
# 7 submarkets for performance pages (Southwest excluded)
SUBMARKETS = ["East", "Hays County", "North Central", "Northeast",
              "South", "Southeast", "Williamson County"]

# 2 property types per submarket
PROPERTY_TYPES = ["Industrial", "Flex"]

# Building list: 8 submarkets × 2 types = 16 sheets (Southwest included)
BUILDING_LIST_SUBMARKETS = SUBMARKETS + ["Southwest"]
```

**By the Numbers KPI Page:**
- Two sections: Industrial KPIs (left) + Flex KPIs (right)
- Per section: Net Absorption, Avg Base Rent, Vacancy Rate, Market Size Change from Prior Quarter
- Market Size Change computed from NRA difference between last 2 quarters (`Regional_{type}`)
- Pipeline row below: Total Under Construction SF + Total Planned/Proposed SF
- Color arrows: green up for positive/improving, red down for negative/worsening

**Pipeline Data Ingestion:**
- Supports two spreadsheet formats (auto-detected):
  - **New format** (named columns): `Quarter Delivery`, `Name`, `Size (SF)`, `% Leased`, `Submarket`, `Property Type`
  - **Old format** (positional): Year/quarter embedded in data rows as header-like entries
- Detection: checks for `Quarter Delivery` column presence
- Proposed sheet: positional parsing (Name, Size, Submarket), skips header rows like "Future Developments"

**Large Availabilities:**
- Split by generation (First Gen / Second Gen) — different from office (which splits by submarket)
- Columns: `property_name`, `Property Address`, `Total Available Space (SF)`, `submarket_name`
- Column name fallback chain handles variations across quarters

**Quarterly Update Process:**
1. Update `reports/industrial_report_config.py` with new `REPORT_YEAR` and `REPORT_QUARTER` (all paths auto-derive)
2. Ensure all source files are in the expected `Q:` drive folder structure:
   - `Tables and Graphs [Q{N}]/Tables/`
   - `Major Sales and Leases [Q{N}]/`
   - `Large Availabilities [Q{N}]/`
   - `Development Pipeline [Q{N}]/`
   - `Building Lists [Q{N}]/`
   - `Quarterly Changes [Q{N}]/` ← CSV exports with `[Q{N}]` suffix pattern
3. Run `python reports/generate_industrial_report.py`
4. Compare output PDF against InDesign reference

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

1. **Load environment** (handled automatically by `aquila.connectors`)
```python
# No manual load_dotenv needed — aquila connectors auto-load aquila_graph.env
```

2. **Fetch & process data**
```python
# Supabase (preferred: aquila connector)
from aquila.connectors.supabase import get_supabase_client
supabase = get_supabase_client()  # or use_service_role=True for RLS-restricted tables
response = supabase.table('table_name').select('*').execute()
df = pd.DataFrame(response.data)

# Google Sheets
from aquila.connectors.gsheets import get_gsheets_client
client = get_gsheets_client()
sheet = client.open_by_key('sheet_id')
df = pd.DataFrame(sheet.get_worksheet(0).get_all_records())

# FRED API
from aquila.connectors.fred import fetch_fred_series
df = fetch_fred_series('SERIES_ID')
```

3. **Generate chart**
```python
from aquila.charts import aquila_styled_line_chart
from aquila.brand import AQUILA_COLORS, AQUILA_FONT
fig = aquila_styled_line_chart(df, x='date', y='value', color='category', title='Chart Title')

# Or custom chart
import plotly.express as px
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
from aquila.git import commit_and_push_all
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
python update_all_charts.py                    # Run all 13 generators (~59 charts)
python update_all_charts.py --group office     # Office generators only (29 charts)
python update_all_charts.py --group industrial # Industrial generators only (9 charts)
python update_all_charts.py --group economic   # Economic generators only (14 charts)
python update_all_charts.py --group property_mgmt
python update_all_charts.py --group development
```

**Runs 13 generators organized by domain:**

| Domain | Generator | Charts |
|--------|-----------|--------|
| office | `generators/office/requirements.py` | 7 (Google Sheets) |
| office | `generators/office/building_performance.py` | 4 (Supabase) |
| office | `generators/office/market_metrics.py` | 12 (Supabase) |
| office | `generators/office/demand_by_market.py` | 5 (Google Sheets) |
| office | `generators/office/transactions.py` | 2 (Excel) |
| industrial | `generators/industrial/vacancy.py` | 1 (Supabase) |
| industrial | `generators/industrial/demand.py` | 5 (Google Sheets) |
| industrial | `generators/industrial/nnn_rent.py` | 1 (Supabase) |
| economic | `generators/economic/fred_indicators.py` | 7 (FRED API) |
| economic | `generators/economic/fred_housing.py` | 1 (FRED API) |
| economic | `generators/economic/austin_economy.py` | 6 (Excel) |
| property_mgmt | `generators/property_mgmt/ams_kpi.py` | 1 (Excel) |
| development | `generators/development/permits.py` | 6 (API) |

### Individual Generators
```bash
python -m generators.office.requirements
python -m generators.office.market_metrics
python -m generators.industrial.vacancy
python -m generators.industrial.demand
python -m generators.economic.fred_indicators
python -m generators.economic.austin_economy
python -m generators.property_mgmt.ams_kpi
python -m generators.development.permits
```

### Office Quarterly Report
```bash
python reports/generate_office_report.py                            # Cleanup + full PDF
python reports/generate_office_report.py --html-only                # Browser preview
python reports/generate_office_report.py --html-only --skip-charts  # Fast CSS iteration
python reports/generate_office_report.py --skip-cleanup             # Skip data cleanup step
python reports/cleanup_quarterly_data.py --dry-run                  # Preview cleanup changes
python reports/cleanup_quarterly_data.py                            # Run cleanup standalone
```

### Industrial Quarterly Report
```bash
python reports/generate_industrial_report.py                            # Cleanup + full PDF
python reports/generate_industrial_report.py --html-only                # Browser preview
python reports/generate_industrial_report.py --html-only --skip-charts  # Fast CSS iteration
python reports/generate_industrial_report.py --skip-charts              # Full PDF, reuse chart PNGs
python reports/generate_industrial_report.py --skip-cleanup             # Skip data cleanup step
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
| **WeasyPrint DLL error** | `OSError: cannot load library 'libgobject-2.0-0'` — install GTK3 via MSYS2: `pacman -S mingw-w64-ucrt-x86_64-gtk3` and add `C:\msys64\ucrt64\bin` to PATH |
| **Supabase empty for report** | `market_tables_office` returns empty with anon key — `data_loader.py` uses `SUPABASE_KEY` (service role) not `SUPABASE_PUBLIC_KEY` |
| **Citywide data missing** | Citywide uses `table_type="overall"` in Supabase, not `"competitive set"` — `get_kpi_data()` auto-detects |
| **--skip-charts not finding PNGs** | Chart filenames are lowercased but keys are title-case — `_find_existing_charts()` handles the mapping |
| **PDF write PermissionError** | PDF is open in a viewer — close it first, or WeasyPrint cannot overwrite it |
| **Quarterly Changes dir not found** | Folder must be named `Quarterly Changes [Q{N}]` exactly; check `QUARTERLY_CHANGES_DIR` in config |
| **Pipeline UC groups empty** | `Under Construction` sheet uses merged year/quarter header rows — parser expects `2025`/`4Q` pattern |
| **Proposed rows missing** | `Proposed` sheet row 0 is an embedded header (`Future Developments`) — loader skips it automatically |
| **Major Sales gap between title and cards** | WeasyPrint ignores `page-break-before: avoid` on flex containers — use a real `<table>` layout (`.sales-table-grid`) so content flows inline; header+divider sit directly above cards |
| **Major Sales/Leases blank trailing page** | `page-break-after: avoid` on the table pushes it to a new page — remove the rule; use `margin-top` instead |
| **Pipeline Planned/Proposed columns colliding** | Side-by-side two-table flex layout breaks in WeasyPrint — use a single full-width `<table class="proposed-table">` with `table-layout: fixed` column widths (55%/18%/27%) that overflows naturally to the next page |
| **Pipeline proposed content not breaking to next page** | `.pipeline-page.proposed-page` needs `page-break-after: always` — setting it to `auto` prevents the break after the CBD section |
| **NRA Changes title shows wrong label** | `_clean_title()` in `data_loader.py` uses override map; ensure CSV is named `NRA_Changes*.csv` |
| **Property ID has commas (e.g. 12,345)** | `_render_quarterly_changes()` detects columns matching `\bid\b` and skips comma formatting |
| **Abbreviation over-expanded (e.g. "Bldg. E." instead of "Bldg. E")** | Single-letter cardinals use negative lookbehind `(?<!\.)` — letter preceded by `.` is never expanded |
| **Cleanup runs on wrong quarter's files** | `cleanup_quarterly_data.py` derives paths from `report_config.py` — update `REPORT_YEAR`/`REPORT_QUARTER` first |
| **Vertical Format tab missing after cleanup** | Tab is created only if `Major Sales` sheet exists and `Vertical Format` tab is absent; check workbook sheet names |
| **Industrial Supabase empty** | `market_tables_industrial` uses same auth as office — ensure `SUPABASE_KEY` (service role) is set in `aquila_graph.env` |
| **Industrial pipeline named columns not detected** | Auto-detects `Quarter Delivery` column; if spreadsheet reverts to old format, the old positional parser is used as fallback |
| **Industrial large avail shows 0 SF** | Column name must be `Total Available Space (SF)` — fallback chain tries `Available SF`, `Available (SF)`, `available_sf` |
| **Industrial major sales missing buyer/seller** | Excel columns are `Buyer (True) Company` and `Seller (True) Company` — fallback tries `Buyer`/`Seller` |
| **Industrial KPI NRA change is 0** | Requires at least 2 quarters of data in `Regional_{type}` — check Supabase has consecutive quarter rows |
| **Industrial regional comparison too many quarters** | `build_regional_comparison_chart()` takes `n_quarters=8` parameter; table also limits to last 8 via `all_quarters[-8:]` |
| **Industrial quarterly changes CSV not found** | Industrial CSVs use `[Q{N}]` suffix pattern (e.g. `Existing Supply NRA Changes [Q4].csv`), different from office naming |
| **Cleanup AttributeError on industrial config** | Industrial config uses `cfg.PIPELINE` / `cfg.LARGE_AVAIL` not `cfg.CITYWIDE_PIPELINE` / `cfg.OFFICE_AVAIL` — `_get_files_to_process()` auto-detects report type |
| **Cleanup Supabase connection fails** | Inventory loading is optional — building name matching and pipeline verification are skipped with a warning; abbreviation standardization continues |
| **Major Leases not sorted after cleanup** | `Major Leases` sheet must exist in the workbook; SF column detected via fallback chain (`SF Leased` → `Size (SF)` → `Size` → `Square Feet`) |
| **Major Sales not consolidated** | Buyer/Seller columns detected case-insensitively; grouping is by normalized (lowercased, stripped) buyer+seller names |
| **Pipeline verification shows false warnings** | Building name matching uses normalized comparison (lowercase, strip punctuation) — check if the building name in Excel differs significantly from Supabase `property_name`/`building_park` |
| **Proposed not re-sorted** | Submarket/SF columns detected by keyword or positional fallback; header-like rows (`Future Developments`, etc.) are filtered before sorting |

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
Supabase:       PostgreSQL market data (market_tables_office, market_tables_industrial)
Google Sheets:  Office requirements (1bzpRnUrpBH6l_zX7DtTypczZf5bpYVwqPUG3tzg2vec)
Google Sheets:  Industrial TITM (1natA0ALaQnX3U_vGC5Vrchy1QqmbW8k0zvTKwuE2wys)
FRED API:       Economic indicators
Excel:          AMS data, Transaction forms, Quarterly report data (Q: drive)
```

**Public URLs:**
```
Repository: https://github.com/realdatallc/aquila-insights
Pages:      https://realdatallc.github.io/aquila-insights/
Charts:     https://realdatallc.github.io/aquila-insights/charts/{category}/{filename}.html
```

---

**Last Updated:** 2026-03-02
**Document Version:** 5.3.0

---

## Changelog

### Version 5.3.0 (2026-03-02)
- **Report layout and pagination improvements** (`reports/static/report.css`, `reports/report_assembler.py`, `reports/templates/`):
  - **TOC disclaimer pushed to bottom** (`report.css`, `.toc-disclaimer`): Changed `margin-top: 20px` → `margin-top: auto` so the disclaimer text sits at the very bottom of the TOC page in PDF output (leverages existing `flex-direction: column` on `.toc-page`)
  - **Major Sales column gap — clean white space** (`report.css`, `.sales-table-grid`): Replaced padding-based gap with `border-spacing: 40px 12px` on the grid table; added `border: none` on `.sales-row td.sale-cell` to eliminate any visible dividing line between the two card columns; negative margins (`margin-left/right: -20px`) keep the columns centered on the page
  - **Pipeline UC quarter row — white/navy style** (`report.css`, `.pipeline-quarter-header`): Changed from navy background + white text to white background + navy text (`background-color: white; color: var(--navy)`) with a subtle bottom border
  - **Multi-page chunking pagination for building lists** (`report_assembler.py`, `_render_building_list()`): Function now returns a `list` of HTML page strings instead of a single string; rows chunked at 35 per page; each page receives a `page_label` of `(Page X of Y)` when total pages > 1; totals row (`<tfoot>`) appears only on the last page
  - **Multi-page chunking pagination for large availabilities** (`report_assembler.py`, `_render_large_availability()`): Same pattern as building lists — returns list of pages, 35 rows/page, `(Page X of Y)` label
  - **`page_label` support in templates** (`page_building_list.html`, `page_large_availability.html`): `BUILDING LIST` / `LARGE AVAILABILITIES` sub-label now appends `{{ page_label }}` (e.g. `BUILDING LIST (Page 1 of 2)`)
  - **`build_page_sequence()` updated** (`report_assembler.py`): Iterates over paginated lists for large availability and building list sections; pipeline still uses `(uc_html, prop_html)` tuple pattern from v5.2.0
  - **New pipeline templates** (`reports/templates/`):
    - `page_pipeline_uc.html` — Under Construction only (Page 1 of 2); retains `id="development-pipeline"` anchor for TOC
    - `page_pipeline_proposed.html` — Planned/Proposed only (Page 2 of 2); standalone `.pipeline-page` class

### Version 5.2.0 (2026-03-02)
- **Report layout and style fixes** (`reports/static/report.css`, `reports/static/tables.css`, `reports/report_assembler.py`, `reports/templates/`):
  - **TOC heading style** (`report.css`, `.toc-heading`): Font weight changed 400→300 (Futura Light), font family explicitly set to `'Futura LT', 'Futura Light', 'Futura', 'Arial', sans-serif`, color changed from Copper (`var(--copper)`) to Navy (`var(--navy)`)
  - **TOC rule color** (`report.css`, `.toc-rule`): Horizontal rule below TOC heading changed from Brass to Glass Blue (`var(--glass-blue)`)
  - **Major Sales column gap** (`report.css`, `.sales-row td.sale-cell:last-child`): Added `padding-left: 20px` to the right card column for a visible white-space gap between the two sale card columns
  - **Second column left-alignment** (`tables.css`): Added `th/td:nth-child(2) { text-align: left }` rules to `.avail-table` (Large Availability) and `.sublease-table` (Sublease Report) so the property/building name column is left-aligned when column 1 is a row-number index
  - **Building list TOTAL suppression** (`report_assembler.py`, `_render_building_list()`): Totals row passed as `None` when `len(rows) > 35`, suppressing the TOTAL `<tfoot>` row on long building lists (e.g. CBD at 55 rows) that overflow to a second page
  - **Pipeline split into two page-counted sections** (`report_assembler.py`):
    - `_render_pipeline()` now returns `(uc_html, proposed_html)` tuple instead of a single combined string
    - `build_page_sequence()` unpacks the tuple and calls `_add()` twice (each section gets its own page counter increment for accurate TOC page numbers)
    - Removed `pdf_pages=2` workaround on the old single `_add()` call
  - **New pipeline templates** (`reports/templates/`):
    - `page_pipeline_uc.html` — Under Construction only (PAGE 1 of 2); retains `id="development-pipeline"` anchor for TOC
    - `page_pipeline_proposed.html` — Planned/Proposed only (PAGE 2 of 2); standalone `.pipeline-page` class
  - **Vacancy line color fix** (`reports/industrial_chart_builder.py`, `build_industrial_rental_chart()`): Vacancy Rate line changed from Copper to Glass Blue Alt (`GLASS_ALT = #88ABC8`) to match office chart color hierarchy; secondary y-axis range changed from `rangemode='nonnegative'` to `range=[0, None]`

### Version 5.1.0 (2026-03-02)
- **Report design improvements** across office and industrial quarterly report generators:
  - **Arrow icon assets** (`reports/static/arrows/`): New PNG icons for KPI direction indicators
    - `arrow_up.png` — Greenspace (#556B30) filled circle with white upward triangle (22×22 px)
    - `arrow_down.png` — Signal (#BF4040) filled circle with white downward triangle (22×22 px)
    - Generated via PIL at 2× scale (44px) then downsampled with LANCZOS for crisp rendering
  - **KPI template updates** (`page_kpi_header.html`, `page_industrial_kpi.html`): Replaced Unicode arrow spans (`&#9650;`/`&#9660;`) with conditional `<img>` tags using base64 data URIs; falls back to Unicode if PNGs not found
  - **Assembler updates** (`report_assembler.py`, `industrial_report_assembler.py`):
    - Added `_load_arrow_uris(static_dir)` helper: reads `arrows/arrow_up.png` and `arrows/arrow_down.png`, encodes as `data:image/png;base64,...` URIs
    - `_render_kpi_header()` and `_render_industrial_kpi()` now accept and pass `arrow_uris` dict to templates
    - Arrow URIs loaded once at start of `build_page_sequence()`
  - **CSS additions** (`report.css`):
    - `.kpi-arrow-img`: `width: 22px; height: 22px; vertical-align: middle; margin-right: 4px`
    - `.toc-entry`: `margin-bottom` increased for more vertical breathing room
    - `.toc-section-group`: increased `margin-top` and `margin-bottom`
    - `.toc-disclaimer`: `margin-top: auto` to push disclaimer to bottom of TOC flex column
    - `.section-divider`: `border-top` color changed from Navy to Glass Blue (`var(--glass-blue)`)
    - `.section-header h2`, `.lt-heading`: `font-weight` changed from 400 → 300 (Futura Light)
    - `.pipeline-blurb`: `max-width` changed from `45%` → `100%` (full page width)
    - `.page-of-label`: new class for "Page X of Y" sub-labels (7pt, letter-spaced, `var(--text-light)`)
  - **TOC layout** (`page_toc.html`, `page_industrial_toc.html`): Moved disclaimer `<div>` outside `.toc-body` to be a direct child of `.toc-page`, paired with `margin-top: auto` to push it to the bottom of the page
  - **Pipeline page headers** (`page_pipeline.html`, `page_industrial_pipeline.html`): Added `(Page 1 of 2)` / `(Page 2 of 2)` sub-labels below section h2 using `.page-of-label` class
  - **Vacancy/Absorption charts** (`chart_builder.py`): Added `fig.update_yaxes(rangemode='nonnegative', secondary_y=True)` to `build_vacancy_sf_chart()`, `build_long_term_vacancy_chart()`, `build_absorption_chart()`, `build_cbd_suburban_vacancy_chart()` — secondary y-axis (vacancy/occupancy rate %) now always starts at 0%
  - **Industrial rental chart** (`industrial_chart_builder.py`): Added same `rangemode='nonnegative'` to `build_industrial_rental_chart()` secondary y-axis
  - **Rental rate chart Opex color** (`chart_builder.py`, `build_rental_chart()`): Opex stacked bar changed from Concrete (`#AAA9A8`) to Glass Blue (`#C2DAF1`) for better brand hierarchy

### Version 5.0.0 (2026-02-27)
- **MAJOR: Repository architecture refactoring**
  - Created `aquila/` shared Python package consolidating all duplicated utilities:
    - `aquila/brand.py` — AQUILA_COLORS (13-color palette), AQUILA_FONT, named color aliases
    - `aquila/connectors/supabase.py` — `get_supabase_client(use_service_role=False)` with auto-env-loading
    - `aquila/connectors/gsheets.py` — `get_gsheets_client()` with auto-env-loading
    - `aquila/connectors/fred.py` — `fetch_fred_series()` with auto-env-loading
    - `aquila/dateutil.py` — `parse_quarter()`, `quarter_sort_key()`
    - `aquila/charts.py` — `aquila_styled_line_chart()`
    - `aquila/git.py` — `commit_and_push_all()`
  - Converted `aquila_graphing_tools.py` to backward-compat shim (re-exports from `aquila/`)
  - Moved 13 chart generators to `generators/` organized by domain:
    - `generators/office/` (5 generators, 29 charts)
    - `generators/industrial/` (3 generators, 9 charts)
    - `generators/economic/` (3 generators, 14 charts)
    - `generators/property_mgmt/` (1 generator, 1 chart)
    - `generators/development/` (1 generator, 6 charts)
  - Rewrote `update_all_charts.py` as direct-import orchestrator with `--group` flag
  - Migrated `reports/data_loader.py`, `reports/industrial_data_loader.py`, and `reports/cleanup_quarterly_data.py` to use `aquila.connectors.supabase` (eliminated 3 duplicate `_get_supabase_client()` copies)
  - Moved 6 notebooks to `notebooks/`, 7 deprecated scripts to `archive/`
  - Fixed `building_performance.py` output paths (`charts/` root -> `charts/{type}/`)
  - Fixed all Unicode chars (U+2192, U+2022, U+2500) for Windows CP1252 compatibility
  - All 13/13 generators verified passing end-to-end
  - Updated README.md and CLAUDE.md with new architecture documentation

### Version 4.4.0 (2026-02-26)
- **Brand color palette updated to 13-color 2026 hierarchy** (`aquila_graphing_tools.py`)
  - Added **Glass Blue Alt** (#88ABC8) at index [2] — new color between Glass Blue and Concrete
  - Reordered: Concrete moved from [5]→[3], Copper [2]→[4], Brass [3]→[5], Greenspace [4]→[6], Mopac Gray [10]→[7], Pennybacker [7]→[8], Texas Sun [8]→[9] (hex #FFDB99→#FFD899), Zilker [9]→[10], Signal [6]→[11], SoCo [11]→[12]
  - All chart scripts updated to use correct new color indices for named aliases
- **All chart titles centered** — `aquila_styled_line_chart` now sets `title_x=0.5, title_xanchor='center'` globally; all custom `update_layout` title dicts also updated with `'x': 0.5, 'xanchor': 'center'`
- **Austin 2025 chart updates** (`create_austin_2025_charts.py`):
  - Jobs by Industry: colors now follow hierarchy order [0]–[9] sequentially
  - New Relocations vs. Expansions: rewritten from stacked bar → **pie chart** (New Operations vs Expansions, Navy + Glass Blue)
  - Jobs by Location (Top 10): each bar now gets a distinct color cycling through the 13-color palette
  - HQ vs Branch/Production: colors changed from Copper/Navy → **Navy/Glass Blue** (indices [0] and [1])
- **Sequential category colors** applied to all size-range charts: Mega=[0], next=[1], next=[2], etc. (was using old non-sequential indices)
  - Scripts updated: `update_office_combined_requirements.py`, `create_office_demand_by_market.py`, `create_industrial_demand_charts.py`
- **Bug fixes** (pre-existing, discovered during run):
  - `create_industrial_demand_charts.py`: replaced deprecated `titlefont=` with `title=dict(text=..., font=dict(...))` for yaxis/yaxis2
  - `create_ams_kpi_chart.py`, `create_office_demand_by_market.py`: replaced Unicode `✓`, `→`, `⚠` with ASCII equivalents for Windows CP1252 compatibility
- **Windows run tip**: Use `PYTHONUTF8=1 python script.py` to avoid CP1252 encoding errors when scripts contain Unicode print chars

### Version 4.3.0 (2026-02-25)
- **New: Office Market Metrics Charts** (`create_office_market_metrics_charts.py`)
  - 12 standalone HTML charts for CBD, Northwest, Southwest, and The Domain (competitive set / micromarket)
  - 3 chart types per submarket: vacancy rate (line), rental rate (stacked bar: Base Rent + Opex), operating expenses (line)
  - Outputs: `charts/office/office_{vacancy_rate|rental_rate|opex}_{cbd|northwest|southwest|domain}.html`
  - Full history from 2018 Q1; quarterly update = re-run the script
  - Uses `SUPABASE_KEY` (service role) directly via local `_get_supabase_client()` — anon key lacks RLS access
  - Auto-commits and pushes on completion via `commit_and_push_all()`
- Fixed duplicate `### 8.` section numbering in CLAUDE.md; renumbered sections 9–13
- Updated office chart count in repo structure: 17 → 29

### Version 4.2.0 (2026-02-25)
- **New: Austin Economy charts** (`create_austin_2025_charts.py`)
  - 6 Plotly HTML charts supporting the article "The Industries and Companies That Came to Austin in 2025"
  - Data source: `data/Industries and Companies 2025.xlsx` (Austin Chamber relocations/expansions log; 71 companies, 10,621 jobs)
  - Chart types (final): jobs by industry (horizontal bar, 10 distinct colors) · new vs. expanded by industry (stacked bar) · jobs by location top 10 (horizontal bar) · HQ vs. branch/production (pie chart, 2 slices: Copper/Navy) · monthly jobs Jan–Dec (line chart with markers) · top 10 companies (Plotly table: Company, Jobs, Industry, Location)
  - Published to `charts/economic-indicators/austin_2025_*.html`
  - README: new `## Austin Economy` section added above `## Development & Permitting`
  - No external API dependencies — reads directly from Excel via `pandas.read_excel()`

### Version 4.0.0 (2026-02-24)
- **MAJOR: Added Industrial Quarterly Report PDF generator** (`reports/` directory)
  - Parallel architecture to office report: separate config, data loader, chart builder, assembler, and CLI orchestrator
  - 9 new Jinja2 templates: industrial title, TOC, KPI (By the Numbers), performance, major leases, major sales, pipeline, large availability, regional comparison
  - 52 Plotly charts: 3 dual-axis performance charts per page + 4 regional comparison multi-line charts
  - Data from Supabase `market_tables_industrial` (primary) + 6 Excel/CSV sources on Q: drive (fallback)
  - 7 submarkets × 2 property types (Industrial + Flex) = 14 performance pages + regional pages
  - First test: 2025 Q4 report (45 pages, 52 charts, 5.3 MB PDF)
- **New files (5 Python modules):**
  - `generate_industrial_report.py` — CLI entry point with `--html-only`, `--skip-charts`, `--skip-cleanup` flags
  - `industrial_report_config.py` — Quarter constants, data paths, submarket/property type ordering
  - `industrial_data_loader.py` — Supabase-first + Excel fallback data loading; includes `load_quarterly_changes()` for CSV files with `[Q{N}]` suffix pattern
  - `industrial_chart_builder.py` — `build_industrial_rental_chart()` (single bar, no opex), `build_regional_comparison_chart()` (multi-line, last 8 quarters), imports shared primitives from office `chart_builder.py`
  - `industrial_report_assembler.py` — All render functions + `build_page_sequence()` + two-pass TOC
- **New templates (9 Jinja2 HTML files):**
  - `page_industrial_title.html` — "INDUSTRIAL" letter-spaced cover
  - `page_industrial_toc.html` — Auto-generated TOC with computed page numbers
  - `page_industrial_kpi.html` — By the Numbers: Industrial (4 KPIs) + Flex (4 KPIs) + Pipeline totals; KPIs include Net Absorption, Avg Base Rent, Vacancy Rate, Market Size Change from Prior Quarter
  - `page_industrial_performance.html` — Table + 3 charts; "Average Base Rent" header (not "Full Service"); smaller title label, larger submarket name
  - `page_industrial_major_leases.html` — Columns: Tenant, Building, Submarket, Size (SF), Transaction Type
  - `page_industrial_major_sales.html` — Card grid with subtitle blurb; columns: Market, Size, Buyer, Seller
  - `page_industrial_pipeline.html` — Auto-detects new (named columns) vs old (positional) spreadsheet format; UC grouped by quarter + Proposed table
  - `page_industrial_large_avail.html` — Split by generation (First Gen / Second Gen); columns: Property Name, Address, Total Available Space (SF), Submarket
  - `page_regional_comparison.html` — Cross-submarket table (last 8 quarters) + multi-line chart (7 submarket lines)
- **Reuses from office (no modifications):** `base.html`, `page_building_list.html`, `page_quarterly_changes.html`, `report.css`, `tables.css`, shared chart primitives
- **Key differences from office report:**
  - Supabase keyed by `(submarket_name, property_type)` not `(aquila_micromarket, table_type)`
  - No opex data → single-bar rental chart instead of stacked (Base + Opex)
  - Large availabilities split by generation (1st/2nd Gen) not by submarket
  - Pipeline data ingestion supports dual format (named columns + positional fallback)
  - Market Size Change KPI computed from NRA delta between last 2 quarters
  - Pipeline totals (UC SF + Proposed SF) displayed on KPI page, not pipeline page
  - Industrial CSVs use `[Q{N}]` suffix pattern for quarterly changes
- Added industrial report automation commands to Automation section
- Added 8 new industrial-specific troubleshooting entries
- Updated repository structure to include all industrial report files

### Version 4.1.0 (2026-02-25)
- **Enhanced cleanup script** (`reports/cleanup_quarterly_data.py`) with 6 new data quality features for both office and industrial reports:
  - **Report type auto-detection:** `_detect_report_type()` checks config module attributes; `_get_files_to_process()` now handles both office (`cfg.OFFICE_AVAIL`, `cfg.CITYWIDE_PIPELINE`) and industrial (`cfg.LARGE_AVAIL`, `cfg.PIPELINE`) config paths via role-tagged file list
  - **Supabase inventory loading:** Connects to `inventory_office` or `inventory_industrial` at cleanup start for building name matching and pipeline verification; graceful degradation if Supabase unavailable
  - **Major Leases cleanup** (`_cleanup_major_leases`): sorts by SF ascending, formats SF with commas, matches building names against Supabase `report_name` (normalized string comparison on `property_name`/`building_park`)
  - **Major Sales consolidation** (`_cleanup_major_sales`): merges portfolio sales with same buyer+seller (case-insensitive); sums SF, joins building names, combines unique submarkets
  - **Pipeline UC verification** (`_verify_pipeline_buildings`): checks Under Construction buildings against Supabase inventory; prints warnings for missing buildings, `aquila_competitive_set=False`, or empty `report_name` — no data modification
  - **Proposed sorting** (`_sort_proposed`): sorts Planned/Proposed sheet by Submarket (A-Z) then SF (ascending); filters header-like rows before sorting
  - Shared helper `_rewrite_sheet()` for atomic sheet replacement (preserves other sheets in workbook at same index)
  - All new functions respect `--dry-run` flag
- **Sublease report sorting** (`reports/report_assembler.py`): `_render_sublease_report()` now sorts rows by sublease SF descending (largest first) before pagination
- **Header consistency verified:** All performance table templates already use "Sublease Vacant SF" consistently — no changes needed
- 7 new troubleshooting entries (industrial config AttributeError, Supabase connection, Major Leases sort, Major Sales consolidation, pipeline verification, Proposed sort)

### Version 3.5.0 (2026-02-24)
- **New: Pre-report data cleanup script** (`reports/cleanup_quarterly_data.py`)
  - Runs automatically as **Step 0** of `generate_office_report.py` (before data loading); skip with `--skip-cleanup`
  - **Abbreviation standardization:** applies period-correct street abbreviations (`Dr.`, `Blvd.`, `Pkwy.`, etc.) and cardinal directions (`N.`, `S.E.`, etc.) to address/name/tenant columns across all quarterly Excel and CSV files (Major Leases & Sales, Office Avail, Building List, Citywide Pipeline, Quarterly Changes CSVs)
  - Single-letter cardinals (`N`, `S`, `E`, `W`) use a **negative lookbehind** `(?<!\.)` so letters that already follow a period (e.g. `Bldg. E`) are never expanded to `Bldg. E.`
  - **Vertical Format tab:** if `Major Leases and Sales` workbook lacks a `Vertical Format` sheet, creates one from `Major Sales` (sorted by SF descending, vertical key-value layout per record)
  - `--dry-run` flag previews changes without writing any files
  - Can be run standalone: `python reports/cleanup_quarterly_data.py`
- **Quarterly Changes page fixes:**
  - **Title rename:** `NRA Changes` → **`Existing Supply NRA Changes`** via override map in `data_loader._clean_title()`
  - **Property ID formatting:** columns matching `\bid\b` (e.g. "Property ID") now render as plain integers — no comma insertion (e.g. `12345678` not `12,345,678`)
- Added `import re` to `report_assembler.py` (required for ID column detection)
- 5 new troubleshooting entries (NRA title, Property ID commas, abbreviation over-expansion, cleanup path, Vertical Format tab)

### Version 3.4.0 (2026-02-24)
- **New: Long-term performance pages** (placed after micromarket performance, before overall performance)
  - **Page 1 — Of Submarkets** (`page_long_term_submarkets.html`): 2×3 grid of 6 charts — Citywide/CBD/NW/SW vacant SF vs vacancy rate, Citywide Class A & B asking rates, Citywide absorption & occupancy rate
  - **Page 2 — CBD vs Suburban** (`page_long_term_cbd_suburban.html`): 2×2 grid of 4 charts — Class A asking rates (CBD vs Suburban lines), vacant SF vs vacancy rate (stacked bars + rate line), direct & sublease vacancy (fully stacked bars), SF under construction (stacked bars)
  - Suburban defined as NW + SW competitive set combined (SF columns summed; rent/rate columns NRA-weighted average); East shown separately on under construction chart
  - 4 new chart builder functions in `chart_builder.py`: `build_cbd_suburban_asking_chart`, `build_cbd_suburban_vacancy_chart`, `build_cbd_suburban_direct_sublease_chart`, `build_cbd_suburban_under_construction_chart`
  - `generate_long_term_charts()` updated to generate 10 charts total (was 6)
  - TOC entry added: "Long-Term Performance" anchor `long-term-performance`
  - Total charts: 55 (was 48); total pages: ~54 (adds 2 new pages)
  - Template count: 12 → 14
- **Chart refinements (iterative):**
  - **Citywide asking rates** (`build_long_term_asking_rates`): Added Class B rent line (Brass) alongside Class A (Navy); was single-line Class A only
  - **Citywide absorption** (`build_long_term_absorption`): Changed from single citywide bar to **submarket-stacked bars** (CBD=Navy, NW=Glass Blue, SW=Brass) using `barmode='relative'` (handles negative absorption); Citywide occupancy rate line (Copper) on secondary y-axis. Previously used single Navy bar.
  - **Direct & Sublease Vacancy** (`build_cbd_suburban_direct_sublease_chart`): Changed from grouped side-by-side to **fully stacked** `barmode='stack'`. Color scheme matched to vacant SF vs vacancy rate: CBD Sublease (Glass Blue), CBD Direct (Navy), Suburban Sublease (Brass), Suburban Direct (Brass + `/` hatch pattern). Quarters aligned via `set_index` union.

### Version 3.3.1 (2026-02-24)
- **TOC readability improvements** (`report.css`, `report_assembler.py`)
  - Switched TOC to single-column layout (removed two-column + photo placeholder)
  - Widened TOC body to 70% of page width so labels fit on one line (`white-space: nowrap`)
  - Increased entry margin to 10px and label padding-bottom to 8px for more breathing room between entries
  - Shortened appendix label: "Sublease Report, Direct & Sublease Availability" → "Sublease Report & Direct/Sublease Availability"
  - Removed "Long-Term Performance" appendix entry (no matching page in current report)

### Version 3.3.0 (2026-02-24)
- **New: Table of Contents page** (`page_toc.html`, updated `report_assembler.py`, `report.css`)
  - Inserted between title page and quarterly changes (page 2)
  - Two-column layout matching InDesign reference: left = Citywide Update + Submarket sections, right = city photo + Appendix
  - Each entry shows a copper page number + navy uppercase label, with a bottom-border rule per entry
  - City photo: place `austin_skyline.jpg` in `reports/static/` for the right-column photo; falls back to gray placeholder
  - Hyperlinks to section anchors using `<a href="#anchor-id">` — works in HTML preview and WeasyPrint PDF
  - **Two-pass build:** all content pages rendered first to compute accurate page numbers; TOC built last then inserted at position 2
  - `pdf_pages=2` parameter on pipeline `_add()` call accounts for its dual-page HTML generating 2 physical PDF pages
  - Page counter suppressed on TOC via `@page toc-page` named CSS rule
  - All 10 page templates updated with optional `id="{{ anchor_id }}"` attribute; `major-leases`, `major-sales`, `development-pipeline` anchors hard-coded in templates
  - Template count: 11 → 12
- Added TOC architecture notes to template documentation section

### Version 3.2.0 (2026-02-23)
- **Report layout fixes (all changes in `reports/` directory):**
  - **Chart fonts:** All chart text scaled to 1.5× original — base font `10→15`, legend/ticks/axis titles `8→12`; long-term chart overrides `7/6→10/9`
  - **Building list totals:** Moved totals row from separate `<table>` into `<tfoot>` of the main table so column widths align correctly; styled via `.totals-row` with navy top border
  - **Major Leases blank page:** Removed `page-break-after: avoid` on `.leases-table` (was paradoxically pushing table to next page); replaced with `margin-top: 16px`
  - **Major Sales layout:** Replaced flex-based `.sales-grid` with an HTML `<table class="sales-table-grid">` (2 cards per row via Jinja2 `batch(2)` filter); eliminates WeasyPrint gap between header/divider and cards
  - **Major Sales property names:** Styled as bold navy subheaders with navy bottom border (`11pt`, uppercase, `1.5px` border)
  - **Pipeline Planned/Proposed:** Replaced broken side-by-side two-table flex layout with a single full-width `<table class="proposed-table">` using `table-layout: fixed` (55%/18%/27% columns); overflows naturally to next page
  - **Pipeline→CBD page break:** Restored `page-break-after: always` on `.pipeline-page.proposed-page` so CBD always starts on a fresh page
- Added 4 new troubleshooting entries (Major Sales gap, blank trailing page, pipeline column collision, pipeline page break)

### Version 3.1.0 (2026-02-23)
- **Report layout improvements (all changes in `reports/` directory):**
  - Increased chart export scale from 2× to 3× (`CHART_SCALE = 3`) for higher pixel density across all 48 charts
  - All table columns now center-aligned (first column stays left); removed bold styling from last row globally
  - Added navy dividing line (`<hr class="section-divider">`) after section titles on Major Leases and Major Sales pages
  - Major Leases: fixed blank trailing page with `page-break-after: avoid` on the table element
  - Major Sales: reformatted from label/value div blocks into mini-tables per card (Market / Size / Buyer / Seller rows), matching InDesign style
- **New: Development Pipeline pages** (`page_pipeline.html`, updated `_render_pipeline()`)
  - Parses `Citywide Pipeline {YEAR} Q{N}.xlsx` → `Under Construction` sheet (year/quarter grouped) + `Proposed` sheet
  - Split into **two separate pages**: page 1 = Under Construction, page 2 = Planned/Proposed (two-column table)
  - Under Construction: year large-gray header + quarter navy sub-header + Name/Size/% Leased/Submarket table
  - Planned/Proposed: centered gray header + single full-width Name/Size/Submarket table (overflows to next page) + footnote
- **New: Quarterly Changes page** (`page_quarterly_changes.html`, `load_quarterly_changes()`, `_render_quarterly_changes()`)
  - Inserted immediately after title page
  - Reads all CSVs from `Quarterly Changes [Q{N}]/` folder: `NRA_Changes`, `Status_Changes`, `Vacancy_Changes`
  - Each CSV gets its own navy subheader; empty CSVs display "No changes recorded this quarter"
  - `QUARTERLY_CHANGES_DIR` added to `report_config.py` (auto-derives from `DATA_ROOT`)
- Updated page count: 47 → ~50 pages (adds Quarterly Changes + 2 Pipeline pages)
- Updated template count: 9 → 11 templates
- Updated page sequence documentation to reflect new order
- Added 6 new troubleshooting entries (PDF PermissionError, Quarterly Changes dir, Pipeline parsing, Major Sales gap)

### Version 3.0.0 (2026-02-19)
- **MAJOR:** Added Office Quarterly Report PDF generator (`reports/` directory)
  - Programmatic recreation of 56-page InDesign quarterly report using Plotly + Jinja2 + WeasyPrint
  - 9 Jinja2 HTML templates: title, KPI header, performance (table + 3 charts), major leases, major sales, large availability, building list, sublease report
  - 48 Plotly charts: 3 dual-axis performance charts per page (vacancy SF, absorption, rental rates)
  - Data from Supabase `market_tables_office` (service role key) + 5 Excel files on Q: drive
  - Page sequence matches InDesign report: title → citywide → leases → sales → submarkets → micromarkets → overall → subleases → building lists
  - CSS @page US Letter layout with AQUILA brand styling (Futura font, Navy/Copper/Brass color scheme)
  - CLI: `--html-only` for browser preview, `--skip-charts` to reuse existing PNGs
  - First test: 2025 Q4 report (47 pages)
- New files: `report_config.py`, `data_loader.py`, `chart_builder.py`, `report_assembler.py`, `generate_office_report.py`, 9 templates, 2 CSS files
- Added report-specific troubleshooting entries (WeasyPrint GTK3, Supabase RLS, Citywide mapping)

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
