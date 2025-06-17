import wx
import os

class FileExplorer(wx.Frame):
    def __init__(self, parent, title):
        super(FileExplorer, self).__init__(parent, title=title, size=(800, 600))

        # Create a panel in the frame
        panel = wx.Panel(self)

        # Create a list control to display files
        self.list_ctrl = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.BORDER_SUNKEN)
        self.list_ctrl.InsertColumn(0, 'File Name', width=500)
        self.list_ctrl.InsertColumn(1, 'File Path', width=300)

        # Create a sizer to layout the widgets
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list_ctrl, 1, wx.EXPAND | wx.ALL, 5)

        # Set the panel's sizer
        panel.SetSizer(sizer)

        # Bind events for drag and drop
        self.Bind(wx.EVT_LIST_BEGIN_DRAG, self.on_begin_drag)
        # self.Bind(wx.EVT_LIST_DROP_HIGHLIGHT, self.on_drop_highlight)
        # self.Bind(wx.END_DRAG, self.on_end_drag)

        # Show the frame
        self.Show()

    def on_begin_drag(self, event):
        index = event.GetIndex()
        if index != -1:
            data = wx.FileDataObject()
            item_text = self.list_ctrl.GetItemText(index)
            data.AddFile(item_text)
            drop_source = wx.DropSource(self.list_ctrl)
            drop_source.SetData(data)
            drop_source.DoDragDrop()

    def on_drop_highlight(self, event):
        pass

    def on_end_drag(self, event):
        pass

    def add_file(self, file_path):
        if os.path.isfile(file_path):
            index = self.list_ctrl.GetItemCount()
            self.list_ctrl.InsertItem(index, os.path.basename(file_path))
            self.list_ctrl.SetItem(index, 1, file_path)

if __name__ == '__main__':
    app = wx.App(False)
    frame = FileExplorer(None, 'File Explorer')
    app.MainLoop()