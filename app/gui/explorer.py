import wx
import os
from pathlib import Path
from typing import List

from artifactory import ArtifactoryPath

from app.core.config import CONFIG
from app.core.telemetry import log
from app.services import af as AF
from app.services import file_handler
from app.services import explorer as EXPLORER
from app.models.af_search_results import AF_Result, AF_Repo



class FileExplorer(wx.Frame):
    def __init__(self, af_conn : ArtifactoryPath):
        super().__init__(None, title=CONFIG.APP_NAME, size=(800, 600))
        icon = wx.Icon(CONFIG.ICON_LOCATION, wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)
        
        self.conn = af_conn
        # self.current_dir : ArtifactoryPath = self.conn.get_repositories()[33].path
        self.current_dir = AF.open(
            self.conn, CONFIG.AF_URL
        )
        self.clipboard = []
        
        self.create_ui()
        self.file_list.SetDropTarget(FileDropTarget(self))
        self.items : List[AF_Result] = []
        self.load_directory()
    
    def _create_nav_button(self, panel : wx.Panel, icon_name : str, tooltip : str):
        button_size = wx.Size(23,23)
        icon_bmp = wx.Bitmap(
            f"Assets/Icons/{icon_name}_Dark.png",
            wx.BITMAP_TYPE_ANY
        )
        button = wx.Button(panel, size=button_size)
        button.SetBitmapLabel(icon_bmp)
        button.SetToolTip(tooltip)
        return button

    
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
        
        # Navigation Buttons
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        self.back_button = self._create_nav_button(panel, "Back", "Back a directory")
        self.forward_button = self._create_nav_button(panel, "Forward", "Forward a directory")
        self.up_button = self._create_nav_button(panel, "Up", "Go up a directory")
        self.new_folder_button = self._create_nav_button(panel, "New_Folder", "New Folder")
        self.search_button = self._create_nav_button(panel, "Search", "Find File")
        self.goto_button = self._create_nav_button(panel, "Goto", "Open CR/XECO Folder")
        self.copy_button = self._create_nav_button(panel, "Copy", "Copy Files")
        self.download_button = self._create_nav_button(panel, "Download", "Download Files")
        self.paste_button = self._create_nav_button(panel, "Paste", "Paste Files from Clipboard")
        self.upload_button = self._create_nav_button(panel, "Upload", "Upload files")
        self.open_button = self._create_nav_button(panel, "Open", "Open files")
        self.delete_button = self._create_nav_button(panel, "Delete", "Delete files")
        self.docusign_button = self._create_nav_button(panel, "DocuSign", "Transfer to DocuSign")
        self.revision_button = self._create_nav_button(panel, "ReVision", "Compare CR to ReVision")
        btns = [
            self.back_button,
            self.forward_button,
            self.up_button,
            self.new_folder_button,
            self.search_button,
            self.goto_button,
            self.copy_button,
            self.download_button,
            self.paste_button,
            self.upload_button,
            self.open_button,
            self.delete_button,
            self.docusign_button,
            self.revision_button
        ]
        for btn in btns:
            hbox2.Add(btn, 0, wx.ALL, 1)
        vbox.Add(hbox2, 0, wx.ALIGN_CENTER)
        # Event bindings
        self.up_button.Bind(wx.EVT_BUTTON, self.on_up)
        self.new_folder_button.Bind(wx.EVT_BUTTON, self.start_make_folder)
        self.search_button.Bind(wx.EVT_BUTTON, self.start_search)
        # self.goto_button.Bind(wx.EVT_BUTTON, pass)
        self.copy_button.Bind(wx.EVT_BUTTON, self.on_copy)
        self.paste_button.Bind(wx.EVT_BUTTON, self.on_paste)
        self.open_button.Bind(wx.EVT_BUTTON, self.on_open)
        self.delete_button.Bind(wx.EVT_BUTTON, self.on_delete)
        
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
                
        # Search panel (initially hidden)
        self.search_panel = wx.CollapsiblePane(panel, label="Search")
        self.search_panel.Bind(wx.EVT_COLLAPSIBLEPANE_CHANGED, self.on_search_pane_change)
        search_pane = self.search_panel.GetPane()
        search_sizer = wx.BoxSizer(wx.VERTICAL)
        self.search_input = wx.TextCtrl(search_pane)
        self.search_results = wx.ListCtrl(search_pane, style=wx.LC_REPORT|wx.BORDER_SUNKEN)
        self.search_results.InsertColumn(0, "Location", width=400)
        self.search_results.InsertColumn(1, "Name", width=400)
        self.search_results.InsertColumn(2, "Size", width=70)
        self.search_results.InsertColumn(3, "Date Modified", width=100)
        self.search_results.InsertColumn(4, "Date Updated", width=100)
        self.search_results.InsertColumn(5, "Deployed By", width=135)
        self.search_results.InsertColumn(6, "Sha256", width=100)
        search_sizer.Add(self.search_input, 0, wx.EXPAND|wx.ALL, 5)
        search_sizer.Add(self.search_results, 1, wx.EXPAND|wx.ALL, 5)
        search_pane.SetSizer(search_sizer)
        vbox.Add(self.search_panel, 0, wx.EXPAND)
        
        # Event bindings
        self.file_list.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        self.file_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated)
        self.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.on_start_rename)
        self.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.on_end_rename)

        # Key bindings
        panel.SetFocus()
        self.file_list.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        
        panel.SetSizer(vbox)
        self.search_panel.Collapse(True)  # Initially collapse the search pane

    def load_directory(self, files_to_highlight : List[str] = ()):
        """Load the contents of the current directory into the list
        
        Arguments:
            file_to_highlight : List[str]
                List of SHA #s of the files to highlight.

        """
        self.file_list.DeleteAllItems()
        try:
            curr_foldername = "/" + self.current_dir.repo + self.current_dir.path_in_repo
            self.dir_text.SetValue(curr_foldername)
            path_in_repo = self.current_dir.path_in_repo[1:] or "."
            items_dict = self.conn.aql(
                *AF.get_folder_contents_aql(
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
        indexes_to_highlight = []
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
                if item.sha256 in files_to_highlight:
                    indexes_to_highlight.append(index)
        except Exception as e:
            wx.MessageBox(f"Error reading directory: {str(e)}", "Error", wx.OK|wx.ICON_ERROR)
        # Highlight the files
        for i in indexes_to_highlight:
            self.file_list.Select(i)
            self.file_list.Focus(i)
            self.file_list.EnsureVisible(i)
        pass
    
    def on_context_menu(self, event):
        menu = wx.Menu()
        copy_as_path_item = menu.Append(wx.ID_ANY, "Copy as Path")
        copy_item = menu.Append(wx.ID_ANY, "Copy")
        copy_sha_item = menu.Append(wx.ID_ANY, "Copy SHA")
        copy_as_table_item = menu.Append(wx.ID_ANY, "Copy as Table")
        download_item = menu.Append(wx.ID_ANY, "Download")
        delete_item = menu.Append(wx.ID_ANY, "Delete")
        compare_to_revision_item = menu.Append(wx.ID_ANY, "Check against ReVision")
        
        # Event bindings
        self.Bind(wx.EVT_MENU, self.on_copy_as_path, copy_as_path_item)
        self.Bind(wx.EVT_MENU, self.on_copy_sha, copy_sha_item)
        self.Bind(wx.EVT_MENU, self.on_copy, copy_item)
        self.Bind(wx.EVT_MENU, self.on_save_to_file, download_item)
        self.Bind(wx.EVT_MENU, self.on_copy_as_table, copy_as_table_item)
        self.Bind(wx.EVT_MENU, self.on_delete, delete_item)
        self.Bind(wx.EVT_MENU, self.on_compare_to_revision_item, compare_to_revision_item)
        
        af_paths = self.get_selected_paths()
        af_paths = [f for f in af_paths if not f.name == ".."]
        if not af_paths:
            return # Nothing selected, do nothing
        if all(f.type == "folder" for f in af_paths):
            copy_item.Enabled(False)
            copy_sha_item.Enabled(False)
            download_item.Enabled(False)
        self.PopupMenu(menu)
    
    def on_copy_as_path(self, event : wx.CommandEvent):
        af_paths = self.get_selected_paths()
        shas = [str(self.current_dir / f.name) for f in af_paths]
        clipboard_str = ", ".join(shas)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(clipboard_str))
            wx.TheClipboard.Close()

    def on_copy_sha(self, event : wx.CommandEvent):
        af_paths = self.get_selected_paths()
        af_paths = [f for f in af_paths if f.type == "file"]
        shas = [f.sha256 for f in af_paths]
        clipboard_str = "\n".join(shas)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(clipboard_str))
            wx.TheClipboard.Close()
    
    def on_copy_as_table(self, event : wx.CommandEvent):
        af_paths = self.get_selected_paths()
        rows = ["Name", "Modified By", "SHA256"]
        rows += [
            f"{item.name}\t{item.modified_by}\t{item.sha256}"
            for item in af_paths
        ]
        clipboard_str = "\n".join(rows)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(clipboard_str))
            wx.TheClipboard.Close()
    
    def on_save_to_file(self, event):
        # Create the dialog
        dialog = wx.DirDialog(
            self,  # parent window
            "Select a folder:",  # message
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST
        )
        # Show the dialog and check if user clicked OK
        if dialog.ShowModal() == wx.ID_OK:
            selected_folder = Path(dialog.GetPath())
            af_paths = self.get_selected_paths()
            af_paths = [f for f in af_paths if f.type == "file"]
            for path in af_paths:
                file_path_str = self.current_dir.as_posix() + "/" + path.name
                af_file = AF.open(self.conn, file_path_str)
                self._download_file(
                    file_conn = af_file,
                    open = len(af_paths) == 1,
                    output_path = selected_folder
                )
        # Destroy the dialog when done
        dialog.Destroy()

    def on_begin_drag(self, event):
        """Handle drag initiation from the file list"""
        paths = self.get_selected_paths()
        if not paths:
            return
        
        # Create a file drop source
        data_object = wx.FileDataObject()
        af_paths = [
            self.current_dir / str(path.name)
            for path in paths
        ]
        for path in af_paths:
            file_path_str = path.as_posix()
            data_object.AddFile(
                str(self._download_file(
                    file_conn = AF.open(self.conn, file_path_str),
                    open = False
                ))
            )
        
        drop_source = wx.DropSource(self.file_list)
        drop_source.SetData(data_object)
        
        # Start the drag operation
        result = drop_source.DoDragDrop(wx.Drag_AllowMove)
        
        # You could handle different results here if needed
        if result == wx.DragCopy:
            pass
        elif result == wx.DragMove:
            # I should delete the files...
            for path in af_paths:
                path.unlink(missing_ok = True)
            self.load_directory()
    
    def on_up(self, event):
        """Navigate to parent directory"""
        # parent_dir = os.path.dirname(self.current_dir)
        parent_dir = self.current_dir.parent
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
    
    def on_delete(self, event, show_confirmation = True):
        """Delete selected files"""
        paths = self.get_selected_paths()
        # Filter out parent directory if selected
        paths = [p for p in paths if isinstance(p, AF_Result)]
        if not paths:
            if show_confirmation:
                wx.MessageBox("Please select one or more files/directories first.", "Info", wx.OK|wx.ICON_INFORMATION)
            return
        
        names = ", ".join([p.name for p in paths])
        if show_confirmation:
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
            
            if errors and show_confirmation:
                wx.MessageBox("Errors occurred while deleting:\n" + "\n".join(errors), 
                            "Error", wx.OK|wx.ICON_ERROR)
            self.load_directory()
            if show_confirmation:
                log(f"Deleted files - {len(paths)}")

    def on_compare_to_revision_item(self, event):
        first_item = self.file_list.GetItem(1,0).GetText()
        EXPLORER.compare_to_revision(
            self.current_dir
        )

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
        shift_down = event.ShiftDown()
        if key_code == wx.WXK_DELETE:
            self.on_delete(None)
        elif key_code == wx.WXK_F2:
            index = self.file_list.GetFirstSelected()
            if index > 0:
                self.file_list.EditLabel(index)
        elif control_down and (key_code == ord("C")):
            self.on_copy(None, False)
        elif control_down and (key_code == ord("V")):
            self.on_paste(None)
        elif alt_down and (key_code == wx.WXK_LEFT):
            self.on_up(None)
        elif control_down and shift_down and (key_code == ord("N")):
            self.start_make_folder()
        elif control_down and (key_code == ord("F")):
            # self.start_search()
            self.search_panel.Collapse(not self.search_panel.IsCollapsed())
        else:
            event.Skip()  # Allow other key events to be processed

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
        
        return selected_paths if selected_paths else []
    
    def _download_file(self, file_conn : ArtifactoryPath, open = False, output_path : Path | None = None) -> Path:
        # Make a temp folder if necessary
        if not output_path:
            output_path = CONFIG.STORE_TEMPFILES_PATH
            output_path.mkdir(parents=True, exist_ok=True)
        fname = file_conn.name
        tmp_file_path = output_path / fname
        with tmp_file_path.open(mode="wb") as f:
            file_conn.writeto(f, chunk_size=256)
        if open:
            os.startfile(tmp_file_path.as_posix())
        return tmp_file_path
    
    def start_make_folder(self, *_):
        dialog = wx.TextEntryDialog(self, "Enter a folder name:", "Folder Input")
        if dialog.ShowModal() == wx.ID_OK:
            folder_name = dialog.GetValue()
            new_folder = self.current_dir / folder_name
            file_handler.make_folder(new_folder)
            self.current_dir = new_folder
            self.load_directory()
    
    def start_search(self, *_):
        dialog = wx.TextEntryDialog(self, "Enter a SHA-256 Number:", "SHA-256")
        if dialog.ShowModal() == wx.ID_OK:
            search_term = dialog.GetValue().strip()
            items_dict = AF.find(self.conn, search_term)
            if not items_dict:
                wx.MessageBox("No results found", "Error", wx.OK|wx.ICON_ERROR)
                return
            #if len(items_dict) == 1:
            # Go to the folder
            item = items_dict[0]
            self.current_dir = item.parent
            shas_to_highlight = [item.stat().sha256]
            self.load_directory(shas_to_highlight)
    

    def on_search_pane_change(self, event):
        if not self.search_panel.IsCollapsed():
            self.search_input.SetFocus()

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

