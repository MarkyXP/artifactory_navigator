import pathlib
import shutil
import zipfile
from typing import List

from app.core.config import CONFIG


def _is_zip(path : pathlib.Path | str):
    if isinstance(path, pathlib.Path):
        path = path.as_posix()
    return path.lower().endswith(".zip") 

def unzip(src : pathlib.Path | str) -> List[pathlib.Path]:
    if isinstance(src, str):
        src = pathlib.Path(src)
    o_path = CONFIG.STORE_TEMPFILES_PATH / src.stem
    shutil.rmtree(o_path.as_posix(), ignore_errors= True)
    # o_path.unlink(missing_ok=True) # Delete the output folder to clear any old files
    o_path.mkdir(parents=True, exist_ok=True) # Make the new output folder
    with zipfile.ZipFile(src.as_posix(), 'r') as zip_ref:
        zip_ref.extractall(o_path)
    unzipped_files = [f for f in o_path.glob("*")]
    return unzipped_files

def check_is_summary_file(src : pathlib.Path | str):
    if isinstance(src, str):
        src = pathlib.Path(src)
    if not src.exists():
        return False
    contents = unzip(src)
    if len(contents) != 2:
        return False
    summary_files = [f for f in contents if f.name=="Summary.pdf"]
    signed_docs = [f for f in contents if f.name != "Summary.pdf"]
    if len(summary_files) != 1 or len(signed_docs) != 1:
        return False
    signed_doc = signed_docs[0]
    new_summary_doc = signed_doc.parent / (signed_doc.stem + "_Summary.pdf")
    summary_files[0].rename(new_summary_doc)
    return (
        signed_doc, new_summary_doc
    )
