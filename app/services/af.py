# https://leap.jfrog.com/rs/256-FNZ-187/images/AQL_Ref_Cards_Downloadable.pdf

import re
from collections import deque
from typing import List

from artifactory import ArtifactoryPath
from requests import Session

from app.core.config import CONFIG
from app.models.af_search_results import AF_Result

repos_with_write_permissions = []


def get_af_conn(username: str, password: str) -> ArtifactoryPath:
    session = Session()
    session.auth = (username, password)
    connection = ArtifactoryPath(CONFIG.AF_URL, session=session)
    return connection


def open(conn: ArtifactoryPath, url: str) -> ArtifactoryPath:
    existing_session = conn.session
    existing_cert = conn.verify
    new_conn = ArtifactoryPath(url, verify=existing_cert, session=existing_session)
    return new_conn


def get_folder_contents_aql(repo_name: str, foldername: str):
    args = {
        "$and": [
            {"$or": [{"type": "file"}, {"type": "folder"}]},
            {"repo": repo_name},
            {"path": {"$match": foldername}},
        ]
    }
    aqlargs = [
        "items.find",
        args,
        ".include",
        [
            "repo",
            "path",
            "name",
            "size",
            "sha256",
            "modified",
            "updated",
            "created_by",
            "modified_by",
            "type",
        ],
    ]
    # NOTE: This previously sorted the results, however it has been removed as it
    # is not supported by the Artifactory OSS, which I'm using to debug this.
    return aqlargs


def check_has_write_permissions(path: ArtifactoryPath) -> bool:
    """
    Checks for a path whether the user has permission to write to it.
    Note that this is only a simple check, and does not implement the full
    regex / pattern that I should look for.
    """
    global repos_with_write_permissions
    repo_name = (list(path.parts) + [""])[1]
    if not repos_with_write_permissions:
        resp = path.session.get(
            url=CONFIG.AF_BASE_URL + "ui/api/v1/ui/repodata?deploy=true"
        )
        resp_dict = resp.json()
        if isinstance(resp_dict, dict) and "repoTypesList" in resp_dict:
            repos_with_write_permissions = [
                repo["repoKey"]
                for repo in resp_dict["repoTypesList"]
                if repo["repoType"] == "Generic"
            ]

    return repo_name in repos_with_write_permissions


def find_folder_contents(
    conn: ArtifactoryPath, repo_name: str, folderpath: str
) -> List[AF_Result]:
    items_dict = conn.aql(
        *get_folder_contents_aql(repo_name=repo_name, foldername=folderpath)
    )
    items = [AF_Result(**item) for item in items_dict if not item["name"] == "."]
    items.sort(key=lambda r: r.name)
    items.sort(key=lambda r: r.type)
    return items


def find_folders(
    conn: ArtifactoryPath, repo: str, foldername_substring: str
) -> List[ArtifactoryPath]:
    aql_ary = [
        "items.find",
        {
            "$and": [
                {"type": "folder"},
                {"name": {"$match": f"*{foldername_substring}*"}},
                {"repo": {"$match": f"*{repo}*"}},
            ]
        },
        ".include",
        ["repo", "path", "name"],
        ".sort",
        {"$asc": ["name"]},
    ]
    folders = conn.aql(*aql_ary)
    af_paths = [
        conn / folder["repo"] / folder["path"] / folder["name"] for folder in folders
    ]
    return af_paths


def _find_sha_aql(sha: str):
    aqlargs = [
        "items.find",
        {"sha256": sha},
        ".include",
        [
            "repo",
            "path",
            "name",
            "size",
            "modified",
            "updated",
            "modified_by",
            "created_by",
            "sha256",
        ],
    ]
    return aqlargs


def _find_sha256(conn: ArtifactoryPath, sha: str) -> List[ArtifactoryPath]:
    aql_ary = _find_sha_aql(sha)
    results = conn.aql(*aql_ary)
    results.sort(key=lambda r: r["path"])
    results.sort(key=lambda r: r["name"])
    return results
    results_afpath = [
        conn / result["repo"] / result["path"] / result["name"] for result in results
    ]
    return results_afpath


def _find_all(
    conn: ArtifactoryPath, query: str, limit: int = -1
) -> List[ArtifactoryPath]:
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
        {"$and": [{"name": {"$match": f"*{number}*"}} for number in query_numbers]},
        ".include",
        [
            "repo",
            "path",
            "name",
            "size",
            "modified",
            "updated",
            "modified_by",
            "created_by",
            "sha256",
        ],
    ]
    if limit > 0:
        aql_ary += [".limit", limit]
    docs = conn.aql(*aql_ary)
    docs.sort(key=lambda r: r["name"])
    docs.sort(key=lambda r: r["path"])
    matches = deque()
    for doc in docs:
        checks = [word in doc["name"].lower() for word in query_words]
        if all(checks):
            # doc_af_path = conn / doc["repo"] / doc["path"] / doc["name"]
            matches.append(doc)
    return list(matches)


def find(conn: ArtifactoryPath, query: str, limit=-1) -> List[ArtifactoryPath]:
    """
    Searches for the query
     - If the query is 64characters long treats it as a sha256 checksum search
     - Otherwise it does a case insensitive search
    """
    query = query.strip().lower()
    if len(query) == 64:
        return _find_sha256(conn, query)
    return _find_all(conn, query, limit=limit)


def make_folder(folderpath: ArtifactoryPath):
    folderpath.mkdir()
