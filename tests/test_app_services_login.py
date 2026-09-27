"""
Tests for the login probe and the "resume last folder" behaviour.

The point of interest is that verifying the credentials and drawing the root
view are the *same* request. These tests pin that down: a bad login must not
result in a second trip to the repositories endpoint.
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
from app.models.af_search_results import AF_Login_Error, AF_Login_Result
from app.services import login as LOGIN


class _FakeRepo:
    """Stands in for a dohq_artifactory Repository object."""

    def __init__(self, name):
        self.name = name


class _FakeConn:
    """
    Minimal stand-in for ArtifactoryPath.

    Records every get_repositories() call so the tests can assert on how many
    round trips were made, which is the behaviour under test.
    """

    def __init__(self, repos=(), raises=None):
        self._repos = [_FakeRepo(name) for name in repos]
        self._raises = raises
        self.calls = []

    def get_repositories(self, lazy=False):
        self.calls.append(lazy)
        if self._raises is not None:
            raise self._raises
        return self._repos


class Services_Login(unittest.TestCase):
    def test_good_creds_return_the_connection_and_its_repos(self):
        conn = _FakeConn(["repo-a", "repo-b"])
        with mock.patch.object(LOGIN, "get_af_conn", return_value=conn):
            result = LOGIN._test_af_creds("bob", "pw")

        self.assertIsInstance(result, AF_Login_Result)
        self.assertIs(result.conn, conn)
        self.assertEqual(result.repos, ["repo-a", "repo-b"])

    def test_good_creds_cost_exactly_one_request(self):
        """
        The repo list is the payload of the credential check, so it must not be
        thrown away and fetched again. lazy=True also stops the library issuing
        an extra read() per repository.
        """
        conn = _FakeConn(["repo-a", "repo-b", "repo-c"])
        with mock.patch.object(LOGIN, "get_af_conn", return_value=conn):
            LOGIN._test_af_creds("bob", "pw")

        self.assertEqual(len(conn.calls), 1, "the repositories endpoint was hit more than once")
        self.assertEqual(conn.calls, [True], "get_repositories should be called with lazy=True")

    def test_bad_creds_return_the_error(self):
        conn = _FakeConn(raises=dohq_artifactory.exception.ArtifactoryException("Bad credentials"))
        with mock.patch.object(LOGIN, "get_af_conn", return_value=conn):
            result = LOGIN._test_af_creds("bob", "wrong")

        self.assertIsInstance(result, AF_Login_Error)
        self.assertNotIsInstance(result, AF_Login_Result)
        self.assertEqual(result.message, "Invalid username or password")

    def test_404_is_reported_as_could_not_connect(self):
        conn = _FakeConn(raises=dohq_artifactory.exception.ArtifactoryException("404 Client Error"))
        with mock.patch.object(LOGIN, "get_af_conn", return_value=conn):
            result = LOGIN._test_af_creds("bob", "pw")

        self.assertEqual(result.message, "Error: Could not connect to Artifactory")

    def test_a_failed_login_is_not_silently_swallowed(self):
        """
        Regression guard. The probe used to build an error message and return
        None, and the dialog checked isinstance(conn, str) - so a wrong password
        produced no message at all. The error has to survive the return.
        """
        conn = _FakeConn(raises=dohq_artifactory.exception.ArtifactoryException("Bad credentials"))
        with mock.patch.object(LOGIN, "get_af_conn", return_value=conn):
            result = LOGIN._test_af_creds("bob", "wrong")

        self.assertTrue(result.message, "an empty message would be indistinguishable from success")


class Core_Credentials_LastDir(unittest.TestCase):
    """The last folder is kept in the same encrypted store as the credentials."""

    def setUp(self):
        self._store = {}
        patcher = mock.patch.object(
            credentials, "_get_store", side_effect=lambda: dict(self._store)
        )
        self._get_store = patcher.start()
        self.addCleanup(patcher.stop)
        save = mock.patch.object(
            credentials, "_save_store", side_effect=lambda s: self._store.update(s)
        )
        save.start()
        self.addCleanup(save.stop)

    def test_no_stored_folder_starts_empty(self):
        self.assertEqual(credentials.get_last_dir(), "")

    def test_folder_round_trips(self):
        credentials.set_last_dir("artifactory/myrepo/some/folder")
        self.assertEqual(credentials.get_last_dir(), "artifactory/myrepo/some/folder")

    def test_folder_does_not_disturb_the_stored_username(self):
        credentials.set_username("bob")
        credentials.set_last_dir("artifactory/myrepo")
        self.assertEqual(credentials.get_username(), "bob")
        self.assertEqual(credentials.get_last_dir(), "artifactory/myrepo")


if __name__ == "__main__":
    unittest.main()
