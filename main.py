import wx

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