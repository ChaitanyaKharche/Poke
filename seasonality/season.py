import glob, json, math, os, statistics as st, sys
from datetime import datetime, timezone

BASE = sys.argv[1]
SERIES = sys.argv[2] if len(sys.argv) > 2 else 'used'  # used = ungraded, manualonly = PSA 10, graded = grade 9
MIN_CENTS = 300
CLIP = 0.5
RELEASE = {
    'pokemon-base-set': '1999-01', 'pokemon-jungle': '1999-06', 'pokemon-fossil': '1999-10', 'pokemon-team-rocket': '2000-04',
    'pokemon-gym-heroes': '2000-08', 'pokemon-neo-genesis': '2000-12', 'pokemon-neo-destiny': '2002-02', 'pokemon-skyridge': '2003-05',
    'pokemon-generations': '2016-02', 'pokemon-evolutions': '2016-11', 'pokemon-team-up': '2019-02', 'pokemon-unified-minds': '2019-08',
    'pokemon-hidden-fates': '2019-08', 'pokemon-cosmic-eclipse': '2019-11', 'pokemon-vivid-voltage': '2020-11',
    'pokemon-shining-fates': '2021-02', 'pokemon-chilling-reign': '2021-06', 'pokemon-evolving-skies': '2021-08',
    'pokemon-celebrations': '2021-10', 'pokemon-fusion-strike': '2021-11', 'pokemon-brilliant-stars': '2022-02',
    'pokemon-astral-radiance': '2022-05', 'pokemon-go': '2022-07', 'pokemon-lost-origin': '2022-09', 'pokemon-silver-tempest': '2022-11',
    'pokemon-crown-zenith': '2023-01', 'pokemon-scarlet-&-violet': '2023-03', 'pokemon-paldea-evolved': '2023-06',
    'pokemon-obsidian-flames': '2023-08', 'pokemon-scarlet-&-violet-151': '2023-09', 'pokemon-paradox-rift': '2023-11',
    'pokemon-paldean-fates': '2024-01', 'pokemon-temporal-forces': '2024-03', 'pokemon-twilight-masquerade': '2024-05',
    'pokemon-stellar-crown': '2024-09', 'pokemon-surging-sparks': '2024-11', 'pokemon-prismatic-evolutions': '2025-01',
}
VINTAGE = {k for k, v in RELEASE.items() if v < '2010'}
MONTHS = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()


def ym(ts):
    d = datetime.fromtimestamp(ts / 1000, timezone.utc)
    return d.year, d.month


def idx(y, m):
    return y * 12 + m - 1


def load():
    cards = []
    for f in glob.glob(os.path.join(BASE, 'cards', '*.json')):
        d = json.load(open(f))
        pts = {idx(*ym(t)): v for t, v in d['chart'].get(SERIES, []) if v}
        if len(pts) >= 13:
            cards.append({'set': d['set'], 'name': d['name'], 'pts': pts})
    return cards


def monthly_returns(cards, era=None):
    # returns {month_index: [log returns]}; PriceCharting points are roughly monthly averages,
    # so the return for month t+1 is ln(avg price in t+1 / avg price in t)
    out = {}
    for c in cards:
        if c['set'] not in RELEASE:
            continue
        if era == 'vintage' and c['set'] not in VINTAGE:
            continue
        if era == 'modern' and c['set'] in VINTAGE:
            continue
        ry, rm = map(int, RELEASE[c['set']].split('-'))
        start = idx(ry, rm) + 12
        last = max(c['pts']) - 1  # final point is the current, partial month
        for t, p in c['pts'].items():
            q = c['pts'].get(t + 1)
            if t < start or q is None or t + 1 > last or p < MIN_CENTS or q < MIN_CENTS:
                continue
            r = max(-CLIP, min(CLIP, math.log(q / p)))
            out.setdefault(t + 1, []).append(r)
    return out


def analyze(cards, era=None, label=''):
    rets = monthly_returns(cards, era)
    index = {t: st.mean(v) for t, v in rets.items() if len(v) >= 20}
    n = {t: len(v) for t, v in rets.items()}
    years = sorted({t // 12 for t in index})
    pct = lambda x: f'{(math.exp(x) - 1) * 100:+6.1f}%'
    print(f'\n===== {label} [{SERIES}] cards used per month: min {min(n[t] for t in index)}, max {max(n[t] for t in index)}')
    print('Year  ' + ' '.join(f'{m:>7}' for m in MONTHS) + '   | Sep-Dec  Jan-Apr  May-Aug  Year')
    by_month_dt = {m: [] for m in range(12)}
    rows = []
    for y in years:
        vals = [index.get(y * 12 + m) for m in range(12)]
        have = [v for v in vals if v is not None]
        mean_y = st.mean(have) if have else 0
        for m, v in enumerate(vals):
            if v is not None and len(have) >= 6:
                by_month_dt[m].append((y, v - mean_y))
        win = lambda ms: sum(vals[m] for m in ms) if all(vals[m] is not None for m in ms) else None
        sd, ja, ma = win([8, 9, 10, 11]), win([0, 1, 2, 3]), win([4, 5, 6, 7])
        rows.append((y, sd, ja, ma, sum(have), len(have)))
        cell = lambda v: f'{pct(v):>7}' if v is not None else '      .'
        print(f'{y}  ' + ' '.join(cell(v) for v in vals) + f'   | {cell(sd)} {cell(ja)} {cell(ma)} {pct(sum(have))} ({len(have)}m)')
    print('\nMonth-of-year, after removing each year\'s average monthly move:')
    summary = {}
    for m in range(12):
        xs = [v for _, v in by_month_dt[m]]
        if len(xs) < 2:
            continue
        mu = st.mean(xs)
        se = st.stdev(xs) / math.sqrt(len(xs))
        neg = sum(1 for x in xs if x < 0)
        summary[MONTHS[m]] = {'mean': mu, 'se': se, 'n': len(xs), 'neg': neg, 'by_year': {y: v for y, v in by_month_dt[m]}}
        print(f'  {MONTHS[m]}: {pct(mu)} (se {se * 100:4.1f}pp, years below trend {neg}/{len(xs)})  ' + ' '.join(f'{y}:{pct(v)}' for y, v in by_month_dt[m]))
    # Sep-Dec vs following Jan-Apr, and vs same-year Jan-Apr
    print('\nSep-Dec vs the next Jan-Apr (raw, not detrended):')
    rmap = {r[0]: r for r in rows}
    pairs = []
    for y in years:
        sd = rmap[y][1]
        ja = rmap.get(y + 1, (None, None, None))[2]
        if sd is not None and ja is not None:
            pairs.append((y, sd, ja))
            print(f'  {y} Sep-Dec {pct(sd)}  ->  {y + 1} Jan-Apr {pct(ja)}   {"pattern holds" if sd < 0 < ja else "pattern fails"}')
    return {'index': index, 'rows': rows, 'summary': summary, 'pairs': pairs}


if __name__ == '__main__':
    cards = load()
    print('cards loaded', len(cards), 'series', SERIES)
    res = {}
    for era, label in ((None, 'ALL'), ('modern', 'MODERN (2016+ sets)'), ('vintage', 'VINTAGE (1999-2003 sets)')):
        res[label] = analyze(cards, era, label)
    json.dump({k: {'rows': v['rows'], 'pairs': v['pairs'], 'index': v['index'],
                   'summary': {m: {kk: vv for kk, vv in s.items()} for m, s in v['summary'].items()}}
               for k, v in res.items()}, open(os.path.join(BASE, f'season_{SERIES}.json'), 'w'), indent=1, default=str)
