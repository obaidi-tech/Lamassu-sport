"""U17 World Cup: 24-team (2017-2023) vs 48-team (2025-) editions. Usage: python3 analyze.py"""
import csv, glob, json
from collections import defaultdict
conf = {r['team']: r for r in csv.DictReader(open('teams.csv'))}
out = {}
for f in sorted(glob.glob('results_*.csv')):
    year = f[8:12]; rows = list(csv.DictReader(open(f)))
    for r in rows:
        for t in (r['home'], r['away']):
            assert t in conf, (year, t)
    def stats(L):
        n = len(L); g = [int(r['home_goals']) + int(r['away_goals']) for r in L]
        m = [abs(int(r['home_goals']) - int(r['away_goals'])) for r in L]
        return dict(matches=n, goals=sum(g), gpm=round(sum(g)/n, 2),
                    margin_avg=round(sum(m)/n, 2),
                    pct_margin5=round(100*sum(x >= 5 for x in m)/n, 1),
                    pct_margin3=round(100*sum(x >= 3 for x in m)/n, 1),
                    pct_close=round(100*sum(x <= 1 for x in m)/n, 1),
                    pct_draw=round(100*sum(x == 0 for x in m)/n, 1),
                    biggest=max(m))
    grp = [r for r in rows if r['stage'] == 'Group']; ko = [r for r in rows if r['stage'] != 'Group']
    teams = {t for r in rows for t in (r['home'], r['away'])}
    # points per confederation in group stage
    pts = defaultdict(lambda: [0, 0])  # points, games
    arab = defaultdict(lambda: [0, 0, 0, 0, 0])  # W D L GF GA
    for r in grp:
        h, a, hg, ag = r['home'], r['away'], int(r['home_goals']), int(r['away_goals'])
        for t, gf, ga in ((h, hg, ag), (a, ag, hg)):
            p = 3 if gf > ga else 1 if gf == ga else 0
            c = conf[t]['confed']; pts[c][0] += p; pts[c][1] += 1
            if conf[t]['arab'] == '1':
                s = arab[t]; s[0 if gf > ga else 1 if gf == ga else 2] += 1; s[3] += gf; s[4] += ga
    ko_teams = {t for r in ko for t in (r['home'], r['away'])}
    out[year] = dict(teams=len(teams), all=stats(rows), group=stats(grp), knockout=stats(ko) if ko else None,
                     ppg_by_confed={c: round(v[0]/v[1], 2) for c, v in sorted(pts.items())},
                     arab_group={t: dict(zip('WDL', v[:3]), gf=v[3], ga=v[4], advanced=t in ko_teams) for t, v in arab.items()})
json.dump(out, open('summary.json', 'w'), ensure_ascii=False, indent=1)
for y, d in out.items():
    print(y, d['teams'], 'ALL', d['all']); print('   GRP', d['group']); print('   KO ', d['knockout'])
    print('   PPG', d['ppg_by_confed']); print('   ARAB', d['arab_group'])
