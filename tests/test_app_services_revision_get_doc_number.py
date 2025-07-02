import os
import sys
import unittest

# Get the parent directory of the current file
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

from app.services.revision import get_doc_no

class Services_Revision(unittest.TestCase):
    
    def test_standard_dmr(self):
        filename = "21_5901_130_H02_BOND_Mainboard.zip"
        actual = ("21.5901.130", "H02", "BOND Mainboard", "ZIP")
        found = get_doc_no(filename)
        assert actual == found
    
    def test_spares_dmr(self):
        filename = "S21_5901_130_H02_BOND_Mainboard_Spare.zip"
        actual = ("S21.5901.130", "H02", "BOND Mainboard Spare", "ZIP")
        found = get_doc_no(filename)
        assert actual == found
    
    def test_old_oem_dmr_wo_name(self):
        filename = "109_1200_000_A01.PDF"
        actual = ("109.1200.000", "A01", "", "PDF")
        found = get_doc_no(filename)
        assert actual == found
    
    def test_old_oem_dmr(self):
        filename = "109_1201_000_a01_bond_max_front_panel_box.pdf"
        actual = ("109.1201.000", "A01", "bond max front panel box", "PDF")
        found = get_doc_no(filename)
        assert actual == found
    
    def test_tbe_dmr(self):
        # filename = "109_12001_000_A01_BOND_MAX_Front_Panel_Box.pdf"
        # actual = ("109.1200.000", "A01", "BOND Max Front Panel Box", "PDF")
        # found = get_doc_no(filename)
        # assert actual == found
        pass
    
    def test_oem_dmr(self):
        return
        filename = "OEM971006_01_BOND_PRIME_Pump.pdf"
        actual = ("OEM971006", "01", "BOND PRIME Pump", "PDF")
        found = get_doc_no(filename)
        assert actual == found
    
    def test_lbs_oem_dmr(self):
        return
        filename = "LBS000026_01_Jadak__Imager.pdf"
        actual = ("LBS000026", "01", "Jadak Imager", "PDF")
        found = get_doc_no(filename)
        assert actual == found
    
    def test_standard_dhfr(self):
        return
        filename = "DHFR_12345_A01_P3_IA.pdf"
        actual = ("DHFR_12345", "A01", "P3 IA", "PDF")
        found = get_doc_no(filename)
        assert actual == found
    
    def test_sub_dhfr(self):
        return
        filename = "DHFR_12345_001_A01_P3_IA.pdf"
        actual = ("DHFR_12345_001", "A01", "P3 IA", "PDF")
        found = get_doc_no(filename)
        assert actual == found

if __name__ == "__main__":
    unittest.main()