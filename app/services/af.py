# https://leap.jfrog.com/rs/256-FNZ-187/images/AQL_Ref_Cards_Downloadable.pdf

from artifactory import ArtifactoryPath
import ahocorasick
from requests import Session
from typing import List
import re

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

def find_sha_aql(sha : str):
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
    aql_ary = find_sha_aql(sha)
    results = conn.aql(*aql_ary)
    results_afpath = [
        conn / result["repo"] / result["path"] / result["name"]
        for result
        in results
    ]
    return results_afpath

def _find_all(conn : ArtifactoryPath, query : str) -> List[ArtifactoryPath]:
    automaton = ahocorasick.Automaton()
    fmt_query = re.sub(r"\_\.", " ", query)
    # Search AF for any numbers in the original query without formatting
    query_numbers = re.findall(r"[0-9]+", query)
    aqlargs = [
        "items.find",
        {"$and" : [ {"path" : {"$match" : numbers}} for numbers in query_numbers]}
        ,
        ".include",
        ["repo", "path", "name", "size", "sha256", "modified", "updated", "created_by", "modified_by", "type"],
        ".sort",
        {"$asc": ["name"]}
    ]
    haystack = conn.aql(aqlargs)
    for idx, key in enumerate(fmt_query.split()):
        automaton.add_word(key, (idx, key))
    automaton.make_automaton()
    for end_index, (insert_order, original_value) in automaton.iter(haystack):
        start_index = end_index - len(original_value) + 1
        print((start_index, end_index, (insert_order, original_value)))


def find(conn : ArtifactoryPath, query : str) -> List[ArtifactoryPath]:
    """
    Searches for the query
     - If the query is 64characters long treats it as a sha256 checksum search
     - Otherwise it does a case insensitive search
    """
    query = query.strip()
    if len(query) == 64:
        return _find_sha256(conn, query)
    _find_all(conn, query)