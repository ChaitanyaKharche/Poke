import json, os, statistics as st, sys
from datetime import date, timedelta
BASE = sys.argv[1]
TODAY = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date.today()
SETS = {'24722': ('30th Celebration', '2026-09-16'), '24837': ('30th Classic Collection', '2026-09-16'),
        '24541': ('Ascended Heroes', '2026-01-30'), '24587': ('Perfect Order', '2026-03-27'),
        '24655': ('Chaos Rising', '2026-05-22'), '24688': ('Pitch Black', '2026-07-17')}

def nm_series(card):
    hv = (card.get('priceHistory') or {}).get('variants') or {}
    var = (card.get('prices') or {}).get('primaryPrinting')
    h = ((hv.get(var) or {}).get('Near Mint') or {}).get('history') or []
    return {date.fromisoformat(x['date'][:10]): x['market'] for x in h if x.get('market')}

def at(s, d, tol=7):
    ks = [k for k in s if k <= d and (d - k).days <= tol]
    return s[max(ks)] if ks else None

out = {}
for sid, (name, rel) in SETS.items():
    rel = date.fromisoformat(rel)
    cards = json.load(open(os.path.join(BASE, 'api', f'set_{sid}.json')))['data']
    ser = [(c['name'], c.get('rarity'), nm_series(c)) for c in cards]
    ser = [x for x in ser if x[2]]
    first = min(min(s) for _, _, s in ser)
    base_d = max(first, rel + timedelta(days=7))
    checkpoints = sorted({base_d, TODAY - timedelta(days=60), TODAY - timedelta(days=30), TODAY - timedelta(days=14), TODAY})
    checkpoints = [d for d in checkpoints if d >= base_d]
    ranked = sorted([(at(s, base_d) or 0, n, r, s) for n, r, s in ser], reverse=True, key=lambda x: x[0])
    top10 = ranked[:10]
    print(f'\n=== {name} (released {rel}; history from {first}; base {base_d}, day {(base_d - rel).days})')
    def total(group, d):
        vals = [(at(s, d), at(s, base_d)) for _, _, _, s in group]
        vals = [(a, b) for a, b in vals if a and b]
        return sum(a for a, _ in vals), sum(b for _, b in vals), len(vals)
    for label, group in (('whole set', ranked), ('top 10 chase', top10), ('set minus #1 card', ranked[1:])):
        line = []
        for d in checkpoints:
            a, b, n = total(group, d)
            line.append(f'{d.isoformat()[5:]} ${a:,.0f} ({(a / b - 1) * 100:+.0f}%)')
        print(f'  {label:18}: ' + ' | '.join(line))
    print('  top 5 cards at base:')
    for p0, n, r, s in ranked[:5]:
        now = at(s, TODAY)
        d30 = at(s, TODAY - timedelta(days=30))
        print(f'    {n[:40]:40} {r or "":28} base ${p0:8.2f} -> now ${now or 0:8.2f} ({((now or 0) / p0 - 1) * 100:+.0f}%)' + (f'  last 30d {((now or 0) / d30 - 1) * 100:+.0f}%' if d30 else ''))
    # last 30 days breadth
    pairs = [(at(s, TODAY), at(s, TODAY - timedelta(days=30))) for _, _, _, s in ranked if at(s, TODAY - timedelta(days=30)) and (at(s, TODAY - timedelta(days=30)) or 0) >= 5]
    if pairs:
        print(f'  cards >= $5 a month ago: {len(pairs)}, down over last 30 days: {sum(1 for a, b in pairs if a < b)}, median {st.median(a / b - 1 for a, b in pairs) * 100:+.0f}%')
    out[name] = {'release': rel.isoformat(), 'base': base_d.isoformat()}
