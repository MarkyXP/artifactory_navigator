from typing import List

import wx

from app.core import telemetry
from app.models.af_search_results import AF_Result
from app.models.revision import ReVision_Response
from app.services.revision import get_doc_no


class BGColourManager():
    _COLOURS = {
        "GOOD" : [
            "#ecfcca", # Lime    100
            "#baf7da"  # Emerald 150
        ],
        "BAD" : [
            "#fff085", # Yellow 200
            "#fee685"  # Amber 200
        ],
        "NA" : [
            "#d4d4d8", # Zinc 300
            "#bababa"  # Zinc 400
        ]
    }
    def __init__(self):
        self._show_indexes = {
            key : 0 for key in list(self._COLOURS.keys())
        }
        self._last_doc_no = None
    
    def _get_colour(self, colour_description : str) -> str:
        """
        Takes a colour description from the keys of _COLOURS (e.g. 'GOOD', 'BAD')
        And returns the HEX colour (e.g. #ecfcca) based on self._show_index
        """
        return self._COLOURS[colour_description][self._show_indexes[colour_description]]


    def get(self, document_number : str, af_item : dict, rv_item : dict) -> wx.Colour:
        """
        Accepts a revision item dictionary, and returns the appropriate colour
        that should be used as the background colour.

        Note that it alternates the colour index as the part number changes
        """
        # Extract the info needed from the 
        af_rev = af_item[1].strip()
        rv_rev = rv_item[1].strip()
        # Logic to determine which colour to use
        if (rv_rev == af_rev) and rv_rev:
            colour_description = "GOOD"
        elif (rv_rev or af_rev) and rv_item[3]: # There is an AF or ReVision rev, and it is an Artifactory item
            colour_description = "BAD"
        else:
            colour_description = "NA"
        # Change the colour index if the part has changed
        if document_number != self._last_doc_no:
            self._show_indexes[colour_description] = (self._show_indexes[colour_description] + 1) % len(self._COLOURS[colour_description])
        colour = self._get_colour(colour_description)
        self._last_doc_no = document_number
        return wx.Colour(colour)

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
        # Show the data
        no_items_shown = 0
        empty = [""] * 5
        index = 0
        green_amount = 240
        for item in full_parts_list:
            green_amount = 240 + (250 - green_amount)
            rv_item = rv_dict.get(item, empty)
            rv_rev = rv_item[1].strip()
            rv_title = rv_item[2]
            af_items = af_dict.get(item, [empty])
            af_items.reverse()
            for af_item in af_items:
                af_rev = af_item[1].strip()
                af_title = af_item[2]
                index = self.file_list.InsertItem(0, item)
                self.file_list.SetItem(index, 1, rv_item[4])
                self.file_list.SetItem(index, 2, rv_rev)
                self.file_list.SetItem(index, 3, af_rev)
                self.file_list.SetItem(index, 4, rv_title)
                self.file_list.SetItem(index, 5, af_title)
                self.file_list.SetItem(index, 6, af_item[3])
                bg_colour = bg_colours.get(item, af_item, rv_item)
                self.file_list.SetItemBackgroundColour(
                    index, bg_colour
                )
                no_items_shown += 1
        # Change the height of the window based on how many items are shown
        self.SetSize(wx.Size(1250, 19*(no_items_shown+3)+80))