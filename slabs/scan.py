"""Scan English cards in a raw price range and keep the numbers a slab buyer needs.

For every card: raw Near Mint price, and per grade (PSA 10, PSA 9, ...) the recent sold
prices, sales per week and price trend from eBay graded sales (PokemonPriceTracker API).

Usage:
    API_KEY=... python3 slabs/scan.py slabs/data/scan.json [--min 5 --max 150]
    API_KEY=... python3 slabs/scan.py slabs/data/scan_high.json --min 150 --max 700

Cost: 2 credits per card (card + eBay data). About 7,900 cards between $5 and $150 raw,
and about 900 more between $150 and $700.
"""
import argparse
import json
import os
import statistics as st
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta

API = 'https://www.pokemonpricetracker.com/api/v2'
GRADES = ['psa10', 'psa9', 'psa8', 'cgc10', 'cgc9_5', 'bgs9_5', 'bgs10', 'tag10', 'ace10']
WINDOWS = [(5, 10), (10, 20), (20, 40), (40, 80), (80, 150), (150, 300), (300, 700)]
PAGE = 50  # eBay data caps a page at 50 cards


def get(path, params):
    url = f'{API}/{path}?' + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + os.environ['API_KEY']})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read()), r.headers
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get('Retry-After') or 30)
                body = e.read().decode()[:200]
                if 'daily' in body.lower():
                    sys.exit(f'Daily credit limit reached: {body}')
                time.sleep(wait + 1)
                continue
            if e.code in (500, 502, 503, 504):
                time.sleep(5 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f'Gave up on {url}')


def grade_stats(sales, history, today):
    """Recent comps, sales per week and trend for one grade."""
    days = sorted(history.items())
    recent = [(d, v) for d, v in days if d >= (today - timedelta(days=30)).isoformat()]
    older = [(d, v) for d, v in days if (today - timedelta(days=90)).isoformat() <= d < (today - timedelta(days=30)).isoformat()]
    def wavg(rows):
        n = sum(v['count'] for _, v in rows)
        return (sum(v['average'] * v['count'] for _, v in rows) / n, n) if n else (None, 0)
    r_avg, r_n = wavg(recent)
    o_avg, o_n = wavg(older)
    med30 = None
    if r_n >= 3:
        expanded = sorted(v['average'] for _, v in recent for _ in range(v['count']))
        med30 = round(st.median(expanded), 2)
    smart = (sales.get('smartMarketPrice') or {}).get('price')
    comp = r_avg if r_n >= 3 else smart or sales.get('medianPrice')
    return {
        'comp': round(comp, 2) if comp else None,
        'med30': med30,
        'n30': r_n,
        'perWeek': round(r_n / 30 * 7, 1),
        'trend': round(r_avg / o_avg - 1, 3) if r_avg and o_avg and r_n >= 2 and o_n >= 3 else None,
        'last5': [round(v['average'], 2) for _, v in days[-5:]],
        'lastSale': (sales.get('lastSaleDate') or '')[:10],
        'median': sales.get('medianPrice'),
        'count': sales.get('count'),
        'low30': round(min(v['average'] for _, v in recent), 2) if recent else None,
        'high30': round(max(v['average'] for _, v in recent), 2) if recent else None,
    }


def compact(card, today):
    prices = card.get('prices') or {}
    ebay = card.get('ebay') or {}
    by_grade = ebay.get('salesByGrade') or {}
    hist = ebay.get('priceHistory') or {}
    grades = {g: grade_stats(by_grade[g], hist.get(g) or {}, today) for g in GRADES if g in by_grade}
    return {
        'id': card['tcgPlayerId'],
        'name': card['name'],
        'set': card.get('setName'),
        'setId': card.get('setId'),
        'num': card.get('cardNumber'),
        'rarity': card.get('rarity'),
        'printing': prices.get('primaryPrinting'),
        'raw': prices.get('market'),
        'rawLow': prices.get('low'),
        'listings': prices.get('listings'),
        'grades': grades,
        'url': card.get('tcgPlayerUrl'),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--min', type=float, default=WINDOWS[0][0])
    ap.add_argument('--max', type=float, default=150)
    args = ap.parse_args()
    today = date.today()
    cards = {}
    if os.path.exists(args.out + '.partial'):
        cards = {c['id']: c for c in json.load(open(args.out + '.partial'))}
    for lo, hi in WINDOWS:
        if hi <= args.min or lo >= args.max:
            continue
        offset, total = 0, None
        while total is None or offset < total:
            body, headers = get('cards', {
                'language': 'english', 'minPrice': max(lo, args.min), 'maxPrice': min(hi, args.max),
                'sortBy': 'price', 'sortOrder': 'desc', 'limit': PAGE, 'offset': offset,
                'includeEbay': 'true', 'days': 90, 'maxDataPoints': 90,
            })
            total = body['metadata']['total']
            for c in body.get('data') or []:
                cards[c['tcgPlayerId']] = compact(c, today)
            offset += PAGE
            print(f'${lo}-{hi}: {min(offset, total)}/{total}  cards kept {len(cards)}  credits left {headers.get("x-ratelimit-daily-remaining")}', flush=True)
            json.dump(list(cards.values()), open(args.out + '.partial', 'w'))
            time.sleep(1.2)
    sets, _ = get('sets', {'language': 'english', 'limit': 500, 'sortBy': 'releaseDate', 'sortOrder': 'desc'})
    release = {s.get('tcgPlayerNumericId'): (s.get('releaseDate') or '')[:10] for s in sets.get('data') or []}
    for c in cards.values():
        c['released'] = release.get(c['setId'])
    json.dump({'scanned': today.isoformat(), 'cards': list(cards.values())}, open(args.out, 'w'))
    os.remove(args.out + '.partial')
    print('done', len(cards), 'cards ->', args.out)


if __name__ == '__main__':
    main()
