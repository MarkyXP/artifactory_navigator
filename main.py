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


app = wx.App(False)
conn = login.GetAFConnection(app)
# User cancelled logging in
if not conn:
    import sys

    sys.exit()
try:
    # Start the background job to get DST config
    azure_storage.AF_SESSION = conn
    azure_storage.get_azure_details.start()
    # Run the main app
    explorer.Run(app, conn)
finally:
    app.ExitMainLoop()
    shutil.rmtree(CONFIG.STORE_TEMPFILES_PATH.as_posix(), ignore_errors=True)
