"""The ingest log: which units of work finished, so a rerun skips them and a failure shows where it stopped."""

import logging
import sqlite3
from collections.abc import Callable
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

DONE = "done"
ERROR = "error"
INTERRUPTED = "interrupted"


def runLoggedUnit(
    db: sqlite3.Connection, kind: str, unitKey: str, load: Callable[[], int], shouldRefresh: bool,
) -> None:
    """
    Run one unit of work in its own transaction and log the outcome.

    A unit already logged as done is skipped unless shouldRefresh is set. load writes the unit's
    rows without committing and returns how many it wrote. Any error or interrupt rolls the unit
    back, is logged as 'error' (or 'interrupted' for Ctrl-C), and is re-raised.
    """
    if not shouldRefresh and isUnitDone(db, kind, unitKey):
        return
    try:
        rowCount = load()
        logUnit(db, kind, unitKey, DONE, rowCount)
        db.commit()
    except BaseException as error:
        # BaseException, so an interrupt also rolls back instead of leaving half a unit behind.
        db.rollback()
        message = describeError(error)
        logStop(db, kind, unitKey, INTERRUPTED if isinstance(error, KeyboardInterrupt) else ERROR, message)
        db.commit()
        # Also on the console, with the traceback, so a failure is visible without opening the database.
        logger.error("Unit %s/%s stopped the run: %s", kind, unitKey, message, exc_info=True)
        raise


def isUnitDone(db: sqlite3.Connection, kind: str, unitKey: str) -> bool:
    """Say whether the unit is logged as done."""
    row = db.execute("SELECT status FROM ingestLog WHERE kind = ? AND unitKey = ?", (kind, unitKey)).fetchone()
    return row is not None and row[0] == DONE


def describeError(error: BaseException) -> str:
    """Name the error's type and add its text when it has any, e.g. 'ConnectionError: NBA API unreachable'."""
    text = str(error)
    return f"{type(error).__name__}: {text}" if text else type(error).__name__


def logStop(db: sqlite3.Connection, kind: str, unitKey: str, status: str, message: str) -> None:
    """
    Record that a run stopped at this unit, with the error text, without touching an earlier row count.

    A failed refresh rolls back to the old rows, so the count of what is stored stays true
    while the status shows the run stopped here. Not marked done, so the next run retries it.
    """
    db.execute(
        "INSERT INTO ingestLog (kind, unitKey, status, rowCount, finishedAt, message) VALUES (?, ?, ?, 0, ?, ?) "
        "ON CONFLICT (kind, unitKey) DO UPDATE SET status = excluded.status, finishedAt = excluded.finishedAt, "
        "message = excluded.message",
        (kind, unitKey, status, datetime.now(timezone.utc).isoformat(), message),
    )


def logUnit(db: sqlite3.Connection, kind: str, unitKey: str, status: str, rowCount: int) -> None:
    """Record a unit's outcome, replacing an earlier row such as a failed attempt."""
    db.execute(
        "INSERT OR REPLACE INTO ingestLog (kind, unitKey, status, rowCount, finishedAt, message) VALUES (?, ?, ?, ?, ?, NULL)",
        (kind, unitKey, status, rowCount, datetime.now(timezone.utc).isoformat()),
    )
