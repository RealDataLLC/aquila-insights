Run chart generators and commit the results.

Usage: /update-charts [group]
- No argument: run all 13 generators (~59 charts)
- group: office, industrial, economic, property_mgmt, development

Steps:
1. Run `PYTHONUTF8=1 python update_all_charts.py` (or with `--group $ARGUMENTS` if a group is specified)
2. Check for errors in the output
3. If successful, show which chart HTML files were modified using `git status`
4. Ask the user if they want to commit and push the changes
5. If yes, commit with message "Update [group] charts [date]" and push
