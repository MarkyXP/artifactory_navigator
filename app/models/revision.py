from dataclasses import dataclass

@dataclass
class ReVision_Response():
    """
    Args:
        CR_ID               : e.g. 12345
        DOC_NUMBER          : e.g. "091.1700.000"
        DOC_REVISION        : e.g. "B01"
        DOC_NAME_FULL       : e.g. "BOND-PRIME PM Add Kit - UK"
        
    """
    CR_ID : int
    DOC_NUMBER : str
    DOC_REVISION : str
    DOC_NAME_FULL : str
    DOC_LOCATION : str
    DOC_IS_PDF : bool
    DOC_IS_CD : bool
    DOC_IS_ZIP : bool
    DOC_IN_AF : bool