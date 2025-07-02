import os
import sys
import unittest

# Get the parent directory of the current file
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

from app.services.revision import get_drawings_for_cr

class Services_Revision(unittest.TestCase):
    def test_12345(self):
        get_drawings_for_cr(12345)

if __name__ == "__main__":
    unittest.main()