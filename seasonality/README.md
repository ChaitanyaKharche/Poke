# Seasonality check

Tests whether Pokémon singles fall in Sept to Dec and recover in Jan to Apr, and measures post-release price decay. Result page: [`seasonality.html`](seasonality.html).

## Data

- **PriceCharting** public card pages (monthly prices since about Jan 2021, ungraded and graded). Top 15 cards by price from 37 English sets, 1999 to 2025. Each card's first 12 months after its set's release are excluded.
- **PokemonPriceTracker API** (`API_KEY`): every card in three 2026 sets, with 180 days of TCGplayer history, for the release-decay curves (about 760 credits).

Scraped data goes in `seasonality/data/` (gitignored) and is not committed.

## Run (Python 3, standard library only)

```bash
cd seasonality
python3 pc_scrape.py data/pc/cards          # ~525 card pages, about 15 minutes with 4 workers
python3 season.py data/pc used              # ungraded; use manualonly for PSA 10, graded for grade 9
python3 season_tests.py data/pc used        # Jan-Apr vs Sep-Dec within each year, mean and median
API_KEY=... python3 fetch_sets.py data/api  # three 2026 sets with history
python3 decay.py data                       # post-release decay
python3 make_page.py data seasonality.html  # expects data/pc/season_used.json and data/api/decay.json
```

## Findings (Oct 2026)

- **Sept to Dec is not a regular crash.** The basket fell in Sep to Dec in 2 of 5 years (2021 -10.8%, 2023 -3.8%), was flat in 2022, and rose in 2024 (+13.1%) and 2025 (+6.8%).
- **Jan to Apr vs Sep to Dec is close to a coin flip once the trend is removed.** It beat Sep to Dec within the same year in 3 of 5 years (4 of 5 for vintage, 3 of 4 for PSA 10). Raw numbers make Jan to Apr look better every year, but that is the 2023 to 2026 bull market accelerating.
- **The mild soft stretch is Jun to Nov.** July and September ran below trend in 5 of 6 years. January ran above trend in 4 of 5 years. Treat this as a lean: 12 months tested over 5 to 6 years will produce a couple of consistent-looking months by chance.
- **Release decay is the strong, reliable pattern.** Cards worth $5+ in Pitch Black fell a median 34% by day 60, Chaos Rising 60% by day 120, Perfect Order 51% by day 180. By day 120, every chase card in Chaos Rising and Perfect Order was below its early price.
