import os
import sys
import unittest

# Get the parent directory of the current file
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

from app.services.file_handler import _is_approval_cover_page

class Services_Revision(unittest.TestCase):
    def test_21_5901_500(self):
        test_doc = _is_approval_cover_page("tests/Assets/21_5901_500_D01_Approval_Sheet_Form.pdf")
        assert test_doc

    def test_21_6604(self):
        test_doc = _is_approval_cover_page("tests/Assets/21_6604_100_a01_bond_rx_resale_rating_plate_label_Summary.pdf")
        assert not test_doc

    def test_zip(self):
        test_doc = _is_approval_cover_page("tests/Assets/Complete_with_Docusign_T45_0001_110_A01_Hist.zip")
        assert not test_doc

if __name__ == "__main__":
    unittest.main()