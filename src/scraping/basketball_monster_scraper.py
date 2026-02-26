from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np

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
    
def get_season_averages(season_stats):
    stat_columns = season_stats.select_dtypes("number").drop(columns=['BM_VAL', 'MINUTES', 'ESPN']).columns

    # Stat Means
    season_means_by_position = (
        season_stats.groupby('POSITION')[stat_columns].mean()
    )

    # Stat Standard Deviations
    season_stds_by_position = (
        season_stats.groupby('POSITION')[stat_columns].std()
    )

    # Calculate FG and FT impacts for season stats
    season_stats_copy = season_stats.copy()
    season_stats_copy['FG_IMPACT'] = season_stats_copy.apply(
        lambda row: (row['FG_PCT'] - season_means_by_position.loc[row['POSITION'], 'FG_PCT']) * row['FG_AT']
        if row['POSITION'] in season_means_by_position.index else 0,
        axis=1
    )
    season_stats_copy['FT_IMPACT'] = season_stats_copy.apply(
        lambda row: (row['FT_PCT'] - season_means_by_position.loc[row['POSITION'], 'FT_PCT']) * row['FT_AT']
        if row['POSITION'] in season_means_by_position.index else 0,
        axis=1
    )

    # Get means and stds for impacts from season data
    fg_impact_means = season_stats_copy.groupby('POSITION')['FG_IMPACT'].mean()
    fg_impact_stds = season_stats_copy.groupby('POSITION')['FG_IMPACT'].std()
    ft_impact_means = season_stats_copy.groupby('POSITION')['FT_IMPACT'].mean()
    ft_impact_stds = season_stats_copy.groupby('POSITION')['FT_IMPACT'].std()

    return season_means_by_position, season_stds_by_position, fg_impact_means, fg_impact_stds, ft_impact_means, ft_impact_stds

def player_z_scores_weighted(season_means, season_stds, daily_stats, fg_impact_means, fg_impact_stds, ft_impact_means, ft_impact_stds):
    # Start with NAME, POSITION, and raw stats
    raw_stat_cols = ['NAME', 'POSITION', 'FG_PCT', 'FG_AT', 'FT_PCT', 'FT_AT', '3P_MADE', 'PTS', 'RB', 'AST', 'STL', 'BLK', 'TOV']
    z_scores_df = daily_stats[raw_stat_cols].copy()

    # Step 1: Calculate volume-weighted percentage impacts
    # FG Impact = (player_FG% - position_avg_FG%) × player_FGA
    daily_stats['FG_IMPACT'] = daily_stats.apply(
        lambda row: (row['FG_PCT'] - season_means.loc[row['POSITION'], 'FG_PCT']) * row['FG_AT']
        if row['POSITION'] in season_means.index else 0,
        axis=1
    )

    # FT Impact = (player_FT% - position_avg_FT%) × player_FTA
    daily_stats['FT_IMPACT'] = daily_stats.apply(
        lambda row: (row['FT_PCT'] - season_means.loc[row['POSITION'], 'FT_PCT']) * row['FT_AT']
        if row['POSITION'] in season_means.index else 0,
        axis=1
    )

    # Step 2: Calculate position-based z-scores for all 9 categories
    # Define the 9 categories (using impacts for percentages)
    nine_cat_raw = {
        'FG_IMPACT': 'FG_IMPACT_Z',
        'FT_IMPACT': 'FT_IMPACT_Z',
        '3P_MADE': '3PM_Z',
        'PTS': 'PTS_Z',
        'RB': 'REB_Z',
        'AST': 'AST_Z',
        'STL': 'STL_Z',
        'BLK': 'BLK_Z',
        'TOV': 'TOV_Z'
    }

    for raw_stat, z_col in nine_cat_raw.items():
        if raw_stat == 'FG_IMPACT':
            z_scores = daily_stats.apply(
                lambda row: (row['FG_IMPACT'] - fg_impact_means.loc[row['POSITION']]) /
                           (fg_impact_stds.loc[row['POSITION']] + 1e-10)
                if row['POSITION'] in fg_impact_means.index else 0,
                axis=1
            )
        elif raw_stat == 'FT_IMPACT':
            z_scores = daily_stats.apply(
                lambda row: (row['FT_IMPACT'] - ft_impact_means.loc[row['POSITION']]) /
                           (ft_impact_stds.loc[row['POSITION']] + 1e-10)
                if row['POSITION'] in ft_impact_means.index else 0,
                axis=1
            )
        else:
            # Regular position-based z-scores for counting stats
            z_scores = daily_stats.apply(
                lambda row: (row[raw_stat] - season_means.loc[row['POSITION'], raw_stat]) /
                           (season_stds.loc[row['POSITION'], raw_stat] + 1e-10)
                if row['POSITION'] in season_means.index else 0,
                axis=1
            )

        # Invert turnovers (fewer is better)
        if raw_stat == 'TOV':
            z_scores = -z_scores

        z_scores_df[z_col] = z_scores

    # Step 3: Cap extreme z-scores
    Z_SCORE_CAP = 5.0
    nine_cat_z_cols = list(nine_cat_raw.values())

    for z_col in nine_cat_z_cols:
        z_scores_df[f'{z_col}_CAPPED'] = z_scores_df[z_col].clip(-Z_SCORE_CAP, Z_SCORE_CAP)

    # Step 4: Calculate NIGHT_SCORE (sum of 9 capped z-scores, equal weight)
    capped_cols = [f'{z}_CAPPED' for z in nine_cat_z_cols]
    z_scores_df['NIGHT_SCORE'] = z_scores_df[capped_cols].sum(axis=1)

    # Additional metrics
    z_scores_df['OVERALL_Z'] = z_scores_df[nine_cat_z_cols].mean(axis=1)

    return z_scores_df


def main():
    server = 'http://127.0.0.1:4444'

    # Season Stats Test
    driver = start_remote_server(server, False)
    season_stats = scrape_stats(driver, False)
    season_means, season_stds, fg_impact_means, fg_impact_stds, ft_impact_means, ft_impact_stds = get_season_averages(season_stats)
    print(season_means)
    print(season_stds)

    # Daily Stats Test
    driver = start_remote_server(server, True)
    daily_stats = scrape_stats(driver, True)
    print(daily_stats.head(10))

    player_z_scores_weighted_df = player_z_scores_weighted(season_means, season_stds, daily_stats, fg_impact_means, fg_impact_stds, ft_impact_means, ft_impact_stds)
    player_z_scores_weighted_df = player_z_scores_weighted_df.sort_values(by='OVERALL_Z', ascending=False)
    print(player_z_scores_weighted_df.head(10))

    # Save top 10 of each dataframe to separate files
    with open('daily_stats.txt', 'w') as f:
        f.write("Daily Stats - Top 15\n")
        f.write("="*80 + "\n\n")
        f.write(daily_stats.head(15).to_string())
        f.write("\n")

    with open('z_scores.txt', 'w') as f:
        f.write("Z-Scores - Top 15 by OVERALL_Z (9-Cat Position-Based)\n")
        f.write("="*80 + "\n\n")
        f.write(player_z_scores_weighted_df.head(15).to_string())
        f.write("\n")

if __name__ == '__main__':
    main()