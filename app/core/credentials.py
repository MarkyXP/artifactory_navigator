import json
import os
import subprocess

from cryptography.fernet import Fernet

from app.core.config import CONFIG

_key = CONFIG.APP_SECRET.encode()
_fernet = Fernet(_key)


def _get_login_users_full_name(username: str | None = None) -> str:
    """

    Returns a string with the domain name registered against the username,
    e.g. "Mark Evans".
    Note: If no match is found it will just return a blank string.
    Args:

     username : Uses the domain registry to lookup the full name for the username
                If no username is provided it just uses the currently logged
                in users username.
    """
    if username is None:
        username = "%USERNAME%"
    try:
        name = subprocess.check_output(
            f'net user {username} /domain | FIND /I "Full Name"', shell=True
        )
    except Exception as _:
        return ""
    full_name = name.replace(b"Full Name", b"").strip().decode(errors="ignore")
    return full_name


def _get_login_username() -> str:
    """
    Returns the users username, e.g. "zmze"
    """
    return os.getlogin()


def _get_store() -> dict:
    """
    Loads and decrypts the store with user details.
    Returns an empty dictionary if the store doesn't exist or is corrupted.
    """
    store_path = CONFIG.STORE_LOCATION_PATH
    if store_path.exists():
        with store_path.open() as f:
            try:
                encrypted_store = f.read()
                decrypted_store_json = _fernet.decrypt(encrypted_store.encode())
                return json.loads(decrypted_store_json)
            except Exception as _:
                # The file has been corrupted
                return {}
    return {}


def _save_store(store: dict):
    """
    Encrypts the store with user details and saves it.
    """
    store_path = CONFIG.STORE_LOCATION_PATH
    encrypted_store_json = _fernet.encrypt(json.dumps(store).encode()).decode()
    # Make the folderpath if it doesn't already exist
    store_path.parent.mkdir(parents=True, exist_ok=True)
    with store_path.open(mode="w") as f:
        f.write(encrypted_store_json)


def get_username() -> str:
    """
    Returns the users username to log in to Artifactory.
    Note: If creds are saved it will get it from there
          If creds are not saved it will use the logged in users username
    """
    store = _get_store()
    return store.get("username", _get_login_username())


def set_username(username: str) -> None:
    """
    Saves the username to the store for quick login next time
    """
    store = _get_store()
    store["username"] = username
    _save_store(store)


def get_password() -> str:
    """
    Gets the stored password (if stored)
    """
    store = _get_store()
    return store.get("pass", "")


def set_password(pw: str) -> None:
    """
    Encrypts the password using fernet encryption
    and saves it to the store.
    """
    store = _get_store()
    store["pass"] = pw
    _save_store(store)
