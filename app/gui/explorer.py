import wx
import os
from pathlib import Path
from typing import List

from artifactory import ArtifactoryPath

from app.core.config import CONFIG
from app.core.telemetry import log
from app.services import af as AF
from app.services import file_handler
from app.models.af_search_results import AF_Result, AF_Repo



class FileExplorer(wx.Frame):
    def __init__(self, af_conn : ArtifactoryPath):
        super().__init__(None, title=CONFIG.APP_NAME, size=(800, 600))
        icon = wx.Icon("Assets/LBS_AF_Logo.ico", wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)
        
        self.conn = af_conn
        self.current_dir : ArtifactoryPath = self.conn.get_repositories()[33].path
        self.current_dir = AF.open(
            self.conn, CONFIG.AF_URL# + "/ddc-dhfr-wip-prod-mel"
        )
        self.clipboard = []
        
        self.create_ui()
        self.file_list.SetDropTarget(FileDropTarget(self))
        self.items : List[AF_Result] = []
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
        self.file_list = wx.ListCtrl(panel, style=wx.LC_REPORT|wx.BORDER_SUNKEN|wx.LC_EDIT_LABELS)
        self.file_list.InsertColumn(0, "Name", width=400)
        self.file_list.InsertColumn(1, "Type", width=70)
        self.file_list.InsertColumn(2, "Size", width=70)
        self.file_list.InsertColumn(3, "Date Modified", width=100)
        self.file_list.InsertColumn(4, "Date Updated", width=100)
        self.file_list.InsertColumn(5, "Deployed By", width=135)
        self.file_list.InsertColumn(6, "Sha256", width=100)
        
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
        self.open_button.Bind(wx.EVT_BUTTON, self.on_open)
        self.copy_button.Bind(wx.EVT_BUTTON, self.on_copy)
        self.paste_button.Bind(wx.EVT_BUTTON, self.on_paste)
        self.delete_button.Bind(wx.EVT_BUTTON, self.on_delete)
        self.file_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated)
        self.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.on_start_rename)
        self.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.on_end_rename)

        # Key bindings
        self.file_list.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        
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
        try:
            curr_foldername = "/" + self.current_dir.repo + self.current_dir.path_in_repo
            self.dir_text.SetValue(curr_foldername)
            path_in_repo = self.current_dir.path_in_repo[1:] or "."
            items_dict = self.conn.aql(
                *AF.get_search_args(
                    repo_name = self.current_dir.repo,
                    foldername = path_in_repo
                )
            )
            self.items = [
                AF_Result(**item)
                for item in items_dict
                if not item["name"] == "."
            ]
            self.selecting_offset = -1
        except:
            repo_list = self.conn.get_repositories()
            self.dir_text.SetValue("/")
            self.items = [
                AF_Repo(
                    repo = repo.name,
                    path = repo.name,
                    name = repo.name
                )
                for repo in repo_list
            ]
            self.selecting_offset = 0
        pass
        self.items.sort(key=lambda f: f.type, reverse=True)
        # Add parent directory entry
        parent_dir = self.current_dir.parent
        if parent_dir.as_posix() != self.current_dir.as_posix():  # Not at root
            index = self.file_list.InsertItem(0, "..")
            self.file_list.SetItem(index, 1, "Parent Directory")
            self.file_list.SetItem(index, 2, "")
            self.file_list.SetItem(index, 3, "")
            self.file_list.SetItem(index, 4, "")
            self.file_list.SetItem(index, 5, "")
            self.file_list.SetItem(index, 6, "")
        # Add files and directories
        try:
            for i, item in enumerate(self.items):
                # Item 0 - Name
                index = self.file_list.InsertItem(i + 1, item.name)
                if item.sha256 == None:
                    self.file_list.SetItem(index, 1, "Directory")
                else:
                    self.file_list.SetItem(index, 1, "File")
                size = item.size
                self.file_list.SetItem(index, 2, self.format_size(size))
                self.file_list.SetItem(index, 3, item.modified)
                self.file_list.SetItem(index, 4, item.updated)
                self.file_list.SetItem(index, 5, item.modified_by or item.created_by or "")
                self.file_list.SetItem(index, 6, item.sha256 or "")
        except Exception as e:
            wx.MessageBox(f"Error reading directory: {str(e)}", "Error", wx.OK|wx.ICON_ERROR)
        pass
    
    def format_size(self, size):
        """Format file size in human-readable format"""
        if size == 0:
            return ""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def get_selected_paths(self) -> List[AF_Result]:
        """Get the full paths of all selected items"""
        selected_paths = []
        index = self.file_list.GetFirstSelected()
        
        while index != -1:
            item_text = self.file_list.GetItemText(index)
            if item_text == "..":
                selected_paths.append("..")
            else:
                # selected_paths.append(os.path.join(self.current_dir, item_text))
                selected_paths.append(
                    self.items[index + self.selecting_offset]
                )
            index = self.file_list.GetNextSelected(index)
        
        return selected_paths if selected_paths else None
    
    def on_up(self, event):
        """Navigate to parent directory"""
        # parent_dir = os.path.dirname(self.current_dir)
        parent_dir = self.current_dir.parent
        if parent_dir != self.current_dir:  # Not at root
            self.current_dir = parent_dir
            self.load_directory()
    
    def _download_file(self, file_conn : ArtifactoryPath, open = False) -> Path:
        # Make a temp folder if necessary
        tmp_path = CONFIG.STORE_TEMPFILES_PATH
        tmp_path.mkdir(parents=True, exist_ok=True)
        fname = file_conn.name
        tmp_file_path = tmp_path / fname
        with tmp_file_path.open(mode="wb") as f:
            file_conn.writeto(f, chunk_size=256)
        if open:
            os.startfile(tmp_file_path.as_posix())
        return tmp_file_path

    def on_open(self, event):
        """Open selected file or directory (only works with single selection)"""
        paths = self.get_selected_paths()
        if not paths or len(paths) > 1:
            wx.MessageBox("Please select a single file or directory to open.", "Info", wx.OK|wx.ICON_INFORMATION)
            return
        
        path = paths[0]
        if path == "..":
            self.on_up(None)
        elif path.type == "folder":
            # Go back a directory
            if path.name == ".":
                new_dir = self.current_dir.parent
            # Open the new directory
            else:
                new_path =  self.current_dir.as_posix() + "/" + path.name
                new_dir = AF.open(self.conn, new_path)
            self.current_dir = new_dir
            self.load_directory()
        else:
            file_path_str =  self.current_dir.as_posix() + "/" + path.name
            af_file = AF.open(self.conn, file_path_str)
            self._download_file(af_file, open = True)
            log("File downloaded for preview")
            return
    
    def on_item_activated(self, event):
        """Handle double-click on item"""
        self.on_open(event)
    
    def on_copy(self, event, show_feedback = True):
        """Copy selected files to clipboard"""
        af_paths = self.get_selected_paths()
        if not af_paths:
            wx.MessageBox("Please select one or more files/directories first.", "Info", wx.OK|wx.ICON_INFORMATION)
            return
        local_paths = [self._download_file(self.current_dir / path.name) for path in af_paths]
        self.clipboard = local_paths
        local_path_strings = ", ".join([f"'{f.as_posix()}'" for f in local_paths])
        file_names = ", ".join([f.name for f in local_paths])
        no_files_copied = len(local_paths)
        command = f"powershell Set-Clipboard -LiteralPath {local_path_strings}"
        os.system(command)
        if show_feedback:
            wx.MessageBox(f"Copied {no_files_copied} items: {file_names}", "Info", wx.OK|wx.ICON_INFORMATION)
        log(f"Files copied to clipboard - {no_files_copied}")
    
    def on_paste(self, event):
        """Paste files from clipboard to current directory"""
        files = file_handler.get_clipboard_file_paths()
        if not files:
            wx.MessageBox("No files in clipboard to paste.", "Info", wx.OK|wx.ICON_INFORMATION)
            return
        errors = file_handler.upload_formatted_files(
            files,
            self.current_dir
        )
        log(f"Files uploaded - {len(files)}")
        self.load_directory()
        if errors:
            wx.MessageBox(
                "Errors occurred while copying:\n" + "\n".join(errors),
                "Error",
                wx.OK|wx.ICON_ERROR
            )
    
    def on_delete(self, event):
        """Delete selected files"""
        paths = self.get_selected_paths()
        # Filter out parent directory if selected
        paths = [p for p in paths if isinstance(p, AF_Result)]
        if not paths:
            wx.MessageBox("Please select one or more files/directories first.", "Info", wx.OK|wx.ICON_INFORMATION)
            return
        
        names = ", ".join([p.name for p in paths])
        confirm = wx.MessageBox(f"Are you sure you want to delete {len(paths)} items?\n{names}", 
                              "Confirm Delete", wx.YES_NO|wx.ICON_QUESTION)
        if confirm == wx.YES:
            errors = []
            for path in paths:
                try:
                    file_to_delete = AF.open(self.conn, self.current_dir.as_posix() + "/" + path.name)
                    file_to_delete.unlink()
                except Exception as e:
                    errors.append(f"{os.path.basename(path)}: {str(e)}")
            
            if errors:
                wx.MessageBox("Errors occurred while deleting:\n" + "\n".join(errors), 
                            "Error", wx.OK|wx.ICON_ERROR)
            self.load_directory()
            log(f"Deleted files - {len(paths)}")

    def on_start_rename(self, event):
        if event.GetIndex() == 0:
            event.Veto()
        else:
            event.Skip()

    def on_end_rename(self, event):
        index = event.GetIndex()
        old_path = self.items[index - 1]
        old_name = old_path.name
        old_af = self.current_dir / old_name
        new_label = event.GetText()
        new_af = self.current_dir / new_label
        if new_label == old_name:
            return
        if new_label:
            old_af.move(new_af)
            log("File renamed")
            self.load_directory()
        else:
            event.Veto() 

    def on_key_down(self, event):
        key_code = event.GetKeyCode()
        control_down = event.ControlDown()
        alt_down = event.AltDown()
        if key_code == wx.WXK_DELETE:
            self.on_delete(None)
        elif key_code == wx.WXK_F2:
            index = self.file_list.GetFirstSelected()
            if index > 0:
                self.file_list.EditLabel(index)
        elif control_down and key_code == ord("C"):
            self.on_copy(None, False)
        elif control_down and key_code == ord("V"):
            self.on_paste(None)
        elif alt_down and wx.WXK_LEFT:
            self.on_up(None)
        else:
            event.Skip()  # Allow other key events to be processed

class FileDropTarget(wx.FileDropTarget):
    """Handles both drag-in and drag-out operations"""
    def __init__(self, window):
        super().__init__()
        self.window = window
    
    def OnDropFiles(self, x, y, filenames):
        """Handle files dropped into the window"""
        errors = file_handler.upload_formatted_files(
            [Path(f) for f in filenames], self.window.current_dir
        )
        if errors:
            wx.MessageBox("Errors occurred while copying:\n" + "\n".join(errors), 
                        "Error", wx.OK|wx.ICON_ERROR)
        self.window.load_directory()
        log(f"Files uploaded - {len(filenames)}")
        return True

