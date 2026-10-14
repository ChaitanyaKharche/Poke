import json, os, sys, time, urllib.request, urllib.parse
OUT = sys.argv[1]
SETS = {'24688': 'ME05: Pitch Black', '24655': 'ME04: Chaos Rising', '24587': 'ME03: Perfect Order'}
for sid, name in SETS.items():
    q = urllib.parse.urlencode({'setId': sid, 'fetchAllInSet': 'true', 'includeHistory': 'true', 'days': 180, 'maxDataPoints': 180})
    req = urllib.request.Request('https://www.pokemonpricetracker.com/api/v2/cards?' + q, headers={'Authorization': 'Bearer ' + os.environ['API_KEY']})
    with urllib.request.urlopen(req, timeout=180) as r:
        hdr = {k: v for k, v in r.headers.items() if k.lower().startswith('x-')}
        body = json.loads(r.read())
    print(name, 'cards', len(body['data']), 'credits', hdr.get('x-api-calls-consumed') or hdr.get('X-API-Calls-Consumed'), 'remaining', hdr.get('x-ratelimit-daily-remaining') or hdr.get('X-RateLimit-Daily-Remaining'), flush=True)
    json.dump(body, open(os.path.join(OUT, f'set_{sid}.json'), 'w'))
    time.sleep(3)
