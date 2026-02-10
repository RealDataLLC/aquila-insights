#!/usr/bin/env python3
"""
Update All Charts
Regenerates all charts from all data sources (Google Sheets, Supabase, FRED)

Usage:
    python3 update_all_charts.py
    python3 update_all_charts.py --update-readme

This script runs:
1. update_office_combined_requirements.py (7 Office requirement charts)
2. update_industrial_vacancy.py (1 Industrial vacancy chart)
3. update_fred_housing_chart.py (1 Housing chart)
4. update_building_performance_charts.py (4 Office & Industrial charts)
5. update_fred_economic_indicators.py (7 Economic charts)
"""

import subprocess
import sys
from datetime import datetime

def run_script(script_name, description):
    """Run a Python script and capture output"""
    print(f"\n{'=' * 70}")
    print(f"Running: {description}")
    print(f"{'=' * 70}\n")

    cmd = ["python3", script_name]
    if '--update-readme' in sys.argv:
        cmd.append('--update-readme')

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,  # Show output in real-time
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n✗ ERROR running {script_name}")
        return False

def main():
    """Main execution"""
    print("=" * 70)
    print("UPDATING ALL CHARTS")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    results = {}

    # 1. Office Combined Requirements Charts (Google Sheets)
    results['office_requirements'] = run_script(
        'update_office_combined_requirements.py',
        'Office Combined Requirements (7 charts)'
    )

    # 2. Industrial Vacancy Charts (Supabase)
    results['industrial_vacancy'] = run_script(
        'update_industrial_vacancy.py',
        'Industrial Vacancy (1 chart)'
    )

    # 3. FRED Housing Chart
    results['fred_housing'] = run_script(
        'update_fred_housing_chart.py',
        'FRED Housing Starts (1 chart)'
    )

    # 4. Building Performance Charts (Supabase - Office & Industrial)
    results['building_performance'] = run_script(
        'update_building_performance_charts.py',
        'Building Performance by Size (4 charts)'
    )

    # 5. FRED Economic Indicators
    results['fred_economic'] = run_script(
        'update_fred_economic_indicators.py',
        'FRED Economic Indicators (7 charts)'
    )

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    success_count = sum(results.values())
    total_count = len(results)

    print(f"\nCompleted: {success_count}/{total_count} data sources")
    print("\nResults:")
    for source, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"  {status}: {source}")

    if success_count == total_count:
        print("\n✓ ALL CHARTS UPDATED SUCCESSFULLY")

        print("\nTotal charts generated (20 charts):")
        print("\n  Office Requirements (7):")
        print("    • requirements_sf_total.html")
        print("    • requirements_sf_avg.html")
        print("    • requirements_sf_avg_by_industry.html")
        print("    • requirements_by_size_range.html")
        print("    • requirements_vs_absorption_office.html")
        print("    • requirements_yoy_rolling_12m.html")
        print("    • requirements_demand_by_tenant_size.html")
        print("\n  Industrial (1):")
        print("    • vacancy_rate_industrial.html")
        print("\n  Building Performance (4):")
        print("    • office_occupancy_by_size.html")
        print("    • office_rent_by_size.html")
        print("    • industrial_occupancy_by_size.html")
        print("    • industrial_rent_by_size.html")
        print("\n  Economic Indicators (8):")
        print("    • austin_housing_starts.html")
        print("    • austin_employment_office_sectors.html")
        print("    • austin_employment_industrial.html")
        print("    • austin_employment_retail.html")
        print("    • austin_vs_national_tech_employment.html")
        print("    • austin_vs_dallas_vs_national_wage_growth.html")
        print("    • interest_rates_treasury_mortgage.html")
        print("    • inflation_cpi_ppi_office.html")

        if '--update-readme' in sys.argv:
            print("\n✓ README.md dates updated")

        print("\nNext steps:")
        print("  1. Review all charts in browser")
        print("  2. Commit: git add charts/ README.md && git commit -m 'Update all charts'")
        print("  3. Push: git push")
        print("")

        sys.exit(0)
    else:
        print("\n⚠ SOME UPDATES FAILED")
        print("Check error messages above for details")
        print("")
        sys.exit(1)

if __name__ == '__main__':
    main()
