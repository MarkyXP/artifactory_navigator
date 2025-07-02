from dataclasses import dataclass

@dataclass
class ReVision_Response():
    """
    Args:
        CR_ID               : e.g. 12345
        DOC_NUMBER          : e.g. "091.1700.000"
        DOC_REVISION        : e.g. "B01"
        DOC_NAME_FULL       : e.g. "BOND-PRIME PM Add Kit - UK"
        DOC_IS_CO_APPROVED  : e.g. 1
        DOC_IS_OBSOLETE     : e.g. 0
        DATE_APPROVED       :
        DATE_OBSOLETE       :
    """
    CR_ID : int
    DOC_NUMBER : str
    DOC_REVISION : str
    DOC_NAME_FULL : str
    DOC_IS_CO_APPROVED : int
    DOC_IS_OBSOLETE : int
    DATE_APPROVED : str
    DATE_OBSOLETE : str