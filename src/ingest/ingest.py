import sqlite3
from datetime import datetime, timezone
from typing import Any

from src.ingest.schema import createSchema
from src.ingest.source import NbaSource

# The source's own season type names, which differ from our Game Types ('Pre Season' vs
# 'Preseason', 'PlayIn' vs 'Postseason'). Each season is fetched once per name, and each
# name's games share one game ID prefix, which is how a unit's old rows are found.
SEASON_TYPE_PREFIXES = {
    "Pre Season": "001",
    "Regular Season": "002",
    "Playoffs": "004",
    "PlayIn": "005",
    "Summer League": "152",
}

SEASON_GAME_LOG_KIND = "seasonGameLog"
DONE = "done"
FAILED = "failed"

# The first three digits of an NBA game ID say what kind of game it is.
GAME_TYPES_BY_PREFIX = {
    "001": "Preseason",
    "002": "Regular Season",
    "004": "Postseason",
    "005": "Postseason",
    "152": "Summer League",
}
PLAY_IN_PREFIX = "005"

# From this season on, stat lines come from the per-game box score, which has exact seconds
# and Did Not Play rows. The season game log is only used before it.
BOX_SCORE_FIRST_SEASON = 1996

# Team IDs of the NBA's past franchises (the first range) and current ones (the second). Hardcoded because the source also
# returns international and other non-NBA teams that the preseason games include.
NBA_TEAM_ID_RANGES = [range(1610610023, 1610610038), range(1610612737, 1610612767)]

SECONDS_PER_MINUTE = 60

# Database column -> season game log column. The source leaves stats an era did not
# track empty, and they are stored as NULL, never as zero.
STAT_COLUMNS = {
    "fgm": "FGM", "fga": "FGA", "fg3m": "FG3M", "fg3a": "FG3A", "ftm": "FTM", "fta": "FTA",
    "oreb": "OREB", "dreb": "DREB", "reb": "REB", "ast": "AST", "stl": "STL", "blk": "BLK",
    "tov": "TOV", "pf": "PF", "pts": "PTS", "plusMinus": "PLUS_MINUS",
}


def ingestSeason(source: NbaSource, db: sqlite3.Connection, season: str, shouldRefresh: bool = False) -> None:
    """
    Load one season of games, across every Game Type, into the database.

    One unit is one season and source season type. Each unit loads in its own transaction and
    is logged; units already logged as done are skipped, so a rerun resumes where a failed run
    stopped, unless shouldRefresh is set, which replaces each unit's rows. Games against a
    Non-NBA Team are skipped. Player stat lines come from the game log only for seasons
    before BOX_SCORE_FIRST_SEASON.

    Args:
        source: Where the NBA API responses come from.
        db: Open SQLite connection; the tables are created if missing.
        season: Season label such as '2023-24'.
        shouldRefresh: True to reload units that are already done instead of skipping them.

    Raises:
        ValueError: A game ID has a prefix that is not a known Game Type.
        BaseException: Any error or interrupt from a unit is re-raised after the unit is rolled
            back and, unless it was already done, logged as failed, so a run stops at its first failure.
    """
    createSchema(db)
    for seasonType in SEASON_TYPE_PREFIXES:
        unitKey = f"{season}/{seasonType}"
        if not shouldRefresh and isUnitDone(db, SEASON_GAME_LOG_KIND, unitKey):
            continue
        try:
            rowCount = ingestUnit(source, db, season, seasonType)
            logUnit(db, SEASON_GAME_LOG_KIND, unitKey, DONE, rowCount)
            db.commit()
        except BaseException:
            # BaseException, so an interrupt also rolls back instead of leaving half a unit behind.
            db.rollback()
            # A failed refresh restores the old rows, so a done unit stays logged as done.
            if not isUnitDone(db, SEASON_GAME_LOG_KIND, unitKey):
                logUnit(db, SEASON_GAME_LOG_KIND, unitKey, FAILED, 0)
                db.commit()
            raise


def ingestUnit(source: NbaSource, db: sqlite3.Connection, season: str, seasonType: str) -> int:
    """
    Load one season and source season type without committing; return the rows written.

    Deletes the unit's existing rows first, so loading a unit again never duplicates them.
    """
    seasonStartYear = int(season[:4])
    deleteUnitRows(db, seasonStartYear, SEASON_TYPE_PREFIXES[seasonType])
    storedGameIds = insertGames(db, readRows(source.fetchTeamGameLog(season, seasonType)), seasonStartYear)
    rowCount = len(storedGameIds)
    if seasonStartYear < BOX_SCORE_FIRST_SEASON:
        playerRows = readRows(source.fetchPlayerGameLog(season, seasonType))
        # A skipped game's stat lines would be orphans, since nothing links them to a game row.
        keptRows = [row for row in playerRows if row["GAME_ID"] in storedGameIds]
        insertPlayerGames(db, keptRows)
        rowCount += len(keptRows)
    return rowCount


def deleteUnitRows(db: sqlite3.Connection, seasonStartYear: int, gameIdPrefix: str) -> None:
    """Remove the games and stat lines a unit loaded earlier, so reloading it never duplicates rows."""
    # From BOX_SCORE_FIRST_SEASON on, the box score loader owns the stat lines and this loader never
    # rewrites them, so deleting them here would lose them.
    if seasonStartYear < BOX_SCORE_FIRST_SEASON:
        unitGames = "SELECT gameId FROM game WHERE season = ? AND substr(gameId, 1, 3) = ?"
        db.execute(f"DELETE FROM playerGame WHERE gameId IN ({unitGames})", (seasonStartYear, gameIdPrefix))
    db.execute("DELETE FROM game WHERE season = ? AND substr(gameId, 1, 3) = ?", (seasonStartYear, gameIdPrefix))


def isUnitDone(db: sqlite3.Connection, kind: str, unitKey: str) -> bool:
    """Say whether the unit is logged as done."""
    row = db.execute("SELECT status FROM ingestLog WHERE kind = ? AND unitKey = ?", (kind, unitKey)).fetchone()
    return row is not None and row[0] == DONE


def logUnit(db: sqlite3.Connection, kind: str, unitKey: str, status: str, rowCount: int) -> None:
    """Record a unit's outcome, replacing an earlier row such as a failed attempt."""
    db.execute(
        "INSERT OR REPLACE INTO ingestLog (kind, unitKey, status, rowCount, finishedAt) VALUES (?, ?, ?, ?, ?)",
        (kind, unitKey, status, rowCount, datetime.now(timezone.utc).isoformat()),
    )


def readRows(response: dict[str, Any]) -> list[dict[str, Any]]:
    """Turn a game log response into one dict per row, keyed by the response's column names."""
    resultSet = response["resultSets"][0]
    return [dict(zip(resultSet["headers"], row)) for row in resultSet["rowSet"]]


def insertGames(db: sqlite3.Connection, teamRows: list[dict[str, Any]], seasonStartYear: int) -> set[str]:
    """
    Store one game row per game, pairing the two team rows to find the home and away sides.

    Returns the IDs of the games stored; games against a Non-NBA Team are left out.
    """
    rowsByGame: dict[str, list[dict[str, Any]]] = {}
    for row in teamRows:
        rowsByGame.setdefault(row["GAME_ID"], []).append(row)

    games = []
    for gameId, rows in rowsByGame.items():
        if not all(isNbaTeam(row["TEAM_ID"]) for row in rows):
            continue
        # The source has one row per team and no home/away column; "BOS vs. NYK" marks the home side.
        homeRow = next(row for row in rows if " vs. " in row["MATCHUP"])
        awayRow = next(row for row in rows if " @ " in row["MATCHUP"])
        games.append((
            gameId, homeRow["GAME_DATE"], seasonStartYear, getGameType(gameId),
            gameId.startswith(PLAY_IN_PREFIX), homeRow["TEAM_ID"], awayRow["TEAM_ID"], homeRow["PTS"], awayRow["PTS"],
        ))
    db.executemany(
        "INSERT INTO game (gameId, gameDate, season, gameType, isPlayIn, homeTeamId, awayTeamId, homeScore, awayScore) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        games,
    )
    return {game[0] for game in games}


def isNbaTeam(teamId: int) -> bool:
    """Say whether the team ID belongs to a current or past NBA franchise."""
    return any(teamId in idRange for idRange in NBA_TEAM_ID_RANGES)


def getGameType(gameId: str) -> str:
    """
    Return the Game Type named by the game ID's three-digit prefix.

    Raises:
        ValueError: The prefix is not a known Game Type, so the game is never loaded mislabeled.
    """
    gameType = GAME_TYPES_BY_PREFIX.get(gameId[:3])
    if gameType is None:
        raise ValueError(f"Unrecognized game type for game {gameId}")
    return gameType


def insertPlayerGames(db: sqlite3.Connection, playerRows: list[dict[str, Any]]) -> None:
    """Store one row per player per game, with minutes converted from whole minutes to seconds."""
    columns = ["gameId", "playerId", "teamId", "minutes", *STAT_COLUMNS]
    placeholders = ", ".join("?" for _ in columns)
    db.executemany(
        f"INSERT INTO playerGame ({', '.join(columns)}) VALUES ({placeholders})",
        [
            (
                row["GAME_ID"], row["PLAYER_ID"], row["TEAM_ID"], row["MIN"] * SECONDS_PER_MINUTE,
                *(row[apiColumn] for apiColumn in STAT_COLUMNS.values()),
            )
            for row in playerRows
        ],
    )
