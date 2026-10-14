# Poke: Collectr price check

Checks how close the prices in a Collectr portfolio are to real TCGplayer market prices.

## How it works

1. **Collectr**: opens the public showcase page in headless Chromium (the card data only renders in a real browser) and reads every card's product ID, printing, condition, grade, quantity and Collectr price from the page payload.
2. **PokemonPriceTracker API** (`API_KEY`): looks up each card by TCGplayer product ID and picks the matching printing and condition. It also pulls 14 days of daily TCGplayer price history, plus eBay graded sales for slabs.
3. **TCGplayer live**: calls TCGplayer's own public `pricepoints` endpoint as a cross-check on the API.

Collectr product IDs are TCGplayer product IDs, except for some Japanese cards where Collectr uses its own ID (10,000,000 and up). For those, the script searches by name and number to find the real TCGplayer listing.

## Run

```bash
npm install
API_KEY=... npm run compare
# options
npm run compare -- --profile <showcase uuid> --collection Main --grade 477059=psa9 --out reports/custom
```

The script only reads the collection the showcase shows by default (currently `Main`). Graded cards are only scored when you pass `--grade <productId>=<grade>`, with grade keys like `psa10`, `psa9`, `cgc9_5`, `bgs9`. Each run costs about 2 to 3 API credits per card.

Output goes to `reports/<date>/`:

- `report.md`: summary and per-card table
- `comparison.csv`: the same table as a CSV
- `raw.json`: raw Collectr and API data for each card

## Findings, 2026-10-14 (Main folder, 28 line items, Collectr total $933.90)

See [`reports/2026-10-14/report.md`](reports/2026-10-14/report.md) for the full table.

**For raw cards, Collectr's total ($883.25) is within $0.23 of TCGplayer's ($883.48), but that is partly errors canceling out.** The median per-card gap is 1.2%. 25 of 27 raw cards are within 5%, and the per-card errors add up to $15.03 (1.7% of value). The two biggest misses (Mega Darkrai +$4.36, Mew JP -$4.32) almost exactly offset each other. Without Mew JP, Collectr reads about $4 high, because most cards drifted down during the lag.

With the Deoxys PSA 9 at its recent eBay price ($60), the Main folder is worth about **$943.48** on TCGplayer and eBay prices, vs Collectr's $933.90.

Collectr's price is TCGplayer's market price, just delayed:

- **About 2 days stale.** 14 cards match TCGplayer's Oct 12 price to the cent and match no other day. Most of the remaining error comes from this lag, not from a different method.
- **The +/- change is a 7-day change.** For 12 cards, the change is measured from the Oct 5 price. It is not a daily change.
- **Cheap cards look worse.** On cards that trade often and cost under $10 (Lapras -12%, Meowth +4.6%, Swinub +4.6%), TCGplayer's market price moves within the day, so a snapshot taken at a different time misses. A few cents is a large percentage at these prices.

Specific problems:

| Card | Issue | Impact |
|---|---|---|
| Mew 183/172 (JP, VSTAR Universe) | Collectr uses its own product 10009707, not the TCGplayer listing 571721 | Collectr $44.18 vs TCGplayer $48.50 (-8.9%), the largest % miss |
| Mega Darkrai ex 114/081 (JP) | The 2-day lag hit while the price was falling ($186.65 → $181.54 → $177.18) | Collectr +$4.36 (+2.5%), the largest $ miss |
| Zapdos 15/62 (Fossil) | Priced as **Unlimited** Holo ($38.69, exact). TCGplayer's headline price ($198.67) is **1st Edition** | Correct if your card is Unlimited. If it has the 1st Edition stamp, it is undervalued by about $160 |
| Deoxys VSTAR GG46 (PSA 9) | Collectr shows $50.65, close to the all-time PSA 9 median ($50). Recent PSA 9 sales are about $60 | Undervalued by $9.35 (-15.6%) against recent sales |

The API checks out against TCGplayer's own live endpoint: median gap 0.27%, with the differences explained by when each was snapshotted.

The report was produced with `npm run compare -- --grade 477059=psa9`.
