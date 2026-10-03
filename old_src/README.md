# old_src — Selenium backup pipeline

Self-contained copy of the original Basketball Monster (Selenium) scraper + Reddit poster.
Use only as an emergency fallback if the `nba_api` pipeline in `src/` is down.

Nothing in `src/` imports from here, and nothing here imports from `src/`.

## Run

```
./old_src/post_daily.sh      # scrape + post top 10 to r/fantasybball (real post)
./old_src/test_scraper.sh    # scrape only, prints stats / z-scores, no post
```

## Requirements
- Repo `venv` (`../venv`) with `requirements.txt` installed
- Java + Selenium standalone jar (default `~/Downloads/selenium-server-4.25.0.jar`;
  override with `SELENIUM_JAR=/path/to.jar ./old_src/post_daily.sh`)
- Chrome installed
- `.env` at the repo root with `MY_ID`, `MY_SECRET`, `MY_USERNAME`, `MY_PASSWORD`

## Files
- `basketball_monster_scraper.py` — Selenium + BeautifulSoup scrape, ESPN score, season/daily z-scores
- `daily_top_ten.py` — builds the Reddit post from the scrape and submits it (uses praw)
- `post_daily.sh` / `test_scraper.sh` — start the Selenium server on :4444, run the Python, clean up

To test without posting to the real subreddit, edit `main()` in `daily_top_ten.py` to call
`post(title, top10, False)` (posts to r/bballfanalyst).
