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


def top_10_report(players, date: str) -> str:
    """
    Generates a formatted string for the top 10 performing players of the night with their stats.

    :param players: List of dictionaries, each containing player data with the keys: Rank, Player, Time, FG, 3PTS, FT,
                    REB, AST, STL, BLK, TOV, PTS, Value, and ESPN_Score (ESPN Score can be left as a placeholder if unavailable)
    :return: A formatted string report for the top 10 players.
    """

    # Create the report as a single formatted string
    report = (
        f"Hello r/fantasybball! Here are the top 10 performing players for {date}!\n\n"
        "|Rank|Player|Time|FG|FT|3PT|REB|AST|STL|BLK|TOV|PTS|BM Value|ESPN Score|\n"
        "|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|:-|\n" +
        "".join(
            f"|{index + 1}|{player['NAME']}|{player['MINUTES']} mins|{player['FG_MADE']}-{player['FG_AT']}|{player['FT_MADE']}-{player['FT_AT']}|"
            f"{player['3P_MADE']}|{player['RB']}|{player['AST']}|{player['STL']}|{player['BLK']}|"
            f"{player['TOV']}|{player['PTS']}|{player['BM_VAL']}|{player['ESPN']}|\n"
            for index, player in players.iloc[:10].iterrows()
        )
    )

    honorable_mentions = ", ".join(player['NAME'] for index, player in players.iloc[10:15].iterrows())

    report += (
        "\n------------\n"
        f"*Honorable Mentions*: {honorable_mentions}\n\n"
        "# FAQ\n\n"
        "* **How are players ranked?**\n\n"
        "We directly use [Basketball Monster's rankings](https://basketballmonster.com/) for daily leaders (which is based off of their value system).\n\n"
        "* **Some exciting news, bot is almost up! Posts will follow the same format but will include some additional things!**\n\n"
        "Some things that have been requested: Emojis for performance, Link to previous day's thread, ESPN fantasy scores (default). Please continue to leave suggestions in the comments on what you want to see!"
    )

    return report
    
def main():

    server = 'http://10.24.217.195:4444'
    driver = parserV2.start_remote_server(server)
    players = parserV2.get_stats(driver)
    top = parserV2.rank(players, False)
    report = top_10_report(top, today())
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