import json, math, os, statistics as st, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import season
season.SERIES = sys.argv[2] if len(sys.argv) > 2 else 'used'
season.BASE = sys.argv[1]
cards = season.load()
pct = lambda x: f'{(math.exp(x) - 1) * 100:+.1f}%'
for era in (None, 'modern', 'vintage'):
    rets = season.monthly_returns(cards, era)
    for agg_name, agg in (('mean', st.mean), ('median', st.median)):
        index = {t: agg(v) for t, v in rets.items() if len(v) >= 20}
        years = sorted({t // 12 for t in index})
        lines, wins, n = [], 0, 0
        for y in years:
            vals = [index.get(y * 12 + m) for m in range(12)]
            have = [v for v in vals if v is not None]
            if len(have) < 9: continue
            mu = st.mean(have)
            ja = [vals[m] - mu for m in range(4) if vals[m] is not None]
            sd = [vals[m] - mu for m in range(8, 12) if vals[m] is not None]
            ja_s, sd_s = sum(ja), sum(sd)
            if len(sd) == 4 and len(ja) >= 3:
                n += 1; wins += ja_s > sd_s
                lines.append(f'{y}: Jan-Apr {pct(ja_s)} vs Sep-Dec {pct(sd_s)} (vs trend)')
            elif len(ja) >= 3:
                lines.append(f'{y}: Jan-Apr {pct(ja_s)} (Sep-Dec not complete)')
        print(f'[{season.SERIES}] {era or "all"} / {agg_name}: Jan-Apr beat Sep-Dec within the same year in {wins}/{n} years | ' + '; '.join(lines))
