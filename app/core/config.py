import json
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
