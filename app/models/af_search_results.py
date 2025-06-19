from dataclasses import dataclass
from typing import Literal

from app.core.config import CONFIG

@dataclass
class AF_Result:
    """
    Args:
     - Name : Name of the file / folder ('21_5901_130_A01.zip')
     - Repo : Name of the repoisotry for the file, e.g. 'ddc-dhfr-wip-mel'
               - Not used..
     - type : 
    """
    repo : str
    path : str
    name : str
    type : Literal["folder", "file"]
    size : int # Bytes
    modified : str
    updated : str
    created_by : str | None = None
    modified_by : str | None = None
    sha256 : str | None = None

@dataclass
class AF_Repo:
    repo : str
    path : str
    name : str
    type : str = "folder"
    size : int = 0
    modified : str = ""
    updated : str = ""
    created_by : str | None = None
    modified_by : str | None = None
    sha256 : str | None = None