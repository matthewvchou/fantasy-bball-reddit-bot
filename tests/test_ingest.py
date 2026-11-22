import sqlite3
from typing import Any

import pytest

from src.ingest.ingest import ingestSeason
from tests.fakesource import FixtureSource


class UnknownTypeSource(FixtureSource):
    """Serves the 2023-24 fixtures with one game ID changed to a prefix that is not a Game Type."""

    def fetchTeamGameLog(self, season: str, seasonType: str) -> dict[str, Any]:
        response = super().fetchTeamGameLog(season, seasonType)
        resultSet = response["resultSets"][0]
        gameIdColumn = resultSet["headers"].index("GAME_ID")
        for row in resultSet["rowSet"]:
            if row[gameIdColumn] == "0022300061":
                row[gameIdColumn] = "0092300061"
        return response


class NonNbaTeamSource(FixtureSource):
    """Serves the 1970-71 fixtures with one team in game 0027000005 changed to a non-NBA team ID."""

    def fetchTeamGameLog(self, season: str, seasonType: str) -> dict[str, Any]:
        response = super().fetchTeamGameLog(season, seasonType)
        if seasonType != "Regular Season":
            return response
        resultSet = response["resultSets"][0]
        gameIdColumn = resultSet["headers"].index("GAME_ID")
        teamIdColumn = resultSet["headers"].index("TEAM_ID")
        for row in resultSet["rowSet"]:
            if row[gameIdColumn] == "0027000005" and row[teamIdColumn] == 1610612765:
                row[teamIdColumn] = 12315
        return response


def testLoadsEveryPlayerStatLineFromTheSeason(dbConnection: sqlite3.Connection) -> None:
    ingestSeason(FixtureSource(), dbConnection, "1970-71")

    lineCount = dbConnection.execute("SELECT COUNT(*) FROM playerGame").fetchone()[0]
    assert lineCount == 65

    # Bob Lanier, Detroit at Seattle on 1970-10-14
    statLine = dbConnection.execute(
        "SELECT teamId, fgm, fga, ftm, fta, reb, ast, pf, pts "
        "FROM playerGame WHERE gameId = ? AND playerId = ?",
        ("0027000005", 600005),
    ).fetchone()
    assert statLine == (1610612765, 10, 18, 2, 5, 6, 1, 2, 22)


def testLoadsNoStatLinesFromTheGameLogFrom1996On(dbConnection: sqlite3.Connection) -> None:
    ingestSeason(FixtureSource(), dbConnection, "2023-24")

    # The per-game box score supplies these seasons, with exact seconds and Did Not Play rows.
    lineCount = dbConnection.execute("SELECT COUNT(*) FROM playerGame").fetchone()[0]
    gameCount = dbConnection.execute("SELECT COUNT(*) FROM game").fetchone()[0]
    assert (lineCount, gameCount) == (0, 6)


def testReadsHomeAndAwayTeamsAndScoresFromTheMatchup(dbConnection: sqlite3.Connection) -> None:
    ingestSeason(FixtureSource(), dbConnection, "2023-24")

    # New Orleans at Sacramento on 2024-01-07; the source lists the away team's row first.
    game = dbConnection.execute(
        "SELECT homeTeamId, awayTeamId, homeScore, awayScore FROM game WHERE gameId = ?",
        ("0022300500",),
    ).fetchone()
    assert game == (1610612758, 1610612740, 100, 133)


def testStoresDateSeasonStartYearAndGameType(dbConnection: sqlite3.Connection) -> None:
    ingestSeason(FixtureSource(), dbConnection, "2023-24")

    # A January 2024 game still belongs to the 2023 season.
    game = dbConnection.execute(
        "SELECT gameDate, season, gameType FROM game WHERE gameId = ?",
        ("0022300500",),
    ).fetchone()
    assert game == ("2024-01-07", 2023, "Regular Season")


def testStoresMinutesAsSecondsFromWholeMinutes(dbConnection: sqlite3.Connection) -> None:
    ingestSeason(FixtureSource(), dbConnection, "1970-71")

    # Bob Lanier played 26 minutes; the source gives no seconds.
    minutes = dbConnection.execute(
        "SELECT minutes FROM playerGame WHERE gameId = ? AND playerId = ?",
        ("0027000005", 600005),
    ).fetchone()[0]
    assert minutes == 1560


def testStoresStatsAnEraDidNotTrackAsNull(dbConnection: sqlite3.Connection) -> None:
    ingestSeason(FixtureSource(), dbConnection, "1970-71")

    # John Clemens, Seattle vs. Detroit on 1970-10-14: the NBA did not record threes,
    # offensive and defensive rebounds, steals, blocks, turnovers or plus-minus then.
    statLine = dbConnection.execute(
        "SELECT fg3m, fg3a, oreb, dreb, stl, blk, tov, plusMinus, pts, reb "
        "FROM playerGame WHERE gameId = ? AND playerId = ?",
        ("0027000005", 76403),
    ).fetchone()
    assert statLine == (None, None, None, None, None, None, None, None, 6, 5)


def testRejectsAGameWhoseTypeItDoesNotRecognize(dbConnection: sqlite3.Connection) -> None:
    with pytest.raises(ValueError, match="0092300061"):
        ingestSeason(UnknownTypeSource(), dbConnection, "2023-24")


def testLabelsEachGameTypeFromTheGameIdPrefix(dbConnection: sqlite3.Connection) -> None:
    ingestSeason(FixtureSource(), dbConnection, "2023-24")

    gameTypes = dict(dbConnection.execute(
        "SELECT gameId, gameType FROM game WHERE gameId IN (?, ?, ?, ?)",
        ("0012300001", "0022300061", "0042300101", "0052300101"),
    ).fetchall())
    assert gameTypes == {
        "0012300001": "Preseason", "0022300061": "Regular Season",
        "0042300101": "Postseason", "0052300101": "Postseason",
    }


def testFlagsOnlyPlayInGames(dbConnection: sqlite3.Connection) -> None:
    ingestSeason(FixtureSource(), dbConnection, "2023-24")

    flags = dict(dbConnection.execute(
        "SELECT gameId, isPlayIn FROM game WHERE gameType = 'Postseason'",
    ).fetchall())
    assert flags == {"0042300101": 0, "0052300101": 1}


def testLoadsPostseasonStatLinesFromBefore1996(dbConnection: sqlite3.Connection) -> None:
    ingestSeason(FixtureSource(), dbConnection, "1990-91")

    # Magic Johnson, Lakers vs. Rockets on 1991-04-25: 39 minutes, 17 points.
    statLine = dbConnection.execute(
        "SELECT minutes, pts, ast FROM playerGame WHERE gameId = ? AND playerId = ?",
        ("0049000005", 77142),
    ).fetchone()
    assert statLine == (2340, 17, 10)


def testSummerLeagueJulyGameBelongsToThatYearsSeason(dbConnection: sqlite3.Connection) -> None:
    ingestSeason(FixtureSource(), dbConnection, "2024-25")

    game = dbConnection.execute(
        "SELECT gameDate, season, gameType, isPlayIn FROM game WHERE gameId = ?",
        ("1522400006",),
    ).fetchone()
    assert game == ("2024-07-12", 2024, "Summer League", 0)


def testSkipsGamesAgainstNonNbaTeams(dbConnection: sqlite3.Connection) -> None:
    ingestSeason(FixtureSource(), dbConnection, "2023-24")

    # Dallas at Rakuten Monkeys (Taiwan) on 2023-10-10 is in the source but is not an NBA game.
    storedIds = [row[0] for row in dbConnection.execute("SELECT gameId FROM game WHERE gameType = 'Preseason'")]
    assert storedIds == ["0012300001"]


def testSkipsStatLinesOfGamesAgainstNonNbaTeams(dbConnection: sqlite3.Connection) -> None:
    ingestSeason(NonNbaTeamSource(), dbConnection, "1970-71")

    # Without a stored game, its stat lines would be orphans.
    lineCount = dbConnection.execute("SELECT COUNT(*) FROM playerGame WHERE gameId = ?", ("0027000005",)).fetchone()[0]
    assert lineCount == 0
