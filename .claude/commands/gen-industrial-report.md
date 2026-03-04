Generate the Industrial Quarterly Report PDF.

Usage: /gen-industrial-report [flags]
- No argument: full generation (cleanup + charts + PDF)
- html: HTML-only preview (--html-only)
- fast: HTML-only with existing charts (--html-only --skip-charts)
- pdf-only: Full PDF with existing charts (--skip-charts)

Steps:
1. Check that `reports/industrial_report_config.py` has the correct REPORT_YEAR and REPORT_QUARTER
2. Run the appropriate command based on the flag:
   - default: `PYTHONUTF8=1 python reports/generate_industrial_report.py`
   - html: `PYTHONUTF8=1 python reports/generate_industrial_report.py --html-only`
   - fast: `PYTHONUTF8=1 python reports/generate_industrial_report.py --html-only --skip-charts`
   - pdf-only: `PYTHONUTF8=1 python reports/generate_industrial_report.py --skip-charts`
3. Report any errors encountered
4. Show the output file path when complete
