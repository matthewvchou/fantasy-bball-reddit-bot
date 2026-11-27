import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path

import pytest

from src.ingest.ingest import ingestSeason
from src.ingest.livesource import LiveNbaSource, RetryableFetchError, TooManyFailuresError

RESPONSE_TEXT = json.dumps({"resultSets": [{"headers": ["GAME_ID"], "rowSet": [["0022300061"]]}]})


class FakeClock:
    """A clock that only moves when the code under test sleeps, so tests never wait."""

    def __init__(self) -> None:
        self.seconds = 0.0

    def getTime(self) -> float:
        return self.seconds

    def sleep(self, seconds: float) -> None:
        self.seconds += seconds


class ScriptedTransport:
    """Stands in for the NBA API: plays back one scripted outcome per call and notes when each call happened."""

    def __init__(self, clock: FakeClock, outcomes: Sequence[str | Exception]) -> None:
        self.clock = clock
        self.outcomes = outcomes
        self.callTimes: list[float] = []

    def __call__(self, endpoint: str, params: dict[str, str]) -> str:
        self.callTimes.append(self.clock.getTime())
        outcome = self.outcomes[len(self.callTimes) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def makeSource(clock: FakeClock, transport: ScriptedTransport, payloadDir: Path) -> LiveNbaSource:
    return LiveNbaSource(transport, payloadDir, getTime=clock.getTime, sleep=clock.sleep)


def testSpacesCallsOneSecondApart(tmp_path: Path) -> None:
    clock = FakeClock()
    transport = ScriptedTransport(clock, [RESPONSE_TEXT, RESPONSE_TEXT])
    source = makeSource(clock, transport, tmp_path)

    source.fetchTeamGameLog("2023-24", "Playoffs")
    source.fetchTeamGameLog("2023-24", "PlayIn")

    assert transport.callTimes == [0.0, 1.0]


def testSavesEachResponseAsAFileAndARefetchOverwritesIt(tmp_path: Path) -> None:
    clock = FakeClock()
    newerText = json.dumps({"resultSets": [{"headers": ["GAME_ID"], "rowSet": []}]})
    transport = ScriptedTransport(clock, [RESPONSE_TEXT, newerText])
    source = makeSource(clock, transport, tmp_path)

    source.fetchTeamGameLog("2023-24", "Playoffs")
    savedAfterFirstFetch = (tmp_path / "teamGameLog" / "2023-24_Playoffs.json").read_text()
    source.fetchTeamGameLog("2023-24", "Playoffs")

    assert savedAfterFirstFetch == RESPONSE_TEXT
    assert (tmp_path / "teamGameLog" / "2023-24_Playoffs.json").read_text() == newerText
    assert [path.name for path in (tmp_path / "teamGameLog").iterdir()] == ["2023-24_Playoffs.json"]


def testSavesPlayerAndTeamLogsInTheirOwnFolders(tmp_path: Path) -> None:
    clock = FakeClock()
    source = makeSource(clock, ScriptedTransport(clock, [RESPONSE_TEXT, RESPONSE_TEXT]), tmp_path)

    source.fetchPlayerGameLog("2024-25", "Summer League")
    source.fetchTeamGameLog("2024-25", "Pre Season")

    assert (tmp_path / "playerGameLog" / "2024-25_SummerLeague.json").exists()
    assert (tmp_path / "teamGameLog" / "2024-25_PreSeason.json").exists()


def testRetriesATimeoutAfterAGrowingBackoff(tmp_path: Path) -> None:
    clock = FakeClock()
    timeout = RetryableFetchError("timed out")
    transport = ScriptedTransport(clock, [timeout, timeout, RESPONSE_TEXT])
    source = makeSource(clock, transport, tmp_path)

    response = source.fetchTeamGameLog("2023-24", "Playoffs")

    assert response["resultSets"][0]["rowSet"] == [["0022300061"]]
    # Waits of 2 and then 4 seconds between the attempts.
    assert transport.callTimes == [0.0, 2.0, 6.0]


def testSavesAnUnparseableResponseSeparatelyAndKeepsTheLastGoodOne(tmp_path: Path) -> None:
    clock = FakeClock()
    notJson = "<html>Rate limited</html>"
    transport = ScriptedTransport(clock, [RESPONSE_TEXT] + [notJson] * 5)
    source = makeSource(clock, transport, tmp_path)
    source.fetchTeamGameLog("2023-24", "Playoffs")

    with pytest.raises(TooManyFailuresError):
        source.fetchTeamGameLog("2023-24", "Playoffs")

    assert (tmp_path / "failed" / "teamGameLog" / "2023-24_Playoffs.json").read_text() == notJson
    assert (tmp_path / "teamGameLog" / "2023-24_Playoffs.json").read_text() == RESPONSE_TEXT


def testRemovesTheFailedFileOnceTheCallSucceeds(tmp_path: Path) -> None:
    clock = FakeClock()
    transport = ScriptedTransport(clock, ["<html>Rate limited</html>", RESPONSE_TEXT])
    source = makeSource(clock, transport, tmp_path)

    source.fetchTeamGameLog("2023-24", "Playoffs")

    assert not (tmp_path / "failed" / "teamGameLog" / "2023-24_Playoffs.json").exists()


def testStopsAfterFiveConsecutiveFailures(tmp_path: Path) -> None:
    clock = FakeClock()
    outcomes: list[str | Exception] = [RetryableFetchError("timed out")] * 6
    transport = ScriptedTransport(clock, outcomes)
    source = makeSource(clock, transport, tmp_path)

    with pytest.raises(TooManyFailuresError):
        source.fetchTeamGameLog("2023-24", "Playoffs")

    assert len(transport.callTimes) == 5


def testAFailedAttemptDoesNotCountOnceACallSucceeds(tmp_path: Path) -> None:
    clock = FakeClock()
    timeout = RetryableFetchError("timed out")
    outcomes: list[str | Exception] = [timeout, timeout, timeout, RESPONSE_TEXT, timeout, timeout, timeout, RESPONSE_TEXT]
    source = makeSource(clock, ScriptedTransport(clock, outcomes), tmp_path)

    # Six failures in all, but never five in a row.
    source.fetchTeamGameLog("2023-24", "Playoffs")
    source.fetchTeamGameLog("2023-24", "PlayIn")


def testAnErrorThatIsNotRetryableFailsTheCallAtOnce(tmp_path: Path) -> None:
    clock = FakeClock()
    transport = ScriptedTransport(clock, [ValueError("bad request"), RESPONSE_TEXT])
    source = makeSource(clock, transport, tmp_path)

    with pytest.raises(ValueError, match="bad request"):
        source.fetchTeamGameLog("2023-24", "Playoffs")

    assert len(transport.callTimes) == 1


def testTheIngestLogShowsWhereARunStopped(tmp_path: Path, dbConnection: sqlite3.Connection) -> None:
    clock = FakeClock()
    outcomes: list[str | Exception] = [RetryableFetchError("timed out")] * 5
    source = makeSource(clock, ScriptedTransport(clock, outcomes), tmp_path)

    with pytest.raises(TooManyFailuresError):
        ingestSeason(source, dbConnection, "2023-24")

    statuses = dict(dbConnection.execute("SELECT unitKey, status FROM ingestLog").fetchall())
    assert statuses == {"2023-24/Pre Season": "error"}


@pytest.mark.parametrize("notAGameLog", ["[]", "null", '{"message": "Too many requests"}'])
def testTreatsValidJsonThatIsNotAGameLogAsAFailure(tmp_path: Path, notAGameLog: str) -> None:
    clock = FakeClock()
    outcomes: list[str | Exception] = [RESPONSE_TEXT, *([notAGameLog] * 5)]
    source = makeSource(clock, ScriptedTransport(clock, outcomes), tmp_path)
    source.fetchTeamGameLog("2023-24", "Playoffs")

    with pytest.raises(TooManyFailuresError):
        source.fetchTeamGameLog("2023-24", "Playoffs")

    # The odd response is kept for debugging, and the last good payload is untouched.
    assert (tmp_path / "failed" / "teamGameLog" / "2023-24_Playoffs.json").read_text() == notAGameLog
    assert (tmp_path / "teamGameLog" / "2023-24_Playoffs.json").read_text() == RESPONSE_TEXT


def testFetchesFranchiseHistoryAndSavesItsPayload(tmp_path: Path) -> None:
    clock = FakeClock()
    franchiseText = json.dumps({"resultSets": [{"name": "FranchiseHistory", "headers": ["TEAM_ID"], "rowSet": [[1610612760]]}]})
    source = makeSource(clock, ScriptedTransport(clock, [franchiseText]), tmp_path)

    response = source.fetchFranchiseHistory()

    assert response["resultSets"][0]["rowSet"] == [[1610612760]]
    assert (tmp_path / "franchiseHistory" / "all.json").read_text() == franchiseText


def testFetchesThePlayerIndexAndSavesItsPayload(tmp_path: Path) -> None:
    clock = FakeClock()
    indexText = json.dumps({"resultSets": [{"name": "PlayerIndex", "headers": ["PERSON_ID"], "rowSet": [[77142]]}]})
    source = makeSource(clock, ScriptedTransport(clock, [indexText]), tmp_path)

    response = source.fetchPlayerIndex("2025-26")

    assert response["resultSets"][0]["rowSet"] == [[77142]]
    assert (tmp_path / "playerIndex" / "2025-26.json").read_text() == indexText
