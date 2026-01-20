#!/usr/bin/env python3
"""
Update All Charts
Regenerates all charts from all data sources (Google Sheets, Supabase, FRED)

Usage:
    python3 update_all_charts.py
    python3 update_all_charts.py --update-readme

This script runs:
1. update_google_sheets_charts.py (4 charts)
2. update_supabase_charts.py (1 chart)
3. update_fred_charts.py (1 chart)
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

    # 1. Google Sheets Charts
    results['google_sheets'] = run_script(
        'update_google_sheets_charts.py',
        'Google Sheets Charts (4 charts)'
    )

    # 2. Supabase Charts
    results['supabase'] = run_script(
        'update_supabase_charts.py',
        'Supabase Charts (1 chart)'
    )

    # 3. FRED API Charts
    results['fred'] = run_script(
        'update_fred_charts.py',
        'FRED API Charts (1 chart)'
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

        print("\nTotal charts generated:")
        print("  • requirements_sf_total.html")
        print("  • requirements_sf_avg.html")
        print("  • requirements_sf_avg_by_industry.html")
        print("  • requirements_by_size_range.html")
        print("  • vacancy_rate_industrial.html")
        print("  • austin_housing_starts.html")

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
