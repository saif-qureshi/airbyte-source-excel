#
# Copyright (c) 2025 Airbyte, Inc., all rights reserved.
#

from typing import Any, Dict, Iterable, List, Mapping, Optional

from airbyte_cdk.models import SyncMode
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from source_excel_sheets.client import ExcelSheetsClient
from source_excel_sheets.utils import parse_excel_value, process_headers


class ExcelWorksheetStream(Stream):
    """
    Stream for reading data from an Excel worksheet.
    """
    
    primary_key = None

    def __init__(self, client: ExcelSheetsClient, worksheet_info: Dict[str, Any], config: Dict[str, Any], **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.worksheet_info = worksheet_info
        self.config = config
        self._name = self._determine_stream_name()
        self._schema = None

    def _determine_stream_name(self) -> str:
        """Determine the stream name, applying overrides if configured."""
        worksheet_name = self.worksheet_info.get("name", "Unknown")
        
        # Check for stream name overrides
        overrides = self.config.get("stream_name_overrides", [])
        for override in overrides:
            if override.get("source_stream_name") == worksheet_name:
                return override.get("custom_stream_name", worksheet_name)
        
        return worksheet_name

    @property
    def name(self) -> str:
        return self._name

    def get_json_schema(self) -> Mapping[str, Any]:
        """
        Get the JSON schema for this worksheet.
        All fields are optional strings by default.
        """
        if self._schema is None:
            # Fetch first row to determine schema
            try:
                data = self.client.get_worksheet_data(self.worksheet_info["id"])
                if data.get("values") and len(data["values"]) > 0:
                    headers, _ = process_headers(data["values"][0], self.config.get("names_conversion", False))
                    properties = {header: {"type": ["null", "string"]} for header in headers if header}
                else:
                    properties = {}
                
                self._schema = {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "object",
                    "properties": properties,
                    "additionalProperties": True
                }
            except Exception:
                # Fallback schema
                self._schema = {
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "object",
                    "additionalProperties": True
                }
        
        return self._schema

    def read_records(
        self,
        sync_mode: SyncMode,
        cursor_field: Optional[List[str]] = None,
        stream_slice: Optional[Mapping[str, Any]] = None,
        stream_state: Optional[Mapping[str, Any]] = None,
    ) -> Iterable[Mapping[str, Any]]:
        """
        Read records from the worksheet.
        """
        worksheet_id = self.worksheet_info["id"]
        batch_size = self.config.get("batch_size", 1000000)
        
        # Get the full data first to understand the structure
        initial_data = self.client.get_worksheet_data(worksheet_id)
        if not initial_data.get("values") or len(initial_data["values"]) < 2:
            # No data or only headers
            return
        
        # Process headers
        raw_headers = initial_data["values"][0]
        headers, index_mapping = process_headers(raw_headers, self.config.get("names_conversion", False))
        total_rows = initial_data.get("rowCount", 0)
        
        # Read data in batches
        current_row = 2  # Start from row 2 (1-indexed, row 1 is headers)
        
        while current_row <= total_rows:
            end_row = min(current_row + batch_size - 1, total_rows)
            range_address = f"A{current_row}:Z{end_row}"  # Z is arbitrary, API will adjust
            
            try:
                data = self.client.get_worksheet_data(worksheet_id, range_address)
                values = data.get("values", [])
                
                for row in values:
                    # Skip empty rows
                    if not any(cell for cell in row if cell is not None and str(cell).strip()):
                        continue
                    
                    # Build record using index mapping
                    record = {}
                    for idx, header in index_mapping.items():
                        if idx < len(row):
                            value = row[idx]
                            # Parse value with date conversion if applicable
                            parse_dates = self.config.get("parse_dates", True)
                            parsed_value = parse_excel_value(value, header, parse_dates=parse_dates)
                            if parsed_value is not None:
                                record[header] = parsed_value
                    
                    if record:  # Only yield non-empty records
                        yield record
                
                current_row = end_row + 1
                
            except Exception as e:
                self.logger.error(f"Error reading batch {current_row}-{end_row}: {str(e)}")
                break