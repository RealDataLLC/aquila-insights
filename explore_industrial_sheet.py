#!/usr/bin/env python3
"""
Explore industrial demand Google Sheet structure
"""

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv
import os
import pandas as pd

# Load environment
load_dotenv('aquila_graph.env')

def get_google_credentials():
    """Build Google credentials from environment variables"""
    # Get private key and handle escaped newlines and quotes
    private_key = os.getenv("GOOGLE_PRIVATE_KEY", "")
    private_key = private_key.strip('"').replace('\\n', '\n')

    # Helper function to clean env vars (strip quotes)
    def clean_env(key, default=""):
        val = os.getenv(key, default)
        return val.strip('"') if val else default

    credentials_dict = {
        "type": clean_env("GOOGLE_SERVICE_ACCOUNT_TYPE", "service_account"),
        "project_id": clean_env("GOOGLE_PROJECT_ID"),
        "private_key_id": clean_env("GOOGLE_PRIVATE_KEY_ID"),
        "private_key": private_key,
        "client_email": clean_env("GOOGLE_CLIENT_EMAIL"),
        "client_id": clean_env("GOOGLE_CLIENT_ID"),
        "auth_uri": clean_env("GOOGLE_AUTH_URI"),
        "token_uri": clean_env("GOOGLE_TOKEN_URI"),
        "auth_provider_x509_cert_url": clean_env("GOOGLE_AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": clean_env("GOOGLE_CLIENT_X509_CERT_URL"),
        "universe_domain": clean_env("GOOGLE_UNIVERSE_DOMAIN")
    }

    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]

    return ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)

creds = get_google_credentials()
client = gspread.authorize(creds)

# Open the industrial demand spreadsheet
spreadsheet_id = '1natA0ALaQnX3U_vGC5Vrchy1QqmbW8k0zvTKwuE2wys'
sheet = client.open_by_key(spreadsheet_id)

print('Available worksheets:')
for idx, worksheet in enumerate(sheet.worksheets()):
    print(f'  {idx}: {worksheet.title} ({worksheet.row_count} rows x {worksheet.col_count} cols)')

print('\nFetching TITM - Tenants in the Market tab...')
# Find the TITM worksheet
titm_sheet = None
for worksheet in sheet.worksheets():
    if 'TITM' in worksheet.title.upper():
        titm_sheet = worksheet
        break

if titm_sheet:
    print(f'\nFound worksheet: {titm_sheet.title}')
    records = titm_sheet.get_all_records()
    df = pd.DataFrame(records)
    print(f'\nRows: {len(df)}')
    print(f'\nColumns ({len(df.columns)}):')
    for col in df.columns:
        print(f'  - {col}')

    print(f'\nFirst 3 rows:')
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 200)
    print(df.head(3))

    # Check for date columns
    print(f'\n\nDate-related columns:')
    for col in df.columns:
        if any(word in col.upper() for word in ['DATE', 'TIME', 'QUARTER', 'MONTH', 'YEAR']):
            print(f'  - {col}')
            print(f'    Sample values: {df[col].head(5).tolist()}')

    # Check for SF/size columns
    print(f'\n\nSize-related columns:')
    for col in df.columns:
        if any(word in col.upper() for word in ['SF', 'SIZE', 'SQUARE', 'FOOTAGE', 'ACREAGE', 'ACRE']):
            print(f'  - {col}')
            print(f'    Sample values: {df[col].head(5).tolist()}')
else:
    print('ERROR: Could not find TITM worksheet')
