import json, os, statistics as st, sys
BASE = sys.argv[1]  # data dir holding api/set_<id>.json
from datetime import date
SETS = {'24688': ('Pitch Black', '2026-07-17'), '24655': ('Chaos Rising', '2026-05-22'), '24587': ('Perfect Order', '2026-03-27')}
CHECK = [30, 45, 60, 90, 120, 150, 180]
out = {}
for sid, (name, rel) in SETS.items():
    rel = date.fromisoformat(rel)
    cards = json.load(open(os.path.join(BASE, 'api', f'set_{sid}.json')))['data']
    series = []
    for c in cards:
        ph = (c.get('priceHistory') or {}).get('variants') or {}
        var = (c.get('prices') or {}).get('primaryPrinting')
        h = (ph.get(var) or {}).get('Near Mint', {}).get('history') or []
        pts = {(date.fromisoformat(x['date'][:10]) - rel).days: x['market'] for x in h if x.get('market')}
        if pts: series.append((c['name'], c.get('rarity'), pts))
    def at(pts, d):
        ks = [k for k in pts if k <= d]
        return pts[max(ks)] if ks and d - max(ks) <= 10 else None
    base_day = max(14, min(min(p) for _, _, p in series))
    print(f'\n{name} (released {rel}, {len(series)} cards with history), base = day {base_day} after release')
    res = {}
    for tier, lo, hi in (('cards >= $5 at base', 5, 1e9), ('cards < $5 at base', 0, 5)):
        rows = []
        for n, r, p in series:
            b = at(p, base_day)
            if b and lo <= b < hi: rows.append((n, r, p, b))
        line = []
        for d in CHECK:
            pairs = [(at(p, d), b) for _, _, p, b in rows if at(p, d)]
            if len(pairs) < 5 or d > max(max(p) for _, _, p, _ in rows): continue
            med = st.median(x / b - 1 for x, b in pairs)
            vw = sum(x for x, _ in pairs) / sum(b for _, b in pairs) - 1
            share_down = sum(1 for x, b in pairs if x < b) / len(pairs)
            line.append(f'd{d}: median {med*100:+.0f}%, value-wtd {vw*100:+.0f}%, {share_down*100:.0f}% of cards down')
            res.setdefault(tier, {})[d] = {'median': med, 'vw': vw, 'down': share_down, 'n': len(pairs)}
        print(f'  {tier} (n={len(rows)}):'); [print('     ', l) for l in line]
    out[name] = {'base_day': base_day, 'res': res}
json.dump(out, open(os.path.join(BASE, 'api', 'decay.json'), 'w'), indent=1)
