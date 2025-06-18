from typing import Tuple

import dohq_artifactory.exception
import wx
from artifactory import ArtifactoryPath
import dohq_artifactory

from app.gui.login import LoginDialog
from app.core import credentials
from app.services.af import get_af_conn

_conn = None

def _test_af_creds(uname : str, pw : str) -> ArtifactoryPath | None:
    """
    If the uname / pw are okay returns the connection, otherwise nothing
    """
    conn = get_af_conn(uname, pw)
    try:
        conn.get_repositories()
    # Bad credentials
    except dohq_artifactory.exception.ArtifactoryException:
        return None
    # Credentials were fine
    return conn

def GetAFConnection(app : wx.App) -> ArtifactoryPath:
    # Get the stored username / password
    store_uname = credentials.get_username()
    store_pw = credentials.get_password()
    # Test the username / password
    if store_uname and store_pw:
        conn = _test_af_creds(store_uname, store_pw)
        if conn:
            return conn
    # If the username / password are wrong, as the user for it
    def login_dialog_completed(
            set_uname : str,
            set_pw : str,
            set_remember_me : bool,
            set_conn : ArtifactoryPath
        ):
        global _conn
        if set_remember_me:
            credentials.set_username(set_uname)
            credentials.set_password(set_pw)
        _conn = set_conn
    frame = LoginDialog(
        default_username = store_uname,
        callback_on_complete = login_dialog_completed,
        test_af_creds = _test_af_creds
    )
    frame.Show()
    app.MainLoop()
    return _conn