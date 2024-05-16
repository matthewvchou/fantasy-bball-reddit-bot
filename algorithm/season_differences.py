#!../venv/bin/python3.11

from season_averages import make_ranking

def get_differences(prev_season: dict, curr_season:dict) -> dict:
    '''
    Function that creates a sorted dictionary (greatest -> least) of players based on the difference between two seasons

    Note: Only includes players that were present in both seasons
    '''
    differences = {}
    for person, score in curr_season.items():
        if person in prev_season:
            differences[person] = score - prev_season[person]
    return dict(sorted(differences.items(), key=lambda item: -item[1]))

def main():
    curr_season = make_ranking('2023-24')
    prev_season = make_ranking('2022-23')
    season_differences = get_differences(prev_season, curr_season)
    
    for person, differences in season_differences.items():
        print(f'{person:<25}: {differences}')

if __name__ == '__main__':
    main()