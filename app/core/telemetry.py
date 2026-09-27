"""
Local application logging.

Events are written to disk as newline delimited JSON, one file per day, and files
older than a week are pruned. Nothing is sent off the machine.
"""

import uuid
from pathlib import Path

from loguru import logger

from app.core.config import CONFIG

LOG_DIR = CONFIG.STORE_LOCATION_PATH.parent / "logs"

_session_id = str(uuid.uuid4())
_disable_logging = False


def add_sink(log_dir: Path = LOG_DIR, rotation="1 day") -> int:
    """
    Attach the daily JSON file sink, returning the id needed to remove it again.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    return logger.add(
        # The {time} token is what makes retention work. loguru derives the
        # retention globs from this string: with a literal app_2026-09-27.log it
        # only ever looks for files under that one stem, so yesterday's and last
        # week's files are invisible to it and never pruned. Left as a token, it
        # globs app_*.log, and the name is still re-evaluated on each rotation,
        # so each day's file is named for its dateline.
        log_dir / "app_{time:YYYY-MM-DD}.log",
        rotation=rotation,
        retention="1 week",
        serialize=True,
        # Not cosmetic. This defaults to True, which appends the *values of local
        # variables* to exception records. Login holds set_pw / store_pw in local
        # scope, so the default would write plaintext passwords to the log file.
        diagnose=False,
        # Writes are queued and flushed by a background thread, so a call site
        # never waits on the disk.
        enqueue=True,
    )


try:
    # Drop loguru's default stderr sink. This app ships windowed (no console),
    # it was never chatty, and the file sink is the only destination wanted.
    logger.remove()
    add_sink()
except Exception:
    # Logging failed for some reason, just disable it so it doesn't cause delays
    _disable_logging = True


def log(msg: str):
    """
    Record an event against today's log file. Never raises - a logging failure must
    not break the GUI or add latency to the caller.
    """
    global _disable_logging
    if _disable_logging:
        return
    try:
        # Bound via bind, not logger.info(..., **kwargs) - loguru consumes a
        # literal "extra" kwarg, which would silently shadow the record.
        logger.bind(
            session_id=_session_id, app_version=CONFIG.VERSION
        ).info(msg)
    except Exception:
        _disable_logging = True
