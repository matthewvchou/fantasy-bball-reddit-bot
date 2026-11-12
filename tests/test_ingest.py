import sqlite3
from typing import Any

import pytest

from src.ingest.ingest import ingestSeason
from tests.fakesource import FixtureSource


class PreseasonLabelledSource(FixtureSource):
    """Serves the 2023-24 fixtures with one game ID changed to a Preseason (001) prefix."""

    def fetchTeamGameLog(self, season: str, seasonType: str) -> dict[str, Any]:
        response = super().fetchTeamGameLog(season, seasonType)
        resultSet = response["resultSets"][0]
        gameIdColumn = resultSet["headers"].index("GAME_ID")
        for row in resultSet["rowSet"]:
            if row[gameIdColumn] == "0022300061":
                row[gameIdColumn] = "0012300061"
        return response


def testLoadsEveryPlayerStatLineFromTheSeason(dbConnection: sqlite3.Connection) -> None:
    ingestSeason(FixtureSource(), dbConnection, "2023-24")

    lineCount = dbConnection.execute("SELECT COUNT(*) FROM playerGame").fetchone()[0]
    assert lineCount == 69

    # Reggie Jackson, Denver vs. the Lakers on 2023-10-24
    statLine = dbConnection.execute(
        "SELECT teamId, fgm, fga, fg3m, fg3a, ftm, fta, oreb, dreb, reb, ast, stl, blk, tov, pf, pts, plusMinus "
        "FROM playerGame WHERE gameId = ? AND playerId = ?",
        ("0022300061", 202704),
    ).fetchone()
    assert statLine == (1610612743, 3, 8, 2, 5, 0, 0, 0, 3, 3, 1, 1, 0, 2, 0, 8, 11)


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
    ingestSeason(FixtureSource(), dbConnection, "2023-24")

    # Reggie Jackson played 24 minutes; the source gives no seconds.
    minutes = dbConnection.execute(
        "SELECT minutes FROM playerGame WHERE gameId = ? AND playerId = ?",
        ("0022300061", 202704),
    ).fetchone()[0]
    assert minutes == 1440


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
    with pytest.raises(ValueError, match="0012300061"):
        ingestSeason(PreseasonLabelledSource(), dbConnection, "2023-24")
