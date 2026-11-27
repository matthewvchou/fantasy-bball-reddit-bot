import json
from pathlib import Path
from typing import Any

FIXTURE_DIR = Path(__file__).parent / "fixtures"


class FixtureSource:
    """Serves recorded NBA API responses from the fixtures folder in place of the live API."""

    def fetchPlayerGameLog(self, season: str, seasonType: str) -> dict[str, Any]:
        """Return the recorded player-mode game log for the season and type, or an empty one."""
        return self.loadFixture("playerGameLog", season, seasonType)

    def fetchTeamGameLog(self, season: str, seasonType: str) -> dict[str, Any]:
        """Return the recorded team-mode game log for the season and type, or an empty one."""
        return self.loadFixture("teamGameLog", season, seasonType)

    def fetchFranchiseHistory(self) -> dict[str, Any]:
        """Return the recorded franchise history, both the current and the defunct teams."""
        with open(FIXTURE_DIR / "franchiseHistory.json") as file:
            return json.load(file)

    def loadFixture(self, name: str, season: str, seasonType: str) -> dict[str, Any]:
        """Read one recorded response; a season type with no recording gets an empty response like a season without such games."""
        path = FIXTURE_DIR / f"{name}_{season}_{seasonType.replace(' ', '')}.json"
        if not path.exists():
            return {"resultSets": [{"headers": [], "rowSet": []}]}
        with open(path) as file:
            return json.load(file)
