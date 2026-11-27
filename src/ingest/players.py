"""Loads players and their bio from the NBA's all-time player index."""

import sqlite3
from functools import partial
from typing import Any

from src.ingest.ingestlog import runLoggedUnit
from src.ingest.schema import createSchema
from src.ingest.source import NbaSource

PLAYER_INDEX_KIND = "playerIndex"
PLAYER_INDEX_UNIT = "all"
INCHES_PER_FOOT = 12

# The index uses this text for players who did not attend college; it is not a college.
NO_COLLEGE = "No College"


def loadPlayers(source: NbaSource, db: sqlite3.Connection, season: str, shouldRefresh: bool = False) -> None:
    """
    Load every player and their bio into the database.

    Runs as one logged unit: skipped when already done unless shouldRefresh is set, which
    replaces the stored rows. Commits when it finishes.

    Args:
        source: Where the NBA API responses come from.
        db: Open SQLite connection; the tables are created if missing.
        season: Season label such as '2025-26'. It does not change who is listed.
        shouldRefresh: True to reload instead of skipping a finished load.
    """
    createSchema(db)
    runLoggedUnit(db, PLAYER_INDEX_KIND, PLAYER_INDEX_UNIT, partial(loadUnit, source, db, season), shouldRefresh)


def loadUnit(source: NbaSource, db: sqlite3.Connection, season: str) -> int:
    """Replace the stored players with the source's, without committing; return the rows written."""
    players = parsePlayers(source.fetchPlayerIndex(season)["resultSets"][0])

    db.execute("DELETE FROM player")
    db.executemany(
        "INSERT INTO player (playerId, firstName, lastName, heightInches, weightPounds, country, college, "
        "draftYear, draftRound, draftPick, primaryPosition, secondaryPosition) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        players,
    )
    return len(players)


def parsePlayers(resultSet: dict[str, Any]) -> list[tuple[Any, ...]]:
    """Parse every index row into player values, one per player ID."""
    players: dict[int, tuple[Any, ...]] = {}
    for values in resultSet["rowSet"]:
        row = dict(zip(resultSet["headers"], values))
        # A traded player is listed once per team with identical bio, so the first row is kept.
        players.setdefault(row["PERSON_ID"], parsePlayer(row))
    return list(players.values())


def parsePlayer(row: dict[str, Any]) -> tuple[Any, ...]:
    """Turn one index row into the values of a player row; anything the index leaves out becomes NULL."""
    primaryPosition, secondaryPosition = splitPosition(row["POSITION"])
    return (
        row["PERSON_ID"], row["PLAYER_FIRST_NAME"], row["PLAYER_LAST_NAME"],
        parseHeightInches(row["HEIGHT"]), parseWeightPounds(row["WEIGHT"]),
        row["COUNTRY"], None if row["COLLEGE"] == NO_COLLEGE else row["COLLEGE"],
        row["DRAFT_YEAR"], row["DRAFT_ROUND"], row["DRAFT_NUMBER"],
        primaryPosition, secondaryPosition,
    )


def parseHeightInches(height: str | None) -> int | None:
    """Convert a height such as '6-10' to inches (82); a missing height is None."""
    if not height:
        return None
    feet, inches = height.split("-")
    return int(feet) * INCHES_PER_FOOT + int(inches)


def parseWeightPounds(weight: str | None) -> int | None:
    """Convert a weight such as '240' to pounds; a missing or blank weight is None."""
    if weight is None or not weight.strip():
        return None
    return int(weight)


def splitPosition(position: str | None) -> tuple[str | None, str | None]:
    """
    Split a position such as 'G-F' into ('G', 'F'); a single 'G' gives ('G', None).

    The index does not say that the first letter is the primary position; that is our reading of
    its order. Magic Johnson, a point guard, is listed 'F-G', so treat the split as a hint.
    """
    if not position:
        return None, None
    primary, _, secondary = position.partition("-")
    return primary, secondary or None
