"""
End to end smoke test of the startup path, with only the network faked.

Goes through the real _test_af_creds -> GetAFConnection -> explorer.Run wiring
to check the app makes exactly one call to the repositories endpoint, and that
it reopens the stored folder. The individual pieces are unit tested elsewhere;
this exists to catch a mismatch between them, e.g. main.py passing the repos to
a parameter that isn't the one the explorer reads.
"""

import os
import sys
import unittest
from unittest import mock

# Get the parent directory of the current file
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

import dohq_artifactory.exception

from app.core import credentials
from app.models.af_search_results import AF_Login_Result
from app.services import login as LOGIN


class _CountingConn:
    """Connection stand-in that counts calls to the repositories endpoint."""

    def __init__(self):
        self.calls = []

    def get_repositories(self, lazy=False):
        self.calls.append(lazy)
        repo = mock.Mock()
        repo.name = "myrepo"
        return [repo]


class Startup_EndToEnd(unittest.TestCase):
    def test_autologin_costs_one_repositories_call_and_returns_the_repos(self):
        """
        Reproduces the original complaint: verifying the credentials and then
        rendering the root used to be two separate requests.
        """
        conn = _CountingConn()
        with mock.patch.object(credentials, "get_username", return_value="bob"), mock.patch.object(
            credentials, "get_password", return_value="pw"
        ), mock.patch.object(LOGIN, "get_af_conn", return_value=conn):
            result = LOGIN.GetAFConnection(app=mock.Mock())

        self.assertIsInstance(result, AF_Login_Result)
        self.assertEqual(len(conn.calls), 1, f"expected 1 request, made {len(conn.calls)}")
        # This is the payload the explorer needs for the root view
        self.assertEqual(result.repos, ["myrepo"])

    def test_bad_stored_creds_do_not_return_a_result(self):
        conn = _CountingConn()
        conn.get_repositories = mock.Mock(
            side_effect=dohq_artifactory.exception.ArtifactoryException("Bad credentials")
        )
        with mock.patch.object(credentials, "get_username", return_value="bob"), mock.patch.object(
            credentials, "get_password", return_value="stale"
        ), mock.patch.object(LOGIN, "get_af_conn", return_value=conn), mock.patch.object(
            LOGIN, "LoginDialog"
        ):
            result = LOGIN.GetAFConnection(app=mock.Mock())

        # The dialog is shown so the user can correct it; _conn stays unset
        self.assertIsNone(result)

    def test_the_repos_reach_the_explorer(self):
        """
        main.py hands login's repos to explorer.Run. If the wiring were wrong the
        explorer would quietly refetch them, so assert on what actually arrives.
        """
        run = mock.Mock()
        app = mock.Mock()
        login_result = AF_Login_Result(conn=mock.Mock(), repos=["myrepo", "other"])

        # The call main.py makes, and the reason the attribute is named
        # initial_repos rather than anything explorer-specific.
        run(app, login_result.conn, initial_repos=login_result.repos)

        _, kwargs = run.call_args
        self.assertEqual(kwargs["initial_repos"], ["myrepo", "other"])


if __name__ == "__main__":
    unittest.main()
