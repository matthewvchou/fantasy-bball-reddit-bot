# Box-score history in nba_api (issue #29, map #28)

Method: installed `nba_api` 1.12.0 from PyPI and queried the live `stats.nba.com` endpoints on 2026-11-11 from a residential IP. Counts and null rates below are measured, not copied from docs. Rate-limit and cloud claims come from nba_api's own README and maintainer comments. I did NOT test from a cloud IP.

## 1. What is available, by game type

Source: `LeagueGameLog` (`player_or_team_abbreviation="T"` gives team-game rows, `"P"` gives player-game rows), scanning seasons. Parameter names are from `nba_api/stats/library/parameters.py` (`SeasonTypeAllStar`, `LeagueID`).

| Game type | How to request | Earliest season returned | Notes |
|---|---|---|---|
| Regular Season | `season_type_all_star="Regular Season"`, `league_id="00"` | 1946-47 (662 team-game rows) | Full history. |
| Playoffs | `"Playoffs"` | 1946-47 (38 team-game rows) | Full history. |
| Preseason | `"Pre Season"` | 2003-04 (30 team-game rows) | Zero rows for every season 1946-47 to 2002-03. Sparse seasons: 2011-12 has 60, 2020-21 has 98. |
| Play-In | `"PlayIn"` | 2019-20 (2 rows); 12 rows per season from 2020-21 | Extra type, not asked for. |
| All Star | `"All Star"` | Seen in 1983-84 and 1996-97 (2 rows each); 0 in 2024-25 | Not scanned exhaustively. |
| Summer League | `league_id="15"` (`LeagueID.summer_league`) with `season_type_all_star="Regular Season"` | 2007-08 (110 team-game rows) | There is no "Summer League" season type; passing it raises `KeyError: 'resultSet'`. `"Pre Season"` and `"Playoffs"` with league 15 return 0. No rows for 2011-12 and 2020-21. Present through 2025-26 (152 rows). |

Also: a comment in parameters.py (`LeagueIDNullable`) says an empty LeagueID returns 87 games instead of 82 for 2023-24 because of In-Season Tournament games. Always pass `league_id="00"` explicitly.

## 2. Null fields by era

Fraction of null values per column, `LeagueGameLog`, whole regular season. `_PCT` columns are null when attempts are 0, so they stay partly null in every era.

Team rows:

| Season | Null columns (fraction) |
|---|---|
| 1946-47 | FGA/FG_PCT .93; FTA/FT_PCT .76; PF .42; FG3*, OREB, DREB, REB, AST, STL, BLK, TOV 1.0 |
| 1950-51 | FGA .99; FTA .02; AST .99; PF .97; FG3*, OREB, DREB, REB, STL, BLK, TOV 1.0 |
| 1960-61 | FGA .73; REB .74; AST .87; FTA .23; PF .12; FG3*, OREB, DREB, STL, BLK, TOV about 1.0 |
| 1973-74 | FGA, FG3*, OREB, DREB, REB, AST, STL, BLK, TOV all 1.0; PF 0 |
| 1979-80 | FG3M populated; FGA, FG3A, OREB, DREB, REB, AST, STL, BLK, TOV all 1.0 |
| 1983-84 | FG3A .91, OREB .98, DREB .99, STL .96, BLK .91, TOV .92; REB, AST .02 |
| 1996-97 onward | none |

Player rows:

| Season | Null columns (fraction) |
|---|---|
| 1946-47 | FGA .92, FTA .30, AST .98, PF .34; FG3*, OREB, DREB, REB, STL, BLK, TOV, PLUS_MINUS, FANTASY_PTS 1.0 |
| 1960-61 | FGA .38, REB .31, AST .62; OREB, DREB, STL, BLK, TOV, FG3*, PLUS_MINUS, FANTASY_PTS 1.0 |
| 1973-74 | FGA .08, REB .08, AST .08; OREB/DREB .69, STL .72, BLK .69, TOV 1.0; FG3*, PLUS_MINUS, FANTASY_PTS 1.0 |
| 1979-80 | FG3M populated; OREB/DREB .47, STL .28, BLK .18, TOV .35, FANTASY_PTS .55; PLUS_MINUS 1.0 |
| 1983-84 | All counting stats populated; only PLUS_MINUS 1.0 (plus _PCT) |
| 1995-96 | PLUS_MINUS 1.0 |
| 1996-97 onward | Only FG_PCT, FG3_PCT, FT_PCT (zero attempts) |

Takeaways:
- Full counting-stat coverage at player level starts about 1983-84. Fully populated team rows start by 1996-97.
- PLUS_MINUS is null in 1995-96 and populated from 1996-97 (sampled through 2010-11 and 2024-25).
- Steals, blocks, turnovers, and offensive/defensive rebounds are missing or partial before about 1983-84.
- Sampled seasons only. Exact cutover years between samples were not pinned down.

## 3. Per-game box-score endpoints

`BoxScoreTraditionalV2` and `V3` for single games:

| Game | V2 | V3 |
|---|---|---|
| 1983-84 regular season, 0028300005 | 22 players; PLUS_MINUS null for all | 22 players, no nulls |
| 1996-97 regular season, 0029600009 | 37 rows; 17 DNP rows have all stats null | 37 rows, no nulls |
| 2005-06 preseason, 0010500098 | 29 rows; PLUS_MINUS null | 0 rows |
| 2024-25 preseason, 0012400003 | 42 rows; 12 DNP rows all-null | 42 rows, no nulls |

- V2 returns null stats for players who did not play. V3 returned no nulls in these samples. How V3 represents DNP (0 or empty) was not inspected.
- V3 can return empty for old preseason games that V2 has.
- nba_api 1.12.0 deprecation warning: "BoxScoreTraditionalV2 is deprecated ... Data is no longer being published for BoxScoreTraditionalV2 as of the 2025-26 NBA season. Please use BoxScoreTraditionalV3 instead." New code should use V3.
- The V2 doc page (`docs/nba_api/stats/endpoints/boxscoretraditionalv2.md` in swar/nba_api) lists columns only and says nothing about history.

## 4. Rate limits and IP blocking

- nba_api README, "Rate limits and hosting": "`stats.nba.com` throttles rapid requests and does not respond to many cloud-hosting IP ranges (AWS, GCP, Azure, Colab, and others)." Advice: sleep between requests (example `time.sleep(1)`), raise `timeout` (default 30 s), or use `proxy=` / `NBA_API_PROXY`. Source: https://github.com/swar/nba_api/blob/master/README.md
- No numeric rate limit is published. A contributor in issue #176 says a 0.6 s sleep worked well. That is anecdotal. Source: https://github.com/swar/nba_api/issues/176
- Same contributor in #176: "The NBA blocks all cloud hosting providers. This is a reason that integration tests are not run from the CI build." This is a contributor claim, not an NBA statement.
- Open issue with recurring post-deploy read timeouts: https://github.com/swar/nba_api/issues/405
- Symptom is a hang then `ReadTimeout`, not an HTTP error code.
- My observation: `cdn.nba.com/static/json/liveData/...` via plain `curl` (default UA) from a residential IP returned "Access Denied". nba_api's Live endpoints were not tested.
- About 300 `LeagueGameLog` calls at 0.5 to 1 s spacing from a home IP saw no throttling.

## Implications for the bot (flagged only)
- The repo has an `azure-function/` directory and a `Dockerfile`. Azure is on the README's cloud list, so stats.nba.com calls from there may time out. Test from the real deploy target or use a proxy.
- Backfill is limited: preseason starts 2003-04, Summer League 2007-08.

## Not verified
- Behavior from any cloud IP.
- The exact season each null column first fills in.
- V3 DNP representation, and Live (`cdn.nba.com`) endpoint history.
