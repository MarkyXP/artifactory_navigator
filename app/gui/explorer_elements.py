from typing import Tuple
import wx

from app.models import explorer as models

def make_path_bar(panel : wx.Panel, vbox : wx.BoxSizer):
    hbox1 = wx.BoxSizer(wx.HORIZONTAL)
    dir_label = wx.StaticText(panel, label="Current Directory:")
    dir_text = wx.TextCtrl(panel, style=wx.TE_READONLY)
    hbox1.Add(dir_label, 0, wx.ALIGN_CENTER|wx.ALL, 5)
    hbox1.Add(dir_text, 1, wx.EXPAND|wx.ALL, 5)
    vbox.Add(hbox1, 0, wx.EXPAND)
    return dir_label, dir_text


def _make_nav_btn(parent : wx.Window, icon_name : str, tooltip : str):
    button_size = wx.Size(23,23)
    icon_bmp = wx.Bitmap(
        f"Assets/Icons/{icon_name}_Dark.png",
        wx.BITMAP_TYPE_ANY
    )
    button = wx.Button(parent, size=button_size)
    button.SetBitmapLabel(icon_bmp)
    button.SetToolTip(tooltip)
    return button

def make_navbar(parent : wx.Window, sizer : wx.BoxSizer) -> models.Buttons:
    hbox = wx.BoxSizer(wx.HORIZONTAL)
    buttons = models.Buttons(
        BACK = _make_nav_btn(parent, "Back", "Back a directory"),
        FORWARD = _make_nav_btn(parent, "Forward", "Forward a directory"),
        UP = _make_nav_btn(parent, "Up", "Go up a directory"),
        NEW_FOLDER = _make_nav_btn(parent, "New_Folder", "New Folder"),
        SEARCH = _make_nav_btn(parent, "Search", "Find File"),
        GOTO = _make_nav_btn(parent, "Goto", "Open CR/XECO Folder"),
        COPY = _make_nav_btn(parent, "Copy", "Copy Files"),
        DOWNLOAD = _make_nav_btn(parent, "Download", "Download Files"),
        PASTE = _make_nav_btn(parent, "Paste", "Paste Files from Clipboard"),
        UPLOAD = _make_nav_btn(parent, "Upload", "Upload files"),
        OPEN = _make_nav_btn(parent, "Open", "Open files"),
        DELETE = _make_nav_btn(parent, "Delete", "Delete files"),
        DOCUSIGN = _make_nav_btn(parent, "DocuSign", "Transfer to DocuSign"),
        REVISION = _make_nav_btn(parent, "ReVision", "Compare CR to ReVision")
    )
    for btn in buttons:
        hbox.Add(btn, 0, wx.ALL, 1)
    sizer.Add(hbox, 0, wx.ALIGN_LEFT)
    return buttons

def make_main_explorer(parent : wx.Window, sizer : wx.BoxSizer) -> wx.ListCtrl:
    file_list = wx.ListCtrl(
        parent,
        style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_EDIT_LABELS
    )
    file_list.InsertColumn(0, "Name", width=400)
    file_list.InsertColumn(1, "Type", width=70)
    file_list.InsertColumn(2, "Size", width=70)
    file_list.InsertColumn(3, "Date Modified", width=100)
    file_list.InsertColumn(4, "Date Updated", width=100)
    file_list.InsertColumn(5, "Deployed By", width=135)
    file_list.InsertColumn(6, "Sha256", width=100)
    sizer.Add(file_list, 1, wx.EXPAND | wx.ALL, 5)
    return file_list

def make_search(
        parent : wx.Window,
        sizer : wx.BoxSizer
    ) -> Tuple[wx.CollapsiblePane, wx.TextCtrl, wx.ListCtrl]:
    # Create the collapsible pane
    search_pane = wx.CollapsiblePane(parent, label="Search")
    # Add the box to the pane
    # sizer.Add(search_pane, 0, wx.EXPAND)
    pane_sizer = wx.BoxSizer(wx.VERTICAL)
    # Search input
    search_input = wx.TextCtrl(search_pane.GetPane())
    pane_sizer.Add(search_input, 0, wx.EXPAND | wx.ALL, 5)
    # Make a search results section
    search_results = wx.ListCtrl(
        search_pane.GetPane(),
        style=wx.LC_REPORT | wx.BORDER_SUNKEN
    )
    # the actual search results list
    search_results.InsertColumn(0, "Location", width=400)
    search_results.InsertColumn(1, "Name", width=400)
    search_results.InsertColumn(2, "Size", width=70)
    search_results.InsertColumn(3, "Date Modified", width=100)
    search_results.InsertColumn(4, "Date Updated", width=100)
    search_results.InsertColumn(5, "Deployed By", width=135)
    search_results.InsertColumn(6, "Sha256", width=100)

    pane_sizer.Add(search_results, 1, wx.EXPAND | wx.ALL, 5)
    search_pane.GetPane().SetSizer(pane_sizer)

    return search_pane, search_input, search_results