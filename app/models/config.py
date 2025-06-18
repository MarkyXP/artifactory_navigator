from dataclasses import dataclass
from pathlib import Path

@dataclass
class Config:
    APP_NAME : str
    APP_SECRET : str
    AF_URL : str
    AF_PRETTY_URL : str
    HTTP_CERT_FNAME : str
    STORE_LOCATION: str
    STORE_LOCATION_PATH : Path | None = None
    STORE_TEMPFILES_PATH : Path | None = None
