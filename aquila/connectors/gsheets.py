"""
Google Sheets connector.
Consolidates the 6 duplicated auth implementations across the codebase.

Supports two credential sources (auto-detected):
1. JSON credentials file (aquilacommercialsheets-923494a59a4b.json)
2. GOOGLE_* environment variables from aquila_graph.env
"""

import os


def get_gsheets_client(json_file='aquilacommercialsheets-923494a59a4b.json'):
    """
    Authenticate and return a gspread client.

    Tries JSON credentials file first, falls back to GOOGLE_* env vars.

    Parameters
    ----------
    json_file : str, optional
        Path to JSON credentials file. Checked relative to repo root.

    Returns
    -------
    gspread.Client
        Authenticated Google Sheets client.

    Raises
    ------
    ImportError
        If gspread or oauth2client are not installed.
    ValueError
        If neither JSON file nor env vars provide valid credentials.

    Examples
    --------
    >>> from aquila.connectors import get_gsheets_client
    >>> client = get_gsheets_client()
    >>> sheet = client.open_by_key('1bzpRnUrpBH6l_zX7DtTypczZf5bpYVwqPUG3tzg2vec')
    """
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials

    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive',
    ]

    # Check for JSON file at repo root
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    json_path = os.path.join(repo_root, json_file)

    if os.path.exists(json_path):
        credentials = ServiceAccountCredentials.from_json_keyfile_name(json_path, scope)
    else:
        # Build credentials from GOOGLE_* environment variables
        def _strip(key):
            val = os.getenv(key)
            if val:
                return val.strip('"').strip("'")
            return val

        private_key = _strip("GOOGLE_PRIVATE_KEY")
        if private_key:
            private_key = private_key.replace('\\n', '\n')

        credentials_dict = {
            "type": _strip("GOOGLE_SERVICE_ACCOUNT_TYPE") or "service_account",
            "project_id": _strip("GOOGLE_PROJECT_ID"),
            "private_key_id": _strip("GOOGLE_PRIVATE_KEY_ID"),
            "private_key": private_key,
            "client_email": _strip("GOOGLE_CLIENT_EMAIL"),
            "client_id": _strip("GOOGLE_CLIENT_ID"),
            "auth_uri": _strip("GOOGLE_AUTH_URI"),
            "token_uri": _strip("GOOGLE_TOKEN_URI"),
            "auth_provider_x509_cert_url": _strip("GOOGLE_AUTH_PROVIDER_X509_CERT_URL"),
            "client_x509_cert_url": _strip("GOOGLE_CLIENT_X509_CERT_URL"),
            "universe_domain": _strip("GOOGLE_UNIVERSE_DOMAIN"),
        }

        if not credentials_dict.get("private_key"):
            raise ValueError(
                "Google Sheets credentials not found. "
                "Provide JSON file or set GOOGLE_* env vars in aquila_graph.env"
            )

        credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)

    return gspread.authorize(credentials)
