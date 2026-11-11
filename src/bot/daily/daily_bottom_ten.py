import sys
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv

from src.bot.daily.daily_top_ten import TABLE_HEADER, are_all_games_final, format_date, format_player_row, get_last_season, post
from src.scoring.player_scores import MIN_BASELINE_MINUTES, build_baseline, score_players
from src.scraping.last_season_stats import get_primary_positions, get_season_per_game_stats
from src.scraping.scraper import get_all_player_stats_for_date, process_player_stats


def build_report(players: pd.DataFrame, date_str: str, last_season: str) -> tuple[str, str]:
    """
    Build the post title and markdown body for the night's bottom 10 players.

    Args:
        players: Scored players sorted by NIGHT_SCORE ascending, already filtered by minutes
        date_str: Game date in 'YYYY-MM-DD' format
        last_season: Season the z-scores were measured against (e.g., '2025-26')

    Returns:
        Tuple of (title, body)
    """
    date = format_date(date_str)
    rows = "".join(format_player_row(str(rank), p) for rank, (_, p) in enumerate(players.iloc[:10].iterrows(), start=1))
    dishonorable_mentions = ", ".join(players.iloc[10:15]['PLAYER_NAME'])

    body = (
        f"Hello r/fantasybball! Here are the bottom 10 performing players for {date}!\n\n"
        f"{TABLE_HEADER}\n"
        "|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|\n"
        f"{rows}"
        "\n------------\n"
        f"*Dishonorable Mentions*: {dishonorable_mentions}\n\n"
        "# FAQ\n\n"
        "* **How are players ranked?**\n\n"
        f"Each player's line is compared to {last_season} per-game averages for their primary position "
        f"(G, F or C, using players who averaged {MIN_BASELINE_MINUTES}+ minutes). Each of the 9 categories becomes a z-score "
        "(FG% and FT% are weighted by attempts, turnovers count against). Z-scores are capped at ±10 and "
        f"summed into the Night Score. Only players with {MIN_BASELINE_MINUTES}+ minutes are ranked, "
        "so short bench stints don't fill the list.\n\n"
        "* **Why is [insert player] not ranked here? They had a terrible game!**\n\n"
        "It doesn't mean that this player didn't struggle, it just means that some players had a worse "
        "performance than them across the 9 categories.\n\n"
    )
    title = f"🧊🤢 Bottom 10 Player Discussion - {players.iloc[0]['PLAYER_NAME']} Night 🤮🧊 - {date}"
    return title, body


def main(date_str: str | None = None, is_real: bool = False) -> None:
    """
    Fetch a night's stats, score them against last season, and post the bottom 10.

    Posts to the test subreddit unless is_real is True. Does nothing if any game that night is not Final.
    Only players with at least MIN_BASELINE_MINUTES minutes are ranked.

    Args:
        date_str: Game date in 'YYYY-MM-DD' format. Defaults to yesterday.
        is_real: True to post to r/fantasybball instead of r/bballfanalyst.
    """
    load_dotenv()
    date_str = date_str or (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    if not are_all_games_final(date_str):
        print(f"Not all games are Final (or none played) on {date_str}. Not posting.")
        return

    last_season, last_start_year = get_last_season(date_str)
    night_stats = process_player_stats(get_all_player_stats_for_date(date_str))

    positions = get_primary_positions([last_start_year, last_start_year + 1])
    means, stds = build_baseline(get_season_per_game_stats(last_season), positions)
    players = score_players(night_stats, positions, means, stds)
    players = players[players['MINUTES'] >= MIN_BASELINE_MINUTES].sort_values('NIGHT_SCORE').reset_index(drop=True)

    title, body = build_report(players, date_str, last_season)
    print(title)
    print(body)
    post(title, body, is_real)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
