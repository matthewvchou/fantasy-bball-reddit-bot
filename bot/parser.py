#!../reddit_venv/bin/python3.10

import numpy as np
import pandas as pd
import requests
import json
from nba_api.stats.endpoints import fantasywidget # type: ignore

LEAGUE_ID = '00' #For nba

def parser(season: str) -> pd.DataFrame:
    pd.options.display.max_columns = 0

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
    
    #Gets all 581 players from the NBA in the 2023-24 season
    all_players = fantasywidget.FantasyWidget(season=season, league_id=LEAGUE_ID).get_dict()
    df = pd.DataFrame(columns=all_players["resultSets"][0]["headers"])

    for index, row in enumerate(all_players["resultSets"][0]["rowSet"]):
        df.loc[index] = row

    df = df.drop(['TEAM_ABBREVIATION', 
                  'FAN_DUEL_PTS', 
                  'NBA_FANTASY_PTS', 
                  'PLAYER_POSITION',
                  ], axis=1)
    return df

    
def main():
    season = '2023-24'
    pd = parser(season)

    print(pd)

if __name__ == '__main__':
    main()