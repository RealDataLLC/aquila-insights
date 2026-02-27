# Welcome to aquila-insights
These are data plots for Aquila Commercial, maintained by [Nelson Lin](mailto:nelson@subtlerealestate.com)

## Aquila Operating KPIs
[AMS Managed Properties KPIs [2026-01-20]](https://realdatallc.github.io/aquila-insights/charts/property-management/ams_managed_properties_kpi.html)

[Aquila Transactions by Platform (Quarterly SF) [2026-01-28]](https://realdatallc.github.io/aquila-insights/charts/office/transaction_sf_by_quarter.html)

[Aquila Transactions by Platform (Quarterly Count) [2026-01-28]](https://realdatallc.github.io/aquila-insights/charts/office/transaction_count_by_quarter.html)

## Office

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

### Tenant Requirements
[Requirements Total SF [2026-01-30]](https://realdatallc.github.io/aquila-insights/charts/office/requirements_sf_total.html) - Combined historical data from 2018+

[Requirements Average SF [2026-01-30]](https://realdatallc.github.io/aquila-insights/charts/office/requirements_sf_avg.html) - Combined historical data from 2018+

[Tenant Demand by Industry [2026-01-30]](https://realdatallc.github.io/aquila-insights/charts/office/requirements_sf_avg_by_industry.html) - Combined historical data from 2018+

[Tenant Demand by Size Range and Number [2026-01-30]](https://realdatallc.github.io/aquila-insights/charts/office/requirements_by_size_range.html) - Combined historical data from 2018+

[Requirements vs Absorption (Quarterly) [2026-01-30]](https://realdatallc.github.io/aquila-insights/charts/office/requirements_vs_absorption_office.html) - Compares tenant requirements against market absorption

[Requirements YoY Rolling 12-Month [2026-01-30]](https://realdatallc.github.io/aquila-insights/charts/office/requirements_yoy_rolling_12m.html) - Rolling 12-month average SF and count with prior year comparison

[Office Demand by Tenant Size [2026-02-04]](https://realdatallc.github.io/aquila-insights/charts/office/requirements_demand_by_tenant_size.html) - Annual demand grouped by size category with total demand line

#### Demand by Market

[Office Demand by Tenant Size - CBD [2026-02-04]](https://realdatallc.github.io/aquila-insights/charts/office/requirements_demand_by_tenant_size_cbd.html)

[Office Demand by Tenant Size - Southwest [2026-02-04]](https://realdatallc.github.io/aquila-insights/charts/office/requirements_demand_by_tenant_size_sw.html)

[Office Demand by Tenant Size - Northwest [2026-02-04]](https://realdatallc.github.io/aquila-insights/charts/office/requirements_demand_by_tenant_size_nw.html)

[Office Demand by Tenant Size - East [2026-02-04]](https://realdatallc.github.io/aquila-insights/charts/office/requirements_demand_by_tenant_size_e.html)

[Office Demand by Tenant Size - Central [2026-02-04]](https://realdatallc.github.io/aquila-insights/charts/office/requirements_demand_by_tenant_size_c.html)

### Market Metrics
[Asking vs Effective Rent by Submarket [2026-01-16]](https://realdatallc.github.io/aquila-insights/charts/office/office_asking_vs_effective_rent_by_submarket.html)

[Office Occupancy Rate by Building Size [2026-01-21]](https://realdatallc.github.io/aquila-insights/charts/office/office_occupancy_by_size.html)

[Office Weighted Average Rent by Building Size [2026-01-21]](https://realdatallc.github.io/aquila-insights/charts/office/office_rent_by_size.html)

#### Vacancy Rates (Competitive Set)
[Vacancy Rate — CBD [2026-02-25]](https://realdatallc.github.io/aquila-insights/charts/office/office_vacancy_rate_cbd.html)

[Vacancy Rate — Northwest [2026-02-25]](https://realdatallc.github.io/aquila-insights/charts/office/office_vacancy_rate_northwest.html)

[Vacancy Rate — Southwest [2026-02-25]](https://realdatallc.github.io/aquila-insights/charts/office/office_vacancy_rate_southwest.html)

[Vacancy Rate — The Domain [2026-02-25]](https://realdatallc.github.io/aquila-insights/charts/office/office_vacancy_rate_domain.html)

#### Rental Rates (Competitive Set)
[Rental Rate — CBD [2026-02-25]](https://realdatallc.github.io/aquila-insights/charts/office/office_rental_rate_cbd.html)

[Rental Rate — Northwest [2026-02-25]](https://realdatallc.github.io/aquila-insights/charts/office/office_rental_rate_northwest.html)

[Rental Rate — Southwest [2026-02-25]](https://realdatallc.github.io/aquila-insights/charts/office/office_rental_rate_southwest.html)

[Rental Rate — The Domain [2026-02-25]](https://realdatallc.github.io/aquila-insights/charts/office/office_rental_rate_domain.html)

#### Operating Expenses (Competitive Set)
[Operating Expenses — CBD [2026-02-25]](https://realdatallc.github.io/aquila-insights/charts/office/office_opex_cbd.html)

[Operating Expenses — Northwest [2026-02-25]](https://realdatallc.github.io/aquila-insights/charts/office/office_opex_northwest.html)

[Operating Expenses — Southwest [2026-02-25]](https://realdatallc.github.io/aquila-insights/charts/office/office_opex_southwest.html)

[Operating Expenses — The Domain [2026-02-25]](https://realdatallc.github.io/aquila-insights/charts/office/office_opex_domain.html)


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
[Industrial Demand by Tenant Size [2026-02-09]](https://realdatallc.github.io/aquila-insights/charts/industrial/industrial_demand_by_tenant_size.html) - Quarterly demand grouped by size category with total demand line

[Industrial Demand by Use Type [2026-02-09]](https://realdatallc.github.io/aquila-insights/charts/industrial/industrial_demand_by_use_type.html) - Distribution, Manufacturing, R&D/Lab, etc.

[Industrial Requirements by Size Range [2026-02-09]](https://realdatallc.github.io/aquila-insights/charts/industrial/industrial_requirements_by_size_range.html) - Total cumulative SF by size category

[Industrial Requirements Total SF [2026-02-09]](https://realdatallc.github.io/aquila-insights/charts/industrial/industrial_requirements_sf_total.html) - Monthly total SF (Low/High)

[Industrial Requirements Average SF [2026-02-09]](https://realdatallc.github.io/aquila-insights/charts/industrial/industrial_requirements_sf_avg.html) - Monthly average SF with record count

### Market Metrics
[NNN Rental Rates by Submarket [2026-02-19]](https://realdatallc.github.io/aquila-insights/charts/industrial/industrial_nnn_rent_by_submarket.html)

[Vacancy Rate by Submarket [2026-01-16]](https://realdatallc.github.io/aquila-insights/charts/industrial/vacancy_rate_industrial.html)

[Industrial Occupancy Rate by Building Size [2026-01-21]](https://realdatallc.github.io/aquila-insights/charts/industrial/industrial_occupancy_by_size.html)

[Industrial Weighted Average Rent by Building Size [2026-01-21]](https://realdatallc.github.io/aquila-insights/charts/industrial/industrial_rent_by_size.html)

## Economic Indicators

### Employment
[Austin Employment - Office Sectors [2026-01-21]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_employment_office_sectors.html)

[Austin Employment - Industrial Sector [2026-01-21]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_employment_industrial.html)

[Austin Employment - Retail Sector [2026-01-21]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_employment_retail.html)

[Austin vs National Tech Employment Growth [2026-01-21]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_vs_national_tech_employment.html)

### Wages
[Austin vs Dallas vs National Wage Growth [2026-01-21]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_vs_dallas_vs_national_wage_growth.html)

### Financial Indicators
[Interest Rates - Treasury & Mortgage [2026-01-21]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/interest_rates_treasury_mortgage.html)

[Inflation & PPI - CPI and Office Construction Costs [2026-01-21]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/inflation_cpi_ppi_office.html)

### Housing Indicators
[Austin Housing Starts (Monthly) [2026-01-16]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_housing_starts.html)

## Austin Economy

### Industries and Companies That Came to Austin in 2025
[Jobs Created by Industry — Austin Region 2025 [2026-02-25]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_2025_jobs_by_industry.html)

[New Relocations vs. Expansions by Industry — Austin 2025 [2026-02-25]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_2025_new_vs_expanded.html)

[Jobs by Location — Austin Region 2025 [2026-02-25]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_2025_jobs_by_location.html)

[Headquarters vs. Branch/Production Jobs by Industry — Austin 2025 [2026-02-25]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_2025_hq_activity.html)

[Monthly Jobs Announced — Austin Region 2025 [2026-02-25]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_2025_jobs_by_month.html)

[Top 10 Companies by Jobs Created — Austin 2025 [2026-02-25]](https://realdatallc.github.io/aquila-insights/charts/economic-indicators/austin_2025_top_companies.html)

## Development & Permitting

### Development Pipeline Analysis
[Pipeline Volume by Quarter [2026-02-10]](https://realdatallc.github.io/aquila-insights/charts/development/pipeline_volume_by_quarter.html) - Total proposed SF by quarter and permit status (2015-present)

[Pipeline by Land Use Type [2026-02-10]](https://realdatallc.github.io/aquila-insights/charts/development/pipeline_by_land_use_type.html) - Development activity by CRE sector (Office, Industrial, Retail, Mixed-Use, etc.)

[Pipeline by Neighborhood [2026-02-10]](https://realdatallc.github.io/aquila-insights/charts/development/pipeline_by_neighborhood.html) - Top 15 neighborhoods by total development SF

[Project Size Distribution [2026-02-10]](https://realdatallc.github.io/aquila-insights/charts/development/project_size_distribution.html) - Distribution of projects by size category (Small to Mega)

### Regulatory & Market Efficiency
[Approval Timeline Trends [2026-02-10]](https://realdatallc.github.io/aquila-insights/charts/development/approval_timeline_trends.html) - Median days to approval by quarter

[Density Trends (FAR) [2026-02-10]](https://realdatallc.github.io/aquila-insights/charts/development/density_trends_far.html) - Floor Area Ratio trends showing development intensity

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
├── dashboards/                # Local interactive Dash apps
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