# Team stints and transaction history sources (issue #31, map #28)

## Answer

- Best source for dated moves: the NBA's static Player Movement JSON, `https://stats.nba.com/js/data/playermovement/NBA_Player_Movement.json`. One file, 10,141 rows, 2015-07-01 to 2026-11-10 (fetched 2026-11-11).
- nba_api has **no** endpoint for transactions or player movement. Its endpoints give season-level team only, not start/end dates.
- Stints with start/end dates are not provided anywhere directly. They must be built by pairing transactions per player (sign/trade-in = start, waive/trade-out = end).
- Nothing checked gives dated moves before 2015-07-01. Season-level teams go back to each player's debut.

## nba_api (swar/nba_api docs, `docs/nba_api/stats/endpoints/`)

The endpoint doc listing was grepped for move/trans: no match. Closest endpoints:

| Endpoint | Gives | Dates? |
|---|---|---|
| `playercareerstats` | `SeasonTotals*` per season and team (`SEASON_ID`, `TEAM_ID`, `TEAM_ABBREVIATION`, GP) | Season only |
| `commonplayerinfo` | Current `TEAM_ID`, `ROSTERSTATUS`, `FROM_YEAR`, `TO_YEAR`, `LAST_AFFILIATION` | Years only |
| `playerindex` | Team per season (`Season`, `LeagueID` required), `Historical` filter | Season only |
| `commonteamroster` | Roster per team and season. Only date column is `BIRTH_DATE`. No acquired-how field. | No |
| `playergamelog` / `leaguegamelog` / `leaguegamefinder` | One row per game with team and game date | Per game |
| `franchiseplayers`, `franchisehistory`, `commonteamyears` | Franchise-level history | No |

Inference (not stated in docs): game logs give first/last game date per team, so "played stints" can be derived for every season they cover. This misses time on a roster without playing.

Docs pages carry stale "last validated" notes (2020 to 2023), so column lists may have drifted.

## NBA Player Movement JSON (first-party, undocumented)

Verified by downloading and parsing the file.

- Shape: `NBA_Player_Movement.rows[]`.
- Fields: `Transaction_Type`, `TRANSACTION_DATE` (midnight timestamp), `TRANSACTION_DESCRIPTION` (free text), `TEAM_ID` (float), `TEAM_SLUG`, `PLAYER_ID` (float), `PLAYER_SLUG`, `Additional_Sort` (other team ID on trades, else 0), `GroupSort` (type plus sequence ID).
- Types and counts: Signing 4668, Waive 3448, Trade 1813, ContractConverted 139, AwardOnWaivers 73.
- Rows per year: about 690 to 1,030 for 2016-2026; 498 for 2015 (starts 2015-07-01).
- Signings include 10-day contracts and extensions (258 extensions; these are not team changes).
- `PLAYER_ID` matches nba_api IDs, so joins work.

Caveats:
- No structured contract type, end date, or acquired-from team. Details live in the description text. Trades need `GroupSort` plus `Additional_Sort` to find the partner.
- No event for contract expiry or free agency. Stint ends for expiring contracts must be inferred.
- Undocumented and unofficial; it may change or be blocked. It loaded with a browser User-Agent; behavior without one was not tested.
- Completeness is unknown. I did not check it against a second source. I do not know whether G League or Exhibit 10 moves are included.

## Other sources

- Pro Sports Transactions (prosportstransactions.com/basketball): HTTP 403 to automated fetch. Not verified. Third party, not primary.
- Basketball-Reference transactions: not checked (third party).
- Not checked: nba.com's official transactions page, which the JSON likely backs.

## Suggestions for #34

1. Use the Player Movement JSON as the dated-move source from 2015-07-01.
2. Use `playercareerstats` for season-level team history before 2015.
3. Optionally cross-check stints with `playergamelog` first/last game dates.

## Open questions

- Is the JSON complete versus a second source?
- Is it stable enough for scheduled scraping?
- How to end stints for contract expiry?
