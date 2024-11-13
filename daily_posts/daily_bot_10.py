import os
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timedelta
import parserV2
import praw

def today() -> str:
    now = datetime.now() - timedelta(1)
    
    # Define suffixes for day of the month
    def day_suffix(day):
        if 11 <= day <= 13:
            return "th"
        elif day % 10 == 1:
            return "st"
        elif day % 10 == 2:
            return "nd"
        elif day % 10 == 3:
            return "rd"
        else:
            return "th"
    
    # Return formatted date
    return now.strftime(f"%B {now.day}{day_suffix(now.day)}, %Y")

def insert_player(index, player, top_ten: bool) -> str:
    """
    Inserts a player's data into a formatted row with emojis for exceeding stat thresholds, handling division by zero.

    :param index: The rank of the player (0-indexed, so add 1 for display).
    :param player: A dictionary containing player stats.
    :param top_ten: Boolean indicating if the player is in the top ten.
    :return: A formatted string for the player's row.
    """
    # Threshold values and corresponding emoji
    emojis = {
        'FG_PCT': '🚀🚀' if player['FG_AT'] >= 20 and (player['FG_MADE'] / player['FG_AT']) >= 0.8 else '🚀🔥' if player['FG_AT'] >= 17 and (player['FG_MADE'] / player['FG_AT']) >= 0.7 else '🔥🔥' if player['FG_AT'] >= 15 and (player['FG_MADE'] / player['FG_AT']) >= 0.65 else '🔥' if player['FG_AT'] >= 13 and (player['FG_MADE'] / player['FG_AT']) >= 0.65 else '💩💩' if player['FG_AT'] >= 20 and (player['FG_MADE'] / player['FG_AT']) <= 0.2 else '💩🥶' if player['FG_AT'] >= 15 and (player['FG_MADE'] / player['FG_AT']) <= 0.3 else '🥶🥶' if player['FG_AT'] >= 12 and (player['FG_MADE'] / player['FG_AT']) <= 0.2 else '🥶' if player['FG_AT'] >= 9 and (player['FG_MADE'] / player['FG_AT']) <= 0.3 else '',
        'FT_PCT': '🚀🚀' if player['FT_AT'] >= 15 and (player['FT_MADE'] / player['FT_AT']) == 1 else '🚀🔥' if player['FT_AT'] >= 12 and (player['FT_MADE'] / player['FT_AT']) >= 0.9 else '🔥🔥' if player['FT_AT'] >= 10 and (player['FT_MADE'] / player['FT_AT']) >= 0.9 else '🔥' if player['FT_AT'] >= 9 and (player['FT_MADE'] / player['FT_AT']) >= 0.8 else '💩💩' if player['FT_AT'] >= 15 and (player['FT_MADE'] / player['FT_AT']) <= 0.35 else '💩🥶' if player['FT_AT'] >= 12 and (player['FT_MADE'] / player['FT_AT']) <= 0.4 else '🥶🥶' if player['FT_AT'] >= 10 and (player['FT_MADE'] / player['FT_AT']) <= 0.35 else '🥶' if player['FT_AT'] >= 8 and (player['FT_MADE'] / player['FT_AT']) <= 0.4 else '',
        '3P_MADE': '🚀🚀' if player['3P_MADE'] >= 12 else '🚀🔥' if player['3P_MADE'] >= 9 else '🔥🔥' if player['3P_MADE'] >= 7 else '🔥' if player['3P_MADE'] >= 5 else '🥶' if player['3P_MADE'] == 0 else '',
        'RB': '🚀🚀' if player['RB'] >= 18 else '🚀🔥' if player['RB'] >= 16 else '🔥🔥' if player['RB'] >= 14 else '🔥' if player['RB'] >= 12 else '',
        'AST': '🚀🚀' if player['AST'] >= 16 else '🚀🔥' if player['AST'] >= 14 else '🔥🔥' if player['AST'] >= 12 else '🔥' if player['AST'] >= 10 else '',
        'STL': '🚀🚀' if player['STL'] >= 10 else '🚀🔥' if player['STL'] >= 7 else '🔥🔥' if player['STL'] >= 5 else '🔥' if player['STL'] >= 3 else '',
        'BLK': '🚀🚀' if player['BLK'] >= 9 else '🚀🔥' if player['BLK'] >= 7 else '🔥🔥' if player['BLK'] >= 5 else '🔥' if player['BLK'] >= 3 else '',
        'PTS': '🚀🚀' if player['PTS'] >= 60 else '🚀🔥' if player['PTS'] >= 50 else '🔥🔥' if player['PTS'] >= 40 else '🔥' if player['PTS'] >= 30 else '',
        'TOV': '💩💩' if player['TOV'] >= 11 else '💩🥶' if player['TOV'] >= 9 else '🥶🥶' if player['TOV'] >= 7 else '🥶' if player['TOV'] >= 5 else ''
    }


    # Generate stats string with emojis where applicable
    stat_line = (
        f"{player['FG_MADE']}-{player['FG_AT']}{emojis['FG_PCT']}|"
        f"{player['FT_MADE']}-{player['FT_AT']}{emojis['FT_PCT']}|"
        f"{player['3P_MADE']}{emojis['3P_MADE']}|"
        f"{player['RB']}{emojis['RB']}|"
        f"{player['AST']}{emojis['AST']}|"
        f"{player['STL']}{emojis['STL']}|"
        f"{player['BLK']}{emojis['BLK']}|"
        f"{player['TOV']}|"
        f"{player['PTS']}{emojis['PTS']}|"
        f"{player['BM_VAL']}|{player['ESPN']}"
    )

    # Include rank if the player is in the top ten
    rank_prefix = f"|{index + 1}|" if top_ten else "|HM|"

    return f"{rank_prefix}{player['NAME']}|{player['MINUTES']} mins|{stat_line}|\n"

def bottom_10_report(players, date: str) -> str:
    """
    Generates a formatted string for the top 10 performing players of the night with their stats.

    :param players: List of dictionaries, each containing player data with the keys: Rank, Player, Time, FG, 3PTS, FT,
                    REB, AST, STL, BLK, TOV, PTS, Value, and ESPN_Score (ESPN Score can be left as a placeholder if unavailable)
    :return: A formatted string report for the top 10 players.
    """

    # Create the report as a single formatted string
    report = (
        f"Hello r/fantasybball! Here are the bottom 10 performing players for {date}...\n\n"
        "|Rank|Player|Time|FG|FT|3PT|REB|AST|STL|BLK|TOV|PTS|BM Value|ESPN Score|\n"
        "|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|\n" +
        "".join(insert_player(index, player, True) for index, player in players.iloc[:10].iterrows())
    )

    honorable_mentions = ", ".join(player['NAME'] for index, player in players.iloc[10:15].iterrows())

    report += (
        "\n------------\n"
        f"*Honorable Mentions*: {honorable_mentions}\n\n"
        "# FAQ\n\n"
        "* **How are players ranked?**\n\n"
        "We directly use [Basketball Monster's rankings](https://basketballmonster.com/) for daily leaders (which is based off of their 9cat value system). For worst performers of the night, a player must play at a minimum 24 minutes to make the list.\n\n"
        "* **Some exciting news, bot is almost up! Posts will follow the same format but will include some additional things!**\n\n"
        "Please continue to leave suggestions in the comments on what you want to see!"
    )

    return report
    
def main():

    server = 'http://10.24.162.43:4444'
    driver = parserV2.start_remote_server(server)
    players = parserV2.get_stats(driver)
    bottom = parserV2.rank(players, True)
    report = bottom_10_report(bottom, today())
    print(report)

    ''' # Getting env variables
    load_dotenv()

    # Configuring Bot
    reddit = praw.Reddit(
        client_id = os.getenv('MY_ID'),
        client_secret = os.getenv('MY_SECRET'),
        password = os.getenv('MY_PASSWORD'),
        user_agent = "testscript by u/bball-fanalyst",
        username = os.getenv('MY_USERNAME'),
    )
    print(reddit.user.me())'''

if __name__ == '__main__':
    main()