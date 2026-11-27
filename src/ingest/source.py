from typing import Any, Protocol


class NbaSource(Protocol):
    """Where the ingest gets NBA API responses: the live API, or recorded fixtures in tests."""

    def fetchPlayerGameLog(self, season: str, seasonType: str) -> dict[str, Any]:
        """
        Return the raw season game log response with one row per player per game.

        seasonType is one of 'Pre Season', 'Regular Season', 'Playoffs', 'PlayIn' or 'Summer League'.
        The live API has no Summer League season type; a live source asks league 15 for 'Regular Season'.
        """
        ...

    def fetchTeamGameLog(self, season: str, seasonType: str) -> dict[str, Any]:
        """Return the raw season game log response with one row per team per game; seasonType as for fetchPlayerGameLog."""
        ...

    def fetchFranchiseHistory(self) -> dict[str, Any]:
        """Return the raw franchise history response: a frame of current teams and one of defunct teams."""
        ...

    def fetchPlayerIndex(self, season: str) -> dict[str, Any]:
        """
        Return the raw all-time player index, one row per player.

        The season label does not change which players are listed, but a player who was traded
        that season appears once per team.
        """
        ...
