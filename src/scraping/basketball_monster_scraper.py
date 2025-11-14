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

    return driver

def scrape_stats(driver):
    # Get HTML to pass into 
    html = driver.page_source
    soup = BeautifulSoup(html, features="html.parser")
    raw = soup.find_all('tr')
    players = []
    for row in raw:
        stats_raw = row.find_all('td', class_=['tdr', 'tdl', 'tdc nowrap'])
        if not len(stats_raw):
            continue
        player_stats = create_player_stats_row(stats_raw)
        players.append(player_stats)
    driver.quit()
    return pd.DataFrame(players)

def create_player_stats_row(stats_raw):
    player_stats = {}
    if len(stats_raw) == 28:
        adjustment = 0
    elif len(stats_raw) == 29:
        adjustment = 1
    player_stats['NAME'] = stats_raw[3].text.strip().removesuffix("fouls").strip()
    player_stats['POSITION'] = stats_raw[4].text.strip()
    player_stats['BM_VAL'] = float(stats_raw[2].text.strip())
    player_stats['MINUTES'] = float(stats_raw[6 + adjustment].text.strip())
    player_stats['FG_PCT'] = float(stats_raw[13 + adjustment].text.strip())
    player_stats['FG_AT'] = float(stats_raw[14 + adjustment].text.strip())
    player_stats['FG_MADE'] = player_stats['FG_PCT'] * player_stats['FG_AT']
    player_stats['FT_PCT'] = float(stats_raw[15 + adjustment].text.strip())
    player_stats['FT_AT'] = float(stats_raw[16 + adjustment].text.strip())
    player_stats['FT_MADE'] = player_stats['FT_PCT'] * player_stats['FT_AT']
    player_stats['3P_MADE'] = float(stats_raw[8 + adjustment].text.strip())
    player_stats['RB'] = float(stats_raw[9 + adjustment].text.strip())
    player_stats['AST'] = float(stats_raw[10 + adjustment].text.strip())
    player_stats['STL'] = float(stats_raw[11 + adjustment].text.strip())
    player_stats['BLK'] = float(stats_raw[12 + adjustment].text.strip())
    player_stats['TOV'] = float(stats_raw[17 + adjustment].text.strip())
    player_stats['PTS'] = float(stats_raw[7 + adjustment].text.strip())
    return player_stats

def main():
    server = 'http://127.0.0.1:4444'
    driver = start_remote_server(server)
    players = scrape_stats(driver)
    print(players)
    # bottom = rank(players, True)
    # top = rank(players, False)

if __name__ == '__main__':
    main()