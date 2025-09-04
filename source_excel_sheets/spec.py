#
# Copyright (c) 2025 Airbyte, Inc., all rights reserved.
#

from typing import Any, Dict, List, Literal, Mapping, Optional, Union

from pydantic.v1 import BaseModel, Field, validator


class OAuthCredentials(BaseModel):
    """
    OAuth Credentials for Microsoft Graph API authentication.
    """
    class Config:
        title = "Authenticate via Microsoft (OAuth)"

    auth_type: Literal["Client"] = Field("Client", const=True)
    tenant_id: str = Field(
        default="common",
        title="Tenant ID",
        description="Azure AD Tenant ID (optional for multi-tenant apps, defaults to 'common')"
    )
    client_id: str = Field(
        ...,
        title="Client ID",
        description="The Client ID of your Microsoft Azure application",
        airbyte_secret=True,
    )
    client_secret: str = Field(
        ...,
        title="Client Secret", 
        description="The Client Secret of your Microsoft Azure application",
        airbyte_secret=True,
    )
    refresh_token: str = Field(
        ...,
        title="Refresh Token",
        description="Refresh token obtained from Microsoft OAuth flow",
        airbyte_secret=True,
    )


class ServiceKeyCredentials(BaseModel):
    """
    Service Key Authentication (for future use or enterprise scenarios).
    """
    class Config:
        title = "Service Key Authentication"

    auth_type: Literal["Service"] = Field("Service", const=True)
    tenant_id: str = Field(
        ...,
        title="Tenant ID",
        description="Azure AD Tenant ID",
        airbyte_secret=True,
    )
    client_id: str = Field(
        ...,
        title="Client ID",
        description="The Client ID of your Microsoft Azure application",
        airbyte_secret=True,
    )
    client_secret: str = Field(
        ...,
        title="Client Secret",
        description="The Client Secret of your Microsoft Azure application",
        airbyte_secret=True,
    )


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

    credentials: Union[OAuthCredentials, ServiceKeyCredentials] = Field(
        ...,
        title="Authentication",
        description="Credentials for connecting to Microsoft Graph API",
        discriminator="auth_type",
        order=10,
        type="object",
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

    @classmethod
    def schema(cls, **kwargs) -> Dict[str, Any]:
        """Override schema to add type: object to credentials field and inline oneOf."""
        schema = super().schema(**kwargs)
        
        # Ensure credentials has type: object
        if "properties" in schema and "credentials" in schema["properties"]:
            cred_schema = schema["properties"]["credentials"]
            cred_schema["type"] = "object"
            
            # Replace $ref with inline schemas for oneOf
            if "oneOf" in cred_schema and "definitions" in schema:
                new_one_of = []
                for option in cred_schema["oneOf"]:
                    if "$ref" in option:
                        ref_name = option["$ref"].split("/")[-1]
                        if ref_name in schema["definitions"]:
                            # Add the schema inline with required properties
                            inline_schema = {
                                "type": "object",
                                "properties": schema["definitions"][ref_name]["properties"],
                                "required": schema["definitions"][ref_name].get("required", [])
                            }
                            # Add title if exists
                            if "title" in schema["definitions"][ref_name]:
                                inline_schema["title"] = schema["definitions"][ref_name]["title"]
                            new_one_of.append(inline_schema)
                    else:
                        new_one_of.append(option)
                cred_schema["oneOf"] = new_one_of
        
        return schema