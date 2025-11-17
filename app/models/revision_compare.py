from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Generator

import wx

from app.models.af_search_results import AF_Result
from app.models.revision import ReVision_Response
from app.services.revision import get_doc_no

class ReportItemStatus(Enum):
    GOOD = [
        "#ecfcca", # Lime    100
        "#baf7da"  # Emerald 150
    ] 
    BAD = [
        "#fff085", # Yellow 200
        "#fee685"  # Amber 200
    ]
    NA = [
        "#d4d4d8", # Zinc 300
        "#bababa"  # Zinc 400
    ]

@dataclass
class ReportItem():
    document_number : str
    revision_location : str = ""
    revision_rev : str = ""
    revision_title : str = ""
    artifactory_revision : str = ""
    artifactory_title : str = ""
    artifactory_file_extension : str = ""
    bg_colour : wx.Colour = None
    should_be_in_af : bool = None
    status : ReportItemStatus = ReportItemStatus.NA

@dataclass
class Compare_Report():
    RVItems : List[ReVision_Response]
    AFItems : List[AF_Result]
    def _get_doc_nos_list(self) -> List[str]:
        """
        Extracts all of the document numbers.

        Returns:
            ['21.5901.130', '21.5901.200', ...]
        """
        af_doc_nos = [get_doc_no(doc.name)[0] for doc in self.AFItems]
        rv_doc_nos = [doc.DOC_NUMBER for doc in self.RVItems]
        doc_no_list = list(set(af_doc_nos + rv_doc_nos))
        doc_no_list.sort()#(reverse=True)
        return doc_no_list
    
    def get_af_doc_lookup(self) -> Dict[str, List[ReportItem]]:
        """
        Converts the Artifactory Report Items into a dictionary with the key
        of the document number.

        Returns:
        {
            '091.067.110' : <AF_Item>
        }
        """
        af_doc_lookup = defaultdict(list)
        for af_item in self.AFItems:
            docno, rev, title, extension = get_doc_no(af_item.name)
            report_item = ReportItem(
                document_number=docno,
                artifactory_revision=rev.strip(),
                artifactory_title=title.strip(),
                artifactory_file_extension=extension.strip()
            )
            af_doc_lookup[docno].append(report_item)
            pass
            af_doc_lookup[docno].sort(
                key=lambda item: (
                    item.artifactory_file_extension == "PDF", # Priority 1: Put the PDF files at the end
                    item.artifactory_file_extension,          # Priority 2: Sort by extension, then
                    item.artifactory_title,                   # Priority 3: Sort by file name
                )
            )
            pass
        return af_doc_lookup
    
    def get_revision_doc_lookup(self) -> Dict[str, ReportItem]:
        """
        Converts the ReVision Report Items into a dictionary with the key
        of the document number.

        Returns:
        {
            '091.067.110' : <RV_Item>
        }
        """
        return {
            revision_item.DOC_NUMBER : ReportItem(
                document_number = revision_item.DOC_NUMBER,
                revision_location = revision_item.DOC_LOCATION,
                revision_rev = revision_item.DOC_REVISION,
                revision_title = revision_item.DOC_NAME_FULL,
                should_be_in_af = revision_item.DOC_IN_AF
            )
            for revision_item in self.RVItems
        }

    def get_status(self, item : ReportItem) -> ReportItemStatus:
        #=====================================================================
        # ** Logic to determine which colour to use
        #=====================================================================
        # If the revision and artifactory revisions align, _and_ they're not
        # blank
        if (item.revision_rev == item.artifactory_revision) and item.revision_rev:
            return ReportItemStatus.GOOD
        # If it should be in AF according to ReVision _or_
        # it's a document in AF (and shouldn't be if it got here)
        elif item.should_be_in_af or item.artifactory_revision:
            return ReportItemStatus.BAD
        # Grey it out
        return ReportItemStatus.NA

    def get_items(self) -> Generator[ReportItem]:
        """
        Analyses the RV and AF Items provided when the class was generated,
        and returns a ReportItem for the table with the information needed
        """
        doc_no_list = self._get_doc_nos_list()
        af_doc_lookup = self.get_af_doc_lookup()
        revision_doc_lookup = self.get_revision_doc_lookup()
        bg_colours = BGColourManager()
        for doc_no in doc_no_list:
            rv_item = revision_doc_lookup.get(doc_no, ReportItem(document_number=doc_no))
            summary_found = False
            signoff_found = False
            all_docs_good = True
            # If there are no docs in AF for the item
            if doc_no not in af_doc_lookup:
                rv_item.status = self.get_status(rv_item)
                rv_item.bg_colour = bg_colours.get(rv_item)
                yield rv_item
            # If there are items in AF for the document number
            else:
                for report_item in af_doc_lookup[doc_no]:
                    rv_title = rv_item.revision_title
                    if "summary" in report_item.artifactory_title.lower():
                        summary_found = True
                        rv_title +=  " - Summary"
                    elif report_item.artifactory_file_extension == "PDF":
                        signoff_found = True
                    report_item.revision_location = rv_item.revision_location
                    report_item.revision_rev = rv_item.revision_rev
                    report_item.revision_title = rv_title
                    report_item.should_be_in_af = rv_item.should_be_in_af or False
                    report_item.status = self.get_status(report_item)
                    report_item.bg_colour = bg_colours.get(report_item)
                    if report_item.status != ReportItemStatus.GOOD:
                        all_docs_good = False
                    yield report_item
                if all_docs_good:
                    if not signoff_found:
                        missing_signoff_report = ReportItem(
                            document_number = doc_no,
                            revision_location = rv_item.revision_location,
                            revision_rev = rv_item.revision_rev,
                            revision_title = rv_item.revision_title,
                            artifactory_title = "Approval / Coversheet",
                            artifactory_file_extension= "PDF",
                            status = ReportItemStatus.BAD,
                        )
                        missing_signoff_report.bg_colour = bg_colours.get(missing_signoff_report)
                        yield missing_signoff_report
                    if not summary_found:
                        missing_summary_report = ReportItem(
                            document_number = doc_no,
                            revision_location = rv_item.revision_location,
                            revision_rev = rv_item.revision_rev,
                            revision_title = rv_item.revision_title + " - Summary",
                            artifactory_title = "",
                            artifactory_file_extension= "",
                            status = ReportItemStatus.BAD,
                        )
                        missing_summary_report.bg_colour = bg_colours.get(missing_summary_report)
                        yield missing_summary_report
            
                

class BGColourManager():
    def __init__(self):
        self._colour_indexes = {
            key : -1 for key in ReportItemStatus._member_names_
        }
        self._last_doc_no = None
    
    def _increment_colour_index(self, report : ReportItem) -> str:
        """
        Takes a colour description from the keys of _COLOURS (e.g. 'GOOD', 'BAD')
        And returns the HEX colour (e.g. #ecfcca) based on self._show_index
        """
        if report.document_number != self._last_doc_no:
            self._colour_indexes[report.status.name] = (self._colour_indexes[report.status.name] + 1) % len(report.status.value)
    
    def _get_colour(self, report : ReportItem) -> str:
        """
        Takes a colour description from the keys of _COLOURS (e.g. 'GOOD', 'BAD')
        And returns the HEX colour (e.g. #ecfcca) based on self._show_index
        """
        return report.status.value[self._colour_indexes[report.status.name]]


    def get(self, report : ReportItem) -> wx.Colour:
        """
        Accepts a revision item dictionary, and returns the appropriate colour
        that should be used as the background colour.

        Note that it alternates the colour index as the part number changes
        """
        # Change the colour index if the part has changed
        self._increment_colour_index(report)
        colour = self._get_colour(report)
        self._last_doc_no = report.document_number
        return wx.Colour(colour)