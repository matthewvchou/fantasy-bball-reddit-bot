"""Loads Franchises and their name history from the NBA's franchise history."""

import sqlite3
from functools import partial
from typing import Any

from src.ingest.ingestlog import runLoggedUnit
from src.ingest.schema import createSchema
from src.ingest.source import NbaSource

FRANCHISE_HISTORY_KIND = "franchiseHistory"
FRANCHISE_HISTORY_UNIT = "all"


def loadFranchises(source: NbaSource, db: sqlite3.Connection, shouldRefresh: bool = False) -> None:
    """
    Load every Franchise and its name history into the database.

    Runs as one logged unit: skipped when already done unless shouldRefresh is set, which
    replaces the stored rows. Commits when it finishes.

    Args:
        source: Where the NBA API responses come from.
        db: Open SQLite connection; the tables are created if missing.
        shouldRefresh: True to reload instead of skipping a finished load.
    """
    createSchema(db)
    runLoggedUnit(db, FRANCHISE_HISTORY_KIND, FRANCHISE_HISTORY_UNIT, partial(loadUnit, source, db), shouldRefresh)


def loadUnit(source: NbaSource, db: sqlite3.Connection) -> int:
    """Replace the stored franchises with the source's, without committing; return the rows written."""
    response = source.fetchFranchiseHistory()
    franchises, names = buildFranchises(getRows(response, "FranchiseHistory"), getRows(response, "DefunctTeams"))

    db.execute("DELETE FROM franchiseName")
    db.execute("DELETE FROM franchise")
    db.executemany("INSERT INTO franchise (teamId, isDefunct) VALUES (?, ?)", franchises.items())
    db.executemany(
        "INSERT INTO franchiseName (teamId, city, name, startYear, endYear) VALUES (?, ?, ?, ?, ?)", names,
    )
    return len(franchises) + len(names)


def buildFranchises(
    currentRows: list[dict[str, Any]], defunctRows: list[dict[str, Any]],
) -> tuple[dict[int, int], set[tuple[int, str, str, int, int]]]:
    """
    Turn the source's two frames into franchise IDs with their defunct flag, and name rows.

    Name rows are a set because the source can list two rows that match in every field kept here,
    for example Charlotte's whole-franchise row and its Hornets name row (both 1988-2026).
    """
    franchises = {row["TEAM_ID"]: 0 for row in currentRows} | {row["TEAM_ID"]: 1 for row in defunctRows}
    names = {
        (row["TEAM_ID"], row["TEAM_CITY"], row["TEAM_NAME"], int(row["START_YEAR"]), int(row["END_YEAR"]))
        for row in currentRows + defunctRows
    }
    return franchises, names


def getRows(response: dict[str, Any], resultSetName: str) -> list[dict[str, Any]]:
    """Turn one named result set of the response into a dict per row, keyed by column name."""
    resultSet = next(frame for frame in response["resultSets"] if frame["name"] == resultSetName)
    return [dict(zip(resultSet["headers"], row)) for row in resultSet["rowSet"]]
