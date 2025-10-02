import os

import wx

from app.core.config import CONFIG
from app.models.go_to_cr import RepoType


class CRDialog(wx.Dialog):
    def __init__(self, open_cr_handler):
        super().__init__(None, title=CONFIG.APP_NAME, size=(300, 200))
        icon = wx.Icon(CONFIG.APP_ICON_PATH, wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # CR / XECO Input
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(panel, label="CR / XECO Number:")
        self.cr_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        hbox1.Add(label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        hbox1.Add(self.cr_input, 1, wx.ALL | wx.EXPAND, 5)
        vbox.Add(hbox1, 0, wx.EXPAND)

        # Radio box: DMR / DHFR
        self.radio_box = wx.RadioBox(
            panel,
            label="Select Type:",
            choices=list(RepoType.keys()),
            majorDimension=1,
            style=wx.RA_SPECIFY_ROWS,
        )
        vbox.Add(self.radio_box, 0, wx.ALL | wx.EXPAND, 10)

        # Go To Button
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.open_btn = wx.Button(panel, label="Open")
        btn_sizer.Add(self.open_btn, 0, wx.ALL | wx.CENTER, 5)
        vbox.Add(btn_sizer, 0, wx.ALIGN_CENTER)

        # Bind events
        self.open_btn.Bind(wx.EVT_BUTTON, self.on_go)
        self.cr_input.Bind(wx.EVT_TEXT_ENTER, self.on_go)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down)

        panel.SetSizer(vbox)
        self.Centre()
        self.cr_input.SetFocus()

        # Store handler
        self.open_cr_handler = open_cr_handler

    def on_go(self, event):
        cr_number = self.cr_input.GetValue().strip()
        selected_type = self.radio_box.GetStringSelection()
        selected_repo = RepoType[selected_type]
        if cr_number:
            self.open_cr_handler(cr_number, selected_repo)
            self.Destroy()
        else:
            wx.MessageBox(
                "Please enter a CR / XECO number.",
                "Missing Input",
                wx.OK | wx.ICON_WARNING,
            )

    def on_key_down(self, event):
        key_code = event.GetKeyCode()
        if key_code == wx.WXK_TAB:
            current = self.radio_box.GetSelection()
            new_selection = 1 if current == 0 else 0
            self.radio_box.SetSelection(new_selection)
        else:
            event.Skip()  # Let other keys be processed normally

    def on_close(self, event):
        self.Destroy()
        wx.GetApp().ExitMainLoop()
