# https://leap.jfrog.com/rs/256-FNZ-187/images/AQL_Ref_Cards_Downloadable.pdf

from artifactory import ArtifactoryPath
from requests import Session

from app.core.config import CONFIG

def get_af_conn(username : str, password : str) -> ArtifactoryPath:
    # cert = getcwd()+"\\Leica Biosystems Melbourne Root CA.cer"
    cert = CONFIG.HTTP_CERT_FNAME
    session = Session()
    session.auth = (username, password)
    session.verify = cert
    connection = ArtifactoryPath(CONFIG.AF_URL, verify=cert, session=session)
    return connection

def open(conn : ArtifactoryPath, url : str) -> ArtifactoryPath:
    existing_session = conn.session
    existing_cert = conn.verify
    new_conn = ArtifactoryPath(
        url,
        verify = existing_cert,
        session = existing_session
    )
    return new_conn

def get_search_args(repo_name : str, foldername : str):
    args = {
        "$and" : [
            {"$or" :
                [
                    {"type" : "file"},
                    {"type" : "folder"}
                ]
            },
            {"repo" : repo_name},
            {"path" : {"$match":foldername}}
        ]
    }
    aqlargs = [
        "items.find",args,
        ".include",
        ["repo", "path", "name", "size", "sha256", "modified", "updated", "created_by", "modified_by", "type"],
        ".sort",
        {"$asc": ["name"]}
    ]
    return aqlargs

#aqlargs = _get_search_args(repo)
#artifacts_list = connection.aql(*aqlargs)