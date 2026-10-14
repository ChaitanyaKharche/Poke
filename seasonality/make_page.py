import json, math, os, sys
BASE = sys.argv[1]
OUT = sys.argv[2]
toP = lambda x: None if x is None else round((math.exp(x) - 1) * 100, 1)
s = json.load(open(f'{BASE}/pc/season_used.json'))['ALL']
rows = {int(r[0]): r for r in s['rows']}
raw = [{'label': str(y), 'jan_apr': toP(rows[y][2]), 'sep_dec': toP(rows[y][1])} for y in range(2021, 2027)]
# within-year detrended windows (from season_tests, all cards, mean)
dt = {2021: (3.7, -0.1), 2022: (-0.4, 0.8), 2023: (3.7, -4.4), 2024: (-0.7, 6.3), 2025: (12.5, -6.6), 2026: (6.2, None)}
detr = [{'label': str(y), 'jan_apr': a, 'sep_dec': b} for y, (a, b) in dt.items()]
months = [{'label': m, 'mean': toP(v['mean']), 'below': v['neg'], 'n': v['n'],
           'years': {y: toP(x) for y, x in v['by_year'].items()}} for m, v in s['summary'].items()]
d = json.load(open(f'{BASE}/api/decay.json'))
decay = []
for name in ('Perfect Order', 'Chaos Rising', 'Pitch Black'):
    r = d[name]['res']['cards >= $5 at base']
    pts = [{'x': d[name]['base_day'], 'y': 0}] + [{'x': int(k), 'y': round(v['median'] * 100), 'down': round(v['down'] * 100), 'n': v['n']} for k, v in r.items()]
    decay.append({'name': name, 'points': pts})
data = {'raw': raw, 'detr': detr, 'months': months, 'decay': decay}
html = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'page_template.html')).read().replace('/*DATA*/null', json.dumps(data))
open(OUT, 'w').write(html)
print('wrote', OUT, len(html))
