from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
import pandas as pd

def start_remote_server(server: str, daily: bool):
    # Start driver
    options = webdriver.ChromeOptions()
    driver = webdriver.Remote(command_executor=server, options=options)

    # Go to Basketball Monster Stats Webpage
    driver.get('https://basketballmonster.com/playerrankings.aspx')
    
    # Check if scraping for daily or season stats
    if daily:
        # Select 'Past Days' -> automatically goes to the past 1 day
        selection = driver.find_element(By.NAME, 'DateFilterControl')
        select = Select(selection)
        select.select_by_visible_text('Past Days')

    return driver

def scrape_stats(driver, daily: bool):
    # Get HTML to pass into 
    html = driver.page_source
    soup = BeautifulSoup(html, features="html.parser")
    raw = soup.find_all('tr')
    players = []
    for row in raw:
        stats_raw = row.find_all('td', class_=['tdr', 'tdl', 'tdc nowrap'])
        if not len(stats_raw):
            continue
        player_stats = create_player_stats_row(stats_raw, daily)
        players.append(player_stats)
    driver.quit()
    return pd.DataFrame(players)

def create_player_stats_row(stats_raw: list, daily: bool):
    player_stats = {}

    # Adjusting for injuries column that only exists if a player has an injury designation
    adjustment = 0
    if len(stats_raw) == 29:
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
    player_stats['ESPN'] = espn_score(player_stats)

    if daily: # Need to round stats if it is a daily scrape
        daily_round(player_stats)

    return player_stats

def daily_round(player_stats: dict):
    player_stats['FG_AT'] = int(round(player_stats['FG_AT']))
    player_stats['FG_MADE'] = int(round(player_stats['FG_MADE']))
    player_stats['FT_AT'] = int(round(player_stats['FT_AT']))
    player_stats['FT_MADE'] = int(round(player_stats['FT_MADE']))
    player_stats['3P_MADE'] = int(round(player_stats['3P_MADE']))
    player_stats['RB'] = int(round(player_stats['RB']))
    player_stats['AST'] = int(round(player_stats['AST']))
    player_stats['STL'] = int(round(player_stats['STL']))
    player_stats['BLK'] = int(round(player_stats['BLK']))
    player_stats['TOV'] = int(round(player_stats['TOV']))
    player_stats['PTS'] = int(round(player_stats['PTS']))
    player_stats['ESPN'] = int(round(player_stats['ESPN']))

def espn_score(player: dict) -> int:
    return player['PTS'] + player['3P_MADE'] - player['FG_AT'] + (2 * player['FG_MADE']) - player['FT_AT'] + player['FT_MADE'] + player['RB'] + (2 * player['AST']) + (4 * player['STL']) + (4 * player['BLK']) - (2 * player['TOV'])

def rank_ascending(players, ascend: bool):
    if ascend:
        return players[players['MINUTES'] >= 24].sort_values(by='BM_VAL', ascending=ascend)
    else:
        return players.sort_values(by='BM_VAL', ascending=ascend)

def main():
    server = 'http://127.0.0.1:4444'

    # Season Stats Test
    driver = start_remote_server(server, False)
    season_stats = scrape_stats(driver, False)
    print(season_stats)
    
    # Daily Stats Test
    driver = start_remote_server(server, True)
    daily_stats = scrape_stats(driver, True)
    print(daily_stats)

if __name__ == '__main__':
    main()