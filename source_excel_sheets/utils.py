#
# Copyright (c) 2025 Airbyte, Inc., all rights reserved.
#

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import unidecode


def excel_column_label(col_index: int) -> str:
    """Convert a 0-based column index to an Excel-style column letter (A, B, ..., Z, AA, AB, ...)."""
    label = ""
    col_index += 1  # Convert to 1-based index
    while col_index > 0:
        col_index -= 1
        label = chr(65 + (col_index % 26)) + label
        col_index //= 26
    return label


def normalize_column_name(name: str, names_conversion: bool = False) -> str:
    """Normalize column name to be SQL-compliant if requested."""
    if not names_conversion or not name:
        return name
    
    # Convert to ASCII
    name = unidecode.unidecode(name)
    
    # Replace non-alphanumeric with underscores
    name = re.sub(r'[^a-zA-Z0-9]+', '_', name)
    
    # Remove leading/trailing underscores
    name = name.strip('_')
    
    # Ensure doesn't start with number
    if name and name[0].isdigit():
        name = f"_{name}"
    
    # Convert to lowercase
    name = name.lower()
    
    return name if name else "column"


def deduplicate_headers(headers: List[str]) -> List[str]:
    """Deduplicate headers by appending cell position to duplicates."""
    seen = {}
    result = []
    
    for idx, header in enumerate(headers):
        if header in seen:
            seen[header] += 1
            col_letter = excel_column_label(idx)
            new_header = f"{header}_{col_letter}1"
            result.append(new_header)
        else:
            seen[header] = 1
            result.append(header)
    
    return result


def process_headers(raw_headers: List[str], names_conversion: bool = False) -> Tuple[List[str], Dict[int, str]]:
    """
    Process headers: normalize if requested and deduplicate.
    Returns processed headers list and index mapping.
    """
    # First normalize if requested
    headers = [normalize_column_name(h, names_conversion) for h in raw_headers]
    
    # Then deduplicate
    headers = deduplicate_headers(headers)
    
    # Create index mapping
    index_mapping = {idx: header for idx, header in enumerate(headers) if header}
    
    return headers, index_mapping


def excel_serial_to_date(serial_number: float) -> str:
    """
    Convert Excel serial number to date string.
    Excel stores dates as days since 1899-12-30 (with a bug for 1900 leap year).
    """
    # Excel's epoch is December 30, 1899
    excel_epoch = datetime(1899, 12, 30)
    
    # For serial numbers >= 60, we need to account for Excel's leap year bug
    # Excel incorrectly treats 1900 as a leap year
    if serial_number >= 60:
        serial_number -= 1
    
    # Add the serial number as days to the epoch
    date = excel_epoch + timedelta(days=serial_number)
    
    return date.strftime("%Y-%m-%d")


def is_excel_date_column(column_name: str) -> bool:
    """
    Heuristic to determine if a column likely contains dates based on its name.
    """
    date_keywords = ['date', 'time', 'created', 'updated', 'modified', 'expires', 'due', 'deadline']
    column_lower = column_name.lower()
    return any(keyword in column_lower for keyword in date_keywords)


def parse_excel_value(value: Any, column_name: str, parse_dates: bool = True) -> Any:
    """
    Parse Excel value, converting dates if appropriate.
    """
    if value is None or str(value).strip() == "":
        return None
    
    # If parse_dates is enabled and this looks like a date column
    if parse_dates and is_excel_date_column(column_name):
        try:
            # Check if it's a number (Excel serial date)
            float_val = float(value)
            # Excel dates are typically between 1 (1900-01-01) and ~50000 (2036)
            if 1 <= float_val <= 100000 and float_val == int(float_val):
                return excel_serial_to_date(float_val)
        except (ValueError, TypeError):
            # Not a number, return as is
            pass
    
    return str(value)