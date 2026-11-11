import sys
import time
from datetime import datetime

from nba_api.stats.endpoints import boxscoretraditionalv3, scoreboardv3

from src.bot.daily.daily_bottom_ten import main as post_bottom_ten
from src.bot.daily.daily_top_ten import main as post_top_ten

POLL_SECONDS = 180
MAX_POLLS = 60


def are_box_scores_ready(date_str: str) -> bool:
    """
    Check that every game scheduled on the date has a loadable box score.

    Any API error (missing box score, empty reply) counts as not ready.
    """
    try:
        game_ids = scoreboardv3.ScoreboardV3(game_date=date_str, timeout=60).game_header.get_data_frame()['gameId'].unique()
        for game_id in game_ids:
            boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=game_id, timeout=60).get_dict()
            time.sleep(1)
    except Exception as error:
        print(f"Not ready: {type(error).__name__}", flush=True)
        return False
    return True


def poll_and_post(date_str: str, is_real: bool = False) -> None:
    """
    Wait until every box score for the date loads, then run the daily top 10 and bottom 10 posts once each.

    Checks every POLL_SECONDS for up to MAX_POLLS times. Posts nothing if the box scores never load.
    Does not guard against posting the same date twice.

    Args:
        date_str: Game date in 'YYYY-MM-DD' format
        is_real: True to post to r/fantasybball instead of r/bballfanalyst

    Raises:
        ValueError: If date_str is not in 'YYYY-MM-DD' format.
    """
    # The scoreboard API silently returns other days' games for malformed dates, which makes polling retry forever.
    datetime.strptime(date_str, '%Y-%m-%d')

    for _ in range(MAX_POLLS):
        if are_box_scores_ready(date_str):
            print("All box scores ready. Running posts.", flush=True)
            post_top_ten(date_str, is_real)
            post_bottom_ten(date_str, is_real)
            return
        time.sleep(POLL_SECONDS)

    print("Gave up waiting for box scores. Nothing posted.", flush=True)


if __name__ == '__main__':
    poll_and_post(sys.argv[1], is_real='--real' in sys.argv[2:])
