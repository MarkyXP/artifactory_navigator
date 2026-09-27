"""
Tests for the explorer's directory handling - restoring the last folder, and
drawing the root view from the repository list login already fetched.
"""

import os
import sys
import unittest
from unittest import mock

# Get the parent directory of the current file
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

from artifactory import ArtifactoryPath

from app.core import credentials
from app.core.config import CONFIG

# Imported in this order for the same reason main.py does: app.gui.explorer and
# app.services.explorer import each other, and whichever is imported first
# breaks if the other is still initialising.
from app.services import explorer as EXPLORER
from app.gui.explorer import FileExplorer


def _conn() -> ArtifactoryPath:
    """A connection that never touches the network."""
    return ArtifactoryPath(CONFIG.AF_URL)


def _folder(repo: str, path_in_repo: str = "") -> ArtifactoryPath:
    """
    A path inside Artifactory, built the way the app builds them.

    CONFIG.AF_URL already carries the server, so appending the base to it would
    produce a nonsense URL.
    """
    return ArtifactoryPath(f"{CONFIG.AF_URL}/{repo}{path_in_repo}")


class _Explorer(FileExplorer):
    """
    FileExplorer with the wx.Frame constructor and the initial load bypassed.

    The tests here are about how paths are chosen and stored, not about
    drawing, so the real __init__ would only get in the way.
    """

    def __init__(self, af_conn, initial_repos=None):  # noqa: D107
        self.conn = af_conn
        self._repos = list(initial_repos) if initial_repos else None


class Gui_Explorer_Restore(unittest.TestCase):
    def test_nothing_stored_starts_at_the_root(self):
        with mock.patch.object(credentials, "get_last_dir", return_value=""):
            result = _Explorer(_conn())._restore_last_dir()
        self.assertEqual(result.as_posix(), _conn().as_posix())

    def test_stored_folder_is_reopened(self):
        stored = "artifactory/myrepo/some/folder"
        with mock.patch.object(credentials, "get_last_dir", return_value=stored):
            with mock.patch.object(ArtifactoryPath, "is_dir", return_value=True):
                result = _Explorer(_conn())._restore_last_dir()
        self.assertIn("myrepo/some/folder", result.as_posix())

    def test_a_folder_deleted_while_closed_falls_back_to_the_root(self):
        """
        The stored folder can be gone by the next start, so it has to be checked
        rather than trusted.
        """
        with mock.patch.object(
            credentials, "get_last_dir", return_value="artifactory/vanished"
        ):
            with mock.patch.object(ArtifactoryPath, "is_dir", return_value=False):
                result = _Explorer(_conn())._restore_last_dir()
        self.assertEqual(result.as_posix(), _conn().as_posix())

    def test_an_unreachable_server_falls_back_to_the_root(self):
        with mock.patch.object(
            credentials, "get_last_dir", return_value="artifactory/myrepo"
        ):
            with mock.patch.object(ArtifactoryPath, "is_dir", side_effect=OSError("boom")):
                result = _Explorer(_conn())._restore_last_dir()
        self.assertEqual(result.as_posix(), _conn().as_posix())


class Gui_Explorer_RepoCache(unittest.TestCase):
    def test_the_root_view_uses_the_list_login_already_fetched(self):
        """
        With the list supplied by login, drawing the root must not call the
        server - that request was already made and paid for.
        """
        explorer = _Explorer(_conn(), initial_repos=["repo-a", "repo-b"])
        explorer.conn = mock.Mock()
        self.assertEqual(explorer._get_repo_list(), ["repo-a", "repo-b"])
        explorer.conn.get_repositories.assert_not_called()

    def test_without_a_list_the_root_view_fetches_it_once(self):
        conn = mock.Mock()
        repo = mock.Mock()
        repo.name = "repo-a"
        conn.get_repositories.return_value = [repo]
        explorer = _Explorer(conn)

        self.assertEqual(explorer._get_repo_list(), ["repo-a"])
        self.assertEqual(conn.get_repositories.call_count, 1)
        # lazy=True avoids an extra read() per repository
        conn.get_repositories.assert_called_with(lazy=True)

    def test_the_list_is_fetched_at_most_once(self):
        conn = mock.Mock()
        repo = mock.Mock()
        repo.name = "repo-a"
        conn.get_repositories.return_value = [repo]
        explorer = _Explorer(conn)

        explorer._get_repo_list()
        explorer._get_repo_list()
        self.assertEqual(conn.get_repositories.call_count, 1)


class Gui_Explorer_SaveLastDir(unittest.TestCase):
    # "artifactory" - the part of AF_URL that follows the server base
    _AF_ROOT = CONFIG.AF_URL.replace(CONFIG.AF_BASE_URL.rstrip("/"), "", 1).strip("/")

    def test_a_folder_is_stored_relative_to_the_artifactory_base(self):
        explorer = _Explorer(_conn())
        explorer.current_dir = _folder("myrepo", "/some/folder")
        with mock.patch.object(credentials, "set_last_dir") as set_last_dir:
            explorer._save_last_dir()
        # The repository has to be included - path_in_repo on its own would
        # reopen the folder one level too deep - and the server must not be, or
        # a change of Artifactory would leave a stale hostname behind.
        set_last_dir.assert_called_once_with(
            f"{self._AF_ROOT}/myrepo/some/folder"
        )

    def test_the_root_is_not_stored(self):
        explorer = _Explorer(_conn())
        explorer.current_dir = ArtifactoryPath(CONFIG.AF_URL)
        with mock.patch.object(credentials, "set_last_dir") as set_last_dir:
            explorer._save_last_dir()
        set_last_dir.assert_not_called()

    def test_a_failed_write_does_not_interrupt_the_explorer(self):
        explorer = _Explorer(_conn())
        explorer.current_dir = _folder("myrepo", "/folder")
        with mock.patch.object(credentials, "set_last_dir", side_effect=OSError("keyring gone")):
            explorer._save_last_dir()  # must not raise

    def test_stored_path_reopens_to_the_same_place(self):
        """
        What gets stored has to read back into the folder it came from, which
        is the whole point of the feature.
        """
        explorer = _Explorer(_conn())
        original = _folder("myrepo", "/some/folder")
        explorer.current_dir = original
        with mock.patch.object(credentials, "set_last_dir") as set_last_dir:
            explorer._save_last_dir()
        stored = set_last_dir.call_args.args[0]

        with mock.patch.object(credentials, "get_last_dir", return_value=stored):
            with mock.patch.object(ArtifactoryPath, "is_dir", return_value=True):
                restored = _Explorer(_conn())._restore_last_dir()
        self.assertEqual(restored.as_posix(), original.as_posix())


if __name__ == "__main__":
    unittest.main()
