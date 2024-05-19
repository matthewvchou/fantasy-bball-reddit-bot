#!../reddit_venv/bin/python3.10

import numpy as np
from datetime import datetime, timedelta, date
from typing import Generator
import pandas as pd
import requests
import json
from nba_api.stats.endpoints import fantasywidget, cumestatsplayer, scoreboardv2, boxscoreadvancedv2 # type: ignore

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

def average_season(season: str) -> pd.DataFrame:
    #Gets all 581 players from the NBA in the 2023-24 season
    #This data tells per game
    all_players = fantasywidget.FantasyWidget(season=season, league_id=LEAGUE_ID).get_dict()
    df = pd.DataFrame(columns=all_players["resultSets"][0]["headers"])

    for index, row in enumerate(all_players["resultSets"][0]["rowSet"]):
        df.loc[index] = row

    df = df.drop(columns=['TEAM_ABBREVIATION', 
                  'FAN_DUEL_PTS', 
                  'NBA_FANTASY_PTS', 
                  'PLAYER_POSITION',
                  ], axis=1)
    return df


def get_week_dates_generator(target_date: date) -> Generator:
    start_of_week = target_date - timedelta(days=target_date.weekday())
    yield from (start_of_week + timedelta(days=i) for i in range(7))


def game_id_generator(offset: int) -> Generator:
    current_date = datetime.today().date()
    all_games_on_day = scoreboardv2.ScoreboardV2(day_offset=offset, game_date=current_date, league_id=LEAGUE_ID).get_dict()
    yield from ( game[2] for game in all_games_on_day['resultSets'][0]['rowSet'] )


def per_day(day: int) -> pd.DataFrame:
    #18 seconds runtime for the program, need to make run faster
    game_ids = game_id_generator(day)
    df = pd.DataFrame()

    all_game_data = {}
    for game_id in game_ids:
        all_game_data[game_id] = boxscoreadvancedv2.BoxScoreAdvancedV2(game_id=game_id).get_dict()

    for game_id, game_data in all_game_data.items():
        for player in game_data['resultSets'][0]['rowSet']:
            player_stats = cumestatsplayer.CumeStatsPlayer(player_id=player[4], game_ids=game_id).get_dict()
            if df.empty:
                df = pd.DataFrame(columns=player_stats['resultSets'][1]['headers'])
            if len(player_stats['resultSets'][1]['rowSet']) != 0:
                df.loc[len(df)] = player_stats['resultSets'][1]['rowSet'][0]

    df.rename(columns={'DISPLAY_FI_LAST': 'PLAYER_NAME',
               'PERSON_ID': 'PLAYER_ID',
               'ACTUAL_MINUTES': 'MIN',
               'FG3': 'FG3M',
               'TURNOVERS': 'TOV',
               'TOT_REB': 'REB',
               }, inplace=True)
    
    for column in df.columns:
        if column not in required:
            df = df.drop(columns=column, axis=1)
    df['count'] = 1
    return df
            

def per_week(week: date) -> pd.DataFrame:
    df_total = pd.DataFrame()
    #rly rly slow, 1 min 20 s

    for specific_day in get_week_dates_generator(week):
        current_date = datetime.today().date()
        # print(day.date().day - current_date.day)
        df_day = per_day(specific_day.date().day - current_date.day)
        df_total = pd.concat([df_total, df_day], ignore_index=True)

    aggregation_functions = {col: 'sum' for col in df_total.columns if col not in ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ID']}
    grouped = df_total.groupby(['PLAYER_ID', 'PLAYER_NAME'], as_index=False).agg(aggregation_functions)

    for col in grouped.columns:
        if col not in ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ID', 'count']:
            grouped[col] = grouped[col] / grouped['count']
    grouped = grouped.drop(columns=['count'])

    print(grouped)
    return grouped
        
def main():
    season = '2023-24'
    # pd = average_season(season)

    #Runs yesterday game
    # per_day(-1)

    week = datetime(2024, 5, 7)
    per_week(week)


if __name__ == '__main__':
    main()