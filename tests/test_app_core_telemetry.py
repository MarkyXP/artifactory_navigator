import json
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path

# Get the parent directory of the current file
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, parent_dir)

# app.core.config reads CONFIG_PATH at import time, and there is no .env in the
# repo, so point it at the checked in config unless one is already set.
os.environ["CONFIG_PATH"] = os.environ.get(
    "CONFIG_PATH", os.path.join(parent_dir, "app", "core", "config.json")
)

from loguru import logger

from app.core import telemetry

_A_PASSWORD = "hunter2"


class Core_Telemetry(unittest.TestCase):
    def setUp(self):
        # telemetry adds a sink to the real log dir at import time - drop it so
        # the tests below are the only thing writing anywhere.
        logger.remove()
        self._log_dir = Path(tempfile.mkdtemp())
        self._sink_id = telemetry.add_sink(self._log_dir)

    def tearDown(self):
        logger.remove(self._sink_id)
        logger.complete()

    def _today(self) -> Path:
        return self._log_dir / f"app_{datetime.now():%Y-%m-%d}.log"

    def test_10_writes_to_dated_file(self):
        telemetry.log("Files uploaded - 3")
        # enqueue=True means the write lands on a worker thread
        logger.complete()

        log_file = self._today()
        self.assertTrue(log_file.exists(), f"{log_file} was not created")

    def test_20_lines_are_json(self):
        telemetry.log("Files uploaded - 3")
        telemetry.log("Auto-login successful")
        logger.complete()

        lines = self._today().read_text().strip().splitlines()
        self.assertEqual(len(lines), 2)

        records = [json.loads(line)["record"] for line in lines]
        for record in records:
            self.assertIn("time", record)
            self.assertIn("session_id", record["extra"])
            self.assertIn("app_version", record["extra"])

        self.assertEqual(
            [record["message"] for record in records],
            ["Files uploaded - 3", "Auto-login successful"],
        )

    def test_30_creates_log_dir_if_missing(self):
        nested = self._log_dir / "does" / "not" / "exist"
        sink_id = telemetry.add_sink(nested)
        try:
            self.assertTrue(nested.is_dir())
        finally:
            logger.remove(sink_id)

    def test_35_retention_prunes_older_than_a_week(self):
        # Retention is derived from the sink path, so this exercises the real
        # add_sink(). If the {time} token in the filename is ever replaced with a
        # literal date, loguru only globs that one stem and older files are never
        # pruned - this test is what catches that.
        rollover_dir = Path(tempfile.mkdtemp())
        now = time.time()
        for days, label in ((8, "old"), (3, "recent")):
            aged = rollover_dir / f"app_{label}.log"
            aged.write_text("{}")
            os.utime(aged, (now - days * 86400, now - days * 86400))

        # rotation=1s stands in for the real "1 day" so the sweep fires now.
        # A rotation is what triggers retention; sink creation does not.
        sink_id = telemetry.add_sink(rollover_dir, rotation=1)
        try:
            telemetry.log("first")
            logger.complete()
            time.sleep(1.1)
            telemetry.log("second")
            logger.complete()
        finally:
            logger.remove(sink_id)

        self.assertTrue(
            list(rollover_dir.glob("app_*.log")), "the sink never rotated"
        )
        self.assertFalse(
            (rollover_dir / "app_old.log").exists(),
            "an 8 day old file survived the 1 week retention",
        )
        self.assertTrue(
            (rollover_dir / "app_recent.log").exists(),
            "a 3 day old file should be kept",
        )

    def _log_a_crash(self, sink_dir: Path, **sink_kwargs) -> str:
        """
        Log an exception raised in a frame holding store_pw, and return the file.
        """
        sink_id = logger.add(
            sink_dir / "log.log",
            rotation="1 day",
            retention="1 week",
            serialize=True,
            enqueue=True,
            **sink_kwargs,
        )
        try:
            def _frames():
                # diagnose reports the *raising* line, so store_pw has to appear
                # on it to be picked up. Assigned from a module level name so the
                # value is not also sitting in the echoed source line - otherwise
                # the test would pass with diagnose on and prove nothing.
                store_pw = _A_PASSWORD; raise ValueError("boom")

            try:
                _frames()
            except ValueError:
                logger.exception("Login failed")
        finally:
            logger.remove(sink_id)
        logger.complete()
        return (sink_dir / "log.log").read_text()

    def test_40_diagnose_does_not_dump_locals(self):
        # diagnose defaults to True, and it appends the *values* of local
        # variables for the raising frame. login.py holds set_pw / store_pw in
        # local scope, so with the default on, a crash in those functions would
        # write a plaintext Artifactory password into the log file.
        # Control first - if diagnose=True does not leak, the test is vacuous.
        control = self._log_a_crash(Path(tempfile.mkdtemp()))
        self.assertIn(_A_PASSWORD, control, "diagnose=True control did not leak")

        # Same crash, same sink config as the app, minus diagnose.
        actual = self._log_a_crash(Path(tempfile.mkdtemp()), diagnose=False)
        self.assertNotIn(_A_PASSWORD, actual)


if __name__ == "__main__":
    unittest.main()
