"""
Pre-report data cleanup for AQUILA Office Quarterly Report.

Runs before generate_office_report.py to:
  1. Standardize street abbreviations and cardinal directions in address/name columns
     across all quarterly Excel and CSV files.
  2. Ensure the Major Leases and Sales file has a 'Vertical Format' tab derived
     from the 'Major Sales' sheet (creates it if missing).

Usage:
    python reports/cleanup_quarterly_data.py          # uses report_config paths
    python reports/cleanup_quarterly_data.py --dry-run  # preview only, no writes
"""

import os
import re
import sys
import argparse

import pandas as pd
import openpyxl

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from reports import report_config as config


# ---------------------------------------------------------------------------
# Abbreviation standardization
# ---------------------------------------------------------------------------

# Patterns applied in order. Each key is a regex pattern; value is replacement.
# The regex uses \b word boundaries so we don't clobber partial words.
# Replacements that already end with '.' are left untouched (the lookahead below
# ensures we only replace when NOT already followed by '.').
ABBREVIATIONS = {
    r'\bDr\b':   'Dr.',
    r'\bBlvd\b': 'Blvd.',
    r'\bLn\b':   'Ln.',
    r'\bRd\b':   'Rd.',
    r'\bSt\b':   'St.',
    r'\bCv\b':   'Cv.',
    r'\bAve\b':  'Ave.',
    r'\bPkwy\b': 'Pkwy.',
    r'\bCir\b':  'Cir.',
    r'\bCt\b':   'Ct.',
    r'\bPl\b':   'Pl.',
    r'\bTer\b':  'Ter.',
    r'\bWy\b':   'Wy.',
    r'\bTrl\b':  'Trl.',
    r'\bHwy\b':  'Hwy.',
    r'\bSq\b':   'Sq.',
    r'\bLp\b':   'Lp.',
    # Cardinal directions — negative lookbehind (?<!\.) prevents expanding
    # a letter that already follows a period (e.g. "Bldg. E" stays "Bldg. E")
    r'(?<!\.)\bN\b':    'N.',
    r'(?<!\.)\bS\b':    'S.',
    r'(?<!\.)\bE\b':    'E.',
    r'(?<!\.)\bW\b':    'W.',
    r'\bNE\b':   'N.E.',
    r'\bNW\b':   'N.W.',
    r'\bSE\b':   'S.E.',
    r'\bSW\b':   'S.W.',
}

# Column name patterns that should be standardized (case-insensitive)
ADDRESS_COLUMN_PATTERNS = [
    r'property[\s_]*name',
    r'property[\s_]*address',
    r'building[\s_]*park',
    r'building[\s_]*name',
    r'tenant',
]


def standardize_abbreviations(text):
    """Add periods to common street abbreviations and cardinal directions."""
    if pd.isna(text) or not isinstance(text, str):
        return text
    result = text
    for pattern, replacement in ABBREVIATIONS.items():
        # Only replace when NOT already followed by a period
        result = re.sub(f'{pattern}(?!\\.)', replacement, result, flags=re.IGNORECASE)
    return result


def find_address_columns(columns):
    """Return list of column names matching address/name patterns."""
    matching = []
    for col in columns:
        col_norm = str(col).lower().replace(' ', '_')
        for pat in ADDRESS_COLUMN_PATTERNS:
            if re.search(pat, col_norm):
                matching.append(col)
                break
    return matching


def _apply_to_worksheet(ws, dry_run=False):
    """
    Apply abbreviation standardization to visible address columns in an openpyxl worksheet.
    Returns count of cells changed.
    """
    # Read header row (row 1) to find address columns
    header = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
    address_col_indices = []  # 1-based column indices
    for i, col_name in enumerate(header, start=1):
        if col_name is None:
            continue
        col_norm = str(col_name).lower().replace(' ', '_')
        for pat in ADDRESS_COLUMN_PATTERNS:
            if re.search(pat, col_norm):
                address_col_indices.append(i)
                break

    changed = 0
    for row_idx in range(2, ws.max_row + 1):
        for col_idx in address_col_indices:
            cell = ws.cell(row=row_idx, column=col_idx)
            original = cell.value
            updated = standardize_abbreviations(original)
            if updated != original:
                if not dry_run:
                    cell.value = updated
                changed += 1
    return changed


def process_excel_file(path, dry_run=False):
    """Standardize address abbreviations across all visible sheets of an Excel file."""
    wb = openpyxl.load_workbook(path, data_only=False)
    visible_sheets = [ws for ws in wb.worksheets if ws.sheet_state == 'visible']
    total_changed = 0

    for ws in visible_sheets:
        n = _apply_to_worksheet(ws, dry_run=dry_run)
        if n:
            print(f"    Sheet '{ws.title}': {n} cell(s) updated")
            total_changed += n

    if total_changed and not dry_run:
        wb.save(path)
    return total_changed


def process_csv_file(path, dry_run=False):
    """Standardize address abbreviations in address columns of a CSV file."""
    df = pd.read_csv(path)
    cols = find_address_columns(df.columns)
    total_changed = 0

    for col in cols:
        original = df[col].copy()
        df[col] = df[col].apply(standardize_abbreviations)
        n = (df[col] != original).sum()
        if n:
            print(f"    Column '{col}': {n} cell(s) updated")
            total_changed += n

    if total_changed and not dry_run:
        df.to_csv(path, index=False)
    return total_changed


# ---------------------------------------------------------------------------
# Vertical Format tab for Major Sales
# ---------------------------------------------------------------------------

VERTICAL_SHEET_NAME = 'Vertical Format'


def _ensure_vertical_format(path, dry_run=False):
    """
    Check if the Major Leases and Sales workbook already has a 'Vertical Format'
    sheet. If not, create one from the 'Major Sales' sheet with a vertical key-value
    layout (sorted by square footage descending).
    """
    wb = openpyxl.load_workbook(path, data_only=False)

    if VERTICAL_SHEET_NAME in wb.sheetnames:
        print(f"    '{VERTICAL_SHEET_NAME}' tab already exists — skipping.")
        return False

    if 'Major Sales' not in wb.sheetnames:
        print(f"    'Major Sales' sheet not found in {os.path.basename(path)} — skipping vertical format.")
        return False

    print(f"    Creating '{VERTICAL_SHEET_NAME}' tab from 'Major Sales'...")

    # Read Major Sales into a DataFrame
    df = pd.read_excel(path, sheet_name='Major Sales')

    # Sort by square footage descending (try common column names)
    for sf_col in ('Square Feet', 'Size', 'SF', 'GLA'):
        if sf_col in df.columns:
            df = df.sort_values(sf_col, ascending=False)
            df[sf_col] = df[sf_col].apply(
                lambda x: f"{int(x):,}" if pd.notna(x) and str(x).replace('.', '', 1).isdigit()
                else x
            )
            break

    # Build vertical key-value rows
    vertical_rows = []
    for i, (_, row) in enumerate(df.iterrows()):
        if i > 0:
            vertical_rows.append(('', ''))  # blank separator between records
        for col_name, value in row.items():
            vertical_rows.append((col_name, value))

    if dry_run:
        print(f"    [dry-run] Would add {len(df)} records ({len(vertical_rows)} rows) to '{VERTICAL_SHEET_NAME}'.")
        return False

    # Add the new sheet
    ws_vert = wb.create_sheet(VERTICAL_SHEET_NAME)
    ws_vert.append(['Attribute', 'Value'])  # header
    for row in vertical_rows:
        ws_vert.append(list(row))

    wb.save(path)
    print(f"    Added '{VERTICAL_SHEET_NAME}' with {len(df)} sale records.")
    return True


# ---------------------------------------------------------------------------
# Main cleanup orchestrator
# ---------------------------------------------------------------------------

def _get_files_to_process(cfg):
    """Return list of (label, path, is_major_leases_sales) for all quarterly Excel/CSV files."""
    files = [
        ('Major Leases & Sales', cfg.MAJOR_LEASES_SALES, True),
        ('Office Availability',   cfg.OFFICE_AVAIL,         False),
        ('Building List',         cfg.BUILDING_LIST,         False),
        ('Citywide Pipeline',     cfg.CITYWIDE_PIPELINE,     False),
    ]

    # Quarterly Changes CSV files
    qc_dir = cfg.QUARTERLY_CHANGES_DIR
    if os.path.isdir(qc_dir):
        for fname in sorted(os.listdir(qc_dir)):
            if fname.lower().endswith('.csv'):
                files.append((fname, os.path.join(qc_dir, fname), False))

    return files


def run_cleanup(cfg=None, dry_run=False):
    """
    Main entry point.
    cfg: report_config module (defaults to imported config).
    dry_run: if True, report changes without writing files.
    """
    if cfg is None:
        cfg = config

    label = '[DRY RUN] ' if dry_run else ''
    print('=' * 60)
    print(f'{label}QUARTERLY DATA CLEANUP — {cfg.REPORT_LABEL}')
    print('=' * 60)

    files = _get_files_to_process(cfg)
    total_files = 0
    total_changes = 0

    for label_name, path, is_major_leases in files:
        if not os.path.exists(path):
            print(f"  [SKIP] {label_name}: file not found")
            print(f"         {path}")
            continue

        print(f"\n  Processing: {label_name}")
        ext = os.path.splitext(path)[1].lower()

        if ext in ('.xlsx', '.xls'):
            n = process_excel_file(path, dry_run=dry_run)
            if is_major_leases:
                _ensure_vertical_format(path, dry_run=dry_run)
        elif ext == '.csv':
            n = process_csv_file(path, dry_run=dry_run)
        else:
            print(f"    Unsupported file type: {ext}")
            continue

        total_files += 1
        total_changes += n
        if n == 0:
            print(f"    No address changes needed.")

    print()
    print('=' * 60)
    action = 'Would update' if dry_run else 'Updated'
    print(f'CLEANUP COMPLETE — {action} {total_changes} cell(s) across {total_files} file(s)')
    print('=' * 60)
    return total_changes


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Clean up quarterly report source data')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without writing files')
    args = parser.parse_args()
    run_cleanup(dry_run=args.dry_run)
