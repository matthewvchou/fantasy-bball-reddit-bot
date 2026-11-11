import os
import sys
from datetime import datetime, timedelta

import pandas as pd
import praw
from dotenv import load_dotenv
from nba_api.stats.endpoints import leaguegamefinder, scoreboardv3

from src.scoring.player_scores import MIN_BASELINE_MINUTES, build_baseline, score_players
from src.scraping.last_season_stats import get_primary_positions, get_season_per_game_stats
from src.scraping.scraper import get_all_player_stats_for_date, process_player_stats

# Position z-score cutoffs, strongest first. Applied to every category, so hot and bad stats count equally.
HOT_EMOJI_THRESHOLDS = [(10.0, '🚀🚀'), (9.0, '🚀🔥'), (6.0, '🔥🔥'), (3.0, '🔥')]
BAD_EMOJI_THRESHOLDS = [(-10.0, '💩💩'), (-9.0, '💩🧊'), (-6.0, '🧊🧊'), (-3.0, '🧊')]

# Turnover z-scores rarely reach the cutoffs, so they are scaled up to trigger emojis sooner.
TOV_SENSITIVITY = 2.0

STAT_COLUMN_WIDTH = 10
STAT_COLUMNS = ['Time', 'FG', 'FT', '3PT', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'PTS']
# FG and FT cells are the longest ("16-29🚀🚀"), so they get extra room.
EXTRA_COLUMN_WIDTH = {'FG': 8, 'FT': 8}


def pad_header(label: str) -> str:
    # Non-breaking spaces widen the column so emoji rows don't wrap. Plain spaces would be collapsed by markdown.
    return label + '&nbsp;' * (STAT_COLUMN_WIDTH + EXTRA_COLUMN_WIDTH.get(label, 0) - len(label))


TABLE_HEADER = (
    "|Rank|Player|Pos|" + "|".join(pad_header(label) for label in STAT_COLUMNS) + "|Night Score|ESPN Score|"
)


def get_last_season(date_str: str) -> tuple[str, int]:
    """
    Get the season before the one a date falls in.

    Args:
        date_str: Date in 'YYYY-MM-DD' format

    Returns:
        Tuple of (season string like '2025-26', its start year like 2025)
    """
    date = datetime.strptime(date_str, '%Y-%m-%d')
    current_start_year = date.year if date.month >= 8 else date.year - 1
    last_start_year = current_start_year - 1
    return f"{last_start_year}-{str(last_start_year + 1)[-2:]}", last_start_year


def are_all_games_final(date_str: str) -> bool:
    """
    Check that the date has games and every scheduled game has a result.

    Compares the scoreboard schedule to LeagueGameFinder results, because ScoreboardV3's
    status column stays stale on live nights.
    """
    scheduled = scoreboardv3.ScoreboardV3(game_date=date_str, timeout=60).game_header.get_data_frame()['gameId']
    if scheduled.empty:
        return False

    results = leaguegamefinder.LeagueGameFinder(
        date_from_nullable=date_str,
        date_to_nullable=date_str,
        timeout=60
    ).get_data_frames()[0]
    finished = results[results['WL'].notna()]['GAME_ID']
    return set(scheduled) <= set(finished)


def format_date(date_str: str) -> str:
    """
    Format 'YYYY-MM-DD' as 'January 5th, 2026'.
    """
    date = datetime.strptime(date_str, '%Y-%m-%d')
    if 11 <= date.day <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(date.day % 10, 'th')
    return date.strftime(f"%B {date.day}{suffix}, %Y")


def get_emoji(z_score: float, can_be_bad: bool = True) -> str:
    """
    Get the hot or bad emoji for a category z-score with a leading space, or '' if it is within +-3.

    Args:
        z_score: Category z-score against the position baseline
        can_be_bad: False for low-count stats (3PM, STL, BLK), where zero is normal and not a bad night
    """
    for threshold, emoji in HOT_EMOJI_THRESHOLDS:
        if z_score >= threshold:
            return f" {emoji}"
    if not can_be_bad:
        return ''
    for threshold, emoji in BAD_EMOJI_THRESHOLDS:
        if z_score <= threshold:
            return f" {emoji}"
    return ''


def format_player_row(rank_label: str, player) -> str:
    cells = [
        rank_label,
        player['PLAYER_NAME'],
        player['POSITION'],
        f"{player['MINUTES']:.0f} mins",
        f"{player['FGM']}-{player['FGA']}{get_emoji(player['Z_FG_IMPACT'])}",
        f"{player['FTM']}-{player['FTA']}{get_emoji(player['Z_FT_IMPACT'])}",
        f"{player['FG3M']}{get_emoji(player['Z_FG3M'], can_be_bad=False)}",
        f"{player['REB']}{get_emoji(player['Z_REB'])}",
        f"{player['AST']}{get_emoji(player['Z_AST'])}",
        f"{player['STL']}{get_emoji(player['Z_STL'], can_be_bad=False)}",
        f"{player['BLK']}{get_emoji(player['Z_BLK'], can_be_bad=False)}",
        f"{player['TO']}{get_emoji(player['Z_TOV'] * TOV_SENSITIVITY)}",
        f"{player['PTS']}{get_emoji(player['Z_PTS'])}",
        f"{player['NIGHT_SCORE']:.1f}",
        f"{player['ESPN_SCORE']:.0f}",
    ]
    return "|" + "|".join(str(cell) for cell in cells) + "|\n"


def build_report(players: pd.DataFrame, date_str: str, last_season: str) -> tuple[str, str]:
    """
    Build the post title and markdown body for the night's top 10 players.

    Args:
        players: Scored players sorted by NIGHT_SCORE descending
        date_str: Game date in 'YYYY-MM-DD' format
        last_season: Season the z-scores were measured against (e.g., '2025-26')

    Returns:
        Tuple of (title, body)
    """
    date = format_date(date_str)
    rows = "".join(format_player_row(str(rank), p) for rank, (_, p) in enumerate(players.iloc[:10].iterrows(), start=1))
    honorable_mentions = ", ".join(players.iloc[10:15]['PLAYER_NAME'])

    body = (
        f"Hello r/fantasybball! Here are the top 10 performing players for {date}!\n\n"
        f"{TABLE_HEADER}\n"
        "|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|\n"
        f"{rows}"
        "\n------------\n"
        f"*Honorable Mentions*: {honorable_mentions}\n\n"
        "# FAQ\n\n"
        "* **How are players ranked?**\n\n"
        f"Each player's line is compared to {last_season} per-game averages for their primary position "
        f"(G, F or C, using players who averaged {MIN_BASELINE_MINUTES}+ minutes). Each of the 9 categories becomes a z-score "
        "(FG% and FT% are weighted by attempts, turnovers count against). Z-scores are capped at ±10 and "
        f"summed into the Night Score. Only players with {MIN_BASELINE_MINUTES}+ minutes are ranked, "
        "so short bench stints don't fill the list.\n\n"
        "* **Why is [insert player] not ranked here? They had a great game!**\n\n"
        "It doesn't mean that this player didn't perform well, it just means that some players had a more "
        "balanced performance than them across the 9 categories.\n\n"
    )
    title = f"🔥🚀 Top 10 Player Discussion - {players.iloc[0]['PLAYER_NAME']} Night 🚀🔥 - {date}"
    return title, body


def post(title: str, body: str, is_real: bool) -> None:
    """
    Submit the post to Reddit. A real post goes to r/fantasybball with the Discussion flair,
    otherwise it goes to the test subreddit r/bballfanalyst.
    """
    reddit = praw.Reddit(
        client_id=os.getenv('MY_ID'),
        client_secret=os.getenv('MY_SECRET'),
        password=os.getenv('MY_PASSWORD'),
        user_agent="Daily Top 10 Player Post Bot for r/fantasybball",
        username=os.getenv('MY_USERNAME'),
    )

    if is_real:
        subreddit = reddit.subreddit('fantasybball')
        choices = list(subreddit.flair.link_templates.user_selectable())
        template_id = next(x for x in choices if x["flair_text"] == "Discussion")["flair_template_id"]
        submission = subreddit.submit(title=title, selftext=body, flair_id=template_id)
    else:
        submission = reddit.subreddit('bballfanalyst').submit(title=title, selftext=body)

    print(f"Posted: https://reddit.com{submission.permalink}")


def main(date_str: str | None = None, is_real: bool = False) -> None:
    """
    Fetch a night's stats, score them against last season, and post the top 10.

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
    players = players[players['MINUTES'] >= MIN_BASELINE_MINUTES].reset_index(drop=True)

    title, body = build_report(players, date_str, last_season)
    print(title)
    print(body)
    post(title, body, is_real)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
