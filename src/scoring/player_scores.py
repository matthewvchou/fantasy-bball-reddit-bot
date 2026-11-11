import pandas as pd

# Last-season players below this many minutes a game are left out of the baseline
MIN_BASELINE_MINUTES = 24
Z_SCORE_CAP = 10.0

# Percentages are scored as volume-weighted impacts (FG_IMPACT, FT_IMPACT) instead.
COUNTING_STATS = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'FG3M', 'TOV']
NINE_CATS = ['FG_IMPACT', 'FT_IMPACT', 'FG3M', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV']


def build_baseline(season_stats: pd.DataFrame, positions: dict[int, str]):
    """
    Build per-position means and standard deviations from a season's per-game stats.

    Only players averaging at least MIN_BASELINE_MINUTES with a known position are used.

    Args:
        season_stats: Per-game season DataFrame (PLAYER_ID, MIN, FGA, FG_PCT, FTA, FT_PCT, etc.)
        positions: PLAYER_ID -> 'G', 'F' or 'C'

    Returns:
        Tuple of (means, stds) DataFrames indexed by position, with FG_IMPACT and FT_IMPACT columns.
    """
    base = season_stats[season_stats['MIN'] >= MIN_BASELINE_MINUTES].copy()
    base['POSITION'] = base['PLAYER_ID'].map(positions)
    base = base.dropna(subset=['POSITION'])

    pct_means = base.groupby('POSITION')[['FG_PCT', 'FT_PCT']].mean()
    base['FG_IMPACT'] = (base['FG_PCT'] - base['POSITION'].map(pct_means['FG_PCT'])) * base['FGA']
    base['FT_IMPACT'] = (base['FT_PCT'] - base['POSITION'].map(pct_means['FT_PCT'])) * base['FTA']

    stat_cols = COUNTING_STATS + ['FG_IMPACT', 'FT_IMPACT']
    means = base.groupby('POSITION')[stat_cols].mean()
    stds = base.groupby('POSITION')[stat_cols].std()
    means[['FG_PCT', 'FT_PCT']] = pct_means
    return means, stds


def score_players(night_stats: pd.DataFrame, positions: dict[int, str], means: pd.DataFrame, stds: pd.DataFrame) -> pd.DataFrame:
    """
    Score one night's player lines against last season's position baseline.

    Players with no known position are dropped. Turnovers are inverted so fewer is better.
    NIGHT_SCORE is the sum of the nine capped z-scores. OVERALL_Z is the mean of the uncapped ones.

    Args:
        night_stats: Processed nightly DataFrame from the scraper (needs PLAYER_ID)
        positions: PLAYER_ID -> 'G', 'F' or 'C'
        means: Per-position means from build_baseline
        stds: Per-position standard deviations from build_baseline

    Returns:
        DataFrame of the night's players with POSITION, Z_ columns, NIGHT_SCORE, OVERALL_Z and ESPN_SCORE,
        sorted by NIGHT_SCORE descending.
    """
    night = night_stats.copy()
    night['POSITION'] = night['PLAYER_ID'].map(positions)
    unknown = night['POSITION'].isna().sum()
    if unknown:
        print(f"Skipping {unknown} players with no known position")
    night = night.dropna(subset=['POSITION']).copy()

    night['FG_IMPACT'] = night['FGM'] - night['POSITION'].map(means['FG_PCT']) * night['FGA']
    night['FT_IMPACT'] = night['FTM'] - night['POSITION'].map(means['FT_PCT']) * night['FTA']
    night['TOV'] = night['TO']

    for cat in NINE_CATS:
        z = (night[cat] - night['POSITION'].map(means[cat])) / (night['POSITION'].map(stds[cat]) + 1e-10)
        night[f'Z_{cat}'] = -z if cat == 'TOV' else z

    z_cols = [f'Z_{cat}' for cat in NINE_CATS]
    night['NIGHT_SCORE'] = night[z_cols].clip(-Z_SCORE_CAP, Z_SCORE_CAP).sum(axis=1)
    night['OVERALL_Z'] = night[z_cols].mean(axis=1)
    night['ESPN_SCORE'] = (
        night['PTS'] + night['FG3M'] - night['FGA'] + 2 * night['FGM'] - night['FTA'] + night['FTM']
        + night['REB'] + 2 * night['AST'] + 4 * night['STL'] + 4 * night['BLK'] - 2 * night['TO']
    )

    return night.sort_values(by='NIGHT_SCORE', ascending=False).reset_index(drop=True)
