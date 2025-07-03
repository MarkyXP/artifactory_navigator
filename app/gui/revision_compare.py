from typing import List

import wx
import wx.grid as gridlib

from app.models.af_search_results import AF_Result
from app.models.revision import ReVision_Response
from app.services.revision import get_doc_no

# The table window with 4 columns and dummy data
class ReVision_Report_Frame(wx.Frame):
    def __init__(self,
                 title : str,
                 revision_data : List[ReVision_Response],
                 af_data : List[AF_Result]
                 ):
        super(ReVision_Report_Frame, self).__init__(None, title=title, size=(750, 500))
        self.refresh(revision_data, af_data)
    
    def refresh(
            self,
            revision_data : List[ReVision_Response],
            af_data : List[AF_Result]
    ):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        # File list with drag source support
        self.file_list = wx.ListCtrl(panel, style=wx.LC_REPORT|wx.BORDER_SUNKEN|wx.LC_EDIT_LABELS)
        self.file_list.InsertColumn(0, "Document Number", width=100)
        self.file_list.InsertColumn(1, "RV Rev", width=50)
        self.file_list.InsertColumn(2, "AF Rev.", width=50)
        self.file_list.InsertColumn(3, "RV Title", width=250)
        self.file_list.InsertColumn(4, "AF Title", width=250)
        vbox.Add(self.file_list, 1, wx.EXPAND|wx.ALL, 5)
        panel.SetSizer(vbox)
        # Format the data
        af_simple = [
            get_doc_no(f.name) for f in af_data
        ]
        af_dict = {
            i[0] : i for i in af_simple
        }
        rv_dict = {
            f.DOC_NUMBER : (
                f.DOC_NUMBER,
                f.DOC_REVISION,
                f.DOC_NAME_FULL,
                f.DOC_IN_AF
            )
            for f in revision_data
        }
        full_parts_list = list(set(i for i in list(af_dict.keys()) + list(rv_dict.keys())))
        full_parts_list.sort()
        # Show the data 
        empty = [""] * 4
        for index, item in enumerate(full_parts_list):
            rv_item = rv_dict.get(item, empty)
            af_item = af_dict.get(item, empty)
            rv_rev = rv_item[1]
            af_rev = af_item[1]
            rv_title = rv_item[2]
            af_title = af_item[2]
            index = self.file_list.InsertItem(0, item)
            self.file_list.SetItem(index, 1, rv_rev)
            self.file_list.SetItem(index, 2, af_rev)
            self.file_list.SetItem(index, 3, rv_title)
            self.file_list.SetItem(index, 4, af_title)
            if rv_rev == af_rev:
                self.file_list.SetItemBackgroundColour(index, wx.Colour(230, 250, 210, 50))
            if rv_item[3] == False:
                self.file_list.SetItemBackgroundColour(index, wx.Colour(230, 230, 230, 50))