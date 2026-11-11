import time

import pandas as pd
from nba_api.stats.endpoints import leaguedashplayerstats, playerindex


def get_season_per_game_stats(season: str) -> pd.DataFrame:
    """
    Get every player's per-game averages for one season.

    Args:
        season: Season in 'YYYY-YY' format (e.g., '2025-26')

    Returns:
        DataFrame with one row per player (PLAYER_ID, MIN, PTS, REB, FGA, FG_PCT, etc.)
    """
    stats = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        per_mode_detailed='PerGame',
        timeout=60
    )
    time.sleep(1)
    return stats.get_data_frames()[0]


def get_primary_positions(start_years: list[int]) -> dict[int, str]:
    """
    Get each player's primary position (G, F or C) from the NBA player index.

    The NBA lists positions like 'G-F'. The first letter is the primary position.
    Later years in start_years win when a player appears in more than one.

    Args:
        start_years: Season start years to read rosters from (e.g., [2025, 2026])

    Returns:
        Dict mapping PLAYER_ID to 'G', 'F' or 'C'. Players with no listed position are omitted.
    """
    positions = {}
    for year in start_years:
        index = playerindex.PlayerIndex(season=str(year), timeout=60).get_data_frames()[0]
        time.sleep(1)
        listed = index.dropna(subset=['POSITION'])
        positions.update(dict(zip(listed['PERSON_ID'], listed['POSITION'].str[0])))
    return positions
