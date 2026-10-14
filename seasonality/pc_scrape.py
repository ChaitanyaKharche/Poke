import html, json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

OUT = sys.argv[1]
TOP_N = 15
SETS = [
    'pokemon-base-set', 'pokemon-jungle', 'pokemon-fossil', 'pokemon-team-rocket', 'pokemon-gym-heroes',
    'pokemon-neo-genesis', 'pokemon-neo-destiny', 'pokemon-skyridge', 'pokemon-evolutions', 'pokemon-generations',
    'pokemon-hidden-fates', 'pokemon-team-up', 'pokemon-unified-minds', 'pokemon-cosmic-eclipse',
    'pokemon-vivid-voltage', 'pokemon-shining-fates', 'pokemon-chilling-reign', 'pokemon-evolving-skies',
    'pokemon-celebrations', 'pokemon-fusion-strike', 'pokemon-brilliant-stars', 'pokemon-astral-radiance',
    'pokemon-go', 'pokemon-lost-origin', 'pokemon-silver-tempest', 'pokemon-crown-zenith',
    'pokemon-scarlet-&-violet', 'pokemon-paldea-evolved', 'pokemon-obsidian-flames', 'pokemon-scarlet-&-violet-151',
    'pokemon-paradox-rift', 'pokemon-paldean-fates', 'pokemon-temporal-forces', 'pokemon-twilight-masquerade',
    'pokemon-stellar-crown', 'pokemon-surging-sparks', 'pokemon-prismatic-evolutions',
]
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36'}

def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.read().decode('utf-8', 'replace')
        except Exception as e:
            print('  retry', url, e, flush=True)
            time.sleep(5 * (attempt + 1))
    return None

index = {}

def fetch_card(args):
    s, u, n = args
    fn = os.path.join(OUT, re.sub(r'[^A-Za-z0-9]+', '_', u.strip('/')) + '.json')
    if not os.path.exists(fn):
        p = get('https://www.pricecharting.com' + u)
        time.sleep(1.0)
        m = p and re.search(r'chart_data = (\{.*?\});', p, re.S)
        if not m:
            print('  no chart', u, flush=True)
            return None
        json.dump({'url': u, 'set': s, 'name': n, 'chart': json.loads(m.group(1))}, open(fn, 'w'))
    return u, {'set': s, 'name': n, 'file': fn}

def set_cards(s):
    page = get(f'https://www.pricecharting.com/console/{urllib.request.quote(s)}?sort=highest-price')
    if not page:
        print('SET FAIL', s, flush=True)
        return []
    links = re.findall(r'<a href="(/game/' + re.escape(s) + r'/[^"]+)">([^<]+)</a>', page)
    seen, picked = set(), []
    for u, n in links:
        if '#' not in n or u in seen:
            continue
        seen.add(u)
        picked.append((s, html.unescape(u), html.unescape(n)))
        if len(picked) == TOP_N:
            break
    print('SET', s, 'picked', len(picked), flush=True)
    return picked

with ThreadPoolExecutor(4) as ex:
    jobs = [j for lst in ex.map(set_cards, SETS) for j in lst]
    print('JOBS', len(jobs), flush=True)
    done = 0
    for r in ex.map(fetch_card, jobs):
        done += 1
        if r:
            index[r[0]] = r[1]
        if done % 50 == 0:
            print('progress', done, flush=True)
json.dump(index, open(os.path.join(OUT, '..', 'index.json'), 'w'), indent=1)
print('DONE', len(index), flush=True)
