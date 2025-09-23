import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List

import wx
from artifactory import ArtifactoryPath

from app.core.config import CONFIG
from app.gui.revision_compare import ReVision_Report_Frame
from app.gui.explorer import FileExplorer
from app.services import af as AF
from app.services.revision import get_drawings_for_cr
from app.models.af_search_results import AF_Result
from app.services import shipping_tool

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
    frame = ReVision_Report_Frame(
        title = f"ReVision Report - {cr_no}",
        revision_data = revision_docs,
        af_data = docs_in_path
    )
    frame.Show()

def send_to_shipping_tool(items : List[ArtifactoryPath], recipient_company : str):
    # Download & Zip the items
    now = datetime.now().strftime(r"%d-%M-%y-%H-%m-%S")
    output_path = CONFIG.STORE_TEMPFILES_PATH
    archive = Path(f"LBS_{recipient_company}-{now}")
    archive_path = output_path / archive
    with zipfile.ZipFile(archive_path.as_posix(), 'w') as zipf:
        for af_file in items:
            # af_file = AF.open(self.conn, file_path_str)
            local_file = download_file(
                file_conn=af_file,
                open=False,
            )
            zipf.write(local_file)
    # Send them through to the DST
    response = shipping_tool.upload(
        src = archive_path,
        dst_file_name = archive_path.name,
        sender_email = "lbsmel.hw-engineeringrelease@leicabiosystems.com",
        recipient_name = "Tony",
        recipient_email = "",
        recipient_company = recipient_company
    )


def download_file(
        self, file_conn: ArtifactoryPath, open=False, output_path: Path | None = None
    ) -> Path:
        # Make a temp folder if necessary
        if not output_path:
            output_path = CONFIG.STORE_TEMPFILES_PATH
            output_path.mkdir(parents=True, exist_ok=True)
        fname = file_conn.name
        tmp_file_path = output_path / fname
        with tmp_file_path.open(mode="wb") as f:
            file_conn.writeto(f, chunk_size=256)
        if open:
            os.startfile(tmp_file_path.as_posix())
        return tmp_file_path
        file_conn.archive()