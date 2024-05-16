#!../venv/bin/python3.11

from parser import parser

def custom_score(player) -> int:
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
    

def main():
    season1 = '2023-24'
    pd = parser(season1)
    season23_24 = {}
    for index, player in pd.iterrows():
        player_name = player['PLAYER_NAME']
        season23_24[player_name] = custom_score(player)
    sorted23_24 = dict(sorted(season23_24.items(), key=lambda item: -item[1]))
    for person, score in sorted23_24.items():
        print(f'{person:<25}: {score}')

if __name__ == '__main__':
    main()