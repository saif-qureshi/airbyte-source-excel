#
# Copyright (c) 2025 Airbyte, Inc., all rights reserved.
#

from functools import lru_cache
from typing import Any, Dict, List, Optional

import requests
from msal import ConfidentialClientApplication
from msal.exceptions import MsalServiceError
from office365.graph_client import GraphClient

from airbyte_cdk import AirbyteTracedException, FailureType
from source_excel_sheets.spec import SourceExcelSheetsSpec


class ExcelSheetsClient:
    """
    Client to interact with Microsoft Excel via Graph API.
    """

    def __init__(self, config: SourceExcelSheetsSpec):
        self.config = config
        self._client = None
        self._msal_app = None

    @property
    @lru_cache(maxsize=None)
    def msal_app(self):
        """Returns an MSAL app instance for authentication."""
        return ConfidentialClientApplication(
            self.config.credentials.client_id,
            authority=f"https://login.microsoftonline.com/{self.config.credentials.tenant_id}",
            client_credential=self.config.credentials.client_secret,
        )

    @property
    def client(self):
        """Initializes and returns a GraphClient instance."""
        if not self._client:
            self._client = GraphClient(self._get_access_token)
        return self._client

    def _get_access_token(self):
        """Retrieves an access token for Excel/OneDrive access."""
        scope = ["https://graph.microsoft.com/.default"]
        
        if self.config.credentials.auth_type == "Client":
            refresh_token = self.config.credentials.refresh_token
            if refresh_token:
                result = self.msal_app.acquire_token_by_refresh_token(refresh_token, scopes=scope)
            else:
                result = self.msal_app.acquire_token_for_client(scopes=scope)
        else:
            # Service Key authentication - client credentials flow
            result = self.msal_app.acquire_token_for_client(scopes=scope)

        if "access_token" not in result:
            error_description = result.get("error_description", "No error description provided.")
            raise MsalServiceError(error=result.get("error"), error_description=error_description)

        return result

    def get_access_token(self) -> str:
        """Get fresh access token."""
        return self._get_access_token()["access_token"]

    def get_worksheets(self) -> List[Dict[str, Any]]:
        """Get all worksheets from the workbook."""
        access_token = self.get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Remove leading slash for API call
        workbook_path = self.config.workbook_path.lstrip('/')
        url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{workbook_path}:/workbook/worksheets"
        
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            error_info = response.json().get("error", {}).get("message", "Unknown error")
            raise AirbyteTracedException(
                internal_message=f"Failed to get worksheets: {error_info}",
                message=f"Failed to access workbook at {self.config.workbook_path}. Please check the path and permissions.",
                failure_type=FailureType.config_error,
            )
        
        data = response.json()
        # Filter only visible worksheets
        worksheets = [ws for ws in data.get("value", []) if ws.get("visibility") == "Visible"]
        return worksheets

    def get_worksheet_data(self, worksheet_id: str, range_address: Optional[str] = None) -> Dict[str, Any]:
        """Get data from a specific worksheet."""
        access_token = self.get_access_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        
        workbook_path = self.config.workbook_path.lstrip('/')
        
        if range_address:
            url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{workbook_path}:/workbook/worksheets/{worksheet_id}/range(address='{range_address}')"
        else:
            url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{workbook_path}:/workbook/worksheets/{worksheet_id}/usedRange"
        
        response = requests.get(url, headers=headers)
        if response.status_code == 404:
            # Empty worksheet
            return {"values": [], "rowCount": 0, "columnCount": 0}
        elif response.status_code != 200:
            error_info = response.json().get("error", {}).get("message", "Unknown error")
            raise Exception(f"Failed to get worksheet data: {error_info}")
        
        return response.json()

    def check_connection(self) -> bool:
        """Check if we can connect to the workbook."""
        try:
            worksheets = self.get_worksheets()
            return len(worksheets) > 0
        except Exception:
            return False