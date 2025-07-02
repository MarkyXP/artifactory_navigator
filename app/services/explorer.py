import re

import wx
from artifactory import ArtifactoryPath
import dohq_artifactory

from app.gui.revision_compare import TableFrame
from app.gui.explorer import FileExplorer
from app.services import af as AF
from app.services.revision import get_drawings_for_cr
from app.models.af_search_results import AF_Result

_uname = ""
_pw = ""

def Run(app : wx.App, af_conn : ArtifactoryPath):
    # initial_folders = af_conn.get_repositories()
    frame = FileExplorer(af_conn)
    frame.Show()
    app.MainLoop()
    if _uname and _pw:
        return (_uname, _pw)
    return ("", "")

def _extract_cr_for_path(path : ArtifactoryPath) -> int | None:
    cr_no = re.findall(r"\d{5}", path.as_posix())
    if len(cr_no) == 1:
        return int(cr_no[0])
    return None

def compare_to_revision(path : ArtifactoryPath):
    cr_no = _extract_cr_for_path(path)
    if not cr_no:
        return
    revision_docs = get_drawings_for_cr(cr_no)
    docs_in_path_dict = path.aql(
                *AF.get_folder_contents_aql(
                    repo_name = path.repo,
                    foldername = path.path_in_repo[1:]
                )
            )
    docs_in_path = [
        AF_Result(**item)
        for item in docs_in_path_dict
        if not item["name"] == "."
    ]
    frame = TableFrame()
    frame.Show()