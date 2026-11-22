import sqlite3
from typing import Any

from src.ingest.schema import createSchema
from src.ingest.source import NbaSource

# The source's own season type names, which differ from our Game Types ('Pre Season' vs
# 'Preseason', 'PlayIn' vs 'Postseason'). Each season is fetched once per name.
SEASON_TYPES = ["Pre Season", "Regular Season", "Playoffs", "PlayIn", "Summer League"]

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


def ingestSeason(source: NbaSource, db: sqlite3.Connection, season: str) -> None:
    """
    Load one season of games, across every Game Type, into the database.

    Games against a Non-NBA Team are skipped. Player stat lines come from the game log
    only for seasons before BOX_SCORE_FIRST_SEASON. Commits the transaction when it finishes.
    Not safe to repeat: a second run for the same season fails on the primary keys,
    because reruns are a separate ticket.

    Args:
        source: Where the NBA API responses come from.
        db: Open SQLite connection; the tables are created if missing.
        season: Season label such as '2023-24'.

    Raises:
        ValueError: A game ID has a prefix that is not a known Game Type.
    """
    createSchema(db)
    seasonStartYear = int(season[:4])
    for seasonType in SEASON_TYPES:
        storedGameIds = insertGames(db, readRows(source.fetchTeamGameLog(season, seasonType)), seasonStartYear)
        if seasonStartYear < BOX_SCORE_FIRST_SEASON:
            playerRows = readRows(source.fetchPlayerGameLog(season, seasonType))
            # A skipped game's stat lines would be orphans, since nothing links them to a game row.
            insertPlayerGames(db, [row for row in playerRows if row["GAME_ID"] in storedGameIds])
    db.commit()


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
