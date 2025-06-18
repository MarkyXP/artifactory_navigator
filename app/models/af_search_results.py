from dataclasses import dataclass

from app.core.config import CONFIG

@dataclass
class AF_Result:
    repo : str
    path : str
    name : str
    type : str
    size : int # Bytes
    modified : str
    updated : str
    created_by : str | None = None
    modified_by : str | None = None
    sha256 : str | None = None
