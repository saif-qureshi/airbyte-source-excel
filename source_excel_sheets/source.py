#
# Copyright (c) 2025 Airbyte, Inc., all rights reserved.
#

from typing import Any, List, Mapping, Tuple

from airbyte_cdk import AirbyteTracedException, FailureType
from airbyte_cdk.models import ConnectorSpecification, SyncMode
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from source_excel_sheets.client import ExcelSheetsClient
from source_excel_sheets.spec import SourceExcelSheetsSpec
from source_excel_sheets.streams import ExcelWorksheetStream


class SourceExcelSheets(AbstractSource):
    def check_connection(self, logger, config: Mapping[str, Any]) -> Tuple[bool, Any]:
        """
        Check connection to the Excel workbook.
        """
        try:
            spec = SourceExcelSheetsSpec(**config)
            client = ExcelSheetsClient(spec)
            
            # Try to get worksheets
            worksheets = client.get_worksheets()
            
            if not worksheets:
                return False, "No visible worksheets found in the workbook"
            
            return True, None
            
        except Exception as e:
            return False, f"Failed to connect: {str(e)}"

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        """
        Return the list of streams (one per worksheet).
        """
        spec = SourceExcelSheetsSpec(**config)
        client = ExcelSheetsClient(spec)
        
        try:
            worksheets = client.get_worksheets()
            
            if not worksheets:
                raise AirbyteTracedException(
                    message="No visible worksheets found in the workbook",
                    internal_message="The workbook appears to have no visible worksheets",
                    failure_type=FailureType.config_error,
                )
            
            streams = []
            for worksheet in worksheets:
                stream = ExcelWorksheetStream(
                    client=client,
                    worksheet_info=worksheet,
                    config=config,
                )
                streams.append(stream)
            
            return streams
            
        except Exception as e:
            raise AirbyteTracedException(
                message=f"Failed to discover streams: {str(e)}",
                internal_message=str(e),
                failure_type=FailureType.config_error,
                exception=e,
            )

    def spec(self, *args, **kwargs) -> ConnectorSpecification:
        """
        Returns the specification for this source.
        """
        return ConnectorSpecification(
            documentationUrl="https://docs.airbyte.com/integrations/sources/excel-sheets",
            connectionSpecification=SourceExcelSheetsSpec.schema(),
        )