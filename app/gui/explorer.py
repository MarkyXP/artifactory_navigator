import wx
import os
import shutil
import sys
import tempfile
import time

from artifactory import ArtifactoryPath

from app.core.config import CONFIG
from app.services import af as AF



class FileExplorer(wx.Frame):
    def __init__(self, af_conn : ArtifactoryPath):
        super().__init__(None, title=CONFIG.APP_NAME, size=(800, 600))
        
        self.conn = af_conn
        self.current_dir : ArtifactoryPath = self.conn.get_repositories()[33].path
        self.clipboard = []
        
        self.create_ui()
        self.file_list.SetDropTarget(FileDropTarget(self))
        self.load_directory()
    
    def create_ui(self):
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)
        
        # Path controls
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        self.dir_label = wx.StaticText(panel, label="Current Directory:")
        self.dir_text = wx.TextCtrl(panel, style=wx.TE_READONLY)
        hbox1.Add(self.dir_label, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        hbox1.Add(self.dir_text, 1, wx.EXPAND|wx.ALL, 5)
        vbox.Add(hbox1, 0, wx.EXPAND)
        
        # File list with drag source support
        self.file_list = wx.ListCtrl(panel, style=wx.LC_REPORT|wx.BORDER_SUNKEN)
        self.file_list.InsertColumn(0, "Name", width=200)
        self.file_list.InsertColumn(1, "Type", width=100)
        self.file_list.InsertColumn(2, "Size", width=100)
        
        # Make the list a drag source
        self.file_list.Bind(wx.EVT_LIST_BEGIN_DRAG, self.on_begin_drag)
        vbox.Add(self.file_list, 1, wx.EXPAND|wx.ALL, 5)
        
        # Buttons
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        self.up_button = wx.Button(panel, label="Up")
        self.open_button = wx.Button(panel, label="Open")
        self.copy_button = wx.Button(panel, label="Copy")
        self.paste_button = wx.Button(panel, label="Paste")
        self.delete_button = wx.Button(panel, label="Delete")
        
        hbox2.Add(self.up_button, 0, wx.ALL, 5)
        hbox2.Add(self.open_button, 0, wx.ALL, 5)
        hbox2.Add(self.copy_button, 0, wx.ALL, 5)
        hbox2.Add(self.paste_button, 0, wx.ALL, 5)
        hbox2.Add(self.delete_button, 0, wx.ALL, 5)
        vbox.Add(hbox2, 0, wx.ALIGN_CENTER)
        
        # Event bindings
        self.up_button.Bind(wx.EVT_BUTTON, self.on_up)
        self.open_button.Bind(wx.EVT_BUTTON, self.on_open)
        self.copy_button.Bind(wx.EVT_BUTTON, self.on_copy)
        self.paste_button.Bind(wx.EVT_BUTTON, self.on_paste)
        self.delete_button.Bind(wx.EVT_BUTTON, self.on_delete)
        self.file_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated)
        
        panel.SetSizer(vbox)
    
    def on_begin_drag(self, event):
        """Handle drag initiation from the file list"""
        paths = self.get_selected_paths()
        if not paths:
            return
        
        # Create a file drop source
        data_object = wx.FileDataObject()
        for path in paths:
            data_object.AddFile(path)
        
        drop_source = wx.DropSource(self.file_list)
        drop_source.SetData(data_object)
        
        # Start the drag operation
        result = drop_source.DoDragDrop(wx.Drag_AllowMove)
        
        # You could handle different results here if needed
        if result == wx.DragCopy:
            print("Files were copied")
        elif result == wx.DragMove:
            print("Files were moved")
    
    def load_directory(self):
        """Load the contents of the current directory into the list"""
        self.file_list.DeleteAllItems()
        self.dir_text.SetValue(self.current_dir.name)
        
        # Add parent directory entry
        # parent_dir = os.path.dirname(self.current_dir)
        # if parent_dir != self.current_dir:  # Not at root
        #     index = self.file_list.InsertItem(0, "..")
        #     self.file_list.SetItem(index, 1, "Parent Directory")
        #     self.file_list.SetItem(index, 2, "")
        
        # Add files and directories
        try:
            # items = self.current_dir
            # items.sort(key=lambda x: (not os.path.isdir(os.path.join(self.current_dir, x)), x.lower()))
            
            for i, item in enumerate(self.current_dir.iterdir()):
                # full_path = os.path.join(self.current_dir, item)
                full_path = item.as_posix()
                index = self.file_list.InsertItem(i + 1, item.name)
                
                if item.is_dir():
                    self.file_list.SetItem(index, 1, "Directory")
                    self.file_list.SetItem(index, 2, "")
                else:
                    self.file_list.SetItem(index, 1, "File")
                    size = item.stat().size
                    self.file_list.SetItem(index, 2, self.format_size(size))
        except Exception as e:
            wx.MessageBox(f"Error reading directory: {str(e)}", "Error", wx.OK|wx.ICON_ERROR)
        pass
    
    def format_size(self, size):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def get_selected_paths(self):
        """Get the full paths of all selected items"""
        selected_paths = []
        index = self.file_list.GetFirstSelected()
        
        while index != -1:
            item_text = self.file_list.GetItemText(index)
            if item_text == "..":
                selected_paths.append(os.path.dirname(self.current_dir))
            else:
                selected_paths.append(os.path.join(self.current_dir, item_text))
            index = self.file_list.GetNextSelected(index)
        
        return selected_paths if selected_paths else None
    
    def on_up(self, event):
        """Navigate to parent directory"""
        parent_dir = os.path.dirname(self.current_dir)
        if parent_dir != self.current_dir:  # Not at root
            self.current_dir = parent_dir
            self.load_directory()
    
    def on_open(self, event):
        """Open selected file or directory (only works with single selection)"""
        paths = self.get_selected_paths()
        if not paths or len(paths) > 1:
            wx.MessageBox("Please select a single file or directory to open.", "Info", wx.OK|wx.ICON_INFORMATION)
            return
        
        path = paths[0]
        if os.path.isdir(path):
            self.current_dir = path
            self.load_directory()
        else:
            try:
                os.startfile(path)  # Works on Windows
            except:
                try:
                    # Try other platforms
                    import subprocess
                    if sys.platform == 'darwin':
                        subprocess.call(('open', path))
                    else:
                        subprocess.call(('xdg-open', path))
                except:
                    wx.MessageBox(f"Could not open file: {path}", "Error", wx.OK|wx.ICON_ERROR)
    
    def on_item_activated(self, event):
        """Handle double-click on item"""
        self.on_open(event)
    
    def on_copy(self, event):
        """Copy selected files to clipboard"""
        import os
        paths = self.get_selected_paths()
        if not paths:
            wx.MessageBox("Please select one or more files/directories first.", "Info", wx.OK|wx.ICON_INFORMATION)
            return
        
        self.clipboard = paths
        names = ", ".join([os.path.basename(p) for p in paths])
        command = f"powershell Set-Clipboard -LiteralPath {names}"
        os.system(command)
        wx.MessageBox(f"Copied {len(paths)} items: {names}", "Info", wx.OK|wx.ICON_INFORMATION)
    
    def on_paste(self, event):
        """Paste files from clipboard to current directory"""
        if not self.clipboard:
            wx.MessageBox("No files in clipboard to paste.", "Info", wx.OK|wx.ICON_INFORMATION)
            return
        
        try:
            for src in self.clipboard:
                dest = os.path.join(self.current_dir, os.path.basename(src))
                if os.path.isdir(src):
                    shutil.copytree(src, dest)
                else:
                    shutil.copy2(src, dest)
            self.load_directory()
        except Exception as e:
            wx.MessageBox(f"Error pasting files: {str(e)}", "Error", wx.OK|wx.ICON_ERROR)
    
    def on_delete(self, event):
        """Delete selected files"""
        paths = self.get_selected_paths()
        if not paths:
            wx.MessageBox("Please select one or more files/directories first.", "Info", wx.OK|wx.ICON_INFORMATION)
            return
        
        # Filter out parent directory if selected
        paths = [p for p in paths if not p.endswith("..")]
        if not paths:
            return
        
        names = ", ".join([os.path.basename(p) for p in paths])
        confirm = wx.MessageBox(f"Are you sure you want to delete {len(paths)} items?\n{names}", 
                              "Confirm Delete", wx.YES_NO|wx.ICON_QUESTION)
        if confirm == wx.YES:
            errors = []
            for path in paths:
                try:
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                except Exception as e:
                    errors.append(f"{os.path.basename(path)}: {str(e)}")
            
            if errors:
                wx.MessageBox("Errors occurred while deleting:\n" + "\n".join(errors), 
                            "Error", wx.OK|wx.ICON_ERROR)
            self.load_directory()

class FileDropTarget(wx.FileDropTarget):
    """Handles both drag-in and drag-out operations"""
    def __init__(self, window):
        super().__init__()
        self.window = window
    
    def OnDropFiles(self, x, y, filenames):
        """Handle files dropped into the window"""
        errors = []
        for filepath in filenames:
            try:
                dest = os.path.join(self.window.current_dir, os.path.basename(filepath))
                if os.path.isdir(filepath):
                    shutil.copytree(filepath, dest)
                else:
                    shutil.copy2(filepath, dest)
            except Exception as e:
                errors.append(f"{os.path.basename(filepath)}: {str(e)}")
        
        if errors:
            wx.MessageBox("Errors occurred while copying:\n" + "\n".join(errors), 
                        "Error", wx.OK|wx.ICON_ERROR)
        
        self.window.load_directory()
        return True

