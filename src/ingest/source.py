from typing import Any, Protocol


class NbaSource(Protocol):
    """Where the ingest gets NBA API responses: the live API, or recorded fixtures in tests."""

    def fetchPlayerGameLog(self, season: str, seasonType: str) -> dict[str, Any]:
        """Return the raw season game log response with one row per player per game."""
        ...

    def fetchTeamGameLog(self, season: str, seasonType: str) -> dict[str, Any]:
        """Return the raw season game log response with one row per team per game."""
        ...
