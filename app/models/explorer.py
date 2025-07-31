import wx
from dataclasses import dataclass

@dataclass
class Buttons:
    BACK : wx.Button
    FORWARD : wx.Button
    UP : wx.Button
    NEW_FOLDER : wx.Button
    SEARCH : wx.Button
    GOTO : wx.Button
    COPY : wx.Button
    DOWNLOAD : wx.Button
    PASTE : wx.Button
    UPLOAD : wx.Button
    OPEN : wx.Button
    DELETE : wx.Button
    DOCUSIGN : wx.Button
    REVISION : wx.Button

    def __iter__(self):
        return iter([
            self.BACK,
            self.FORWARD,
            self.UP,
            self.NEW_FOLDER,
            self.SEARCH,
            self.GOTO,
            self.COPY,
            self.DOWNLOAD,
            self.PASTE,
            self.UPLOAD,
            self.OPEN,
            self.DELETE,
            self.DOCUSIGN,
            self.REVISION
        ])