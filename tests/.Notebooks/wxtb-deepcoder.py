import wx
import os
import shutil
from urllib.parse import urlparse
import win32api  # For opening files with default OS handler (works on Windows)

class FileBrowser(wx.Frame):
    def __init__(self, title):
        super().__init__(None, title=title, size=(800, 600))

        # Create panels
        self.splitter = wx.SplitterWindow(self)
        left_panel = wx.Panel(self.splitter)
        right_panel = wx.Panel(self.splitter)

        # File list
        self.file_list = wx.ListBox(left_panel, style=wx.LB_EXTENDED)
        files = [f for f in os.listdir('.') if os.path.isfile(f)]
        self.file_list.InsertItems(files, 0)

        # Status bar
        self.status_bar = self.CreateStatusBar()
        self.status_bar.SetStatusText("Ready")

        # Buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        copy_button = wx.Button(left_panel, label="Copy")
        paste_button = wx.Button(left_panel, label="Paste")
        open_button = wx.Button(left_panel, label="Open Selected File")

        # Bind events
        self.Bind(wx.EVT_LISTBOX_DCLICK, self.OpenFile, self.file_list)
        copy_button.Bind(wx.EVT_BUTTON, self.Copy)
        paste_button.Bind(wx.EVT_BUTTON, self.Paste)
        open_button.Bind(wx.EVT_BUTTON, self.OpenFile)

        # Layout
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        left_sizer.Add(self.file_list, 1, wx.EXPAND | wx.ALL, 5)
        left_sizer.Add(copy_button, 0, wx.ALL, 5)
        left_sizer.Add(paste_button, 0, wx.ALL, 5)
        left_sizer.Add(open_button, 0, wx.ALL, 5)

        right_sizer = wx.BoxSizer(wx.VERTICAL)
        self.right_text = wx.TextCtrl(right_panel, style=wx.TE_READONLY)
        right_sizer.Add(self.right_text, 1, wx.EXPAND | wx.ALL, 5)

        left_panel.SetSizer(left_sizer)
        right_panel.SetSizer(right_sizer)
        self.splitter.SplitVertically(left_panel, right_panel)  # Split the window into two panels

        # Drag and drop
        # self.file_list.Bind(wx.EVT_DROPFiles, self.OnDropFiles)

    def OnDropFiles(self, event):
        files = event.GetFiles()
        for file in files:
            if os.path.isfile(file):
                self.file_list.Append(os.path.basename(file))
        self.status_bar.SetStatusText(f"Added {len(files)} files")

    def Copy(self, event):
        selected_indices = self.file_list.GetSelections()
        if not selected_indices:
            wx.MessageBox("Please select at least one file to copy.", "Error")
            return
        copied_files = [self.file_list.GetString(i) for i in selected_indices]
        clipboard = wx.Clipboard()
        clipboard.SetData(wx.DataObjectText('\n'.join(copied_files)))
        self.status_bar.SetStatusText("Files copied to clipboard")

    def Paste(self, event):
        clipboard = wx.Clipboard()
        data = clipboard.GetData(wx.DataFormat(wx.DF_TEXT))
        if data:
            files_pasted = data.GetText().split('\n')
            for file in files_pasted:
                if file.strip() and os.path.isfile(file):
                    self.file_list.Append(os.path.basename(file))
            self.status_bar.SetStatusText(f"Pasted {len(files_pasted)} files")
        else:
            wx.MessageBox("No valid files found in clipboard.", "Error")

    def OpenFile(self, event):
        selected = self.file_list.GetSelection()
        if selected == -1:
            wx.MessageBox("Please select a file to open.", "Error")
            return
        filename = os.path.join(os.getcwd(), self.file_list.GetString(selected))
        try:
            # On Windows, use win32api to open the file with default handler
            # For other OS, you might need a different approach
            win32api.ShellExecute(0, 'open', filename, '', '', 1)
        except Exception as e:
            wx.MessageBox(f"Error opening file: {e}", "Error")

    def Close(self, event):
        self.Destroy()

if __name__ == "__main__":
    app = wx.App()
    frame = FileBrowser("File Browser")
    frame.Show()
    app.MainLoop()