from dataclasses import dataclass

from artifactory import ArtifactoryPath
import dohq_artifactory
from requests import Session

from app.core.config import CONFIG

@dataclass
class AF_File():
    repo: str
    path: str
    name: str
    size: int
    modified: str
    updated: str
    sha256: str

def get_af_conn(username : str, password : str) -> ArtifactoryPath:
    # cert = getcwd()+"\\Leica Biosystems Melbourne Root CA.cer"
    cert = CONFIG.HTTP_CERT_FNAME
    session = Session()
    session.auth = (username, password)
    session.verify = cert
    connection = ArtifactoryPath(CONFIG.AF_URL, verify=cert, session=session)
    return connection

def get_search_args(repo_name : str, last_update_time : str):
    args = [{"repo": repo_name}, {"type": "file"},]
    if last_update_time:
        args.append({"modified": {"$gt": last_update_time}})
    aqlargs = [
        "items.find",
        {
            "$and": args
        },
        ".include",
        ["repo", "path", "name", "size", "sha256", "modified", "updated"],
        ".sort",
        {"$asc": ["updated"]},
    ]
    return aqlargs

#aqlargs = _get_search_args(repo)
#artifacts_list = connection.aql(*aqlargs)