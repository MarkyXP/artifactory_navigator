import json
import os
import pathlib
import sys
from datetime import datetime

from dotenv import load_dotenv

from app.models.config import Config as _Config


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# Load the secrets
load_dotenv(dotenv_path=resource_path(".env"))

# Load the config file
with open(os.getenv("CONFIG_PATH", "config.json"), "r") as config:
    config_dict: dict = json.loads(config.read())
    for route in ["AF_URL", "AF_PRETTY_URL", "AZURE_DST_SETTINGS"]:
        config_dict[route] = config_dict["AF_BASE_URL"] + config_dict[route]


ICON_FOLDER_PATH = resource_path("Assets/Icons")

CONFIG = _Config(
    **config_dict,
    APP_ICON_PATH=os.path.join(ICON_FOLDER_PATH, config_dict["APP_ICON_NAME"]),
    APP_SECRET=os.getenv("APP_SECRET"),
    AZURE_COSMOS_KEY=os.getenv("AZURE_COSMOS_KEY"),
    VERSION=os.getenv("VERSION", f"DEBUG-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}-{os.getlogin()}"),
    ICON_LOCATION=ICON_FOLDER_PATH,
    SHIPPING_TOOL_EMAIL_BODY_LOCATION=resource_path("app/services/email_body.html"),
)

# Make some nice pathlib paths
_store_path_expanded = os.path.expanduser(CONFIG.STORE_LOCATION)
CONFIG.STORE_LOCATION_PATH = pathlib.Path(_store_path_expanded)
CONFIG.STORE_TEMPFILES_PATH = pathlib.Path(_store_path_expanded).parent / "temp"
CONFIG.STORE_TEMPFILES_PATH.mkdir(parents=True, exist_ok=True)
