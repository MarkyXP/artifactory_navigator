import pathlib
import shutil
import re
import subprocess
import zipfile
from typing import List

from artifactory import ArtifactoryPath
import math
# import pymupdf

from app.core.config import CONFIG
from app.services.revision import get_doc_no

# Standard document sizes in mm (width, height, name)
STANDARD_PAGE_SIZES = (
    (841, 1189, "A0"),
    (594, 841, "A1"),
    (420, 594, "A2"),
    (297, 420, "A3"),
    (210, 297, "A4"),
    (148, 210, "A5")
)

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

def check_is_docusign_combined_file(src : pathlib.Path | str):
    if isinstance(src, str):
        src = pathlib.Path(src)
    if not src.exists():
        return False
    if not _is_zip(src):
        return
    if not src.name.lower().startswith("complete_with_docusign"):
        return
    contents = unzip(src)
    if len(contents) != 2:
        return False
    summary_files = [f for f in contents if f.name=="Summary.pdf"]
    signed_docs = [f for f in contents if f.name != "Summary.pdf"]
    if len(summary_files) != 1 or len(signed_docs) != 1:
        return False
    signed_doc = signed_docs[0]
    signed_doc_renamed_double_underscore = re.sub(r"[^a-zA-Z0-9]", "_", signed_doc.stem)
    signed_doc_renamed = re.sub(r"\_+", "_", signed_doc_renamed_double_underscore)
    signed_doc = signed_doc.rename(signed_doc.with_stem(signed_doc_renamed))
    new_summary_doc = signed_doc.parent / (signed_doc.stem + "_Summary.pdf")
    summary_files[0].rename(new_summary_doc)
    return (
        signed_doc, new_summary_doc
    )

def get_clipboard_file_paths() -> List[pathlib.Path]:
    ps_command = (
        'Add-Type -AssemblyName PresentationCore; '
        '[Windows.Clipboard]::GetFileDropList() -join "`n"'
    )
    result = subprocess.run(
        ['powershell', '-NoProfile', '-Command', ps_command],
        capture_output=True,
        text=True
    )
    paths = result.stdout.strip().splitlines()
    return [pathlib.Path(path) for path in paths]

def upload_formatted_files(files : List[pathlib.Path], dest_folder : ArtifactoryPath) -> List[str]:
    """
    Unzips files that need to be unzipped, etc
    returns any errors
    """
    errors = []
    for filepath in files:
        try:
            is_summary = check_is_docusign_combined_file(filepath)
            if is_summary:
                for file in is_summary:
                    deploy_file_w_params(dest_folder, file)
            else:
                deploy_file_w_params(dest_folder, filepath)
        except Exception as e:
            errors.append(f"{filepath.name}: {str(e)}")
    return errors

def deploy_file_w_params(dest_folder : ArtifactoryPath, src_filepath : pathlib.Path):
    # params = get_file_parameters(src_filepath)
    # Consider making this more opinionated?
    # src_doc_renamed_double_underscore = re.sub(r"[^a-zA-Z0-9]", "_", src_filepath.stem)
    # src_doc_renamed = re.sub(r"\_+", "_", src_doc_renamed_double_underscore)
    # src_str = src_str.rename(src_doc_renamed)
    src_str = src_filepath.as_posix()
    dest_folder.deploy_file(
        file_name = src_str,
        # parameters=params
    )

def _is_docusigned(path : pathlib.Path) -> bool:
    is_docusigned_key = b"(Digitally verifiable PDF exported from www.docusign.com)"
    if not path.exists():
        return False
    if not path.name.upper().endswith(".PDF"):
        return False
    with path.open("rb") as f:
        return is_docusigned_key in f.read()
    
def _is_approval_cover_page(path : pathlib.Path) -> bool:
    """Look for QF0472 / QF0035 / QF0231 reference in path"""
    approval_cover_page_forms = ["QF0472", "QF0035", "QF0231"]
    if not isinstance(path, pathlib.Path):
        path = pathlib.Path(path)
    if not path.exists():
        return False
    if not path.name.upper().endswith(".PDF"):
        return False
    pdf = pymupdf.open( path.expanduser() )
    for page in pdf:
        page_text = page.get_text()
        if any([form_no in page_text for form_no in approval_cover_page_forms]):
            return True
    return False

def _get_document_size(pdf_path : pathlib.Path):
    # Read PDF dimensions in mm
    doc = pymupdf.open(pdf_path.expanduser())
    page = doc[0]
    rect = page.rect
    width_mm = rect.width * 0.352778
    height_mm = rect.height * 0.352778
    actual_size = (width_mm, height_mm)
    # Find closest match from standard sizes (check both portrait and landscape)
    closest = min(
        STANDARD_PAGE_SIZES,
        key=lambda s: min(
        math.hypot(s[0] - actual_size[0], s[1] - actual_size[1]), # portrait
        math.hypot(s[1] - actual_size[0], s[0] - actual_size[1]) # landscape
        )
    )
    return closest[2] # Return just the name (e.g. 'A0')

def get_file_parameters(path : pathlib.Path) -> dict:
    parameters = {
        "is_summary" : "False",
        "is_approval_cover_page" : "False",
        "has_signatures" : "False", 
        "page_size" : "",
        "is_pdf" : "False",
        "is_parasolid" : "False",
        "is_zip" : "False",
        "doc_number" : "", #  (just so I don’t have to recalculate it every time - actually, does this mean I need to update the parameters whenever I rename? Probably yeah? Maybe de scope.. )
        "doc_rev" : "",
        "doc_title" : "", 
        "doc_extension" : "" 
    }
    parameters["doc_number"], parameters["doc_rev"], parameters["doc_title"], parameters["doc_extension"] =\
        get_doc_no(path.name)
    if  parameters["doc_extension"] == "PDF":
        parameters["is_pdf"] = "True"
        parameters["page_size"] = _get_document_size(path)
        if "_summary" in path.name.lower():
            parameters["is_summary"] = "True"
        else:
            parameters["is_approval_cover_page"] = str(_is_approval_cover_page(path))
            parameters["has_signatures"] = str(_is_docusigned(path))
    if path.name.upper().endswith(".ZIP"):
        parameters["is_zip"] = "True"
    return parameters