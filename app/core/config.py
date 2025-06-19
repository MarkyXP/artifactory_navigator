import json
import os
import pathlib

from dotenv import load_dotenv

from app.models.config import Config as _Config

# Load the secrets
load_dotenv()

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
        except Exception as e:
            raise f"Error reading config file - Ensure the json is not corrupted"
if not config_found:
    raise "Error - Could not find config.json file"

CONFIG = _Config(
    **config_dict,
    APP_SECRET=os.getenv("APP_SECRET"),
    AZURE_COSMOS_KEY = os.getenv("AZURE_COSMOS_KEY")
)

# Make some nice pathlib paths
_store_path_expanded = os.path.expanduser(CONFIG.STORE_LOCATION)
CONFIG.STORE_LOCATION_PATH = pathlib.Path(_store_path_expanded)
CONFIG.STORE_TEMPFILES_PATH = pathlib.Path(_store_path_expanded).parent / "temp"
