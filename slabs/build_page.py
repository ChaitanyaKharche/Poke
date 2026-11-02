"""Build the Slab Check page from a scan.

Usage:
    python3 slabs/build_page.py slabs/data/scan.json slabs/data/slab-check.html
"""
import json
import os
import sys

KEEP = ('comp', 'n30', 'perWeek', 'trend', 'last5', 'lastSale', 'low30', 'high30')


def trim(card):
    grades = {}
    for g, s in (card.get('grades') or {}).items():
        if s.get('comp'):
            grades[g] = {k: s.get(k) for k in KEEP}
    return {
        'id': card['id'], 'name': card['name'], 'set': card.get('set'), 'num': card.get('num'),
        'rarity': card.get('rarity'), 'printing': card.get('printing'), 'raw': card.get('raw'),
        'listings': card.get('listings'), 'released': card.get('released'), 'grades': grades,
    }


def main():
    scan_path, out_path = sys.argv[1], sys.argv[2]
    scan = json.load(open(scan_path))
    data = {'scanned': scan['scanned'], 'cards': [trim(c) for c in scan['cards'] if c.get('raw')]}
    template = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'page_template.html')).read()
    payload = json.dumps(data, separators=(',', ':')).replace('</', '<\\/')
    html = template.replace('/*DATA*/null', payload)
    open(out_path, 'w').write(html)
    print(f'{len(data["cards"])} cards, {len(html) / 1e6:.1f} MB -> {out_path}')


if __name__ == '__main__':
    main()
