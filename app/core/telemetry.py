import uuid
import warnings

from azure.cosmos import CosmosClient
from requests import Session

from app.core.config import CONFIG
from app.core.tools import run_in_background

_disable_logging = False
_auth_acquired = False
try:
    _client = CosmosClient(
        url = CONFIG.AZURE_COSMOS_ENDPOINT,
        credential = CONFIG.AZURE_COSMOS_KEY,
        connection_verify = False
    )
    _session = Session()
    _session.verify = CONFIG.HTTP_CERT_FNAME
    _client.session = _session

    _database = _client.get_database_client(CONFIG.AZURE_COSMOS_DATABASE_ID)
    _container = _database.get_container_client(CONFIG.AZURE_COSMOS_CONTAINER_ID)
    _session_id = str(uuid.uuid4())
    _msg_count = 0
except Exception as _:
    _disable_logging = True

def set_auth(username : str, pw : str):
    global _auth_acquired
    _session.auth = (username, pw)
    _auth_acquired = True

@run_in_background
def log(msg : str):
    global _msg_count, _disable_logging, _auth_acquired
    if _disable_logging:
        return
    if not _auth_acquired:
        return
    try:
        # Note that it doesn't like using my cert so I'm using a requests
        # session - supressing the warning that the azure client doesn't
        # also have the cert.
        with warnings.catch_warnings(action="ignore"):
            _container.upsert_item(
                {
                    "id" : _session_id + "_" + str(_msg_count),
                    "src": "LBS_Artifactory_Navigator",
                    "session_id" : _session_id,
                    "msg" : msg,
                }
            )
    except Exception as _:
        # Logging failed for some reason, just disable it so it doesn't cause timeout delays
        _disable_logging = True
    _msg_count += 1
    
