from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    APP_NAME: str
    APP_ICON_NAME: str
    APP_ICON_PATH: str
    APP_SECRET: str
    VERSION: str
    AF_BASE_URL: str
    AF_URL: str
    AF_PRETTY_URL: str
    DST_AZURE_KEY: str
    DST_STORAGE_ACCOUNT_NAME: str
    DST_STORAGE_ACCOUNT_CONTAINER: str
    STORE_LOCATION: str
    RELEASE_LOCATION: str
    ICON_LOCATION: str | None = None
    SHIPPING_TOOL_EMAIL_BODY_LOCATION: str | None = None
