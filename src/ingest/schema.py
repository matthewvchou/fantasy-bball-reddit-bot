import sqlite3

GAME_TABLE = """
CREATE TABLE IF NOT EXISTS game (
    gameId TEXT PRIMARY KEY,
    gameDate TEXT NOT NULL,
    season INTEGER NOT NULL,
    gameType TEXT NOT NULL,
    isPlayIn INTEGER NOT NULL,
    homeTeamId INTEGER NOT NULL,
    awayTeamId INTEGER NOT NULL,
    homeScore INTEGER NOT NULL,
    awayScore INTEGER NOT NULL
)
"""

PLAYER_GAME_TABLE = """
CREATE TABLE IF NOT EXISTS playerGame (
    gameId TEXT NOT NULL,
    playerId INTEGER NOT NULL,
    teamId INTEGER NOT NULL,
    minutes INTEGER NOT NULL,
    fgm INTEGER, fga INTEGER, fg3m INTEGER, fg3a INTEGER, ftm INTEGER, fta INTEGER,
    oreb INTEGER, dreb INTEGER, reb INTEGER, ast INTEGER, stl INTEGER, blk INTEGER,
    tov INTEGER, pf INTEGER, pts INTEGER, plusMinus INTEGER,
    PRIMARY KEY (gameId, playerId)
)
"""

# One row per team ID, which survives moves and renames; a defunct team is its own Franchise.
FRANCHISE_TABLE = """
CREATE TABLE IF NOT EXISTS franchise (
    teamId INTEGER PRIMARY KEY,
    isDefunct INTEGER NOT NULL
)
"""

# Every name a Franchise has carried, as the source lists them; its current name is derived on read.
FRANCHISE_NAME_TABLE = """
CREATE TABLE IF NOT EXISTS franchiseName (
    teamId INTEGER NOT NULL,
    city TEXT NOT NULL,
    name TEXT NOT NULL,
    startYear INTEGER NOT NULL,
    endYear INTEGER NOT NULL,
    PRIMARY KEY (teamId, city, name, startYear, endYear)
)
"""

# One row per NBA player ID, with the current name and the bio the all-time player index lists.
# Positions are the index's text split in order, a choice the index itself does not state: the
# first letter listed is the primary position and the second, if any, the secondary.
PLAYER_TABLE = """
CREATE TABLE IF NOT EXISTS player (
    playerId INTEGER PRIMARY KEY,
    firstName TEXT NOT NULL,
    lastName TEXT NOT NULL,
    heightInches INTEGER,
    weightPounds INTEGER,
    country TEXT,
    college TEXT,
    draftYear INTEGER,
    draftRound INTEGER,
    draftPick INTEGER,
    primaryPosition TEXT,
    secondaryPosition TEXT
)
"""

# One row per unit of work, so a rerun can tell which units already finished.
INGEST_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS ingestLog (
    kind TEXT NOT NULL,
    unitKey TEXT NOT NULL,
    status TEXT NOT NULL,
    rowCount INTEGER NOT NULL,
    finishedAt TEXT NOT NULL,
    PRIMARY KEY (kind, unitKey)
)
"""


def createSchema(db: sqlite3.Connection) -> None:
    """Create the ingest tables if they do not exist yet."""
    db.execute(GAME_TABLE)
    db.execute(PLAYER_GAME_TABLE)
    db.execute(FRANCHISE_TABLE)
    db.execute(FRANCHISE_NAME_TABLE)
    db.execute(PLAYER_TABLE)
    db.execute(INGEST_LOG_TABLE)
