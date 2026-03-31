#!/usr/bin/env python3
"""
Update All Charts
Regenerates all charts from all data sources (Google Sheets, Supabase, FRED).

Usage:
    python update_all_charts.py                   # Run all generators
    python update_all_charts.py --group office     # Office charts only
    python update_all_charts.py --group industrial # Industrial charts only
    python update_all_charts.py --group economic   # Economic charts only
    python update_all_charts.py --update-readme    # Also update README dates

Generators:
  office:      requirements (7), building_performance (2), market_metrics (12),
               demand_by_market (5), transactions (2)
  industrial:  vacancy (1), building_performance (2), demand (5), nnn_rent (1)
  economic:    fred_indicators (7), fred_housing (1), austin_economy (6), census_office (10)
  property_mgmt: ams_kpi (1)
  development: permits (2)
"""

import sys
import os
import argparse
import traceback
from datetime import datetime

# Ensure repo root is on sys.path so generators can resolve aquila imports
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


# ── Generator registry ──────────────────────────────────────────────────────
# Each entry: (module_path, description, group)

GENERATORS = [
    # --- Office ---
    ('generators.office.requirements',          'Office Combined Requirements (7 charts)',       'office'),
    ('generators.office.building_performance',   'Building Performance by Size (4 charts)',       'office'),
    ('generators.office.market_metrics',         'Office Market Metrics (12 charts)',             'office'),
    ('generators.office.demand_by_market',       'Office Demand by Market (5 charts)',            'office'),
    ('generators.office.transactions',           'Office Transaction Charts (2 charts)',          'office'),
    # --- Industrial ---
    ('generators.industrial.vacancy',            'Industrial Vacancy (1 chart)',                  'industrial'),
    ('generators.industrial.demand',             'Industrial Demand Charts (5 charts)',           'industrial'),
    ('generators.industrial.nnn_rent',           'Industrial NNN Rent (1 chart)',                 'industrial'),
    # --- Economic ---
    ('generators.economic.fred_indicators',      'FRED Economic Indicators (7 charts)',           'economic'),
    ('generators.economic.fred_housing',         'FRED Housing Starts (1 chart)',                 'economic'),
    ('generators.economic.austin_economy',       'Austin Economy Charts (6 charts)',              'economic'),
    ('generators.economic.census_office',        'Census + LODES Office Market Charts (10 charts)', 'economic'),
    # --- Property Management ---
    ('generators.property_mgmt.ams_kpi',         'AMS KPI Chart (1 chart)',                      'property_mgmt'),
    # --- Development ---
    ('generators.development.permits',           'Austin Permits Charts (2 charts)',              'development'),
]

GROUPS = sorted(set(g for _, _, g in GENERATORS))


def run_generator(module_path, description):
    """Import a generator module and call its main() function."""
    print(f"\n{'=' * 70}")
    print(f"Running: {description}")
    print(f"  Module: {module_path}")
    print(f"{'=' * 70}\n")

    try:
        # Clear cached sys.argv so generators that use argparse don't choke
        saved_argv = sys.argv
        sys.argv = [module_path]

        mod = __import__(module_path, fromlist=['main'])
        mod.main()

        sys.argv = saved_argv
        return True

    except SystemExit as e:
        sys.argv = saved_argv
        # Some generators call sys.exit(0) on success
        if e.code == 0 or e.code is None:
            return True
        print(f"\n[ERROR] {module_path} exited with code {e.code}")
        return False

    except Exception:
        sys.argv = saved_argv
        print(f"\n[ERROR] {module_path} failed:")
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='Update all Aquila Insights charts')
    parser.add_argument('--group', choices=GROUPS,
                        help='Run only generators in this group')
    parser.add_argument('--update-readme', action='store_true',
                        help='Update README.md dates after generation')
    args = parser.parse_args()

    generators = GENERATORS
    if args.group:
        generators = [(m, d, g) for m, d, g in GENERATORS if g == args.group]

    print("=" * 70)
    print("UPDATING ALL CHARTS" if not args.group else f"UPDATING {args.group.upper()} CHARTS")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Generators to run: {len(generators)}")
    print("=" * 70)

    results = {}
    for module_path, description, _group in generators:
        results[module_path] = run_generator(module_path, description)

    # ── Summary ──────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    success_count = sum(results.values())
    total_count = len(results)

    print(f"\nCompleted: {success_count}/{total_count} generators")
    print("\nResults:")
    for module_path, success in results.items():
        status = "[OK]" if success else "[FAILED]"
        print(f"  {status}  {module_path}")

    if success_count == total_count:
        print(f"\n[OK] ALL {total_count} GENERATORS COMPLETED SUCCESSFULLY")
    else:
        failed = [m for m, s in results.items() if not s]
        print(f"\n[WARN] {len(failed)} generator(s) FAILED:")
        for m in failed:
            print(f"  - {m}")

    print(f"\nFinished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    sys.exit(0 if success_count == total_count else 1)


if __name__ == '__main__':
    main()
