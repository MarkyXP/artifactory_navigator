from typing import List

import wx

from app.core.config import CONFIG
from app.models.af_search_results import AF_Result
from app.services import explorer as EXPLORER

class ShippingToolDialog(wx.Dialog):
    def __init__(self, items_to_ship : List[AF_Result]):
        title = f"{CONFIG.APP_NAME} | Document Shipping TOol"
        super().__init__(None, title=title, size=(300, 200))
        icon = wx.Icon(CONFIG.APP_ICON_PATH, wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Recipient Name
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(panel, label="Name:")
        self.name_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        hbox1.Add(label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        hbox1.Add(self.name_input, 1, wx.ALL | wx.EXPAND, 5)
        vbox.Add(hbox1, 0, wx.EXPAND)  

        # Recipient Email
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        label2 = wx.StaticText(panel, label="Email:")
        self.email_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        hbox2.Add(label2, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        hbox2.Add(self.email_input, 1, wx.ALL | wx.EXPAND, 5)
        vbox.Add(hbox2, 0, wx.EXPAND)  

        # Recipient Company
        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        label3 = wx.StaticText(panel, label="Company:")
        self.company_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        hbox3.Add(label3, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        hbox3.Add(self.company_input, 1, wx.ALL | wx.EXPAND, 5)
        vbox.Add(hbox3, 0, wx.EXPAND)   

        # Generate Email Button
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.generate_email_btn = wx.Button(panel, label="Generate Email")
        btn_sizer.Add(self.generate_email_btn, 0, wx.ALL | wx.CENTER, 5)
        vbox.Add(btn_sizer, 0, wx.ALIGN_CENTER)

        # Bind events
        self.generate_email_btn.Bind(wx.EVT_BUTTON, self.on_send_email)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key_down)

        panel.SetSizer(vbox)
        self.Centre()
        self.name_input.SetFocus()

        # Store handler
        self.items_to_ship = items_to_ship

    def on_send_email(self, event):
        recipient_name = self.name_input.GetValue().strip()
        recipient_email = self.email_input.GetValue().strip()
        recipient_company = self.company_input.GetValue().strip()
        if recipient_name and recipient_email and recipient_company:
            EXPLORER.send_to_shipping_tool(self.items_to_ship)
            self.Destroy()
        else:
            wx.MessageBox(
                "Please enter all of the recipient information",
                "Missing Input",
                wx.OK | wx.ICON_WARNING
            )

    def on_close(self, event):
        self.Destroy()
        wx.GetApp().ExitMainLoop()
