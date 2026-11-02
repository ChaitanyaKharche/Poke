"""Build the Slab Check page from a scan.

Usage:
    python3 slabs/build_page.py slabs/data/scan.json [slabs/data/scan_high.json ...] slabs/data/slab-check.html
"""
import json
import os
import statistics
import sys

KEEP = ('comp', 'n30', 'perWeek', 'trend', 'last5', 'lastSale', 'low30', 'high30')


def trim(card):
    grades = {}
    for g, s in (card.get('grades') or {}).items():
        if not s.get('comp'):
            continue
        row = {k: s.get(k) for k in KEEP}
        row['avg30'] = s['comp']
        last5 = s.get('last5') or []
        if s.get('med30'):
            row['comp'] = s['med30']
        elif (s.get('n30') or 0) >= 3 and len(last5) >= 3:
            row['comp'] = round(statistics.median(last5), 2)  # typical recent sale day; resists one-off spikes
        grades[g] = row
    return {
        'id': card['id'], 'name': card['name'], 'set': card.get('set'), 'num': card.get('num'),
        'rarity': card.get('rarity'), 'printing': card.get('printing'), 'raw': card.get('raw'),
        'listings': card.get('listings'), 'released': card.get('released'), 'grades': grades,
    }


def main():
    *scan_paths, out_path = sys.argv[1:]
    scans = [json.load(open(p)) for p in scan_paths]
    merged = {}
    for scan in scans:
        for c in scan['cards']:
            if c.get('raw'):
                merged[c['id']] = trim(c)
    data = {'scanned': min(s['scanned'] for s in scans), 'cards': list(merged.values())}
    template = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'page_template.html')).read()
    payload = json.dumps(data, separators=(',', ':')).replace('</', '<\\/')
    html = template.replace('/*DATA*/null', payload)
    open(out_path, 'w').write(html)
    print(f'{len(data["cards"])} cards, {len(html) / 1e6:.1f} MB -> {out_path}')


if __name__ == '__main__':
    main()
