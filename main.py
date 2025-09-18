# Run the updater!
# from app.core.run_updater import run_updater
# run_updater()

import shutil

import wx

from app.core.config import CONFIG
from app.services import explorer
from app.services import login

app = wx.App(False)
conn = login.GetAFConnection(app)
# User cancelled logging in
if not conn:
    import sys
    sys.exit()
try:
    explorer.Run(app, conn)
finally:
    app.ExitMainLoop()
    shutil.rmtree(CONFIG.STORE_TEMPFILES_PATH.as_posix(), ignore_errors=True)
