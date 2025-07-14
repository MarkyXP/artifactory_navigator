from typing import List, Tuple
import re

from requests import Session

from app.core.config import CONFIG
# from app.core.tools import run_in_background
from app.models.revision import ReVision_Response

_session = Session()
_session.verify = CONFIG.HTTP_CERT_FNAME
_dhfr_regex = re.compile(r"(DHFR\.\d{4,5}(?:\.\d{4})?)\.([A-Z]\d{2})")
_dmr_regex = re.compile(r"([A-Z]{0,2}\d{2,4}\.\d{4}\.\d{3})\.?([A-Z]{0,2}\d{2})")
_oem_regex = re.compile(r"(OEM\d{2,5})\.(\d{1,2})")
_lbs_oem_regex = re.compile(r"(LBS\d{6})\.(\d{2})")


def get_drawings_for_cr(cr_number : int) -> List[ReVision_Response]:
    if not cr_number:
        return [] 
    REVISION_URL = "http://10.10.240.79:3000/search"
    qry_params = {
        "search" : f"__mdcr__{cr_number}",
        "results" : 10000
    }
    resp =_session.get(
        url = REVISION_URL, params= qry_params
    )
    drawings = resp.json()
    drawing_fmt = [
        ReVision_Response(
            CR_ID = dwg["CR_ID"],
            DOC_NUMBER = dwg["DN_DOC_NUMBER"],
            DOC_REVISION = dwg["RV_DOC_REVISION"],
            DOC_NAME_FULL = dwg["RV_DOC_NAME_FULL"],
            DOC_LOCATION = dwg["RV_DOC_LOCATION"],
            DOC_IS_PDF = dwg["RV_FILE_PDF"] == 1,
            DOC_IS_CD = dwg["RV_FILE_CD"] == 1,
            DOC_IS_ZIP = dwg["RV_FILE_ZIP"] == 1,
            DOC_IN_AF = "art" in dwg["RV_DOC_LOCATION"].lower()
        ) for dwg in drawings
    ]
    return drawing_fmt
    
def get_doc_no(filename : str) -> Tuple[str, str, str, str]:
    """
    Args:
     - filename : e.g. '21_5901_130_A01_BOND_Mainboard_BOM.zip'
    Returns:
     - doc_no  : e.g. "21.5901.130"
     - doc_rev : e.g. "A01"
     - doc_title : e.g. "BOND Mainboard BOM"
     - file_ext : e.g. "PDF"
    """
    # Get (and remove) the file extension to start
    file_ext = filename.upper().split(".")[-1]
    stem = filename[:-(len(file_ext)+1)]
    # Look for DHFR #s _FIRST_ (e.g. 'DHFR_12345_A01_091_5591_130_DDD.PDF')
    # Look for DMR #s
    name_alphanum_raw = re.sub(r"[^A-Z0-9]", r".", stem.upper())
    name_alphanum = re.sub(r"\.+", r".", name_alphanum_raw)
    dhfr = re.findall(_dhfr_regex, name_alphanum)
    dmr = re.findall(_dmr_regex, name_alphanum)
    oem = re.findall(_oem_regex, name_alphanum)
    lbs_oem = re.findall(_lbs_oem_regex, name_alphanum)
    if dhfr:
        doc_no, doc_rev = dhfr[0]
        name_preamble = f"{doc_no}.+?{doc_rev}"
        doc_no = doc_no.replace(".", "_")
    elif dmr:
        doc_no, doc_rev = dmr[0]
        name_preamble = f"{doc_no}.+?{doc_rev}"
    elif oem:
        doc_no, doc_rev = oem[0]
        name_preamble = f"{doc_no}.+?{doc_rev}"
    elif lbs_oem:
        doc_no, doc_rev = lbs_oem[0]
        name_preamble = f"{doc_no}.+?{doc_rev}"
    else:
        doc_no, doc_rev = "", ""
        name_preamble = ""
    doc_title_raw = re.sub(name_preamble, "", stem, flags=re.IGNORECASE)
    doc_title_double_spaces = re.sub(r"[^a-zA-Z0-9]", " ", doc_title_raw)
    doc_title = re.sub(r"\s+", " ", doc_title_double_spaces).strip()
    return doc_no, doc_rev, doc_title, file_ext
