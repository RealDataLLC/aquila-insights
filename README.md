# Welcome to aquila-insights
These are data plots for Aquila Commercial, maintained by [Nelson Lin](mailto:nelson@subtlerealestate.com)

## Aquila Operating KPIs
[AMS Managed Properties KPIs [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/property-management/ams_managed_properties_kpi.html)

[Aquila Transactions by Platform (Quarterly SF) [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/transaction_sf_by_quarter.html)

[Aquila Transactions by Platform (Quarterly Count) [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/transaction_count_by_quarter.html)

## Office

[Broker vs. Direct Deals – Net Effective Rent by Building [2026-03-11]](https://realdatallc.github.io/aquila-insights/charts/office/broker-comparison.html) - New leases only; compares represented vs. unrepresented tenants within same buildings

### Aquila Benefit Dashboard
Interactive local dashboard comparing AQUILA-brokered deals vs peer deals in the same building/year using Skyline (restb.ai) lease comp data.

```bash
python dashboards/office_requirements_dashboard.py
# Open http://127.0.0.1:8050/ and click the 'Aquila Benefit' tab
```

**Aquila Benefit tab features:**
- KPI cards: Deals Analyzed, Win Rate, Median Savings, Total SF
- Average NER by Year — grouped bar chart (AQUILA Navy vs Market Peers Concrete)
- NER Savings Per Deal — horizontal bar chart (Greenspace = saved, Signal = didn't)
- Click any deal bar to expand a detail panel showing the AQUILA deal card + all peer comps
- Deal Browser — filterable/sortable table of all AQUILA deals with peer avg NER and savings
- Broker List — leaderboard ranked by total deals, with win rate and savings per broker
- Filter by year (pill buttons) and lease type (dropdown, defaults to New)

### Quarterly Reports
The Office Quarterly Report is generated programmatically from Supabase + Excel data using Plotly charts, Jinja2 templates, and WeasyPrint PDF conversion. It covers 4 Austin submarkets and 6 micromarkets, producing a ~50-page branded PDF with 55 charts.

```bash
# Generate full PDF
python reports/generate_office_report.py

# HTML preview only
python reports/generate_office_report.py --html-only

# Reuse existing chart PNGs (faster iteration)
python reports/generate_office_report.py --skip-charts
```

Update `reports/report_config.py` with the new quarter before generating. Source data is read from `Q:\0-Quarterly Reports\0-Office\{YEAR} Q{N}\`.

Submarket boundary maps (Citywide, CBD, NW, SW, East) are generated from KMZ polygon data using Plotly Scattermapbox. Requires `MAPBOX_API_KEY` in `aquila_graph.env`.

### Tenant Requirements
[Requirements Total SF [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/requirements_sf_total.html) - Combined historical data from 2018+

[Requirements Average SF [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/requirements_sf_avg.html) - Combined historical data from 2018+

[Tenant Demand by Industry [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/requirements_sf_avg_by_industry.html) - Combined historical data from 2018+

[Tenant Demand by Size Range and Number [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/requirements_by_size_range.html) - Combined historical data from 2018+

[Requirements vs Absorption (Quarterly) [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/requirements_vs_absorption_office.html) - Compares tenant requirements against market absorption

[Requirements YoY Rolling 12-Month [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/requirements_yoy_rolling_12m.html) - Rolling 12-month average SF and count with prior year comparison

### Market Metrics
[Asking vs Effective Rent by Submarket [2026-01-16]](https://realdatallc.github.io/aquila-insights/charts/office/office_asking_vs_effective_rent_by_submarket.html)

[Office Occupancy Rate by Building Size [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/office_occupancy_by_size.html)

[Office Weighted Average Rent by Building Size [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/office_rent_by_size.html)

#### Vacancy Rates (Competitive Set)
[Vacancy Rate — CBD [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/office_vacancy_rate_cbd.html)

[Vacancy Rate — Northwest [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/office_vacancy_rate_northwest.html)

[Vacancy Rate — Southwest [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/office_vacancy_rate_southwest.html)

[Vacancy Rate — The Domain [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/office_vacancy_rate_domain.html)

#### Rental Rates (Competitive Set)
[Rental Rate — CBD [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/office_rental_rate_cbd.html)

[Rental Rate — Northwest [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/office_rental_rate_northwest.html)

[Rental Rate — Southwest [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/office_rental_rate_southwest.html)

[Rental Rate — The Domain [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/office_rental_rate_domain.html)

#### Operating Expenses (Competitive Set)
[Operating Expenses — CBD [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/office_opex_cbd.html)

[Operating Expenses — Northwest [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/office_opex_northwest.html)

[Operating Expenses — Southwest [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/office_opex_southwest.html)

[Operating Expenses — The Domain [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/office/office_opex_domain.html)


## Industrial

### Quarterly Reports
The Industrial Quarterly Report is generated programmatically from Supabase + Excel data using Plotly charts, Jinja2 templates, and WeasyPrint PDF conversion. It covers 7 Austin submarkets across 2 property types (Industrial + Flex), producing a ~45-page branded PDF with 52 charts.

```bash
# Generate full PDF
python reports/generate_industrial_report.py

# HTML preview only
python reports/generate_industrial_report.py --html-only

# Reuse existing chart PNGs (faster iteration)
python reports/generate_industrial_report.py --skip-charts
```

Update `reports/industrial_report_config.py` with the new quarter before generating. Source data is read from `Q:\0-Quarterly Reports\0-Industrial\{YEAR} Q{N}\`.

### Tenant Demand (TITM)
[Industrial Demand by Tenant Size [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/industrial/industrial_demand_by_tenant_size.html) - Quarterly demand grouped by size category with total demand line

[Industrial Demand by Use Type [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/industrial/industrial_demand_by_use_type.html) - Distribution, Manufacturing, R&D/Lab, etc.

[Industrial Requirements by Size Range [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/industrial/industrial_requirements_by_size_range.html) - Total cumulative SF by size category

[Industrial Requirements Total SF [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/industrial/industrial_requirements_sf_total.html) - Monthly total SF (Low/High)

[Industrial Requirements Average SF [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/industrial/industrial_requirements_sf_avg.html) - Monthly average SF with record count

### Market Metrics
[NNN Rental Rates by Submarket [2026-03-16]](https://realdatallc.github.io/aquila-insights/charts/industrial/industrial_nnn_rent_by_submarket.html)

[Vacancy Rate by Submarket [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/industrial/vacancy_rate_industrial.html)

[Industrial Occupancy Rate by Building Size [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/industrial/industrial_occupancy_by_size.html)

[Industrial Weighted Average Rent by Building Size [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/industrial/industrial_rent_by_size.html)

## Economic Indicators

### Employment
[Austin Employment - Office Sectors [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_employment_office_sectors.html)

[Austin Employment - Industrial Sector [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_employment_industrial.html)

[Austin Employment - Retail Sector [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_employment_retail.html)

[Austin vs National Tech Employment Growth [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_vs_national_tech_employment.html)

### Wages
[Austin vs Dallas vs National Wage Growth [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_vs_dallas_vs_national_wage_growth.html)

### Financial Indicators
[Interest Rates - Treasury & Mortgage [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/interest_rates_treasury_mortgage.html)

[Inflation & PPI - CPI and Office Construction Costs [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/inflation_cpi_ppi_office.html)

### Housing Indicators
[Austin Housing Starts (Monthly) [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_housing_starts.html)

## Austin Economy

### Industries and Companies That Came to Austin in 2025
[Jobs Created by Industry — Austin Region 2025 [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_2025_jobs_by_industry.html)

[New Relocations vs. Expansions by Industry — Austin 2025 [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_2025_new_vs_expanded.html)

[Jobs by Location — Austin Region 2025 [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_2025_jobs_by_location.html)

[Headquarters vs. Branch/Production Jobs by Industry — Austin 2025 [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_2025_hq_activity.html)

[Monthly Jobs Announced — Austin Region 2025 [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_2025_jobs_by_month.html)

[Top 10 Companies by Jobs Created — Austin 2025 [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_2025_top_companies.html)

## Development & Permitting

### Development Pipeline Analysis
[Pipeline Volume by Quarter [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/development/pipeline_volume_by_quarter.html) - Total proposed SF by quarter and permit status (2015-present)

[Pipeline by Land Use Type [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/development/pipeline_by_land_use_type.html) - Development activity by CRE sector (Office, Industrial, Retail, Mixed-Use, etc.)

[Pipeline by Council District [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/development/pipeline_by_council_district.html) - Development volume by Austin City Council district

[Permit Status Distribution [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/development/permit_status_distribution.html) - Breakdown of permits by current status (Active, Expired, Approved, etc.)

### Regulatory & Market Efficiency
[Approval Timeline Trends [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/development/approval_timeline_trends.html) - Median days to approval by quarter

[Year-over-Year Permit Trends by Land Use [2026-03-04]](https://realdatallc.github.io/aquila-insights/charts/development/permits_yoy_by_land_use.html) - Annual permit volume comparison across CRE sectors

Todo:
- Requirements vs Absorption (Industrial)
- Sales Taxes in Austin (Retail)
- Inflation adjusted metrics

---

## Repository Architecture

### Directory Structure
```
aquila-insights/
├── aquila/                    # Shared Python package
│   ├── brand.py               #   AQUILA_COLORS, AQUILA_FONT, named aliases
│   ├── charts.py              #   aquila_styled_line_chart()
│   ├── dateutil.py            #   parse_quarter(), quarter_sort_key()
│   ├── git.py                 #   commit_and_push_all()
│   └── connectors/            #   Data source clients
│       ├── supabase.py        #     get_supabase_client()
│       ├── gsheets.py         #     get_gsheets_client()
│       └── fred.py            #     fetch_fred_series()
│
├── generators/                # Chart generators (organized by domain)
│   ├── office/                #   5 generators (29 charts)
│   │   ├── requirements.py    #     7 requirement charts (Google Sheets)
│   │   ├── demand_by_market.py#     5 submarket demand charts
│   │   ├── transactions.py    #     2 transaction charts (Excel)
│   │   ├── market_metrics.py  #     12 vacancy/rent/opex charts (Supabase)
│   │   └── building_performance.py  # 4 occupancy/rent by size
│   ├── industrial/            #   3 generators (9 charts)
│   │   ├── vacancy.py         #     1 vacancy chart (Supabase)
│   │   ├── demand.py          #     5 TITM demand charts (Google Sheets)
│   │   └── nnn_rent.py        #     1 NNN rent chart (Supabase)
│   ├── economic/              #   3 generators (14 charts)
│   │   ├── fred_indicators.py #     7 FRED indicator charts
│   │   ├── fred_housing.py    #     1 housing starts chart
│   │   └── austin_economy.py  #     6 Austin 2025 economy charts
│   ├── property_mgmt/         #   1 generator (1 chart)
│   │   └── ams_kpi.py
│   └── development/           #   1 generator (6 charts)
│       └── permits.py
│
├── reports/                   # Quarterly PDF report generators
│   └── map_builder.py         #   Submarket maps (KMZ -> Mapbox -> PNG)
├── dashboards/                # Local interactive Dash apps
│   ├── office_requirements_dashboard.py  # Requirements + Aquila Benefit tabs
│   └── aquila_benefit.py      #   Aquila Benefit module (Skyline NER analysis)
├── charts/                    # Published HTML charts (GitHub Pages)
├── data/                      # Input data files (Excel, CSV)
├── notebooks/                 # Jupyter development notebooks
├── archive/                   # Deprecated/test scripts
├── update_all_charts.py       # Master orchestrator
├── aquila_graphing_tools.py   # Backward-compat shim
└── aquila_graph.env           # Credentials (gitignored)
```

### Running Charts

```bash
# Regenerate all charts (13 generators)
python update_all_charts.py

# Run a specific domain group
python update_all_charts.py --group office
python update_all_charts.py --group industrial
python update_all_charts.py --group economic
python update_all_charts.py --group property_mgmt
python update_all_charts.py --group development

# Run a single generator directly
python -m generators.office.requirements
python -m generators.industrial.vacancy
python -m generators.economic.fred_indicators
```

### Embedding Charts

```html
<iframe
  src="https://realdatallc.github.io/aquila-insights/charts/office/requirements_sf_total.html"
  width="100%"
  height="500"
  frameborder="0">
</iframe>
```

All chart URLs: `https://realdatallc.github.io/aquila-insights/charts/{category}/{filename}.html`

---

## Changelog

| Version | Date | Summary |
|---------|------|---------|
| **6.8.0** | 2026-03-16 | Report styling overhaul — chart legends moved below charts (horizontal, centered); table pagination reduced to 30 rows/page with continuous row numbering across pages; building lists now include `#` column; TOC entry labels enlarged to 12pt; TOC section headers enlarged to 12pt; footer shows "Aquila Office/Industrial Report" on bottom-left of all pages (except title/TOC); disclaimer text full-width with 8pt right padding; long-term performance chart color swaps for clarity; industrial NNN rent chart legend moved to bottom |
| **6.7.0** | 2026-03-13 | Office report submarket maps — `reports/map_builder.py` generates Plotly Scattermapbox maps from KMZ polygon data (13 submarkets); Citywide + 4 submarket maps embedded as base64 PNGs in KPI header pages; Mapbox "light" basemap with brand-colored polygons |
| **6.6.0** | 2026-03-12 | Aquila Benefit dashboard tab — Skyline API connector (`aquila/connectors/skyline.py`), NER comparison module (`dashboards/aquila_benefit.py`); two-tab layout in office requirements dashboard (Requirements + Aquila Benefit) |
| **6.5.0** | 2026-03-09 | Dashboard UX — moved Annual Demand chart to top of right column; consolidated `demand-submarket-filter` and `demand-size-filter` into left sidebar; all charts export to PNG via Plotly modebar (`_CHART_CONFIG` with `toImageButtonOptions`) |
| **6.4.0** | 2026-03-09 | Magic link auth for `@aquilacommercial.com` — `APP_URL` env var replaces hardcoded Vercel URL; documented `SUPABASE_ANON_KEY`, `FLASK_SECRET_KEY`, `APP_URL` as required Vercel env vars |
| **6.3.0** | 2026-03-06 | Dashboard annual demand chart converted to rolling 12M windows — `aggregate_annual_demand()` now returns `(window_by_size, window_total, window_labels_list)`; solid bars, single total line, "Mar 2025–Feb 2026" range labels on x-axis; matches `requirements.py` Chart 7 behavior |
| **6.2.0** | 2026-03-06 | Removed annualized projection from demand charts — `demand_by_market.py` now uses rolling 12M trailing windows with zero-filled sparse months; `requirements.py` Chart 7 shows actual YTD with "Data through [Month Year]" subtitle; dashboard fixed top-left logo bar |
| **6.1.0** | 2026-03-05 | Vercel deployment for office requirements dashboard — `api/index.py` WSGI entry, `vercel.json`, brand constants stub, `server = app.server`, added numpy to requirements |
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
