"""
Main orchestrator for AQUILA Office Quarterly Report generation.

Usage:
    python reports/generate_office_report.py                  # Full PDF
    python reports/generate_office_report.py --html-only      # HTML preview only
    python reports/generate_office_report.py --skip-charts     # Reuse existing chart PNGs
"""
import os
import sys
import argparse

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reports import report_config as config
from reports.data_loader import load_all_data
from reports.chart_builder import generate_all_charts
from reports.report_assembler import generate_report


def main():
    parser = argparse.ArgumentParser(description='Generate AQUILA Office Quarterly Report')
    parser.add_argument('--html-only', action='store_true',
                        help='Generate HTML only (no PDF conversion)')
    parser.add_argument('--skip-charts', action='store_true',
                        help='Skip chart generation (reuse existing PNGs)')
    args = parser.parse_args()

    print("=" * 60)
    print(f"AQUILA Office Quarterly Report - {config.REPORT_LABEL}")
    print("=" * 60)

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

    Chart files are named: {submarket}_{table_type}_{chart_type}.png
    e.g. citywide_overall_vacancy_sf.png → key "Citywide_overall"

    The assembler looks up charts by keys like "Citywide_overall",
    "CBD_competitive set", "Domain_micromarket", etc. We must map
    the lowercased/underscored filenames back to these keys.
    """
    charts = {}
    if not os.path.exists(charts_dir):
        print(f"  Warning: Charts directory not found: {charts_dir}")
        return charts

    # Build a mapping from lowercased file prefix → proper key
    # The generate_performance_charts uses: prefix = f"{submarket}_{table_type}".replace(' ', '_').lower()
    # We need the reverse mapping. Build it from config.
    from reports import report_config as cfg
    prefix_to_key = {}
    for sub in cfg.SUBMARKETS_COMP:
        ttype = 'overall' if sub == 'Citywide' else 'competitive set'
        prefix = f"{sub}_{ttype}".replace(' ', '_').lower()
        prefix_to_key[prefix] = f"{sub}_{ttype}"
    for micro in cfg.MICROMARKETS:
        prefix = f"{micro}_micromarket".replace(' ', '_').lower()
        prefix_to_key[prefix] = f"{micro}_micromarket"
    for sub in cfg.SUBMARKETS_OVERALL:
        prefix = f"{sub}_overall".replace(' ', '_').lower()
        prefix_to_key[prefix] = f"{sub}_overall"

    for filename in os.listdir(charts_dir):
        if not filename.endswith('.png'):
            continue
        filepath = os.path.join(charts_dir, filename)
        name = filename.replace('.png', '')

        # Performance charts
        for chart_type in ['vacancy_sf', 'absorption', 'rental']:
            if name.endswith(f'_{chart_type}'):
                file_prefix = name[:-(len(chart_type) + 1)]
                key = prefix_to_key.get(file_prefix, file_prefix)
                if key not in charts:
                    charts[key] = {}
                charts[key][chart_type] = filepath

        # Long-term charts
        if name.startswith('lt_'):
            if 'long_term' not in charts:
                charts['long_term'] = {}
            charts['long_term'][name] = filepath

    return charts


if __name__ == '__main__':
    main()
