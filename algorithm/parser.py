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
from nba_api.stats.endpoints import boxscoretraditionalv2, scoreboardv2

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
            'TEAM_ID',
            'GP', 'MIN', 
            'PTS', 'REB', 
            'AST', 'STL', 
            'TO', 'BLK', 
            'FG3M', 'FTA', 
            'FG_PCT', 'FT_PCT']

#Note: Missing TEAM_ID for some reason?

def get_game_ids(today, week):
    start_date = today - timedelta(days=today.weekday())
    end_date = start_date
    
    if week:
        end_date = start_date + timedelta(days=6)

    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        scores = scoreboardv2.ScoreboardV2(
            game_date=date_str,
            day_offset=0,
            league_id=LEAGUE_ID,
        ).get_dict()

        games = scores['resultSets'][0]['rowSet']
        for game in games:
            print(game[0])
            yield game[2]
        current_date += timedelta(days=1)


def generate_player_stats(week, date):
    columns = None
    all_player_stats = []
    for game_id in get_game_ids(today=date, week=week):
        game_stats = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game_id).get_dict()
        if not columns:
            columns = game_stats['resultSets'][0]['headers']
        player_stats = game_stats['resultSets'][0]['rowSet']
        all_player_stats.extend(player_stats)
    return columns, all_player_stats


def convert_str_to_float(time):
    segments = time.split(':')
    minutes = float(segments[0])
    seconds = float(segments[1]) / 60

    return minutes + seconds


def make_dataframe(columns, player_stats):
    df = pd.DataFrame(player_stats, columns=columns)
    df = df.sort_values(by='PLAYER_NAME')
    columns_drop = [column for column in df.columns if column not in required]
    df = df.drop(columns=columns_drop)
    df = df.dropna()
    df['GP'] = 1
    df['MIN'] = df['MIN'].apply(convert_str_to_float)

    aggregate_sum = {col: 'sum' for col in df.columns if col not in ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ID']}
    df = df.groupby(['PLAYER_NAME', 'PLAYER_ID'], as_index=False).agg(aggregate_sum)

    #Get average of all stats
    for col in df.columns:
        if col in ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ID', 'GP']:
            continue
        df[col] = df[col] / df['GP']
    return df


def main():
    week = True
    date = datetime(2024, 5, 7) 
    columns, player_stats = generate_player_stats(week=week, date=date)
    df = make_dataframe(columns=columns, player_stats=player_stats)
    
    #If you need, uncomment this
    # df.to_csv(f'player_stats_{date}.csv', index=False)
    print(df)

if __name__ == '__main__':
    main()