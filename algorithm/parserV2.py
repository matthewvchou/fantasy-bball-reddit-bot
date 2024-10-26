#!../venv/bin/python3.11

import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import pandas as pd

def daily_url() -> str:
    '''
    Function to create URL to Basketball Reference's Daily Leaders site for the previous day

    return str: URL to Basketball Reference's Daily Leaders site for previous day
    '''
    # Get yesterday's date
    today = datetime.now() - timedelta(2)
    yesterday = today.strftime('%Y %m %d').split()
    print(yesterday)

    # Make URL
    url = 'https://www.basketball-reference.com/friv/dailyleaders.fcgi?month={}&day={}&year={}'.format(yesterday[1], yesterday[2], yesterday[0])
    return url

def daily_players():
    '''
    Function to create pd.Dataframe of all players that played the previous day

    return pd.Dataframe:    pd.Dataframe containing all players and their relevant stats
    '''
    # Make request and parse using Beautiful Soup
    r = requests.get(daily_url())
    soup = BeautifulSoup(r.content, features="html.parser")
    raw = soup.find_all('tr')
    players = []
    # Find each player's stats and input into dictionary
    for row in raw:
        player = row.find('td')
        if not player:
            continue
        player_stats = {}
        player_stats['NAME'] = row.find('td', {'data-stat': 'player'}).text.strip()
        player_stats['MINUTES'] = row.find('td', {'data-stat': 'mp'}).text.strip()  # Keep as string to maintain "MM:SS" format
        # Get total seconds played (for filtering <24 minutes played)
        temp_seconds = player_stats['MINUTES'].split(':')
        player_stats['SECONDS'] = (int(temp_seconds[0]) * 60) + int(temp_seconds[1])
        player_stats['FG'] = int(row.find('td', {'data-stat': 'fg'}).text.strip())
        player_stats['FGA'] = int(row.find('td', {'data-stat': 'fga'}).text.strip())
        player_stats['FGM'] = player_stats['FGA'] - player_stats['FG']
        player_stats['FG3'] = int(row.find('td', {'data-stat': 'fg3'}).text.strip())
        player_stats['FG3A'] = int(row.find('td', {'data-stat': 'fg3a'}).text.strip())
        player_stats['FG3M'] = player_stats['FG3A'] - player_stats['FG3']
        player_stats['FT'] = int(row.find('td', {'data-stat': 'ft'}).text.strip())
        player_stats['FTA'] = int(row.find('td', {'data-stat': 'fta'}).text.strip())
        player_stats['FTM'] = player_stats['FTA'] - player_stats['FT']
        player_stats['ORB'] = int(row.find('td', {'data-stat': 'orb'}).text.strip())
        player_stats['DRB'] = int(row.find('td', {'data-stat': 'drb'}).text.strip())
        player_stats['RB'] = int(row.find('td', {'data-stat': 'trb'}).text.strip())
        player_stats['AST'] = int(row.find('td', {'data-stat': 'ast'}).text.strip())
        player_stats['STL'] = int(row.find('td', {'data-stat': 'stl'}).text.strip())
        player_stats['BLK'] = int(row.find('td', {'data-stat': 'blk'}).text.strip())
        player_stats['TOV'] = int(row.find('td', {'data-stat': 'tov'}).text.strip())
        player_stats['PTS'] = int(row.find('td', {'data-stat': 'pts'}).text.strip())
        fantasy = fantasy_score(player_stats)
        player_stats['FTSY'] = fantasy
        players.append(player_stats)
    
    # Return pd.Dataframe of players
    return pd.DataFrame(players)

def fantasy_score(player: dict) -> int:
    return (player['FG'] * 0.5) - (player['FGM'] * 0.5) + player['FT'] - player['FTM'] + (player['FG3'] * 2) - player['FG3M'] + (player['ORB'] * 1.5) + player['DRB'] + player['AST'] + (player['STL'] * 1.5) + (player['BLK'] * 1.5) - player['TOV'] + player['PTS']

def rank(players, ascend: bool):
    return players[players['SECONDS'] > 1440].sort_values(by='FTSY', ascending=ascend)

def main():
    players = daily_players()
    top_ten = rank(players, False)
    bottom_ten = rank(players, True)
    print(top_ten)
    print(bottom_ten)

if __name__ == '__main__':
    main()