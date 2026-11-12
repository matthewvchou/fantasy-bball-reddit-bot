import json
from pathlib import Path
from typing import Any

FIXTURE_DIR = Path(__file__).parent / "fixtures"
RECORDED_SEASON_TYPE = "Regular Season"


class FixtureSource:
    """Serves recorded NBA API responses from the fixtures folder in place of the live API."""

    def fetchPlayerGameLog(self, season: str, seasonType: str) -> dict[str, Any]:
        """Return the recorded player-mode game log for the season."""
        return self.loadFixture("playerGameLog", season, seasonType)

    def fetchTeamGameLog(self, season: str, seasonType: str) -> dict[str, Any]:
        """Return the recorded team-mode game log for the season."""
        return self.loadFixture("teamGameLog", season, seasonType)

    def loadFixture(self, name: str, season: str, seasonType: str) -> dict[str, Any]:
        """Read one recorded response from the fixtures folder; raises LookupError for an unrecorded season type."""
        # Fixtures are Regular Season only; failing loudly avoids a test passing on the wrong data.
        if seasonType != RECORDED_SEASON_TYPE:
            raise LookupError(f"No recorded {seasonType} fixture")
        with open(FIXTURE_DIR / f"{name}_{season}.json") as file:
            return json.load(file)
