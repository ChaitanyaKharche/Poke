# Slab Check

A phone page for card shows: search a card, see what each grade has actually sold for, and type the asking price to get an offer and a verdict.

## What it checks

For each grade (PSA 10, PSA 9, CGC 10, TAG 10, BGS 9.5 and more) and for raw Near Mint:

- **Recent sold comps**: average sale price over the last 30 days, the range, and the last 5 days with sales (eBay graded sales via PokemonPriceTracker).
- **Sales per week**: how fast it resells.
- **Trend**: last 30 days vs the 60 days before.
- **PSA 10 vs raw**: how many times the raw price a PSA 10 sells for, and whether a PSA 9 sells below raw.
- **New set warning**: sets under 6 months old usually keep falling.
- **Offer math**: open at 75% of recent sales, max 85% (80% when the price is falling), compared against your budget minus a gift reserve.

It also lists good PSA 10 targets under your budget (2+ sales a week, price not falling, set older than 6 months) and gift ideas (raw cards of popular Pokémon, $8 to $40).

## Refresh before a show

The page can't call the price API itself (published pages block outside requests, and the API key must not be in a page), so prices are loaded when the page is built.

```bash
API_KEY=... python3 slabs/scan.py slabs/data/scan.json           # ~7,900 English cards, $5-$150 raw, ~15,800 credits, ~40 min
python3 slabs/build_page.py slabs/data/scan.json slabs/data/slab-check.html
```

Then republish `slabs/data/slab-check.html` to the same artifact. The scan resumes from `scan.json.partial` if interrupted. `slabs/data/` is gitignored, since the API terms don't allow redistributing the data.

## Limits

- English cards only, raw price $5 to $150.
- eBay graded sales only; no PSA population data (that needs the Business plan).
- Each sale-day price is that day's average, not individual sales.
