# https://leap.jfrog.com/rs/256-FNZ-187/images/AQL_Ref_Cards_Downloadable.pdf

from collections import deque
import re

from artifactory import ArtifactoryPath
from requests import Session
from typing import List

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

def get_folder_contents_aql(repo_name : str, foldername : str):
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

def _find_sha_aql(sha : str):
    aqlargs = [
        "items.find",
        {"sha256" : sha},
        ".include",
        ["repo", "path", "name"],
        ".sort",
        {"$asc": ["name"]}
    ]
    return aqlargs

def _find_sha256(conn : ArtifactoryPath, sha : str) -> List[ArtifactoryPath]:
    aql_ary = _find_sha_aql(sha)
    results = conn.aql(*aql_ary)
    results_afpath = [
        conn / result["repo"] / result["path"] / result["name"]
        for result
        in results
    ]
    return results_afpath

def _find_all(conn : ArtifactoryPath, query : str) -> List[ArtifactoryPath]:
    """
    Called by 'find', this searches for keywords across AF.
    Note: To support case insensitive search I just search for everything*,
          and handle the case insensitive search in the code below.
          If numbers are given I _do_ search for them since they are not
          case sensitive, and this dramatically speeds up searches.
    """
    fmt_query = re.sub(r"[^a-z0-9]", " ", query)
    query_words = [word for word in fmt_query.split(" ") if word]
    # Search AF for any numbers in the original query without formatting
    query_numbers = re.findall(r"[0-9]+", query) or [""]
    aql_ary = [
        "items.find",
        {"$and" : [ {"name" : {"$match" : f"*{number}*"}} for number in query_numbers ] }
        ,
        ".include",
        ["repo", "path", "name"],
        ".sort",
        {"$asc": ["name"]}
    ]
    docs = conn.aql(*aql_ary)
    matches = deque()
    for doc in docs:
        checks = [word in doc['name'].lower() for word in query_words]
        if all( checks ):
            doc_af_path = conn / doc["repo"] / doc["path"] / doc["name"]
            matches.append( doc_af_path )
    return list(matches)

def find(conn : ArtifactoryPath, query : str) -> List[ArtifactoryPath]:
    """
    Searches for the query
     - If the query is 64characters long treats it as a sha256 checksum search
     - Otherwise it does a case insensitive search
    """
    query = query.strip().lower()
    if len(query) == 64:
        return _find_sha256(conn, query)
    return _find_all(conn, query)