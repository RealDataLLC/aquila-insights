Update the quarterly report configuration for a new quarter.

Usage: /update-quarterly-config <year> <quarter>
Example: /update-quarterly-config 2026 1

Steps:
1. Parse the year and quarter from $ARGUMENTS (e.g., "2026 1")
2. Read `reports/report_config.py` and update REPORT_YEAR and REPORT_QUARTER
3. Read `reports/industrial_report_config.py` and update REPORT_YEAR and REPORT_QUARTER
4. Show the user what was changed in both files
5. Verify that the Q: drive paths derived from the new config are valid (check if directories exist)
6. Report any missing source folders that will be needed for report generation
