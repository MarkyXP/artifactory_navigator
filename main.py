import shutil

import wx

from app.core.config import CONFIG
from app.services.login import GetAFConnection
from app.services.explorer import Run

app = wx.App(False)
conn = GetAFConnection(app)
# User cancelled logging in
if not conn:
    exit()
try:
    Run(app, conn)
finally:
    app.ExitMainLoop()
    shutil.rmtree(CONFIG.STORE_TEMPFILES_PATH.as_posix(), ignore_errors=True)