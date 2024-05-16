#!../venv/bin/python3.11

from parser import parser

def custom_score(player) -> int:
    '''
    Function that calculates the individual custom score for a player based on season averages and usage rates
    '''
    gp_multiplier = player['GP'] / 82
    minutes_multiplier = player['MIN'] / 48
    fg_made = player['FGA'] * player['FG_PCT']
    fg_missed = player['FGA'] - fg_made
    fg = 0.5 * (fg_made - fg_missed)
    ft_made = player['FTA'] * player['FT_PCT']
    ft_missed = player['FTA'] - ft_made
    ft = ft_made - ft_missed
    stocks = 2 * (player['BLK'] + player['STL'])
    threes = 0.75 * player['FG3M']
    return (fg + ft + stocks + threes + player['PTS'] + player['REB'] + player['AST'] - player['TOV']) * (gp_multiplier + minutes_multiplier)

def make_ranking(season: str) -> dict:
    '''
    Function that creates a sorted dictionary (greatest -> least) of players based on their custom scores
    '''
    pd = parser(season)
    season_scores = {}
    for index, player in pd.iterrows():
        season_scores[player['PLAYER_NAME']] = custom_score(player)
    return dict(sorted(season_scores.items(), key=lambda item: -item[1]))

def main():
    season23_24 = make_ranking('2023-24')
    for person, score in season23_24.items():
        print(f'{person:<25}: {score}')

if __name__ == '__main__':
    main()