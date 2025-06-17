import wx
import os
import shutil

class FileExplorerFrame(wx.Frame):
    def __init__(self, *args, **kw):
        super(FileExplorerFrame, self).__init__(*args, **kw)

        self.InitUI()
        self.Centre()

    def InitUI(self):
        self.SetTitle('Simple File Explorer')
        self.SetSize((800, 600))

        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Create a text control for displaying the current directory
        self.current_dir = wx.TextCtrl(panel)
        main_sizer.Add(self.current_dir, 0, wx.EXPAND | wx.ALL, 5)

        # Create a list control for displaying files and directories
        self.file_list = wx.ListCtrl(panel, style=wx.LC_LIST | wx.LC_SORT_ASCENDING)
        main_sizer.Add(self.file_list, 1, wx.EXPAND | wx.ALL, 5)

        # Bind events
        self.file_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
        self.file_list.Bind(wx.EVT_LIST_BEGIN_DRAG, self.OnDragInit)

        # Set the initial directory
        self.current_directory = os.getcwd()
        self.current_dir.SetValue(self.current_directory)
        self.UpdateFileList()

        panel.SetSizer(main_sizer)

    def UpdateFileList(self):
        self.file_list.ClearAll()
        try:
            files = os.listdir(self.current_directory)
            for file in files:
                self.file_list.Append(file)
        except Exception as e:
            wx.MessageBox(str(e), "Error", wx.OK | wx.ICON_ERROR)

    def OnItemActivated(self, event):
        selected_item = self.file_list.GetFirstSelected()
        if selected_item != -1:
            item_text = self.file_list.GetItemText(selected_item)
            item_path = os.path.join(self.current_directory, item_text)
            if os.path.isdir(item_path):
                self.current_directory = item_path
                self.current_dir.SetValue(self.current_directory)
                self.UpdateFileList()
            elif os.path.isfile(item_path):
                os.startfile(item_path)

    def OnDragInit(self, event):
        selected_item = self.file_list.GetFirstSelected()
        if selected_item != -1:
            item_text = self.file_list.GetItemText(selected_item)
            item_path = os.path.join(self.current_directory, item_text)

            # Create a data object for dragging
            data = wx.FileDataObject()
            data.AddFile(item_path)

            # Create a drop source and start dragging
            drop_source = wx.DropSource(self.file_list)
            drop_source.SetData(data)
            result = drop_source.DoDragDrop(wx.Drag_DefaultMove)

            if result == wx.DragMove:
                # Handle move operation
                pass
            elif result == wx.DragCopy:
                # Handle copy operation
                pass

if __name__ == '__main__':
    app = wx.App()
    frame = FileExplorerFrame(None)
    frame.Show()
    app.MainLoop()
