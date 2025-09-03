#
# Copyright (c) 2025 Airbyte, Inc., all rights reserved.
#

from typing import Any, List, Mapping, Optional

from pydantic.v1 import BaseModel, Field, validator


class OAuthCredentials(BaseModel):
    auth_type: str = Field(default="Client", const="Client")
    tenant_id: str = Field(
        default="common",
        description="Azure AD Tenant ID (optional for multi-tenant apps, defaults to 'common')"
    )
    client_id: str = Field(
        ...,
        description="The Client ID of your Microsoft Azure application",
        airbyte_secret=True,
    )
    client_secret: str = Field(
        ...,
        description="The Client Secret of your Microsoft Azure application",
        airbyte_secret=True,
    )
    refresh_token: str = Field(
        ...,
        description="Refresh token obtained from Microsoft OAuth flow",
        airbyte_secret=True,
    )

    class Config:
        schema_extra = {"title": "Authenticate via Microsoft (OAuth)"}


class SourceExcelSheetsSpec(BaseModel):
    """
    Spec for source-excel-sheets.
    Simple spec focused on Excel-specific functionality via Microsoft Graph API.
    """
    
    class Config:
        title = "Excel Sheets Source Spec"
        schema_extra = {
            "documentationUrl": "https://docs.airbyte.com/integrations/sources/excel-sheets",
        }

    workbook_path: str = Field(
        ...,
        title="Workbook Path",
        description=(
            "Path to the Excel workbook file in your OneDrive/SharePoint. Examples: "
            "/Orders.xlsx (file in root directory), "
            "/Documents/Reports/Sales.xlsx (nested folders), "
            "/Shared/Team/Q4-Data.xlsx (shared folder). "
            "Use forward slashes and start with /"
        ),
        examples=["/Orders.xlsx", "/Documents/Reports/Sales.xlsx"],
        order=0,
    )

    credentials: OAuthCredentials = Field(
        ...,
        title="Authentication",
        description="Credentials for connecting to Microsoft Graph API",
        order=10,
    )

    batch_size: int = Field(
        default=1000000,
        title="Row Batch Size",
        description=(
            "An integer representing row batch size for each sent request to Microsoft Graph API. "
            "Row batch size means how many rows are processed from the Excel worksheet. "
            "Based on Microsoft Graph API limits, consider network speed and number of columns when setting this value."
        ),
        order=20,
    )

    names_conversion: bool = Field(
        default=False,
        title="Convert Column Names to SQL-Compliant Format",
        description="Converts column names to a SQL-compliant format (snake_case, lowercase, etc).",
        order=30,
    )
    
    parse_dates: bool = Field(
        default=True,
        title="Parse Excel Date Values",
        description=(
            "Automatically convert Excel date serial numbers to readable dates (YYYY-MM-DD format). "
            "This applies to columns with 'date' in their name."
        ),
        order=35,
    )

    stream_name_overrides: Optional[List[Mapping[str, str]]] = Field(
        default=None,
        title="Stream Name Overrides",
        description=(
            "Allows you to rename streams (Excel worksheet names) as they appear in Airbyte. "
            "Each item should have 'source_stream_name' (worksheet name) and 'custom_stream_name' (desired name)."
        ),
        order=40,
    )

    @validator("workbook_path")
    def validate_workbook_path(cls, v):
        if not v.startswith("/"):
            v = "/" + v
        return v