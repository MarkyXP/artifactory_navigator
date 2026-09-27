from dataclasses import dataclass
from typing import Literal

from artifactory import ArtifactoryPath

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

    repo: str
    path: str
    name: str
    type: Literal["folder", "file"]
    size: int  # Bytes
    modified: str
    updated: str
    created_by: str | None = None
    modified_by: str | None = None
    sha256: str | None = None


@dataclass
class AF_Repo:
    repo: str
    path: str
    name: str
    type: str = "folder"
    size: int = 0
    modified: str = ""
    updated: str = ""
    created_by: str | None = None
    modified_by: str | None = None
    sha256: str | None = None


@dataclass
class AF_Login_Error:
    """
    A failed attempt to authenticate against Artifactory.

    Returned in place of an AF_Login_Result so "did it work?" is answerable by
    type rather than by truthiness - an empty message is still an error.
    """

    message: str


@dataclass
class AF_Login_Result:
    """
    A successful login.

    Args:
     - conn : The authenticated connection to Artifactory
     - repos : Names of the repositories the user can see. Fetched as a side
               effect of verifying the credentials, so the explorer can render
               the root view without asking the server for them a second time.
    """

    conn: ArtifactoryPath
    repos: list[str]
