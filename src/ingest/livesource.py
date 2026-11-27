"""The live NBA API source: paced calls, retries with backoff, and a file copy of every response."""

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import requests
from nba_api.stats.library.http import NBAStatsHTTP

MIN_SECONDS_BETWEEN_CALLS = 1.0
BACKOFF_BASE_SECONDS = 2
MAX_CONSECUTIVE_FAILURES = 5
REQUEST_TIMEOUT_SECONDS = 30
FAILED_FOLDER = "failed"

# Takes the API endpoint name and its parameters and returns the raw response text.
FetchText = Callable[[str, dict[str, str]], str]


class RetryableFetchError(Exception):
    """A fetch failed in a way worth retrying after a wait: a timeout, rate limit or dropped connection."""


class UnparseableResponseError(Exception):
    """A response was not a game log: it was not valid JSON, or it had no result sets."""


class TooManyFailuresError(Exception):
    """Too many fetch attempts failed in a row, so the run stops instead of hammering the API."""


def fetchNbaApiText(endpoint: str, params: dict[str, str]) -> str:
    """
    Fetch one stats.nba.com response and return its raw text.

    Raises:
        RetryableFetchError: The request timed out or the connection failed.
    """
    try:
        return NBAStatsHTTP().send_api_request(endpoint=endpoint, parameters=params, timeout=REQUEST_TIMEOUT_SECONDS).get_response()
    except requests.RequestException as error:
        raise RetryableFetchError(str(error)) from error


class LiveNbaSource:
    """
    Gets NBA API responses one call at a time, at a polite pace.

    Calls are spaced at least a second apart. The fetch, clock and sleep are passed in so that
    tests can replace them and never wait or touch the network.
    """

    def __init__(
        self,
        fetchText: FetchText,
        payloadDir: Path,
        getTime: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.fetchText = fetchText
        self.payloadDir = payloadDir
        self.getTime = getTime
        self.sleep = sleep
        self.lastCallTime: float | None = None
        self.consecutiveFailures = 0

    def fetchTeamGameLog(self, season: str, seasonType: str) -> dict[str, Any]:
        """Return the season game log with one row per team per game."""
        return self.fetchGameLog("T", "teamGameLog", season, seasonType)

    def fetchPlayerGameLog(self, season: str, seasonType: str) -> dict[str, Any]:
        """Return the season game log with one row per player per game."""
        return self.fetchGameLog("P", "playerGameLog", season, seasonType)

    def fetchFranchiseHistory(self) -> dict[str, Any]:
        """Return the franchise history: every team with its past names, current and defunct teams in separate frames."""
        return self.fetchJson("franchisehistory", {"LeagueID": "00"}, "franchiseHistory", "all")

    def fetchGameLog(self, mode: str, folder: str, season: str, seasonType: str) -> dict[str, Any]:
        """
        Fetch one season game log.

        Args:
            mode: 'T' for one row per team, 'P' for one row per player.
            folder: The payloads subfolder the response is saved in.
            season: Season label such as '2023-24'.
            seasonType: One of the source season types; Summer League is league 15 under 'Regular Season'.
        """
        leagueId, apiSeasonType = ("15", "Regular Season") if seasonType == "Summer League" else ("00", seasonType)
        params = {
            "Counter": "0", "DateFrom": "", "DateTo": "", "Direction": "ASC", "LeagueID": leagueId,
            "PlayerOrTeam": mode, "Season": season, "SeasonType": apiSeasonType, "Sorter": "DATE",
        }
        return self.fetchJson("leaguegamelog", params, folder, f"{season}_{seasonType.replace(' ', '')}")

    def fetchJson(self, endpoint: str, params: dict[str, str], folder: str, name: str) -> dict[str, Any]:
        """
        Fetch one response, keep its raw text as payloads/<folder>/<name>.json, and return it parsed.

        A timeout, rate limit or unparseable response is retried after a growing wait (2, 4, 8, then 16 seconds).
        An unparseable response is kept under payloads/failed/ and never replaces a good payload.

        Raises:
            TooManyFailuresError: The fifth failed attempt in a row, counted across calls.
        """
        attempt = 0
        while True:
            attempt += 1
            try:
                return self.fetchOnce(endpoint, params, folder, name)
            except (RetryableFetchError, UnparseableResponseError):
                self.recordFailure()
                self.sleep(BACKOFF_BASE_SECONDS ** attempt)
            except Exception:
                # Nothing a retry would fix, but it still counts toward stopping the run.
                self.recordFailure()
                raise

    def fetchOnce(self, endpoint: str, params: dict[str, str], folder: str, name: str) -> dict[str, Any]:
        """Make one paced attempt, saving the response whether or not it parses."""
        self.waitForTurn()
        text = self.fetchText(endpoint, params)
        failedPath = self.payloadDir / FAILED_FOLDER / folder / f"{name}.json"
        try:
            parsed = json.loads(text)
            # Rate-limit and error replies can be valid JSON, so a game log is told by its result sets.
            if not isinstance(parsed, dict) or "resultSets" not in parsed:
                raise ValueError("response has no result sets")
        except ValueError as error:
            self.savePayload(failedPath, text)
            raise UnparseableResponseError(str(error)) from error
        self.savePayload(self.payloadDir / folder / f"{name}.json", text)
        failedPath.unlink(missing_ok=True)
        self.consecutiveFailures = 0
        return parsed

    def savePayload(self, path: Path, text: str) -> None:
        """Write a raw response to the path, replacing any earlier copy."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def recordFailure(self) -> None:
        """Count a failed attempt and stop the run when too many came in a row."""
        self.consecutiveFailures += 1
        if self.consecutiveFailures >= MAX_CONSECUTIVE_FAILURES:
            raise TooManyFailuresError(f"{self.consecutiveFailures} failed attempts in a row")

    def waitForTurn(self) -> None:
        """Sleep until a second has passed since the last call started."""
        if self.lastCallTime is not None:
            wait = self.lastCallTime + MIN_SECONDS_BETWEEN_CALLS - self.getTime()
            if wait > 0:
                self.sleep(wait)
        self.lastCallTime = self.getTime()
