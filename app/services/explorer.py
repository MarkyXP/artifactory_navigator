import wx
from artifactory import ArtifactoryPath
import dohq_artifactory

from app.gui.explorer import FileExplorer

_uname = ""
_pw = ""

def Run(app : wx.App, af_conn : ArtifactoryPath):
    # initial_folders = af_conn.get_repositories()
    frame = FileExplorer(af_conn)
    frame.Show()
    app.MainLoop()
    if _uname and _pw:
        return (_uname, _pw)
    return ("", "")