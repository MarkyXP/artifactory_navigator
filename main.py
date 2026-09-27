# Run the updater!
# from app.core.run_updater import run_updater
# run_updater()

import shutil

import pip_system_certs.wrapt_requests
import wx

# ------------------------------------------------------------------
#  SSL - Patch certifi package to the the local machine cert store
# ------------------------------------------------------------------
pip_system_certs.wrapt_requests.inject_truststore()

from app.core.config import CONFIG
from app.services import azure_storage, explorer, login, check_new_version

# ------------------------------------------------------------------
#  Check Updater
# ------------------------------------------------------------------
check_new_version.check_for_updates()

# ------------------------------------------------------------------
#  Set App ID
# ------------------------------------------------------------------
from ctypes import windll
app_id = "65453D83-C0FC-46A8-BA56-75DAB289695F"
windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

# ------------------------------------------------------------------
#  Set App ID
# ------------------------------------------------------------------
app = wx.App(False)

# ------------------------------------------------------------------
#  Login (or Auto-login)
# ------------------------------------------------------------------
login_result = login.GetAFConnection(app)
# User cancelled logging in
if not login_result:
    import sys
    sys.exit()

# ------------------------------------------------------------------
#  Run the main app
# ------------------------------------------------------------------
try:
    # Start the background job to get DST config
    azure_storage.AF_SESSION = login_result.conn
    azure_storage.get_azure_details.start()
    # Run the main app
    # The repo list came back with the login, so the root view doesn't have to
    # ask for it again
    explorer.Run(app, login_result.conn, initial_repos=login_result.repos)
finally:
    app.ExitMainLoop()
    shutil.rmtree(CONFIG.STORE_TEMPFILES_PATH.as_posix(), ignore_errors=True)
