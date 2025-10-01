import os
from typing import List

import wx

from app.core.config import CONFIG
from app.models.af_search_results import AF_Result
from app.services import azure_storage, email
from app.services import explorer as EXPLORER


class ShippingToolDialog(wx.Dialog):
    def __init__(self, items_to_ship: List[AF_Result]):
        title = f"{CONFIG.APP_NAME} | Document Shipping TOol"
        super().__init__(None, title=title, size=(300, 200))
        icon = wx.Icon(CONFIG.APP_ICON_PATH, wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        # Recipient Name
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(panel, label="Recipient Name:")
        self.name_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        hbox1.Add(label, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        hbox1.Add(self.name_input, 1, wx.ALL | wx.EXPAND, 5)
        vbox.Add(hbox1, 0, wx.EXPAND)

        # Recipient Email
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        label2 = wx.StaticText(panel, label="Recipient Email:")
        self.email_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        hbox2.Add(label2, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        hbox2.Add(self.email_input, 1, wx.ALL | wx.EXPAND, 5)
        vbox.Add(hbox2, 0, wx.EXPAND)

        # Recipient Company
        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        label3 = wx.StaticText(panel, label="Recipient Company:")
        self.company_input = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        hbox3.Add(label3, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        hbox3.Add(self.company_input, 1, wx.ALL | wx.EXPAND, 5)
        vbox.Add(hbox3, 0, wx.EXPAND)

        # Retention Time
        hbox4 = wx.BoxSizer(wx.HORIZONTAL)
        label4 = wx.StaticText(panel, label="Retention Time (days):")
        self.retention_time_input = wx.SpinCtrl(
            panel, min=5, max=90, initial=30, style=wx.ALIGN_RIGHT
        )
        hbox4.Add(label4, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        hbox4.Add(self.retention_time_input, 1, wx.ALL | wx.EXPAND, 5)
        vbox.Add(hbox4, 0, wx.EXPAND)

        # Generate Email Button
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.generate_email_btn = wx.Button(panel, label="Generate Email")
        btn_sizer.Add(self.generate_email_btn, 0, wx.ALL | wx.CENTER, 5)
        vbox.Add(btn_sizer, 0, wx.ALIGN_CENTER)

        # Bind events
        self.generate_email_btn.Bind(wx.EVT_BUTTON, self.on_send_email)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        # self.Bind(wx.EVT_CHAR_HOOK, self.on_send_email  )

        panel.SetSizer(vbox)
        self.Centre()
        self.name_input.SetFocus()

        # Store handler
        self.items_to_ship = items_to_ship

    def on_send_email(self, event):
        recipient_name = self.name_input.GetValue().strip()
        recipient_email = self.email_input.GetValue().strip()
        recipient_company = self.company_input.GetValue().strip()
        retention_time = int(self.retention_time_input.GetValue())
        if recipient_name and recipient_email and recipient_company:
            # Download the files to a ZIP archive
            archive_path = EXPLORER.download_to_zip_file(
                self.items_to_ship, recipient_company
            )
            # Upload them to Azure and generate a download link
            uploaded_url = azure_storage.upload(
                src=archive_path,
                dst_file_name=archive_path.name,
                sender_email=os.getlogin(),
                recipient_name=recipient_name,
                recipient_email=recipient_email,
                recipient_company=recipient_company,
            )
            access_link = azure_storage.get_access_link_w_token(
                uploaded_url, retention_time
            )
            email.generate_dst_email(
                recipient_name=recipient_name,
                recipient_email=recipient_email,
                recipient_company=recipient_company,
                retention_time=retention_time,
                zip_filename=archive_path.name,
                af_items=self.items_to_ship,
                download_link=access_link,
            )
            self.Destroy()
        else:
            wx.MessageBox(
                "Please enter all of the recipient information",
                "Missing Input",
                wx.OK | wx.ICON_WARNING,
            )

    def on_close(self, event):
        self.Destroy()
        wx.GetApp().ExitMainLoop()
