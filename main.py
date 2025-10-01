# Run the updater!
# from app.core.run_updater import run_updater
# run_updater()

import shutil

import wx

from app.core.config import CONFIG
from app.services import explorer
from app.services import login
from app.services import azure_storage

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
