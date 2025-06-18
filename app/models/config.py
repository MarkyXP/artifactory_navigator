from dataclasses import dataclass

@dataclass
class Config:
    APP_NAME : str
    APP_SECRET : str
    STORE_LOCATION: str
    AF_URL : str
    AF_PRETTY_URL : str
    HTTP_CERT_FNAME : str