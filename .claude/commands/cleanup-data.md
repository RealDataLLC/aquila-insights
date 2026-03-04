Run the quarterly data cleanup script for report preparation.

Usage: /cleanup-data [mode]
- No argument: dry-run (preview changes without writing)
- apply: apply changes to files

Steps:
1. Check which report type is active by reading `reports/report_config.py`
2. Run the appropriate command:
   - default (dry-run): `PYTHONUTF8=1 python reports/cleanup_quarterly_data.py --dry-run`
   - apply: `PYTHONUTF8=1 python reports/cleanup_quarterly_data.py`
3. Summarize what changes were found or applied:
   - Abbreviation standardization (Dr., Blvd., Pkwy., etc.)
   - Major Leases sorting and name matching
   - Major Sales consolidation
   - Pipeline verification warnings
   - Proposed sorting
