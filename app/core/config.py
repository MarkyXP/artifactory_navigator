import json
import os
import pathlib
import sys

from dotenv import load_dotenv

from app.models.config import Config as _Config

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Load the secrets
load_dotenv(dotenv_path=resource_path(".env"))

# Load the config file
possible_config_locations = [
    pathlib.Path("config.json"),
    pathlib.Path("app/core/config.json"),
]
config_found = False
for config_location in possible_config_locations:
    if config_location.exists():
        config = config_location.read_text()
        try:
            config_dict : dict = json.loads(config)
            config_found = True
            break
        except Exception as _:
            raise "Error reading config file - Ensure the json is not corrupted"
if not config_found:
    raise "Error - Could not find config.json file"

ICON_FOLDER_PATH = resource_path("Assets/Icons")

CONFIG = _Config(
    **config_dict,
    APP_ICON_PATH = os.path.join(ICON_FOLDER_PATH, config_dict["APP_ICON_NAME"]),
    APP_SECRET = os.getenv("APP_SECRET"),
    AZURE_COSMOS_KEY = os.getenv("AZURE_COSMOS_KEY"),
    VERSION = os.getenv("VERSION", "DEBUG"),
    ICON_LOCATION = ICON_FOLDER_PATH
)

# Make some nice pathlib paths
_store_path_expanded = os.path.expanduser(CONFIG.STORE_LOCATION)
CONFIG.STORE_LOCATION_PATH = pathlib.Path(_store_path_expanded)
CONFIG.STORE_TEMPFILES_PATH = pathlib.Path(_store_path_expanded).parent / "temp"
