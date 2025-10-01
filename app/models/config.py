from dataclasses import dataclass
from pathlib import Path

@dataclass
class Config:
    APP_NAME : str
    APP_ICON_NAME : str
    APP_ICON_PATH : str
    APP_SECRET : str
    VERSION : str
    AF_URL : str
    AF_PRETTY_URL : str
    HTTP_CERT_FNAME : str
    AZURE_COSMOS_ENDPOINT : str
    AZURE_COSMOS_KEY : str
    AZURE_COSMOS_DATABASE_ID : str
    AZURE_COSMOS_CONTAINER_ID : str
    AZURE_DST_SETTINGS : str
    STORE_LOCATION: str
    STORE_LOCATION_PATH : Path | None = None
    STORE_TEMPFILES_PATH : Path | None = None
    ICON_LOCATION : str | None = None
    SHIPPING_TOOL_EMAIL_BODY_LOCATION : str | None = None
