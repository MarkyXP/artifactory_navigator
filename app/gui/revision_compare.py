from typing import List

import wx

from app.core import telemetry
from app.models.af_search_results import AF_Result
from app.models.revision import ReVision_Response
from app.models.revision_compare import BGColourManager
from app.services.revision import get_doc_no
from app.models.revision_compare import Compare_Report

# The table window with 4 columns and dummy data
class ReVision_Report_Frame(wx.Frame):
    def __init__(
        self,
        title: str,
        revision_data: List[ReVision_Response],
        af_data: List[AF_Result],
    ):
        
        super(ReVision_Report_Frame, self).__init__(None, title=title, size=(1250, 500))
        self.title = title
        self.refresh(revision_data, af_data)
    
    def format_parts_for_report(self, revision_data: List[ReVision_Response], af_data: List[AF_Result]):
        # Format the data
        af_simple = [get_doc_no(f.name) for f in af_data]
        af_dict = {}
        for item in af_simple:
            af_dict[item[0]] = af_dict.get(item[0], []) + [item]
        rv_dict = {
            f.DOC_NUMBER: (
                f.DOC_NUMBER,
                f.DOC_REVISION,
                f.DOC_NAME_FULL,
                f.DOC_IN_AF,
                f.DOC_LOCATION,
            )
            for f in revision_data
        }
        full_parts_list = list(
            set(i for i in list(af_dict.keys()) + list(rv_dict.keys()))
        )
        full_parts_list.sort(reverse=True)
        return full_parts_list

    def refresh(self, revision_data: List[ReVision_Response], af_data: List[AF_Result]):
        telemetry.log(f"Revision Report - Generating - {self.title}")
        bg_colours = BGColourManager()
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        # File list with drag source support
        self.file_list = wx.ListCtrl(
            panel, style=wx.LC_REPORT | wx.BORDER_SUNKEN | wx.LC_EDIT_LABELS
        )
        self.file_list.InsertColumn(0, "Document Number", width=120)
        self.file_list.InsertColumn(1, "RV Location", width=90)
        self.file_list.InsertColumn(2, "RV Rev", width=60)
        self.file_list.InsertColumn(3, "AF Rev.", width=60)
        self.file_list.InsertColumn(4, "RV Title", width=400)
        self.file_list.InsertColumn(5, "AF Title", width=400)
        self.file_list.InsertColumn(6, "AF File Type", width=75)
        vbox.Add(self.file_list, 1, wx.EXPAND | wx.ALL, 5)
        panel.SetSizer(vbox)
        # Format the data
        report = Compare_Report(revision_data, af_data)
        no_items_shown = 0
        for item in report.get_items():
            index = self.file_list.InsertItem(no_items_shown, item.document_number)
            self.file_list.SetItem(index, 1, item.revision_location)
            self.file_list.SetItem(index, 2, item.revision_rev)
            self.file_list.SetItem(index, 3, item.artifactory_revision)
            self.file_list.SetItem(index, 4, item.revision_title)
            self.file_list.SetItem(index, 5, item.artifactory_title)
            self.file_list.SetItem(index, 6, item.artifactory_file_extension)
            self.file_list.SetItemBackgroundColour(
                index, item.bg_colour
            )
            no_items_shown += 1
        # Change the height of the window based on how many items are shown
        self.SetSize(wx.Size(1250, 19*(no_items_shown+3)+80))