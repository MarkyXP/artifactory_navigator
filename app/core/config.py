import json
from pathlib import Path
import os

from dotenv import load_dotenv

from app.models.config import Config as _Config

load_dotenv()

with open("app/core/config.json", "r") as f:
    config_dict : dict = json.load(f)

CONFIG = _Config(
    **config_dict,
    APP_SECRET=os.getenv("APP_SECRET")
)

_store_path_expanded = os.path.expanduser(CONFIG.STORE_LOCATION)
CONFIG.STORE_LOCATION_PATH = Path(_store_path_expanded)
CONFIG.STORE_TEMPFILES_PATH = Path(_store_path_expanded).parent / "temp"
