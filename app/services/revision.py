from typing import List
import re

from requests import Session

from app.core.config import CONFIG
from app.core.tools import run_in_background
from app.models.revision import ReVision_Response

_session = Session()
_session.verify = CONFIG.HTTP_CERT_FNAME

def get_drawings_for_cr(cr_number : int) -> List[ReVision_Response]:
    if not cr_number:
        return [] 
    REVISION_URL = "http://10.10.240.79:3000/search"
    qry_params = {
        "search" : f"cr{cr_number}",
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
            DOC_NAME_FULL = dwg["DN_DOC_NAME_FULL"],
            DOC_IS_CO_APPROVED = dwg["RV_DOC_IS_CO_APPROVED"],
            DOC_IS_OBSOLETE = dwg["RV_DOC_IS_OBSOLETE"],
            DATE_APPROVED = dwg["RV_DATE_APPROVED"],
            DATE_OBSOLETE = dwg["RV_DATE_OBSOLETE"]
        ) for dwg in drawings
    ]
    return drawing_fmt
    
def get_doc_no(filename : str) -> str | None:
    """
    Args:
     - filename : e.g. '21_5901_130_A01_BOND_Mainboard_BOM.zip'
    Returns:
     - Doc No with out Revision : e.g. '21.5901.130'
    """
    dmr_regex = re.compile()