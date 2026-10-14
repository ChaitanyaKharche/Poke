import json, os, sys
from datetime import date, timedelta
BASE = sys.argv[1]
SETS = {'24722': ('30th Celebration', '2026-09-16'), '24541': ('Ascended Heroes', '2026-01-30'), '24587': ('Perfect Order', '2026-03-27'),
        '24655': ('Chaos Rising', '2026-05-22'), '24688': ('Pitch Black', '2026-07-17')}
TODAY = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date.today()
for sid, (name, rel) in SETS.items():
    fn = os.path.join(BASE, 'api', f'sealed_{sid}.json')
    if not os.path.exists(fn): print('\n===', name, 'not fetched yet'); continue
    data = json.load(open(fn)).get('data') or []
    rel = date.fromisoformat(rel)
    base_d = max(rel + timedelta(days=7), TODAY - timedelta(days=176))
    print(f'\n=== {name} sealed ({len(data)} products), base {base_d} (day {(base_d - rel).days})')
    rows = []
    for p in data:
        low = p['name'].lower()
        if 'case' in low or ('display' in low and 'mini tin' not in low):
            continue  # skip multi-unit cases and booster displays
        h = {date.fromisoformat(x['date'][:10]): x['unopenedPrice'] for x in (p.get('priceHistory') or []) if x.get('unopenedPrice')}
        if not h: continue
        def at(d, tol=10):
            ks = [k for k in h if k <= d and (d - k).days <= tol]
            return h[max(ks)] if ks else None
        b, now = at(base_d), at(TODAY)
        after = {k: v for k, v in h.items() if k >= base_d}
        if not (b and now and after): continue
        lo_d = min(after, key=after.get)
        rows.append((b, p['name'], b, after[lo_d], lo_d, now))
    rows.sort(reverse=True)
    tot_b = sum(r[2] for r in rows); tot_n = sum(r[5] for r in rows)
    for _, n, b, lo, lo_d, now in rows[:12]:
        print(f'  {n[:58]:58} ${b:8.2f} -> low ${lo:8.2f} ({lo_d.isoformat()[5:]}) -> now ${now:8.2f}  ({(now / b - 1) * 100:+.0f}% since base, {(now / lo - 1) * 100:+.0f}% off low)')
    if rows:
        up = sum(1 for r in rows if r[5] > r[2])
        med = sorted(r[5] / r[2] - 1 for r in rows)[len(rows) // 2]
        print(f'  basket of {len(rows)} products: ${tot_b:,.0f} -> ${tot_n:,.0f} ({(tot_n / tot_b - 1) * 100:+.0f}%); median product {med * 100:+.0f}%; {up} of {len(rows)} up since base')
