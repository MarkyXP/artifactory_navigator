import dohq_artifactory.exception
import wx
from artifactory import ArtifactoryPath
import dohq_artifactory

from app.gui.explorer import FileExplorer
from app.services.af import get_af_conn

_uname = ""
_pw = ""

def Run(app : wx.App, af_conn : ArtifactoryPath):
    frame = FileExplorer()
    frame.Show()
    app.MainLoop()
    if _uname and _pw:
        return (_uname, _pw)
    return ("", "")