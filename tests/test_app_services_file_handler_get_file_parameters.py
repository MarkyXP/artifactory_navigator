import os
import sys
import unittest

# Get the parent directory of the current file
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

from app.services.file_handler import get_file_parameters


class Services_Revision(unittest.TestCase):
    def test_21_5901_500(self):
        test_doc = get_file_parameters(
            "tests/Assets/21_5901_500_D01_Approval_Sheet_Form.pdf"
        )
        parameters = {
            "is_summary": False,
            "is_approval_cover_page": True,
            "has_signatures": True,
            "page_size": "A4",
            "is_pdf": True,
            "is_parasolid": False,
            "is_zip": False,
            "doc_number": "21.5901.500",
            "doc_rev": "D01",
            "doc_title": "Approval Sheet Form",
            "doc_extension": "PDF",
        }
        assert test_doc == parameters

    def test_LRR(self):
        test_doc = get_file_parameters("tests/Assets/CR12774_LRR.pdf")
        parameters = {
            "is_summary": False,
            "is_approval_cover_page": True,
            "has_signatures": True,
            "page_size": "A4",
            "is_pdf": True,
            "is_parasolid": False,
            "is_zip": False,
            "doc_number": "",
            "doc_rev": "",
            "doc_title": "CR12774 LRR",
            "doc_extension": "PDF",
        }
        assert test_doc == parameters

    def test_ai_file(self):
        test_doc = get_file_parameters(
            "tests/Assets/21_6602_100_a01_bond_iii_resale_rating_plate_label.ai"
        )
        parameters = {
            "is_summary": False,
            "is_approval_cover_page": False,
            "has_signatures": False,
            "page_size": "",
            "is_pdf": False,
            "is_parasolid": False,
            "is_zip": False,
            "doc_number": "21.6602.100",
            "doc_rev": "A01",
            "doc_title": "bond iii resale rating plate label",
            "doc_extension": "AI",
        }
        assert test_doc == parameters

    def test_zip_dhfr(self):
        test_doc = get_file_parameters("tests/Assets/DHFR_18564_A01_Appendix_C.zip")
        parameters = {
            "is_summary": False,
            "is_approval_cover_page": False,
            "has_signatures": False,
            "page_size": "",
            "is_pdf": False,
            "is_parasolid": False,
            "is_zip": True,
            "doc_number": "DHFR_18564",
            "doc_rev": "A01",
            "doc_title": "Appendix C",
            "doc_extension": "ZIP",
        }
        assert test_doc == parameters

    def test_reused_dhfr(self):
        test_doc = get_file_parameters(
            "tests/Assets/DHFR 3772-0121 B01 PostMan REST Client 0.8.4.11 Tool Validation Record.pdf"
        )
        parameters = {
            "is_summary": False,
            "is_approval_cover_page": True,
            "has_signatures": False,
            "page_size": "A4",
            "is_pdf": True,
            "is_parasolid": False,
            "is_zip": False,
            "doc_number": "DHFR_3772_0121",
            "doc_rev": "B01",
            "doc_title": "PostMan REST Client 0 8 4 11 Tool Validation Record",
            "doc_extension": "PDF",
        }
        assert test_doc == parameters


if __name__ == "__main__":
    unittest.main()
