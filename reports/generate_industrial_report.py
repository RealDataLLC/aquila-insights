"""
Main orchestrator for AQUILA Industrial Quarterly Report generation.

Usage:
    python reports/generate_industrial_report.py                  # Full PDF
    python reports/generate_industrial_report.py --html-only      # HTML preview only
    python reports/generate_industrial_report.py --skip-charts    # Reuse existing chart PNGs
    python reports/generate_industrial_report.py --skip-cleanup   # Skip data cleanup step
"""
import os
import sys
import argparse

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reports import industrial_report_config as config
from reports.industrial_data_loader import load_all_data
from reports.industrial_chart_builder import generate_all_charts
from reports.industrial_report_assembler import generate_report


def main():
    parser = argparse.ArgumentParser(description='Generate AQUILA Industrial Quarterly Report')
    parser.add_argument('--html-only', action='store_true',
                        help='Generate HTML only (no PDF conversion)')
    parser.add_argument('--skip-charts', action='store_true',
                        help='Skip chart generation (reuse existing PNGs)')
    parser.add_argument('--skip-cleanup', action='store_true',
                        help='Skip pre-report data cleanup step')
    args = parser.parse_args()

    print("=" * 60)
    print(f"AQUILA Industrial Quarterly Report - {config.REPORT_LABEL}")
    print("=" * 60)

    # Step 0: Data cleanup (abbreviation standardization)
    if not args.skip_cleanup:
        try:
            from reports.cleanup_quarterly_data import run_cleanup
            run_cleanup(config)
        except Exception as e:
            print(f"\n  Warning: Data cleanup failed ({e}), continuing...")
    else:
        print("\n  --skip-cleanup: Skipping data cleanup step")

    # Step 1: Load all data
    data = load_all_data(config)

    # Step 2: Generate charts (or skip if reusing)
    if args.skip_charts:
        print("\n  --skip-charts: Reusing existing chart PNGs")
        charts = _find_existing_charts(config.CHARTS_DIR)
    else:
        print("\n  Generating charts...")
        charts = generate_all_charts(data, config)

    # Step 3: Assemble report
    output = generate_report(data, charts, config, html_only=args.html_only)

    print(f"\n  Output: {output}")
    return output


def _find_existing_charts(charts_dir):
    """Scan charts_dir for existing PNGs and rebuild the chart paths dict.

    Chart files are named: {submarket}_{property_type}_{chart_type}.png
    e.g. regional_industrial_vacancy_sf.png -> key "Regional_Industrial"
    """
    charts = {}
    if not os.path.exists(charts_dir):
        print(f"  Warning: Charts directory not found: {charts_dir}")
        return charts

    # Build prefix-to-key mapping from config
    prefix_to_key = {}
    # Regional charts
    for ptype in config.PROPERTY_TYPES:
        prefix = f"regional_{ptype}".replace(' ', '_').lower()
        prefix_to_key[prefix] = f"Regional_{ptype}"
    # Submarket charts
    for sub in config.SUBMARKETS:
        for ptype in config.PROPERTY_TYPES:
            prefix = f"{sub}_{ptype}".replace(' ', '_').lower()
            prefix_to_key[prefix] = f"{sub}_{ptype}"

    for filename in os.listdir(charts_dir):
        if not filename.endswith('.png'):
            continue
        filepath = os.path.join(charts_dir, filename)
        name = filename.replace('.png', '')

        # Regional comparison charts (standalone paths, not nested dicts)
        if name.startswith('regional_comparison_'):
            charts[name] = filepath
        else:
            # Performance charts (nested dicts keyed by chart type)
            for chart_type in ['vacancy_sf', 'absorption', 'rental']:
                if name.endswith(f'_{chart_type}'):
                    file_prefix = name[:-(len(chart_type) + 1)]
                    key = prefix_to_key.get(file_prefix, file_prefix)
                    if key not in charts:
                        charts[key] = {}
                    charts[key][chart_type] = filepath

    print(f"  Found {sum(len(v) if isinstance(v, dict) else 1 for v in charts.values())} existing chart PNGs")
    return charts


if __name__ == '__main__':
    main()
