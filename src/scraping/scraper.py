from nba_api.stats.endpoints import leaguegamefinder, scoreboardv2, boxscoretraditionalv3
import pandas as pd
from datetime import datetime, timedelta
import time

NBA_TEAMS = {'ATL', 'CHA', 'CHI',
            'CLE', 'DAL', 'SAS',
            'DEN', 'DET', 'GSW',
            'HOU', 'IND', 'LAC',
            'LAL', 'MEM', 'MIA',
            'MIL', 'MIN', 'NOP',
            'NYK', 'BKN', 'BOS',
            'OKC', 'ORL', 'PHI',
            'PHX', 'POR', 'SAC',
            'TOR', 'UTA', 'WAS'}


def get_games_for_date(date_str: str):
    """
    Get all NBA games for a specific date involving teams in NBA_TEAMS.

    Args:
        date_str: Date in 'YYYY-MM-DD' format (e.g., '2024-01-15')

    Returns:
        Array of game IDs for games involving NBA_TEAMS
    """
    # LeagueGameFinder to get games
    gamefinder = leaguegamefinder.LeagueGameFinder(
        date_from_nullable=date_str,
        date_to_nullable=date_str
    )

    games = gamefinder.get_data_frames()[0]
    time.sleep(1)

    if games.empty:
        print(f"No games found for {date_str}")
        return []

    # Filter to only games involving teams in NBA_TEAMS
    games_filtered = games[games['TEAM_ABBREVIATION'].isin(NBA_TEAMS)]

    if games_filtered.empty:
        print(f"No games found for tracked teams on {date_str}")
        return []

    # Get unique game IDs (each game appears twice, once for each team)
    game_ids = games_filtered['GAME_ID'].unique()

    return game_ids


def get_player_stats_for_game(game_id: str):
    """
    Get player statistics for a specific game.

    Args:
        game_id: NBA game ID

    Returns:
        DataFrame with player stats from the game
    """
    boxscore = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id)
    raw = boxscore.get_dict()
    game = raw['boxScoreTraditional']

    rows = []
    for team_key in ('homeTeam', 'awayTeam'):
        team = game[team_key]
        team_abbr = team['teamTricode']
        for player in team['players']:
            s = player['statistics']
            if not s['minutes'] or s['minutes'] == '0:00':
                continue
            rows.append({
                'PLAYER_NAME': f"{player['firstName']} {player['familyName']}",
                'TEAM_ABBREVIATION': team_abbr,
                'MIN': s['minutes'],
                'PTS': s['points'],
                'FGM': s['fieldGoalsMade'],
                'FGA': s['fieldGoalsAttempted'],
                'FG_PCT': s['fieldGoalsPercentage'],
                'FG3M': s['threePointersMade'],
                'FG3A': s['threePointersAttempted'],
                'FG3_PCT': s['threePointersPercentage'],
                'FTM': s['freeThrowsMade'],
                'FTA': s['freeThrowsAttempted'],
                'FT_PCT': s['freeThrowsPercentage'],
                'REB': s['reboundsTotal'],
                'AST': s['assists'],
                'STL': s['steals'],
                'BLK': s['blocks'],
                'TO': s['turnovers'],
                'PF': s['foulsPersonal'],
            })

    return pd.DataFrame(rows)


def get_all_player_stats_for_date(date_str: str):
    """
    Get all player statistics for all games on a specific date.

    Args:
        date_str: Date in 'YYYY-MM-DD' format (e.g., '2024-01-15')

    Returns:
        DataFrame with all player stats from that day
    """
    print(f"Fetching games for {date_str}...")
    game_ids = get_games_for_date(date_str)

    if len(game_ids) == 0:
        return pd.DataFrame()

    print(f"Found {len(game_ids)} games. Fetching player stats...")

    all_player_stats = []

    scoreboard = scoreboardv2.ScoreboardV2(game_date=date_str)
    scoreboard_df = scoreboard.get_data_frames()[0]

    for i, game_id in enumerate(game_ids, 1):
        print(f"Fetching game {i}/{len(game_ids)}: {game_id}")
        status_rows = scoreboard_df[scoreboard_df['GAME_ID'] == game_id]['GAME_STATUS_TEXT'].values
        if len(status_rows) > 0:
            print(f"Game Status: {status_rows[0]}")
        player_stats = get_player_stats_for_game(game_id)
        all_player_stats.append(player_stats)
        time.sleep(1)

    # Combine all player stats into one DataFrame
    combined_stats = pd.concat(all_player_stats, ignore_index=True)

    return combined_stats


def process_player_stats(df):
    """
    Process and clean player stats DataFrame.

    Args:
        df: Raw player stats DataFrame

    Returns:
        Processed DataFrame with relevant columns
    """
    if df.empty:
        return df

    # Select and rename relevant columns
    processed = df[[
        'PLAYER_NAME',
        'TEAM_ABBREVIATION',
        'MIN',
        'PTS',
        'FGM',
        'FGA',
        'FG_PCT',
        'FG3M',
        'FG3A',
        'FG3_PCT',
        'FTM',
        'FTA',
        'FT_PCT',
        'REB',
        'AST',
        'STL',
        'BLK',
        'TO',
        'PF',
    ]].copy()

    # Filter out players who didn't play (MIN is None or '0:00')
    processed = processed[processed['MIN'].notna()]
    processed = processed[~processed['MIN'].isin(['', '0:00'])]

    # Convert minutes to float (from 'MM:SS' format)
    processed['MINUTES'] = processed['MIN'].apply(convert_minutes_to_float)
    processed = processed.drop(columns=['MIN'])

    # Sort by points scored
    processed = processed.sort_values(by='PTS', ascending=False)

    return processed


def convert_minutes_to_float(min_str):
    """
    Convert minutes from 'MM:SS' format to float.
    """
    if pd.isna(min_str) or not min_str or min_str == '0:00':
        return 0.0
    try:
        parts = str(min_str).split(':')
        minutes = int(parts[0])
        seconds = int(parts[1]) if len(parts) > 1 else 0
        return minutes + (seconds / 60.0)
    except:
        return 0.0


def save_stats_to_file(df, date_str: str):
    """
    Save stats to a text file.

    Args:
        df: DataFrame with player stats
        date_str: Date string for filename
    """
    filename = f'nba_stats_{date_str}.txt'

    with open(filename, 'w') as f:
        f.write(f"NBA Player Stats for {date_str}\n")
        f.write("=" * 100 + "\n\n")
        f.write(df.to_string(index=False))
        f.write("\n")

    print(f"\nStats saved to {filename}")


def main():
    """
    Main execution function.
    """
    # Get yesterday's date (or specify your own date)
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    # Or specify a specific date
    date_to_fetch = yesterday

    print(f"Fetching NBA stats for {date_to_fetch}...\n")

    # Fetch all player stats for the date
    raw_stats = get_all_player_stats_for_date(date_to_fetch)

    if raw_stats.empty:
        print("No stats found.")
        return

    # Process the stats
    processed_stats = process_player_stats(raw_stats)

    # Display top 20 performers
    print("\n" + "=" * 100)
    print("Top 20 Performers:")
    print("=" * 100)
    print(processed_stats.head(20).to_string(index=False))

    # Save to file
    save_stats_to_file(processed_stats, date_to_fetch)


if __name__ == '__main__':
    main()
