#!../venv/bin/python3.11

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from time import sleep
from dotenv import load_dotenv
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import pandas as pd

def start_remote_server(server: str):
    # Start driver
    options = webdriver.ChromeOptions()
    driver = webdriver.Remote(command_executor=server, options=options)

    # Go to Basketball Monster Webpage
    driver.get('https://basketballmonster.com/playerrankings.aspx')

    # Select 'Past Days' -> automatically goes to the past 1 day
    selection = driver.find_element(By.NAME, 'DateFilterControl')
    select = Select(selection)
    select.select_by_visible_text('Past Days')

    return driver

def get_stats(driver):
    # Get HTML to pass into 
    html = driver.page_source
    soup = BeautifulSoup(html, features="html.parser")
    raw = soup.find_all('tr')
    players = []
    for row in raw:
        stats_raw = row.find_all('td', class_=['tdr', 'tdl'])
        if not len(stats_raw):
            continue
        player_stats = {}
        player_stats['NAME'] = stats_raw[3].text.strip()
        player_stats['BM_VAL'] = float(stats_raw[2].text.strip())
        player_stats['MINUTES'] = float(stats_raw[5].text.strip())
        fg_pct = float(stats_raw[12].text.strip())
        player_stats['FG_AT'] = int(float(stats_raw[13].text.strip()))
        player_stats['FG_MADE'] = round(fg_pct * player_stats['FG_AT'])
        ft_pct = float(stats_raw[14].text.strip())
        player_stats['FT_AT'] = int(float(stats_raw[15].text.strip()))
        player_stats['FT_MADE'] = round(ft_pct * player_stats['FT_AT'])
        player_stats['3P_MADE'] = int(float(stats_raw[7].text.strip()))
        player_stats['RB'] = int(float(stats_raw[8].text.strip()))
        player_stats['AST'] = int(float(stats_raw[9].text.strip()))
        player_stats['STL'] = int(float(stats_raw[10].text.strip()))
        player_stats['BLK'] = int(float(stats_raw[11].text.strip()))
        player_stats['TOV'] = int(float(stats_raw[16].text.strip()))
        player_stats['PTS'] = int(float(stats_raw[6].text.strip()))
        player_stats['ESPN'] = espn_score(player_stats)
        players.append(player_stats)
    driver.quit()
    return pd.DataFrame(players)

def espn_score(player: dict) -> int:
    return player['PTS'] + player['3P_MADE'] - player['FG_AT'] + (2 * player['FG_MADE']) - player['FT_AT'] + player['FT_MADE'] + player['RB'] + (2 * player['AST']) + (4 * player['STL']) + (4 * player['BLK']) - (2 * player['TOV'])

def rank(players, ascend: bool):
    if ascend:
        return players[players['MINUTES'] >= 24].sort_values(by='BM_VAL', ascending=ascend)
    else:
        return players.sort_values(by='BM_VAL', ascending=ascend)

def main():
    server = 'http://10.5.222.9:4444'
    driver = start_remote_server(server)
    players = get_stats(driver)
    bottom = rank(players, True)
    top = rank(players, False)
    print(top)
    print(bottom)
    

if __name__ == '__main__':
    main()