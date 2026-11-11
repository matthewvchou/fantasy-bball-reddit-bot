# Per-season player positions: sources

Research for issue #30 (child of map #28). Question: where can per-season positions come from, allowing several positions per player per season (e.g. G and F)?

Date: 2026-11-11. No notes folder existed in the repo, so this lives in `docs/research/`.

## Method and limits

- Endpoint shapes come from the `swar/nba_api` repo at commit `e077ba5` (docs, `src/`, `tests/`). That repo is a community client, not the NBA. It is the best primary record of the NBA's undocumented `stats.nba.com` API.
- Real response values come from the repo's recorded smoke-test responses (`tests/integration/smoke/cassettes/`). These are raw `stats.nba.com` payloads for the 2025-26 season. I parsed them myself.
- **I could not call `stats.nba.com` or `cdn.nba.com` live.** Both timed out or returned "Access Denied" from this machine. Anything marked UNVERIFIED needs a live call from a non-blocked network before the design is locked.
- The NBA publishes no official documentation for `stats.nba.com`.

## Summary

- No NBA endpoint returns a per-player, per-season list of positions. Every endpoint returns one string per player per request.
- The multi-position value is a hyphenated string: `G`, `F`, `C`, `G-F`, `F-G`, `F-C`, `C-F`. Parse it by splitting on `-`.
- The NBA's position vocabulary is three letters (G, F, C). It is not the five-position PG/SG/SF/PF/C scheme.
- Which season a returned position belongs to is UNVERIFIED for every endpoint. `Season` is a parameter on `PlayerIndex` and `CommonTeamRoster`, but I found no source saying the position is the position for that season rather than the current one.
- Full history coverage of positions is not demonstrated for any NBA endpoint. See the era table.
- Basketball-Reference has a per-season `Pos` for all history, but its terms bar scraping and reuse in competing databases. Treat it as a cross-check, not an ingest source.

## nba_api endpoints

| Endpoint | Position field | Value shape | Season-aware input | Era evidence |
|---|---|---|---|---|
| `playerindex` | `POSITION` | G, F, C, G-F, F-G, F-C, C-F | `Season`, `Historical` | 2025-26 recording: 557 rows, earliest `FROM_YEAR` 2003. `Historical=1` coverage UNVERIFIED. |
| `commonteamroster` | `POSITION` | G, F, C, G-F, F-C, C-F | `Season`, `TeamID` | 2025-26 recording only. Older seasons UNVERIFIED. |
| `commonplayerinfo` | `POSITION` | Long words, e.g. `Guard` (one sample) | `PlayerID` only | Any player, but returns one current-style value. |
| `commonallplayers` | none | n/a | `Season` | 5111 rows, `FROM_YEAR` back to 1946. No position column. |
| `boxscoretraditionalv2` / `v3` | `START_POSITION` / `position` | `F`, `G`, `C`, or empty | `GameID` | Starters only; bench is empty (13 of 23 empty in the sample game). Per game, not per season. |
| `leaguedashplayerstats`, `leaguedashplayerbiostats` | none returned; `PlayerPosition` is a filter | filter accepts only `F`, `C`, `G` | `Season` | See the filter caveat below. |
| `nba_api.live` boxscore (`cdn.nba.com`) | `position` | Sample shows `SF` | live game | Current games only. Format UNVERIFIED. |

Evidence for the table:

- `PlayerIndex` columns include `POSITION`, plus `FROM_YEAR`, `TO_YEAR`, `ROSTER_STATUS`, `IS_DEFUNCT`. Parameters: `docs/nba_api/stats/endpoints/playerindex.md`. Recorded 2025-26 value counts: G 234, F 165, C 62, G-F 38, F-C 30, C-F 17, F-G 11.
- `CommonTeamRoster` recorded value counts for one team (CLE, 2025-26): G 8, F 4, G-F 2, C 2, F-C 2, C-F 1. Source: `docs/nba_api/stats/endpoints/commonteamroster.md` and its recording.
- `CommonPlayerInfo` returned `Guard` for player 1628378. Same words-not-letters style as the filter class `PlayerPositionNullable` in `src/nba_api/stats/library/parameters.py`. Source: `docs/nba_api/stats/endpoints/commonplayerinfo.md`.
- `BoxScoreTraditionalV2` sample game `0022200552`: starters F 4, G 4, C 2, empty 13.
- `PlayerPosition` filter: `docs/open_api_findings.md` (audit dated 2026-10-21) says the server rejects `C-F`, `F-C`, `F-G`, `G-F` on `LeagueDashPlayerStats` and accepts `F`, `C`, `G`. So the filter groups by single letters and cannot be used to recover multi-position membership directly. It might still be usable as three queries per season (one per letter); whether a G-F player appears under both G and F is UNVERIFIED.

## Other sources

- **Basketball-Reference** (Sports Reference). Per-season `Pos` is a single value from PG, SG, SF, PF, C in the Per Game table. LeBron James's page shows a different single value in most seasons (SG, SF, PF, PG, C across 2003-04 to 2026-27). The player header lists several positions at once ("Small Forward, Power Forward, Point Guard, Center, and Shooting Guard"). The play-by-play table adds estimated minute shares per position (PG%, SG%, SF%, PF%, C%). That play-by-play table is the closest thing to a true multi-position-per-season source. Its start year is UNVERIFIED, and BBR's glossary has no entry on `Pos` or how it is derived.
  - Terms (`https://www.sports-reference.com/data_use.html`): no aggressive spidering; excessive activity can get an IP blocked; no building a competing database or "material substitute"; no use of data for AI training or prompting; custom bulk data starts at $5,000. This rules out a bulk scrape for the project without written permission.
- **NBA live data on `cdn.nba.com`**. Has a `position` per player, current games only. Not a history source.
- **Not checked:** official NBA roster pages on nba.com, Kaggle/other datasets, pre-1980 NBA records. I make no claim about them.

## Hosting risk (affects the map)

`nba_api`'s README and `docs/ai_agents.md` state that `stats.nba.com` "does not respond to many cloud-hosting IP ranges (AWS, GCP, Azure, Colab, and others)". The map plans a hyperscaler host with a nightly ingest. Any `stats.nba.com`-based ingest, including positions, may need a proxy or a non-cloud runner. `cdn.nba.com` also refused a plain request from this machine.

## Implications for the schema (for #34)

- Store positions as a set per player per season (a child table of rows like `player_id, season, position`), populated by splitting the hyphenated string. A single string column loses the ability to query "all guards".
- Use the NBA's G/F/C vocabulary unless the ticket decides to add the five-position scheme from another source.
- Because season attribution is unverified, plan to capture `PlayerIndex` or `CommonTeamRoster` per season during the backfill and keep the raw payloads (as the map already says) so it can be re-derived.

## Open questions needing a live call

1. Does `playerindex` with `Historical=1` and an old `Season` (e.g. 1995-96) return rows, and is `POSITION` that season's value or the player's latest value?
2. Does `commonteamroster` for old seasons return `POSITION`, and from which season is it non-empty?
3. Does a G-F player appear under both `G` and `F` in the `PlayerPosition` filter?
4. Is `stats.nba.com` reachable from the planned server, or does it need a proxy?

## Sources

- https://github.com/swar/nba_api (commit `e077ba5fd381f50bf97c3e834f7eedf56a9c5f52`): `docs/nba_api/stats/endpoints/{playerindex,commonteamroster,commonplayerinfo,boxscoretraditionalv3}.md`, `docs/nba_api/live/endpoints/boxscore.md`, `docs/nba_api/stats/library/parameters.md`, `docs/open_api_findings.md`, `docs/ai_agents.md`, `README.md`, `tests/integration/smoke/cassettes/`.
- https://www.sports-reference.com/data_use.html
- https://www.basketball-reference.com/players/j/jamesle01.html
- https://www.basketball-reference.com/leagues/NBA_2020_play-by-play.html
- https://www.basketball-reference.com/about/glossary.html
