import os
import sys

# Get the parent directory of the current file
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

from app.services.revision import get_drawings_for_cr

get_drawings_for_cr(12345)