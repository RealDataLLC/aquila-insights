"""
Explore both tabs of the Google Sheets to understand column structures
"""
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('aquila_graph.env')

# Build service account credentials from environment
credentials_dict = {
    "type": os.getenv("GOOGLE_SERVICE_ACCOUNT_TYPE"),
    "project_id": os.getenv("GOOGLE_PROJECT_ID"),
    "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("GOOGLE_PRIVATE_KEY").replace('\\n', '\n'),
    "client_email": os.getenv("GOOGLE_CLIENT_EMAIL"),
    "client_id": os.getenv("GOOGLE_CLIENT_ID"),
    "auth_uri": os.getenv("GOOGLE_AUTH_URI"),
    "token_uri": os.getenv("GOOGLE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("GOOGLE_AUTH_PROVIDER_X509_CERT_URL"),
    "client_x509_cert_url": os.getenv("GOOGLE_CLIENT_X509_CERT_URL"),
    "universe_domain": os.getenv("GOOGLE_UNIVERSE_DOMAIN")
}

scope = [
    'https://spreadsheets.google.com/feeds',
    'https://www.googleapis.com/auth/drive'
]

creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client = gspread.authorize(creds)

# Open spreadsheet
spreadsheet_id = '1bzpRnUrpBH6l_zX7DtTypczZf5bpYVwqPUG3tzg2vec'
sheet = client.open_by_key(spreadsheet_id)

# Get all worksheets
worksheets = sheet.worksheets()
print(f"Found {len(worksheets)} worksheets:\n")

for i, ws in enumerate(worksheets):
    print(f"Tab {i}: '{ws.title}'")
    print(f"  Rows: {ws.row_count}, Columns: {ws.col_count}")

print("\n" + "="*80)

# Read Tab 0: "2025 +"
print("\nTAB 0 - '2025 +' (Current data)")
print("="*80)
tab0 = sheet.get_worksheet(0)
df_2025_plus = pd.DataFrame(tab0.get_all_records())
print(f"\nShape: {df_2025_plus.shape}")
print(f"\nColumns ({len(df_2025_plus.columns)}):")
for col in df_2025_plus.columns:
    print(f"  - {col}")
print(f"\nFirst few rows:")
print(df_2025_plus.head(3))
print(f"\nDate range: {df_2025_plus['DATE OF REQUIREMENT'].min()} to {df_2025_plus['DATE OF REQUIREMENT'].max()}")

print("\n" + "="*80)

# Read Tab 1: "DITM & Crab Trap MASTER Report (Through 2024)"
print("\nTAB 1 - 'Through 2024' (Historical data)")
print("="*80)
tab1 = sheet.get_worksheet(1)
df_through_2024 = pd.DataFrame(tab1.get_all_records())
print(f"\nShape: {df_through_2024.shape}")
print(f"\nColumns ({len(df_through_2024.columns)}):")
for col in df_through_2024.columns:
    print(f"  - {col}")
print(f"\nFirst few rows:")
print(df_through_2024.head(3))

# Try to identify date column
date_cols = [col for col in df_through_2024.columns if 'DATE' in col.upper() or 'TIMING' in col.upper()]
print(f"\nPotential date columns: {date_cols}")

print("\n" + "="*80)
print("\nCOLUMN COMPARISON")
print("="*80)

# Find common columns
cols_2025 = set(df_2025_plus.columns)
cols_2024 = set(df_through_2024.columns)

common = cols_2025.intersection(cols_2024)
only_2025 = cols_2025 - cols_2024
only_2024 = cols_2024 - cols_2025

print(f"\nCommon columns ({len(common)}):")
for col in sorted(common):
    print(f"  ✓ {col}")

print(f"\nOnly in 2025+ tab ({len(only_2025)}):")
for col in sorted(only_2025):
    print(f"  + {col}")

print(f"\nOnly in Through 2024 tab ({len(only_2024)}):")
for col in sorted(only_2024):
    print(f"  - {col}")

print("\n" + "="*80)
print("\nKEY COLUMNS FOR MAPPING")
print("="*80)

# Check for SF-related columns
print("\nSquare footage columns:")
print("  2025+ tab:")
sf_cols_2025 = [col for col in df_2025_plus.columns if 'SF' in col.upper() or 'SQUARE' in col.upper()]
for col in sf_cols_2025:
    print(f"    - {col}")

print("  Through 2024 tab:")
sf_cols_2024 = [col for col in df_through_2024.columns if 'SF' in col.upper() or 'SQUARE' in col.upper()]
for col in sf_cols_2024:
    print(f"    - {col}")
