import dohq_artifactory
import dohq_artifactory.exception
import wx

from app.core import credentials, telemetry
from app.gui.login import LoginDialog
from app.models.af_search_results import AF_Login_Error, AF_Login_Result
from app.services.af import get_af_conn

_conn = None


def _test_af_creds(uname: str, pw: str) -> AF_Login_Result | AF_Login_Error:
    """
    Checks the uname / pw against Artifactory.

    Returns an AF_Login_Result holding the connection *and* the repository list,
    or an AF_Login_Error describing why it was rejected. The caller is expected
    to keep the repository list - it is the same response that proves the
    credentials are good, and the explorer needs it to draw the root view, so
    fetching it again later would be a wasted round trip.
    """
    conn = get_af_conn(uname, pw)
    try:
        # lazy=True keeps this to a single request. The default (lazy=False)
        # makes the library issue an extra read() per repository, and the root
        # view only ever uses each repository's name.
        repos = [repo.name for repo in conn.get_repositories(lazy=True)]
    except dohq_artifactory.exception.ArtifactoryException as e:
        msg = f"Error: {e.args[0]}"
        if "404" in e.args[0]:
            msg = "Error: Could not connect to Artifactory"
        elif "Bad credentials" in e.args[0]:
            msg = "Invalid username or password"
        return AF_Login_Error(msg)
    # Credentials were fine
    return AF_Login_Result(conn=conn, repos=repos)


def GetAFConnection(app: wx.App) -> AF_Login_Result | AF_Login_Error:
    # Get the stored username / password
    store_uname = credentials.get_username()
    store_pw = credentials.get_password()
    # Test the username / password
    if store_uname and store_pw:
        result = _test_af_creds(store_uname, store_pw)
        if isinstance(result, AF_Login_Result):
            telemetry.log("Auto-login successful")
            return result

    # If the username / password are wrong, as the user for it
    def login_dialog_completed(
        set_uname: str, set_pw: str, set_remember_me: bool, set_result: AF_Login_Result
    ):
        global _conn
        if set_remember_me:
            credentials.set_username(set_uname)
            credentials.set_password(set_pw)
        _conn = set_result
        telemetry.log("Login successful")

    frame = LoginDialog(
        default_username=store_uname,
        callback_on_complete=login_dialog_completed,
        test_af_creds=_test_af_creds,
    )
    frame.Show()
    app.MainLoop()
    return _conn
