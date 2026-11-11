# Player bio fields available from nba_api (issue #32, map #28)

## Answer

Every requested field exists in nba_api 1.12.0 as a column. All are available via `CommonPlayerInfo` (one call per player). Most are also in `PlayerIndex` (one call for all players). Era coverage and gap behavior could NOT be verified live: `stats.nba.com` was unreachable from the research environment (curl returned no HTTP response). Era statements below are therefore unverified and marked as such. Verify with a live call from the target runtime before relying on them.

## Field map (verified from nba_api 1.12.0 source)

| Wanted field | CommonPlayerInfo column | PlayerIndex column | DraftHistory column |
|---|---|---|---|
| Height | `HEIGHT` | `HEIGHT` | - |
| Weight | `WEIGHT` | `WEIGHT` | - |
| Birthdate | `BIRTHDATE` | not present | - |
| Birthplace (city/state) | not present | not present | - |
| Country | `COUNTRY` | `COUNTRY` | - |
| College | `SCHOOL` (also `LAST_AFFILIATION`) | `COLLEGE` | `ORGANIZATION`, `ORGANIZATION_TYPE` |
| Draft year | `DRAFT_YEAR` | `DRAFT_YEAR` | `SEASON` |
| Draft round | `DRAFT_ROUND` | `DRAFT_ROUND` | `ROUND_NUMBER` |
| Draft pick | `DRAFT_NUMBER` | `DRAFT_NUMBER` | `OVERALL_PICK` (also `ROUND_PICK`) |
| Experience | `SEASON_EXP` | not present (derive from `FROM_YEAR`/`TO_YEAR`) | - |

Notes:
- Birthplace: no city/state/birthplace column exists in any of these endpoints. Only `COUNTRY`.
- Birthdate is only in `CommonPlayerInfo`, so a full-roster birthdate list needs one call per player.
- `CommonPlayerInfo` also has `FROM_YEAR`, `TO_YEAR`, `POSITION`, `JERSEY`, `ROSTERSTATUS`, `LAST_AFFILIATION`, `DLEAGUE_FLAG`.
- `PlayerIndex` also has `FROM_YEAR`, `TO_YEAR`, `IS_DEFUNCT`, `ROSTER_STATUS`, and PTS/REB/AST.
- `DraftHistory` takes optional filters (`college_nullable`, `overall_pick_nullable`, `round_num_nullable`, `round_pick_nullable`, season, etc.) and returns `PERSON_ID`, which joins to player ids.
- Data types/format (e.g. height as `"6-9"` string, weight as string, `BIRTHDATE` as ISO-like timestamp) are NOT stated in the source; the library only lists column names. Unverified.

## Era coverage

- `PlayerIndex` has a `Historical` parameter: `"0"` = season only (default), `"1"` = all-time (nba_api `parameters.py`, `Historical` class). Use `Historical=1` to include past players; otherwise only players for the given `Season` (default current season) come back.
- `CommonPlayerInfo` takes a `PlayerID` and `LeagueID` only. Whether it returns data for a given historical player depends on the server; the library does not document this.
- Unverified (from general knowledge, not a primary source here): stats.nba.com is commonly reported to have sparse or empty height/weight/draft/birthdate for pre-1980s players, and `DRAFT_*` is empty for undrafted players. Treat as likely gaps, to be confirmed.
- Undrafted players: draft columns are expected to be empty/"Undrafted"; confirm the exact representation live.

## Gaps and caveats

- No birthplace city/state.
- No live verification of era coverage, null encoding, or value formats (API unreachable here; stats.nba.com is also known to block cloud/datacenter IPs, which matters if the bot runs in Azure Functions - unverified for this project).
- Endpoints are undocumented, unofficial NBA APIs; nba_api only wraps them, so field behavior is owned by NBA, not the library.

## Suggested follow-up (to close the gaps)

Run from the target runtime:
1. `PlayerIndex(historical_nullable="1")` and count nulls per column by `FROM_YEAR` decade.
2. `CommonPlayerInfo(player_id=...)` for a sample: a 1960s star, a 1980s player, an undrafted player, a current rookie.

## Sources

- nba_api 1.12.0 wheel from PyPI, `nba_api/stats/endpoints/commonplayerinfo.py`, `playerindex.py`, `drafthistory.py`, `nba_api/stats/library/parameters.py` (column lists, parameters, `Historical`).
- nba_api endpoint docs: https://github.com/swar/nba_api/blob/master/docs/nba_api/stats/endpoints/commonplayerinfo.md and `.../playerindex.md` (column lists only; no sample values).
- Live API `https://stats.nba.com/stats/...`: attempted, no response, so no values observed.
