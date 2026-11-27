import sqlite3

from src.ingest.ingest import ingestSeason
from src.ingest.players import loadPlayers
from tests.fakesource import FixtureSource


def testParsesHeightFromFeetAndInchesToInches(dbConnection: sqlite3.Connection) -> None:
    loadPlayers(FixtureSource(), dbConnection, "2025-26")

    # Alaa Abdelnaby is listed at 6-10 and 240 pounds.
    bio = dbConnection.execute(
        "SELECT heightInches, weightPounds, college, country FROM player WHERE playerId = ?", (76001,),
    ).fetchone()
    assert bio == (82, 240, "Duke", "USA")


def testAPlayerListedOnTwoTeamsIsOnePlayerRow(dbConnection: sqlite3.Connection) -> None:
    loadPlayers(FixtureSource(), dbConnection, "2025-26")

    # The source lists Spencer Dinwiddie once per team he played for in the season.
    rows = dbConnection.execute("SELECT firstName, lastName FROM player WHERE playerId = ?", (203915,)).fetchall()
    assert rows == [("Spencer", "Dinwiddie")]


def testSplitsAPositionIntoPrimaryAndSecondaryInTheOrderListed(dbConnection: sqlite3.Connection) -> None:
    loadPlayers(FixtureSource(), dbConnection, "2025-26")

    positions = dict(dbConnection.execute(
        "SELECT lastName, primaryPosition || ',' || IFNULL(secondaryPosition, 'NULL') FROM player WHERE playerId IN (?, ?, ?)",
        (2754, 77142, 101115),
    ).fetchall())
    # Tony Allen is listed 'G-F', Magic Johnson 'F-G' and Andrew Bynum 'C'.
    assert positions == {"Allen": "G,F", "Johnson": "F,G", "Bynum": "C,NULL"}


def testAPlayerWithNoPositionHasBothPositionsNull(dbConnection: sqlite3.Connection) -> None:
    loadPlayers(FixtureSource(), dbConnection, "2025-26")

    # Moe Becker has no position listed.
    positions = dbConnection.execute(
        "SELECT primaryPosition, secondaryPosition FROM player WHERE playerId = ?", (76137,),
    ).fetchone()
    assert positions == (None, None)


def testMissingDraftFieldsAreNullAndNeverUndrafted(dbConnection: sqlite3.Connection) -> None:
    loadPlayers(FixtureSource(), dbConnection, "2025-26")

    # John Abramovic has no draft fields; Paul Arizin was drafted in 1950 with no round or pick listed.
    abramovic = dbConnection.execute(
        "SELECT draftYear, draftRound, draftPick FROM player WHERE playerId = ?", (76007,),
    ).fetchone()
    arizin = dbConnection.execute(
        "SELECT draftYear, draftRound, draftPick FROM player WHERE playerId = ?", (76056,),
    ).fetchone()
    assert abramovic == (None, None, None)
    assert arizin == (1950, None, None)


def testMissingOrBlankHeightAndWeightAreNull(dbConnection: sqlite3.Connection) -> None:
    loadPlayers(FixtureSource(), dbConnection, "2025-26")

    # Moe Becker has neither; Ike Fontaine's weight is a blank space in the source.
    becker = dbConnection.execute("SELECT heightInches, weightPounds FROM player WHERE playerId = ?", (76137,)).fetchone()
    fontaine = dbConnection.execute("SELECT heightInches, weightPounds FROM player WHERE playerId = ?", (1829,)).fetchone()
    assert becker == (None, None)
    assert fontaine == (None, None)


def testNoCollegeIsNullAndARealCollegeIsKept(dbConnection: sqlite3.Connection) -> None:
    loadPlayers(FixtureSource(), dbConnection, "2025-26")

    # Andrew Bynum went from high school to the NBA; Magic Johnson played at Michigan State.
    colleges = dict(dbConnection.execute("SELECT lastName, college FROM player WHERE playerId IN (?, ?)", (101115, 77142)).fetchall())
    assert colleges == {"Bynum": None, "Johnson": "Michigan State"}


def testEveryPlayerOnAStoredStatLineHasAPlayerRow(dbConnection: sqlite3.Connection) -> None:
    ingestSeason(FixtureSource(), dbConnection, "1970-71")
    ingestSeason(FixtureSource(), dbConnection, "1990-91")
    loadPlayers(FixtureSource(), dbConnection, "2025-26")

    lineCount = dbConnection.execute("SELECT COUNT(*) FROM playerGame").fetchone()[0]
    withoutPlayer = dbConnection.execute(
        "SELECT COUNT(*) FROM playerGame WHERE playerId NOT IN (SELECT playerId FROM player)",
    ).fetchone()[0]
    assert lineCount == 82
    assert withoutPlayer == 0


def testALoadIsLoggedAndARerunLeavesTheRowsUnchanged(dbConnection: sqlite3.Connection) -> None:
    loadPlayers(FixtureSource(), dbConnection, "2025-26")
    loadPlayers(FixtureSource(), dbConnection, "2025-26")

    playerCount = dbConnection.execute("SELECT COUNT(*) FROM player").fetchone()[0]
    log = dbConnection.execute("SELECT kind, unitKey, status, rowCount FROM ingestLog").fetchall()
    assert playerCount == 90
    assert log == [("playerIndex", "all", "done", 90)]


def testRefreshReplacesTheStoredPlayers(dbConnection: sqlite3.Connection) -> None:
    loadPlayers(FixtureSource(), dbConnection, "2025-26")
    dbConnection.execute("UPDATE player SET lastName = 'Wrong' WHERE playerId = ?", (77142,))
    dbConnection.commit()

    loadPlayers(FixtureSource(), dbConnection, "2025-26", shouldRefresh=True)

    lastName = dbConnection.execute("SELECT lastName FROM player WHERE playerId = ?", (77142,)).fetchone()[0]
    assert lastName == "Johnson"
