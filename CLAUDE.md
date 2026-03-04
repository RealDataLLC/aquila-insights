# CLAUDE.md - AI Assistant Guide for Aquila Insights

## Project Overview

**Aquila Insights** generates branded, interactive HTML charts from real estate data and publishes them via GitHub Pages.

**Workflow:** Notebooks for development -> Export HTML to `charts/` -> Link in README.md -> Auto-publish to GitHub Pages

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
1. **Supabase** - PostgreSQL database (`market_tables_office`, `market_tables_industrial`)
2. **Google Sheets** - Office tenant requirements (ID: `1bzpRnUrpBH6l_zX7DtTypczZf5bpYVwqPUG3tzg2vec`)
3. **Google Sheets** - Industrial TITM (ID: `1natA0ALaQnX3U_vGC5Vrchy1QqmbW8k0zvTKwuE2wys`)
4. **FRED API** - Economic indicators
5. **Excel Files** - Property management, transactions, quarterly report data (Q: drive)

---

## Repository Structure

```
aquila-insights/
├── aquila/                          # Shared Python package
│   ├── __init__.py                  #   Re-exports AQUILA_COLORS, AQUILA_FONT
│   ├── brand.py                     #   13-color palette, AQUILA_FONT, named aliases
│   ├── charts.py                    #   aquila_styled_line_chart(), write_chart_html(), add_aquila_logo()
│   ├── dateutil.py                  #   parse_quarter(), quarter_sort_key()
│   ├── git.py                       #   commit_and_push_all()
│   └── connectors/                  #   Data source clients (auto-loads aquila_graph.env)
│       ├── supabase.py              #     get_supabase_client(use_service_role=True)
│       ├── gsheets.py               #     get_gsheets_client()
│       └── fred.py                  #     fetch_fred_series()
│
├── generators/                      # Chart generators (organized by domain)
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
├── charts/                          # Published HTML charts (GitHub Pages) - 59 total
│   ├── property-management/         # 1 chart
│   ├── office/                      # 29 charts
│   ├── industrial/                  # 9 charts
│   ├── economic-indicators/         # 14 charts
│   └── development/                 # 6 charts
│
├── reports/                         # Quarterly Report generators (PDF)
│   ├── office/{YEAR}_{QN}/          # Office output per quarter
│   ├── industrial/{YEAR}_{QN}/      # Industrial output per quarter
│   ├── templates/                   # Jinja2 HTML page templates (14 office + 9 industrial)
│   ├── static/                      # CSS (report.css, tables.css), arrow icons
│   ├── generate_office_report.py    # Office report orchestrator (CLI)
│   ├── generate_industrial_report.py# Industrial report orchestrator (CLI)
│   ├── cleanup_quarterly_data.py    # Pre-report data cleanup (auto Step 0)
│   ├── data_loader.py              # Office: Supabase + Excel -> DataFrames
│   ├── industrial_data_loader.py   # Industrial: Supabase + Excel -> DataFrames
│   ├── chart_builder.py            # Office: Plotly -> PNG via Kaleido
│   ├── industrial_chart_builder.py # Industrial: Plotly -> PNG via Kaleido
│   ├── report_assembler.py         # Office: Jinja2 render + WeasyPrint -> PDF
│   └── industrial_report_assembler.py # Industrial: render + WeasyPrint -> PDF
│
├── dashboards/                      # Interactive Dash apps (local only, not published)
├── data/                            # Input data files (Excel, CSV)
├── notebooks/                       # Jupyter development notebooks
├── archive/                         # Deprecated/test scripts
├── update_all_charts.py             # Master orchestrator (runs all generators)
├── aquila_graphing_tools.py         # Backward-compat shim (imports from aquila/)
├── aquila_graph.env                 # CREDENTIALS (gitignored)
└── CLAUDE.md                        # This file
```

---

## Brand Standards

### Color Palette (2026)

```python
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
```

**Rules:**
- All chart titles must be **centered** (`title_x=0.5, title_xanchor='center'`)
- Use colors in **hierarchy order** for categorical series (index [0] first, [1] second, etc.)
- Named aliases: Navy=[0], Glass=[1], GlassAlt=[2], Concrete=[3], Copper=[4], Brass=[5], Greenspace=[6]
- On Windows (CP1252 shell): use `PYTHONUTF8=1 python script.py` or replace Unicode chars with ASCII

### Logo Watermark

All 59 HTML charts include an Aquila logo watermark (bottom-right, 12% width, 0.7 opacity).

```python
# Standard pattern for generators:
from aquila.charts import write_chart_html
write_chart_html(fig, 'charts/category/chart_name.html')

# Custom HTML write (austin_economy.py):
from aquila.charts import add_aquila_logo
add_aquila_logo(fig)  # then fig.to_html(...)

# Logo source: data/Aquila_Logo2.png (embedded as base64)
```

---

## aquila/ Package API

```python
# Brand constants
from aquila.brand import AQUILA_COLORS, AQUILA_FONT, NAVY, GLASS_BLUE, COPPER, BRASS

# Data connectors (auto-loads aquila_graph.env)
from aquila.connectors.supabase import get_supabase_client  # use_service_role=True for RLS tables
from aquila.connectors.gsheets import get_gsheets_client
from aquila.connectors.fred import fetch_fred_series

# Utilities
from aquila.dateutil import parse_quarter, quarter_sort_key
from aquila.charts import aquila_styled_line_chart, write_chart_html, add_aquila_logo
from aquila.git import commit_and_push_all
```

**Backward-compat shim:** `aquila_graphing_tools.py` re-exports everything from `aquila/` -- old imports still work.

**Supabase auth note:** `market_tables_office` and `market_tables_industrial` require service role key (`use_service_role=True`). The anon key lacks RLS access.

---

## Chart Generators (13 generators, 59 charts)

| Domain | Generator | Charts | Data Source |
|--------|-----------|--------|-------------|
| office | `generators/office/requirements.py` | 7 | Google Sheets |
| office | `generators/office/demand_by_market.py` | 5 | Google Sheets |
| office | `generators/office/transactions.py` | 2 | Excel |
| office | `generators/office/market_metrics.py` | 12 | Supabase |
| office | `generators/office/building_performance.py` | 4 | Supabase |
| industrial | `generators/industrial/vacancy.py` | 1 | Supabase |
| industrial | `generators/industrial/demand.py` | 5 | Google Sheets |
| industrial | `generators/industrial/nnn_rent.py` | 1 | Supabase |
| economic | `generators/economic/fred_indicators.py` | 7 | FRED API |
| economic | `generators/economic/fred_housing.py` | 1 | FRED API |
| economic | `generators/economic/austin_economy.py` | 6 | Excel |
| property_mgmt | `generators/property_mgmt/ams_kpi.py` | 1 | Excel |
| development | `generators/development/permits.py` | 6 | API |

### Key Generator Details

**Office Requirements** (`requirements.py`): Combines historical (Tab 2: "Through 2024") + current (Tab 0: "2025 +") Google Sheets data. Market mapping: Flexible/Citywide counts toward all markets. Size bins: Sub 10k, 10k-25k, 25k-50k, 50k-100k, Mega (100k+).

**2026 Annualized Projection** (demand-by-tenant-size charts, main + 5 submarkets): Charts aggregate by year. Current year bar is projected full-year demand via `projected = ytd_current * (full_prior / ytd_prior_same_period)`. Visual: 45% opacity + diagonal hatch for projected bar; dashed connector + open-circle marker. Subtitle shows pace factor.

**Office Market Metrics** (`market_metrics.py`): 12 charts (4 submarkets x 3 types). CBD/NW/SW use `table_type="competitive set"`, Domain uses `table_type="micromarket"`. Charts: vacancy rate (line), rental rate (stacked bar: Base Rent + Opex), opex (line).

**Industrial Demand** (`demand.py`): TITM Google Sheet, Tab 1. Size bins: Sub 25k, 25k-50k, 50k-100k, 100k-250k, Mega (250k+).

**Industrial NNN Rent** (`nnn_rent.py`): Submarkets: Northeast, Southeast, Williamson County. Date range starts 2022 Q1; update `END_QUARTER` constant for new quarters.

**Building Performance** (`building_performance.py`): Supabase tables `quarterly_report_data_office` and `quarterly_report_data_industrial`. Filters: `aquila_competitive_set=True`, `building_status='Existing'`. Auto-creates 5 size bins using quintiles.

**Austin Economy** (`austin_economy.py`): `data/Industries and Companies 2025.xlsx`. 6 charts: jobs by industry, new vs expanded, jobs by location, HQ activity, monthly jobs, top companies.

---

## Quarterly Reports (PDF)

Both office and industrial reports use the same architecture: config -> cleanup -> data load -> chart build -> Jinja2 render -> WeasyPrint PDF.

### Office Report

**Entry point:** `reports/generate_office_report.py`
**Config:** `reports/report_config.py` (update `REPORT_YEAR` and `REPORT_QUARTER` each quarter)
**Data:** Supabase `market_tables_office` (primary) + Excel/CSV on `Q:\0-Quarterly Reports\0-Office\{YEAR} Q{N}\`
**Output:** `reports/office/{YEAR}_{QN}/` -> ~50-page PDF with 55 chart PNGs

**Page sequence:** Title -> TOC -> Quarterly Changes -> Citywide KPI + performance -> Major Leases -> Major Sales -> Pipeline (UC + Proposed) -> Submarket sections (CBD, NW, SW, E) -> Micromarket performance -> Long-term performance (2 pages) -> Overall performance -> Sublease report -> Building lists (18 sheets)

**Key architecture:**
- `cleanup_quarterly_data.py` runs as Step 0 (abbreviation standardization, Major Leases sort, Major Sales consolidation, pipeline verification, Proposed sorting)
- `data_loader.py` loads Supabase (service role key) + Excel
- `chart_builder.py` generates 3 dual-axis charts per performance page (vacancy SF, absorption, rental rates)
- `report_assembler.py` does Jinja2 rendering + WeasyPrint PDF; two-pass TOC build
- Citywide uses `table_type="overall"` (not "competitive set")
- Long-term pages: "Of Submarkets" (2x3 grid) + "CBD vs Suburban" (2x2 grid); Suburban = NW + SW combined

### Industrial Report

**Entry point:** `reports/generate_industrial_report.py`
**Config:** `reports/industrial_report_config.py`
**Data:** Supabase `market_tables_industrial` (primary) + Excel/CSV on `Q:\0-Quarterly Reports\0-Industrial\{YEAR} Q{N}\`
**Output:** `reports/industrial/{YEAR}_{QN}/` -> ~45-page PDF with 52 chart PNGs

**Key differences from office:**
- Supabase keyed by `(submarket_name, property_type)` not `(aquila_micromarket, table_type)`
- Dual property types: Industrial + Flex (7 submarkets x 2 types = 14 performance pages)
- No opex -> single-bar rental chart instead of stacked
- Large availabilities split by generation (1st/2nd Gen) not submarket
- Pipeline auto-detects named-column vs positional format
- Industrial CSVs use `[Q{N}]` suffix pattern
- Submarkets: East, Hays County, North Central, Northeast, South, Southeast, Williamson County (Southwest only in building lists)

### Report CLI Commands

```bash
# Office
python reports/generate_office_report.py                            # Full PDF
python reports/generate_office_report.py --html-only                # Browser preview
python reports/generate_office_report.py --html-only --skip-charts  # Fast CSS iteration
python reports/generate_office_report.py --skip-charts              # PDF with existing PNGs
python reports/generate_office_report.py --skip-cleanup             # Skip data cleanup

# Industrial (same flags)
python reports/generate_industrial_report.py
python reports/generate_industrial_report.py --html-only
python reports/generate_industrial_report.py --html-only --skip-charts
python reports/generate_industrial_report.py --skip-charts
python reports/generate_industrial_report.py --skip-cleanup

# Cleanup standalone
python reports/cleanup_quarterly_data.py --dry-run                  # Preview changes
python reports/cleanup_quarterly_data.py                            # Apply changes
```

### Quarterly Update Process

1. Update config file (`report_config.py` or `industrial_report_config.py`) with new `REPORT_YEAR` and `REPORT_QUARTER`
2. Ensure source files on Q: drive match expected folder structure
3. Run the report generator
4. Compare output PDF against InDesign reference

**WeasyPrint on Windows:** Requires GTK3 via MSYS2: `pacman -S mingw-w64-ucrt-x86_64-pango mingw-w64-ucrt-x86_64-gtk3`, add `C:\msys64\ucrt64\bin` to PATH.

---

## Dashboards (Local)

**File:** `dashboards/office_requirements_dashboard.py` (Dash app at http://127.0.0.1:8050/)
**Data:** Same Google Sheets as static charts. Run: `python dashboards/office_requirements_dashboard.py`

**Key architecture:** Data is never filtered by date -- date range only slices display. Rolling averages computed on full dataset first, then split into current/prior periods. Prior year = same range shifted back 12 months.

---

## Standard Workflow

### Chart Generation

```python
# 1. Fetch data (connectors auto-load aquila_graph.env)
from aquila.connectors.supabase import get_supabase_client
supabase = get_supabase_client(use_service_role=True)
response = supabase.table('table_name').select('*').execute()
df = pd.DataFrame(response.data)

# 2. Generate chart
from aquila.brand import AQUILA_COLORS, AQUILA_FONT
import plotly.express as px
fig = px.bar(df, x='x', y='y', color_discrete_sequence=AQUILA_COLORS)
fig.update_layout(plot_bgcolor='white', font=dict(family=AQUILA_FONT, color='#172344'))

# 3. Export with logo watermark
from aquila.charts import write_chart_html
write_chart_html(fig, 'charts/category/chart_name.html')

# 4. Update README.md (REQUIRED)
# Format: [Descriptive Name [YYYY-MM-DD]](https://realdatallc.github.io/aquila-insights/charts/category/chart_name.html)

# 5. Commit & push
from aquila.git import commit_and_push_all
commit_and_push_all("Update chart description")
```

### Common Patterns

```python
# Date parsing
df['date'] = pd.to_datetime(df['date'], errors='coerce')

# Quarter strings ("2025 Q4" -> datetime)
from aquila.dateutil import parse_quarter
df['date'] = df['quarter'].apply(parse_quarter)

# Numeric cleaning
df['value'] = pd.to_numeric(df['value'].astype(str).str.replace(',', ''), errors='coerce')

# Size binning (office)
df['size_bin'] = pd.cut(df['sf'], bins=[0, 10000, 25000, 50000, 100000, float('inf')],
                        labels=['Sub 10k', '10k-25k', '25k-50k', '50k-100k', 'Mega'])

# Chart formatting
fig.update_yaxes(tickformat='.1%')     # Percentages
fig.update_yaxes(tickprefix='$', tickformat=',')  # Currency
```

---

## Automation

```bash
# Update all charts
python update_all_charts.py                    # All 13 generators (~59 charts)
python update_all_charts.py --group office     # Office only (29 charts)
python update_all_charts.py --group industrial # Industrial only (9 charts)
python update_all_charts.py --group economic   # Economic only (14 charts)
python update_all_charts.py --group property_mgmt
python update_all_charts.py --group development

# Individual generators
python -m generators.office.requirements
python -m generators.office.market_metrics
python -m generators.industrial.vacancy
python -m generators.industrial.demand
python -m generators.economic.fred_indicators
python -m generators.economic.austin_economy
python -m generators.property_mgmt.ams_kpi
python -m generators.development.permits
```

---

## Configuration

### aquila_graph.env (gitignored)

Required keys: `FRED_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY` (service role), `GOOGLE_SERVICE_ACCOUNT_TYPE` through `GOOGLE_UNIVERSE_DOMAIN` (12 Google SA fields).

Verify credentials NOT committed: `git log --all --full-history -- aquila_graph.env`

---

## Troubleshooting

### Data & API

| Issue | Solution |
|-------|----------|
| **Google Sheets 403** | Verify service account has spreadsheet access; check credentials in `aquila_graph.env` |
| **Supabase 403 / empty data** | Use `service_role` key (`use_service_role=True`); anon key lacks RLS access to `market_tables_*` |
| **FRED API Error** | Verify API key at https://fred.stlouisfed.org/ |
| **Empty DataFrame** | Check query/API response; print `df.shape` and `df.head()` |
| **Date Parsing** | Use `pd.to_datetime(..., errors='coerce')` and check for NaTs |
| **Projection factor wrong** | Check `date` column has prior year records; fallback is `365/day_of_year` |
| **Submarket projection is 0** | Market may have no 2026 YTD data; chart still renders historical bars |

### Charts (Plotly)

| Issue | Solution |
|-------|----------|
| **`titlefont` ValueError** | Use `title=dict(text=..., font=dict(...))` syntax instead |
| **Unicode error on Windows** | Use `PYTHONUTF8=1 python script.py` or replace `✓/→/⚠` with ASCII in `print()` |
| **Stray date at end of chart** | Outer merge orphans — filter `df_plot[df_plot['sort_order_current'].notna()]` |
| **Prior year month missing** | Aggregate ALL data first, then split into current/prior periods — never filter `df_global` by date |
| **Dash `app.run_server` error** | Obsolete in Dash 2.x — use `app.run()` instead |
| **Dash axis `font` error** | Use `tickfont=dict(...)` inside `xaxis`/`yaxis`, not `font=dict(...)` |

### PDF Reports (WeasyPrint)

| Issue | Solution |
|-------|----------|
| **WeasyPrint DLL error** | `OSError: cannot load library 'libgobject-2.0-0'` — install GTK3 via MSYS2: `pacman -S mingw-w64-ucrt-x86_64-gtk3`, add `C:\msys64\ucrt64\bin` to PATH |
| **PDF write PermissionError** | PDF is open in a viewer — close it first |
| **--skip-charts not finding PNGs** | Chart filenames are lowercased but keys are title-case — `_find_existing_charts()` handles the mapping |
| **Citywide data missing** | Citywide uses `table_type="overall"`, not `"competitive set"` — `get_kpi_data()` auto-detects |
| **Quarterly Changes dir not found** | Folder must be named `Quarterly Changes [Q{N}]` exactly; check `QUARTERLY_CHANGES_DIR` in config |
| **Pipeline UC groups empty** | `Under Construction` sheet uses merged year/quarter header rows — parser expects `2025`/`4Q` pattern |
| **Proposed rows missing** | `Proposed` sheet row 0 is an embedded header (`Future Developments`) — loader skips it automatically |
| **NRA Changes title shows wrong label** | `_clean_title()` uses override map; ensure CSV is named `NRA_Changes*.csv` |
| **Property ID has commas (e.g. 12,345)** | `_render_quarterly_changes()` detects columns matching `\bid\b` and skips comma formatting |
| **Abbreviation over-expanded** | Single-letter cardinals use negative lookbehind `(?<!\.)` — letter preceded by `.` is never expanded |
| **Cleanup runs on wrong quarter** | `cleanup_quarterly_data.py` derives paths from `report_config.py` — update `REPORT_YEAR`/`REPORT_QUARTER` first |
| **Vertical Format tab missing** | Tab created only if `Major Sales` sheet exists and tab is absent; check workbook sheet names |
| **Major Sales gap between title and cards** | Use `<table class="sales-table-grid">` layout (not flex) — WeasyPrint ignores `page-break-before: avoid` on flex |
| **Pipeline Planned/Proposed columns colliding** | Use single full-width `<table class="proposed-table">` with `table-layout: fixed` (55%/18%/27%) |

### Industrial Report

| Issue | Solution |
|-------|----------|
| **Industrial Supabase empty** | Same auth as office — ensure `SUPABASE_KEY` (service role) is in `aquila_graph.env` |
| **Industrial pipeline format** | Auto-detects `Quarter Delivery` column; falls back to positional parser if not found |
| **Industrial large avail shows 0 SF** | Column must be `Total Available Space (SF)` — fallback chain: `Available SF` -> `Available (SF)` -> `available_sf` |
| **Industrial major sales missing buyer/seller** | Excel columns are `Buyer (True) Company` / `Seller (True) Company`; fallback tries `Buyer`/`Seller` |
| **Industrial KPI NRA change is 0** | Requires at least 2 quarters of data in `Regional_{type}` — check Supabase consecutive quarter rows |
| **Industrial quarterly changes CSV not found** | Industrial CSVs use `[Q{N}]` suffix (e.g. `Existing Supply NRA Changes [Q4].csv`), different from office |
| **Cleanup AttributeError on industrial config** | Industrial config uses `cfg.PIPELINE`/`cfg.LARGE_AVAIL` not `cfg.CITYWIDE_PIPELINE`/`cfg.OFFICE_AVAIL` |
| **Cleanup Supabase connection fails** | Inventory loading is optional — building matching/pipeline verification skip with warning; abbreviations continue |

---

## DO's and DON'Ts

**DO:**
- Use `AQUILA_COLORS` and `AQUILA_FONT` for all charts
- Export to categorized subdirectories (`charts/category/`)
- Update README.md with `[Name [YYYY-MM-DD]](url)` format
- Handle date/numeric parsing with `errors='coerce'`
- Check DataFrame not empty before charting
- Center all chart titles

**DON'T:**
- Commit credentials (`aquila_graph.env`, `*.json`)
- Use random colors (always `AQUILA_COLORS`)
- Skip README.md updates
- Push to main directly (use feature branches)
- Include PII in published charts

---

**Last Updated:** 2026-03-04
**Document Version:** 6.0.0

---

## Changelog

| Version | Date | Summary |
|---------|------|---------|
| **6.0.0** | 2026-03-04 | CLAUDE.md consolidated (1498→418 lines); added custom slash commands (`.claude/commands/`) |
| **5.3.0** | 2026-03-02 | Report pagination — building lists and large availabilities chunked at 35 rows/page with "Page X of Y" labels; TOC disclaimer anchored to bottom; new separate UC/Proposed pipeline templates |
| **5.2.0** | 2026-03-02 | Report style fixes — TOC heading Futura Light/Navy, pipeline split into two independently page-counted sections, industrial rental chart vacancy line corrected to Glass Blue Alt |
| **5.1.0** | 2026-03-02 | PNG arrow icons for KPI direction indicators (Greenspace up, Signal down); CSS polish for TOC/section dividers/pipeline; all secondary y-axes fixed to start at 0% |
| **5.0.0** | 2026-02-27 | MAJOR — Created `aquila/` shared package (brand, connectors, charts, dateutil, git); reorganized all 13 generators to `generators/` by domain; `aquila_graphing_tools.py` converted to backward-compat shim |
| **4.4.0** | 2026-02-26 | Updated to 13-color 2026 palette (Glass Blue Alt added at [2], all indices reordered); centered all chart titles globally; fixed Austin 2025 chart colors and size-range sequential ordering |
| **4.3.0** | 2026-02-25 | Added 12 Office Market Metrics charts (CBD/NW/SW/Domain: vacancy rate, rental rate, opex) via Supabase `market_tables_office` |
| **4.2.0** | 2026-02-25 | Added 6 Austin Economy charts from `Industries and Companies 2025.xlsx` (jobs by industry/location/month, HQ activity, top companies) |
| **4.1.0** | 2026-02-25 | Enhanced cleanup script — auto report-type detection, Supabase inventory loading, Major Leases sort/name-match, Major Sales portfolio consolidation, pipeline UC verification, Proposed sorting |
| **4.0.0** | 2026-02-24 | MAJOR — Added Industrial Quarterly Report PDF generator (~45 pages, 52 charts, 9 templates, 5 new modules); dual property types (Industrial + Flex); generation-based large availabilities; regional comparison charts |
| **3.5.0** | 2026-02-24 | Added pre-report cleanup script (`cleanup_quarterly_data.py`) with abbreviation standardization, Vertical Format tab creation; fixed Quarterly Changes NRA title and Property ID comma formatting |
| **3.4.0** | 2026-02-24 | Added 2 long-term performance pages (10 charts: Of Submarkets 2×3 + CBD vs Suburban 2×2); Class B asking rates; submarket-stacked absorption; fully stacked direct/sublease vacancy chart |
| **3.3.0** | 2026-02-24 | Added Table of Contents page with two-pass page number computation and anchor hyperlinks |
| **3.2.0** | 2026-02-23 | Report layout fixes — Major Sales as table layout, Pipeline Proposed as single fixed-width table, chart fonts scaled 1.5×, building list totals in `<tfoot>` |
| **3.1.0** | 2026-02-23 | Added Development Pipeline pages (UC + Proposed) and Quarterly Changes page; chart export scale 2×→3× |
| **3.0.0** | 2026-02-19 | MAJOR — Added Office Quarterly Report PDF generator (Plotly + Jinja2 + WeasyPrint, ~50 pages, 48 charts, 9 templates) |
| **2.3.0** | 2026-02-19 | Added Industrial NNN Rental Rates chart (Northeast/Southeast/Williamson County) |
| **2.2.0** | 2026-02-19 | Added Office Requirements Dashboard (Dash app with submarket/industry/size filters, YoY comparison, 3-month rolling avg) |
| **2.1.0** | 2026-02-19 | Added 2026 annualized projection to demand-by-tenant-size charts (main + 5 submarkets); YTD pace factor formula |
| **2.0.0** | 2026-02-10 | MAJOR — CLAUDE.md condensed 80%; all scripts renamed for clarity; organized by data source |
| **1.0–1.4** | 2026-01-15–02-09 | Initial documentation; FRED indicators; 2026 brand palette rebrand; Industrial Demand charts; categorized chart subdirectories |
