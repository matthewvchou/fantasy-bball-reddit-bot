#!../venv/bin/python3.11
'''
TODO
Fix API call so that it doesn't do whatever its doing right now
Pulls and puts in csv as temporary storage
Then use csv to make less calls for function calls
'''
import numpy as np
from datetime import datetime, timedelta, date
from typing import Generator
import pandas as pd
import requests
import json
from nba_api.stats.endpoints import LeagueGameFinder, playercareerstats

LEAGUE_ID = '00' #For nba

pd.options.display.max_info_columns = 0

'''
Columns in dataframe:
PLAYER_ID
PLAYER_NAME
TEAM_ID
GP      (Games Played)
MIN     (Minutes Played)
PTS     (Points Scored)
REB     (Total Rebounds)
AST     (Assists)
STL     (Steals)
TOV     (Turnovers)
BLK     (Blocked Shots)
FG3M    (3-Point Shots Made)
FTA     (Free-Throws Attempted)
FG_PCT  (Field Goal Percentage)
FT_PCT  (Free Throw Percentage)
'''

required = ['PLAYER_ID', 'PLAYER_NAME', 
            'GP', 'MIN', 
            'PTS', 'REB', 
            'AST', 'STL', 
            'TOV', 'BLK', 
            'FG3M', 'FTA', 
            'FG_PCT', 'FT_PCT']

def main():
    end_date = datetime(2024, 5, 7)
    start_date = end_date - timedelta(days=7)

    games = LeagueGameFinder(player_or_team_abbreviation='P', date_to_nullable=end_date, date_from_nullable=start_date)
    print(games.get_json())

if __name__ == '__main__':
    main()