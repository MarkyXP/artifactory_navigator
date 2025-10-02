import os
import shutil

import wx
import wx.aui


class FileExplorer(wx.Frame):
    def __init__(self, parent, title):
        super().__init__(parent, title=title, size=(800, 600))

        # Creating the panel and layout
        self.panel = wx.Panel(self)
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)

        # File list box to display files
        self.file_list = wx.ListBox(self.panel, style=wx.LB_SINGLE)
        self.sizer.Add(self.file_list, 1, flag=wx.EXPAND | wx.ALL, border=5)

        # Open file button
        self.open_button = wx.Button(self.panel, label="Open File")
        self.sizer.Add(self.open_button, 0, flag=wx.ALL, border=5)

        # Bind events
        self.Bind(wx.EVT_BUTTON, self.on_open, self.open_button)

        # Setting up drag-and-drop
        self.drop_target = FileDropTarget(self.file_list)
        self.file_list.SetDropTarget(self.drop_target)

        self.panel.SetSizer(self.sizer)

        self.Bind(wx.EVT_LISTBOX, self.on_file_selected, self.file_list)

        self.Centre()
        self.Show()

    def on_open(self, event):
        with wx.FileDialog(
            self,
            "Open File",
            wildcard="All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as file_dialog:
            if file_dialog.ShowModal() == wx.ID_OK:
                file_path = file_dialog.GetPath()
                self.file_list.Append(file_path)
                self.open_file(file_path)

    def open_file(self, file_path):
        """Open the file (this could be customized based on file type)."""
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                content = f.read()
                dlg = wx.MessageDialog(self, content, "File Content", wx.OK)
                dlg.ShowModal()

    def on_file_selected(self, event):
        selected_file = self.file_list.GetStringSelection()
        if selected_file:
            self.open_file(selected_file)


class FileDropTarget(wx.TextDropTarget):
    def __init__(self, list_box):
        self.list_box = list_box
        # Call the base class constructor
        wx.TextDropTarget.__init__(self)

    def OnDropText(self, x, y, text):
        # Add the dropped file to the list box
        self.list_box.Append(text)
        return True


if __name__ == "__main__":
    app = wx.App(False)
    FileExplorer(None, title="File Explorer")
    app.MainLoop()
