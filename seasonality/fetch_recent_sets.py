# Fetch every card (with 180 days of history) and every sealed product for recent sets.
import json, os, sys, time, urllib.request, urllib.parse
OUT = sys.argv[1]  # e.g. data/api
os.makedirs(OUT, exist_ok=True)
KEY = os.environ['API_KEY']
def get(path, params):
    req = urllib.request.Request(f'https://www.pokemonpricetracker.com/api/v2/{path}?' + urllib.parse.urlencode(params), headers={'Authorization': 'Bearer ' + KEY})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read()), r.headers.get('x-api-calls-consumed'), r.headers.get('x-ratelimit-daily-remaining')
    except urllib.error.HTTPError as e:
        return {'error': e.code, 'body': e.read().decode()[:300]}, None, None
SINGLES = {'24722': '30th Celebration', '24837': '30th Celebration Classic Collection', '24541': 'Ascended Heroes'}
SEALED = {'24722': '30th Celebration', '24541': 'Ascended Heroes', '24587': 'Perfect Order', '24655': 'Chaos Rising', '24688': 'Pitch Black'}
for sid, name in SINGLES.items():
    fn = os.path.join(OUT, f'set_{sid}.json')
    if os.path.exists(fn): continue
    body, cost, rem = get('cards', {'setId': sid, 'fetchAllInSet': 'true', 'includeHistory': 'true', 'days': 180, 'maxDataPoints': 180})
    print('singles', name, len(body.get('data') or []), 'credits', cost, 'remaining', rem, body.get('error', ''), flush=True)
    json.dump(body, open(fn, "w")); time.sleep(65)  # fetchAllInSet uses many per-minute calls
for sid, name in SEALED.items():
    fn = os.path.join(OUT, f'sealed_{sid}.json')
    if os.path.exists(fn): continue
    body, cost, rem = get('sealed-products', {'setId': sid, 'fetchAllInSet': 'true', 'includeHistory': 'true', 'days': 180})
    print('sealed', name, len(body.get('data') or []), 'credits', cost, 'remaining', rem, body.get('error', ''), body.get('body', ''), flush=True)
    json.dump(body, open(fn, "w")); time.sleep(65)  # fetchAllInSet uses many per-minute calls
