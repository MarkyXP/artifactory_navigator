import os
import re
from collections import deque
from pathlib import Path
from typing import List

import wx
from artifactory import ArtifactoryPath

from app.core.config import CONFIG
from app.core import credentials, telemetry
from app.gui import explorer_elements as elements
from app.gui.go_to_cr import CRDialog
from app.gui.shipping_tool import ShippingToolDialog
from app.models.af_search_results import AF_Repo, AF_Result
from app.services import af as AF
from app.services import explorer as EXPLORER
from app.services import file_handler


class FileExplorer(wx.Frame):
    def __init__(self, af_conn: ArtifactoryPath, initial_repos: list[str] | None = None):
        title = f"{CONFIG.APP_NAME} | {CONFIG.VERSION}"
        super().__init__(None, title=title, size=(800, 600))
        icon = wx.Icon(CONFIG.APP_ICON_PATH, wx.BITMAP_TYPE_ICO)
        self.SetIcon(icon)

        self.conn = af_conn
        # Login already had to call the repositories endpoint to verify the
        # credentials, so reuse that response for the root view rather than
        # paying for the same round trip a second time.
        self._repos = list(initial_repos) if initial_repos else None
        self.current_dir = self._restore_last_dir()
        self.path_backward_stack = deque()
        self.path_forward_stack = deque()

        self.create_ui()
        self.file_list.SetDropTarget(FileDropTarget(self))
        self.items: List[AF_Result] = []
        self.load_directory()

    def _restore_last_dir(self) -> ArtifactoryPath:
        """
        Reopens the folder the user last browsed, falling back to the root if
        it can't be used.

        The stored folder can be gone by the time we come back - a colleague may
        have deleted or renamed it while the app was closed - so it is checked
        before being trusted rather than assumed.
        """
        root = AF.open(self.conn, CONFIG.AF_URL)
        last_dir = credentials.get_last_dir()
        if not last_dir:
            return root
        candidate = AF.open(self.conn, f"{CONFIG.AF_BASE_URL.rstrip('/')}/{last_dir}")
        try:
            if candidate.is_dir():
                return candidate
        except Exception:
            # Server unreachable, or the path is not readable by this user.
            pass
        return root

    def create_ui(self):
        # -------------------- splitter: Separate segments --------------------
        panel = wx.Panel(self)
        self.splitter = wx.SplitterWindow(panel, style=wx.SP_LIVE_UPDATE | wx.SP_3DSASH)
        # ------- upper pane: path & navigation bar, main file explorer -------
        nav_panel = wx.Panel(self.splitter)
        nav_sizer = wx.BoxSizer(wx.VERTICAL)
        self.dir_label, self.dir_text = elements.make_path_bar(nav_panel, nav_sizer)
        self.buttons = elements.make_navbar(nav_panel, nav_sizer)
        self.file_list = elements.make_main_explorer(nav_panel, nav_sizer)
        nav_panel.SetSizer(nav_sizer)

        # --------------------- lower pane : search area ----------------------
        self.search_panel = wx.Panel(self.splitter)
        search_sizer = wx.BoxSizer(wx.VERTICAL)
        # collapsible search bar
        self.search_input, self.search_ignore_summary, self.search_results = (
            elements.make_search(self.search_panel, search_sizer)
        )
        # search text box inside the collapsible pane
        self.search_panel.SetSizer(search_sizer)

        # -------------------------- splitter set-up --------------------------
        self.splitter.SplitHorizontally(nav_panel, self.search_panel)
        self.search_panel.Show(False)  # Default to show the navigation panel
        self.splitter.SetSashGravity(1.0)  # Give all extra space to nav_panel

        # ------------------ Add the Splitter to the window -------------------
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.splitter, 1, wx.EXPAND | wx.ALL)
        panel.SetSizer(main_sizer)
        panel.Layout()

        # -------------------------- Event Bindings ---------------------------
        # Bindings - Navbar
        self.buttons.BACK.Bind(wx.EVT_BUTTON, self.on_back)
        self.buttons.FORWARD.Bind(wx.EVT_BUTTON, self.on_forward)
        self.buttons.UP.Bind(wx.EVT_BUTTON, self.on_up)
        self.buttons.NEW_FOLDER.Bind(wx.EVT_BUTTON, self.start_make_folder)
        self.buttons.SEARCH.Bind(wx.EVT_BUTTON, self.on_search_toggle)
        self.buttons.GOTO.Bind(wx.EVT_BUTTON, self.start_go_to)
        self.buttons.COPY.Bind(wx.EVT_BUTTON, self.on_copy)
        self.buttons.DOWNLOAD.Bind(wx.EVT_BUTTON, self.on_download)
        self.buttons.PASTE.Bind(wx.EVT_BUTTON, self.on_paste)
        self.buttons.UPLOAD.Bind(wx.EVT_BUTTON, self.on_upload)
        self.buttons.OPEN.Bind(wx.EVT_BUTTON, self.on_open)
        self.buttons.DELETE.Bind(wx.EVT_BUTTON, self.on_delete)
        self.buttons.REVISION.Bind(wx.EVT_BUTTON, self.on_compare_to_revision_item)
        self.buttons.SHIPPING_TOOL.Bind(wx.EVT_BUTTON, self.on_shipping_tool)
        # Bindings - Main File Explorer
        self.file_list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_selected)
        self.file_list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.on_selected)
        self.file_list.Bind(wx.EVT_LIST_BEGIN_DRAG, self.on_begin_drag)
        self.file_list.Bind(wx.EVT_CONTEXT_MENU, self.on_context_menu)
        self.file_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_item_activated)
        self.file_list.Bind(wx.EVT_LIST_COL_CLICK, self.on_column_sort)
        self.Bind(wx.EVT_LIST_BEGIN_LABEL_EDIT, self.on_start_rename)
        self.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.on_end_rename)
        self.file_list.Bind(wx.EVT_KEY_DOWN, self.on_key_down)
        # Bindings - Search
        self.search_input.Bind(wx.EVT_KEY_UP, self.on_search_key_down)
        self.search_ignore_summary.Bind(wx.EVT_CHECKBOX, self.on_search_key_down)
        self.search_results.Bind(
            wx.EVT_LIST_ITEM_ACTIVATED, self.on_search_item_activated
        )
        # Global keybindings
        accel_tbl = wx.AcceleratorTable(
            [
                (wx.ACCEL_CTRL, ord("F"), wx.ID_FIND),
                (wx.ACCEL_CTRL, ord("G"), wx.ID_JUMP_TO),
            ]
        )
        self.SetAcceleratorTable(accel_tbl)
        self.Bind(wx.EVT_MENU, self.on_search_toggle, id=wx.ID_FIND)
        self.Bind(wx.EVT_MENU, self.start_go_to, id=wx.ID_JUMP_TO)

        # Set the window to the foreground
        panel.SetFocus()

    def load_directory(
        self, files_to_highlight: List[str] = (), add_to_back_queue: bool = True
    ):
        """Load the contents of the current directory into the list

        Arguments:
            file_to_highlight : List[str]
                List of SHA #s of the files to highlight _OR_
                file names

        """
        try:
            curr_foldername = (
                "/" + self.current_dir.repo + self.current_dir.path_in_repo
            )
            self.dir_text.SetValue(curr_foldername)
            path_in_repo = self.current_dir.path_in_repo[1:] or "."
            self.items = AF.find_folder_contents(
                conn=self.conn, repo_name=self.current_dir.repo, folderpath=path_in_repo
            )
            self.selecting_offset = -1
        except Exception as e:
            # The root is detected by .repo raising IndexError (the root has no
            # repo), so this except is the root branch - but it is left catching
            # everything so that a folder which is temporarily unreachable still
            # degrades to the root listing instead of taking the app down.
            self.dir_text.SetValue("/")
            self.items = [
                AF_Repo(repo=name, path=name, name=name) for name in self._get_repo_list()
            ]
            self.selecting_offset = 0
        self.items.sort(key=lambda f: f.type, reverse=True)
        self.last_sorted_col = 0
        self.render_filelist(files_to_highlight)
        # Update the navbar
        self.update_navbar()
        # Add the back queue
        if add_to_back_queue:
            self.path_backward_stack.append(self.current_dir)
        # Remember where we are, so the next start reopens this folder
        self._save_last_dir()

    def _get_repo_list(self) -> list[str]:
        """
        Names of the repositories, reusing the list login already fetched.

        Falls back to asking Artifactory if there isn't one, which is the case
        when the app was started without going through login.
        """
        if self._repos is None:
            self._repos = [repo.name for repo in self.conn.get_repositories(lazy=True)]
        return self._repos

    def _save_last_dir(self) -> None:
        """
        Stores the open folder relative to the Artifactory base (e.g.
        "artifactory/myrepo/some/folder") so it can be reopened next time.

        The root isn't worth remembering - it is where the app starts anyway.
        path_in_repo deliberately excludes the repository, so it has to be put
        back in front of it here or the path would reopen one level too deep.
        Stored relative to the Artifactory base rather than as a full URL so a
        change of server doesn't leave a stale hostname behind.
        """
        try:
            repo = self.current_dir.repo
        except IndexError:
            return  # At the root
        # CONFIG.AF_URL is an absolute URL, so the bit to keep is what follows
        # the base.
        af_root = CONFIG.AF_URL.replace(CONFIG.AF_BASE_URL.rstrip("/"), "", 1).strip("/")
        try:
            credentials.set_last_dir(f"{af_root}/{repo}{self.current_dir.path_in_repo}")
        except Exception:
            # Remembering the last folder is a convenience, never a reason to
            # interrupt the user over a failed write.
            pass

    def render_filelist(self, files_to_highlight : list[str] = ()):
        # Clear the files
        self.file_list.DeleteAllItems()
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
                self.file_list.SetItem(
                    index, 5, item.modified_by or item.created_by or ""
                )
                self.file_list.SetItem(index, 6, item.sha256 or "")
                if item.sha256 in files_to_highlight or item.name in files_to_highlight:
                    indexes_to_highlight.append(index)
        except Exception as e:
            wx.MessageBox(
                f"Error reading directory: {str(e)}", "Error", wx.OK | wx.ICON_ERROR
            )
        # Highlight the files
        for i in indexes_to_highlight:
            self.file_list.Select(i)
            self.file_list.Focus(i)
            self.file_list.EnsureVisible(i)
        pass

    def on_context_menu(self, event):
        menu = wx.Menu()
        compare_to_revision_item = menu.Append(wx.ID_ANY, "Check against ReVision")
        copy_as_path_item = menu.Append(wx.ID_ANY, "Copy as Path")
        copy_sha_item = menu.Append(wx.ID_ANY, "Copy SHA")
        copy_as_table_item = menu.Append(wx.ID_ANY, "Copy as Table")
        copy_item = menu.Append(wx.ID_ANY, "Copy")
        download_item = menu.Append(wx.ID_ANY, "Download")
        menu.AppendSeparator()
        delete_item = menu.Append(wx.ID_ANY, "Delete")

        # Event bindings
        self.Bind(
            wx.EVT_MENU, self.on_compare_to_revision_item, compare_to_revision_item
        )
        self.Bind(wx.EVT_MENU, self.on_copy_as_path, copy_as_path_item)
        self.Bind(wx.EVT_MENU, self.on_copy_sha, copy_sha_item)
        self.Bind(wx.EVT_MENU, self.on_copy, copy_item)
        self.Bind(wx.EVT_MENU, self.on_save_to_file, download_item)
        self.Bind(wx.EVT_MENU, self.on_copy_as_table, copy_as_table_item)
        self.Bind(wx.EVT_MENU, self.on_delete, delete_item)

        af_paths = self.get_selected_paths()
        af_paths = [f for f in af_paths if not f.name == ".."]
        if not af_paths:
            return  # Nothing selected, do nothing
        if all(f.type == "folder" for f in af_paths):
            copy_item.Enabled(False)
            copy_sha_item.Enabled(False)
            download_item.Enabled(False)
        self.PopupMenu(menu)

    def on_copy_as_path(self, _: wx.CommandEvent):
        af_paths = self.get_selected_paths()
        str_paths = [
            str(self.current_dir / f.name).replace(CONFIG.AF_URL, CONFIG.AF_PRETTY_URL)
            for f in af_paths
        ]
        clipboard_str = "\n".join(str_paths)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(clipboard_str))
            wx.TheClipboard.Close()

    def on_copy_sha(self, _: wx.CommandEvent):
        af_paths = self.get_selected_paths()
        af_paths = [f for f in af_paths if f.type == "file"]
        shas = [f.sha256 for f in af_paths]
        clipboard_str = "\n".join(shas)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(clipboard_str))
            wx.TheClipboard.Close()

    def on_copy_as_table(self, _: wx.CommandEvent):
        af_paths = self.get_selected_paths()
        rows = ["File Name\tSize\tModified Date\tDate Updated\tModified By\tSHA256"]
        rows += [
            f"{item.name}\t{item.size}\t{item.modified}\t{item.updated}\t{item.modified_by}\t{item.sha256}"
            for item in af_paths
        ]
        clipboard_str = "\n".join(rows)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(clipboard_str))
            wx.TheClipboard.Close()

    def on_save_to_file(self, _):
        # Create the dialog
        dialog = wx.DirDialog(
            self,  # parent window
            "Select a folder:",  # message
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
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
                    file_conn=af_file,
                    open=len(af_paths) == 1,
                    output_path=selected_folder,
                )
        # Destroy the dialog when done
        dialog.Destroy()

    def on_begin_drag(self, _):
        """Handle drag initiation from the file list"""
        paths = self.get_selected_paths()
        if not paths:
            return

        # Create a file drop source
        data_object = wx.FileDataObject()
        af_paths = [self.current_dir / str(path.name) for path in paths]
        for path in af_paths:
            file_path_str = path.as_posix()
            data_object.AddFile(
                str(
                    self._download_file(
                        file_conn=AF.open(self.conn, file_path_str), open=False
                    )
                )
            )

        drop_source = wx.DropSource(self.file_list)
        drop_source.SetData(data_object)

        # Start the drag operation
        result = drop_source.DoDragDrop(wx.Drag_AllowMove)

        # You could handle different results here if needed
        if result == wx.DragCopy:
            pass
        elif result == wx.DragMove:
            # I should **NOT** delete the files...
            # for path in af_paths:
            #    path.unlink(missing_ok=True)
            # self.load_directory(paths)
            pass

    def on_up(self, event):
        """Navigate to parent directory"""
        parent_dir = self.current_dir.parent
        if parent_dir != self.current_dir:  # Not at root
            current_folder_name = self.current_dir.name
            self.current_dir = parent_dir
            self.load_directory([current_folder_name])

    def on_back(self, _):
        """Navigate back a directory"""
        while self.path_backward_stack:
            path = self.path_backward_stack.pop()
            if path != self.current_dir:
                # Go back a directory
                self.path_forward_stack.append(self.current_dir)
                self.current_dir = path
                return self.load_directory()
            # The back path is this path, skip it
            pass
        # We never found a path to go to, so don't do anything.

    def on_forward(self, _):
        """Navigate forward a directory"""
        while self.path_forward_stack:
            path = self.path_forward_stack.pop()
            if path != self.current_dir:
                # Go Forward a directory
                self.current_dir = path
                return self.load_directory()
            # The back path is this path, skip it
            pass
        # We never found a path to go to, so don't do anything.

    def on_open(self, event):
        """Open selected file or directory (only works with single selection)"""
        paths = self.get_selected_paths()
        if not paths or len(paths) > 1:
            wx.MessageBox(
                "Please select a single file or directory to open.",
                "Info",
                wx.OK | wx.ICON_INFORMATION,
            )
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
                new_path = self.current_dir.as_posix() + "/" + path.name
                new_dir = AF.open(self.conn, new_path)
            self.current_dir = new_dir
            self.load_directory()
        else:
            file_path_str = self.current_dir.as_posix() + "/" + path.name
            af_file = AF.open(self.conn, file_path_str)
            self._download_file(af_file, open=True)
            telemetry.log("File downloaded for preview")
            return

    def on_item_activated(self, event):
        """Handle double-click on item"""
        self.on_open(event)
    
    def on_column_sort(self, event):
        """Handle clicking on the column sort"""
        af_paths = self.get_selected_paths()
        column_index = event.Column # 0-based index of the column
        is_reversed = column_index == self.last_sorted_col
        match column_index:
            case 0: # Name column
                self.items.sort(key = lambda item: item.name, reverse = is_reversed)
            case 1: # Type column (file / dir)
                self.items.sort(key = lambda item: item.sha256 == None, reverse = is_reversed)
            case 2: # Size column
                self.items.sort(key = lambda item: item.size, reverse = is_reversed)
            case 3: # Date Modifed column
                self.items.sort(key = lambda item: item.modified, reverse = is_reversed)
            case 4: # Date Created column
                self.items.sort(key = lambda item: item.updated, reverse = is_reversed)
            case 5: # Deployed by column
                self.items.sort(key = lambda item: item.modified_by or item.created_by or "", reverse = is_reversed)
            case 6: # SHA column
                self.items.sort(key = lambda item: item.sha256, reverse = is_reversed)
        if is_reversed:
            self.last_sorted_col = -1
        else:
            self.last_sorted_col = column_index
        self.render_filelist(af_paths)

    def on_copy(self, event, show_feedback=True):
        """Copy selected files to clipboard"""
        af_paths = self.get_selected_paths()
        if not af_paths:
            wx.MessageBox(
                "Please select one or more files/directories first.",
                "Info",
                wx.OK | wx.ICON_INFORMATION,
            )
            return
        local_paths = [
            self._download_file(self.current_dir / path.name) for path in af_paths
        ]
        file_names = "\r\n".join([f"- {f.name}" for f in local_paths])
        no_files_copied = len(local_paths)
        file_handler.add_locations_to_clipboard(local_paths)
        if show_feedback:
            wx.MessageBox(
                f"Copied {no_files_copied} items:\n{file_names}",
                "Info",
                wx.OK | wx.ICON_INFORMATION,
            )
        telemetry.log(f"Files copied to clipboard - {no_files_copied}")

    def on_download(self, event):
        openDirDialog = wx.DirDialog(
            None,
            message="Choose file(s) to upload to Artifactory",
            style=wx.FLP_OPEN | wx.FLP_FILE_MUST_EXIST | wx.FD_MULTIPLE,
        )
        openDirDialog.ShowModal()
        if not openDirDialog.Paths:
            return
        output_path = Path(openDirDialog.Paths[0])
        openDirDialog.Destroy()
        files_to_download = self.get_selected_paths()
        local_paths = [
            self._download_file(
                file_conn=self.current_dir / path.name,
                open=False,
                output_path=output_path,
            )
            for path in files_to_download
        ]
        telemetry.log(f"Downloaded - {len(local_paths)}")
        wx.MessageBox(
            f"Copied {len(local_paths)} items:\n{
                '\r\n'.join([
                    f' - {item.name}' for item in local_paths
                ])
            }",
            "Info",
            wx.OK | wx.ICON_INFORMATION,
        )

    def on_paste(self, event):
        """Paste files from clipboard to current directory"""
        files = file_handler.get_clipboard_file_paths()
        if not files:
            wx.MessageBox(
                "No files in clipboard to paste.", "Info", wx.OK | wx.ICON_INFORMATION
            )
            return
        errors = file_handler.upload_formatted_files(files, self.current_dir)
        telemetry.log(f"Files uploaded - {len(files)}")
        self.load_directory()
        if errors:
            wx.MessageBox(
                "Errors occurred while copying:\n" + "\n".join(errors),
                "Error",
                wx.OK | wx.ICON_ERROR,
            )

    def on_upload(self, event):
        openFileDialog = wx.FileDialog(
            None,
            message="Choose file(s) to upload to Artifactory",
            wildcard="All files (*.*)|*.*",
            style=wx.FLP_OPEN | wx.FLP_FILE_MUST_EXIST | wx.FD_MULTIPLE,
        )
        openFileDialog.ShowModal()
        files = [Path(path) for path in openFileDialog.Paths]
        openFileDialog.Destroy()
        errors = file_handler.upload_formatted_files(files, self.current_dir)
        telemetry.log(f"Files uploaded - {len(files)}")
        self.load_directory()
        if errors:
            wx.MessageBox(
                "Errors occurred while uploading:\n" + "\n".join(errors),
                "Error",
                wx.OK | wx.ICON_ERROR,
            )

    def on_delete(self, event, show_confirmation=True):
        """Delete selected files"""
        paths = self.get_selected_paths()
        # Filter out parent directory if selected
        paths = [p for p in paths if isinstance(p, AF_Result)]
        if not paths:
            if show_confirmation:
                wx.MessageBox(
                    "Please select one or more files/directories first.",
                    "Info",
                    wx.OK | wx.ICON_INFORMATION,
                )
            return

        names = "\r\n".join([f"- {p.name}" for p in paths])
        if show_confirmation:
            confirm = wx.MessageBox(
                f"Are you sure you want to delete {len(paths)} items?\n{names}",
                "Confirm Delete",
                wx.YES_NO | wx.ICON_QUESTION,
            )
        if confirm == wx.YES:
            errors = []
            for path in paths:
                try:
                    file_to_delete = AF.open(
                        self.conn, self.current_dir.as_posix() + "/" + path.name
                    )
                    file_to_delete.unlink()
                except Exception as e:
                    errors.append(f"{os.path.basename(path)}: {str(e)}")

            if errors and show_confirmation:
                wx.MessageBox(
                    "Errors occurred while deleting:\n" + "\n".join(errors),
                    "Error",
                    wx.OK | wx.ICON_ERROR,
                )
            self.load_directory()
            if show_confirmation:
                telemetry.log(f"Deleted files - {len(paths)}")

    def on_compare_to_revision_item(self, event):
        # first_item = self.file_list.GetItem(1, 0).GetText()
        EXPLORER.compare_to_revision(self.current_dir)

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
            telemetry.log("File renamed")
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
            self.on_back(None)
        elif control_down and shift_down and (key_code == ord("N")):
            self.start_make_folder()
        else:
            event.Skip()  # Allow other key events to be processed

    def format_size(self, size):
        """Format file size in human-readable format"""
        if size == 0:
            return ""
        for unit in ["B", "KB", "MB", "GB"]:
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
                selected_paths.append(self.items[index + self.selecting_offset])
            index = self.file_list.GetNextSelected(index)

        return selected_paths if selected_paths else []

    def _download_file(
        self, file_conn: ArtifactoryPath, open=False, output_path: Path | None = None
    ) -> Path:
        # Make a temp folder if necessary
        if not output_path:
            output_path = CONFIG.STORE_TEMPFILES_PATH
        fname = file_conn.name
        tmp_file_path = output_path / fname
        try:
            with tmp_file_path.open(mode="wb") as f:
                file_conn.writeto(f, chunk_size=256)
        except PermissionError:
            # File has already been downloaded and is already open
            pass
        if open:
            os.startfile(tmp_file_path.as_posix())
        return tmp_file_path

    def start_make_folder(self, *_):
        if not self.buttons.NEW_FOLDER.Enabled:
            return
        dialog = wx.TextEntryDialog(self, "Enter a folder name:", "Folder Input")
        if dialog.ShowModal() == wx.ID_OK:
            folder_name = dialog.GetValue()
            new_folder = self.current_dir / folder_name
            AF.make_folder(new_folder)
            # self.current_dir = new_folder
            self.load_directory([folder_name])

    def start_search(self, *_):
        dialog = wx.TextEntryDialog(self, "Enter a SHA-256 Number:", "SHA-256")
        if dialog.ShowModal() == wx.ID_OK:
            search_term = dialog.GetValue().strip()
            items_dict = AF.find(self.conn, search_term)
            if not items_dict:
                wx.MessageBox("No results found", "Error", wx.OK | wx.ICON_ERROR)
                return
            # if len(items_dict) == 1:
            # Go to the folder
            item = items_dict[0]
            self.current_dir = item.parent
            shas_to_highlight = [item.stat().sha256]
            self.load_directory(shas_to_highlight)

    def on_search_toggle(self, evt=None):
        """User pressed Ctrl-F - toggle the search pane."""
        if self.search_panel.Shown:
            self.search_hide()
        else:
            self.search_show()
        # if evt:
        #    evt.Skip()

    def on_search_item_activated(self, event: wx.ListEvent):
        """Handle double-click on item"""
        row_selected_no = event.Index
        folder_path = event.Text
        file_name = self.search_results.GetItem(row_selected_no, 1).Text
        self.current_dir = self.conn / folder_path
        self.load_directory([file_name])
        self.file_list.SetFocus()

    def search_hide(self):
        self.search_panel.Show(False)
        self.file_list.SetFocus()
        self.splitter.SetSashPosition(-1)
        self.splitter.SetMinimumPaneSize(0)
        self.splitter.Layout()

    def search_show(self):
        self.search_panel.Show(True)
        self.search_input.SetFocus()
        self.search_input.SetSelection(-1, -1)  # Highlight all text
        sash_pos = self.file_list.GetSize().GetHeight() - 200
        self.splitter.SetMinimumPaneSize(150)  # so the sash can’t disappear
        splitter_min = self.splitter.MinimumPaneSize
        self.splitter.SetSashPosition(max(splitter_min, sash_pos))
        self.splitter.Layout()

    def on_search_key_down(self, event):
        self.search_results.DeleteAllItems()
        query = str(self.search_input.Value).strip()
        numbers_only_query = re.sub("[^0-9]", "", query)
        if event.EventType == wx.EVT_KEY_UP:
            key_code = event.GetKeyCode()
            is_enter = key_code == wx.WXK_NUMPAD_ENTER or key_code == wx.WXK_RETURN
        else:
            is_enter = False
        is_enough = len(numbers_only_query) > 3
        if is_enter or is_enough:
            limit = 50
            if is_enter:
                limit = -1
            items = AF.find(self.conn, query, limit=limit)
            # Drop the summary files
            if self.search_ignore_summary.Value:
                items = [i for i in items if not "summary" in i["name"].lower()]
            # Show the items
            for i, item in enumerate(items):
                path = item["repo"] + "/" + item["path"]
                index = self.search_results.InsertItem(i + 1, path)
                self.search_results.SetItem(index, 1, item["name"])
                self.search_results.SetItem(index, 2, self.format_size(item["size"]))
                self.search_results.SetItem(index, 3, item["modified"])
                self.search_results.SetItem(index, 4, item["updated"])
                self.search_results.SetItem(
                    index, 5, item["modified_by"] or item["created_by"] or ""
                )
                self.search_results.SetItem(index, 6, item["sha256"] or "")
        else:
            event.Skip()  # Allow other key events to be processed

    def start_go_to(self, *_):
        dlg = CRDialog(self.open_cr_handler)
        dlg.ShowModal()

    def open_cr_handler(self, cr_number: str, selected_type: str):
        folders = AF.find_folders(self.conn, selected_type, cr_number)
        matching_folder = None
        for folder in folders:
            folder_no = re.sub("[^0-9]", "", folder.name)
            if folder_no == cr_number:
                matching_folder = folder
        # If the folder's not found, ask to make it
        if not matching_folder:
            dlg_result = wx.MessageBox(
                f"Folder not found for {cr_number}.\nWould you like to create it?",
                "Folder Not Found",
                wx.YES_NO | wx.ICON_QUESTION,
            )
            if dlg_result == wx.NO:
                return
            new_folder = self.conn / selected_type / cr_number
            AF.make_folder(new_folder)
            matching_folder = new_folder
        self.current_dir = matching_folder
        self.load_directory()

    def on_shipping_tool(self, *_):
        selected_items = self.get_selected_paths()
        selected_items = [
            f for f in selected_items if hasattr(f, "name") and not f.name == ".."
        ]
        selected_items = [self.current_dir / f.name for f in selected_items]
        telemetry.log(f"DST - {', '.join([str(item) for item in selected_items])}")
        dlg = ShippingToolDialog(selected_items)
        dlg.ShowModal()

    def on_selected(self, event):
        self.update_navbar()

    def update_navbar(self):
        # Default to enabling the buttons
        for btn in self.buttons:
            btn.Enable()
        # 100% Disable DocuSign
        self.buttons.DOCUSIGN.Disable()
        # See what's highlighted
        selected_items = self.get_selected_paths()
        selected_items = [
            f for f in selected_items if hasattr(f, "name") and not f.name == ".."
        ]
        # Disable the back button if there are no other folders to go back to
        if not any([not self.current_dir == path for path in self.path_backward_stack]):
            self.buttons.BACK.Disable()
        # Disable the forward button
        if not self.path_forward_stack:
            self.buttons.FORWARD.Disable()
        # Disable the up button
        if self.current_dir.parent == self.current_dir:
            self.buttons.UP.Disable()
        # Disable modifying if we don't have write permissions
        if not AF.check_has_write_permissions(self.current_dir):
            self.buttons.NEW_FOLDER.Disable()
            self.buttons.PASTE.Disable()
            self.buttons.UPLOAD.Disable()
            self.buttons.DELETE.Disable()
        # Disable open/download if nothing is highlighted
        if not selected_items:
            self.buttons.COPY.Disable()
            self.buttons.DOWNLOAD.Disable()
            self.buttons.OPEN.Disable()
            self.buttons.DELETE.Disable()
            self.buttons.SHIPPING_TOOL.Disable()
        if not re.findall(r"(\d{5})", self.current_dir.path_in_repo):
            self.buttons.REVISION.Disable()


class FileDropTarget(wx.FileDropTarget):
    """Handles both drag-in and drag-out operations"""

    def __init__(self, window):
        super().__init__()
        self.window = window

    def OnDropFiles(self, x, y, filenames):
        """Handle files dropped into the window"""
        upload_status = file_handler.upload_formatted_files(
            [Path(f) for f in filenames], self.window.current_dir
        )
        if upload_status["errors"]:
            wx.MessageBox(
                "Errors occurred while copying:\n" + "\n".join(upload_status["errors"]),
                "Error",
                wx.OK | wx.ICON_ERROR,
            )
        self.window.load_directory(
            files_to_highlight=upload_status["success"], add_to_back_queue=False
        )
        telemetry.log(f"Files uploaded - {len(filenames)}")
        return True
