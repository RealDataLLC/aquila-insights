"""
Date and quarter parsing utilities.
Consolidates the 7 duplicated quarter-parsing implementations across the codebase.
"""

import re
import pandas as pd


def parse_quarter(q_str):
    """
    Convert a quarter string to a pandas Timestamp.

    Parameters
    ----------
    q_str : str
        Quarter string like '2025 Q4', '2025Q4', '2025 q4'

    Returns
    -------
    pd.Timestamp or pd.NaT
        First day of the quarter (e.g., 2025-10-01 for Q4)

    Examples
    --------
    >>> parse_quarter('2025 Q4')
    Timestamp('2025-10-01 00:00:00')
    >>> parse_quarter('2019 Q1')
    Timestamp('2019-01-01 00:00:00')
    """
    m = re.match(r'(\d{4})\s*[Qq](\d)', str(q_str))
    if m:
        year, q = int(m.group(1)), int(m.group(2))
        return pd.Timestamp(year=year, month=(q - 1) * 3 + 1, day=1)
    return pd.NaT


def quarter_sort_key(q_str):
    """
    Convert a quarter string to a sortable float.

    Parameters
    ----------
    q_str : str
        Quarter string like '2025 Q4'

    Returns
    -------
    float
        Sortable key (e.g., 2025.4 for '2025 Q4')

    Examples
    --------
    >>> quarter_sort_key('2025 Q4')
    2025.4
    >>> quarter_sort_key('2019 Q1')
    2019.1
    """
    m = re.match(r'(\d{4})\s*[Qq](\d)', str(q_str))
    if m:
        return int(m.group(1)) + int(m.group(2)) / 10
    return 0
