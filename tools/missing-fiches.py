# -*- coding: utf-8 -*-
"""Which estates have no technical sheet, by list.

    python tools/missing-fiches.py
    python tools/missing-fiches.py --all     name every estate, not just
                                             the classified ones

An estate counts as having a fiche when data/sources.json holds a sheet
attributed to it whose role is the grand vin's, or combined, or not yet
identified. A sheet marked as another wine, another property, a page or
a brochure does not count, which is the point: 132 sheets came off five
estates this week and those estates stopped having fiches, correctly.

Writes reports/missing-fiches.txt.
"""
import io, os, re, sys, json, argparse, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr

ap = argparse.ArgumentParser()
ap.add_argument('--all', action='store_true')
a = ap.parse_args()

E = sr.estates(ROOT)

# The list each estate belongs to. app.js assigns cls at runtime where a
# record has none: sweet becomes sauternes, everything else 1855.
src = {}
for f in sr.ESTATE_FILES:
    p = ROOT + 'data/' + f
    if not os.path.exists(p):
        continue
    t = io.open(p, encoding='utf-8').read()
    for m in re.finditer(r"id:'([a-z0-9-]+)'", t):
        w = t[m.end():m.end() + 900]
        n = re.search(r"id:'[a-z0-9-]+'", w)
        if n:
            w = w[:n.start()]
        c = sr.js_strings_after('cls:', w)
        src.setdefault(m.group(1), (f, c[0] if c else None))

LAB = {'1855': '1855 Médoc & Graves', 'sauternes': '1855 Sauternes',
       'graves': 'Graves 1959', 'stem': 'Saint-Émilion classed',
       'pomerol': 'Pomerol (listed)', 'cotes': 'Côtes',
       'graves-doux': 'Graves, sweet', 'libournais': 'Libournais'}
ORDER = ['1855 Médoc & Graves', '1855 Sauternes', 'Graves 1959',
         'Saint-Émilion classed', 'Pomerol (listed)', 'Libournais',
         'Côtes', 'Graves, sweet', 'Saint-Émilion unclassed',
         'Pomerol unlisted', 'Cru Bourgeois', 'Cru Artisan', 'other']
CLASSIFIED = set(ORDER[:8])


def group(eid):
    f, c = src.get(eid, (None, None))
    if c:
        return LAB.get(c, c)
    if f:
        return ('1855 Sauternes' if (E[eid].get('cat') == 'sweet')
                else '1855 Médoc & Graves')
    for pre, lab in (('bourgeois-', 'Cru Bourgeois'),
                     ('artisan-', 'Cru Artisan'),
                     ('stem-', 'Saint-Émilion unclassed'),
                     ('pomerol-', 'Pomerol unlisted')):
        if eid.startswith(pre):
            return lab
    return 'other'


man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
has = set()
for s in man['sheets']:
    if s.get('estate') and s.get('role') in ('grand', 'combined', 'unknown'):
        has.add(s['estate'])
blend = set()
for line in io.open(ROOT + 'data/fiches.js', encoding='utf-8'):
    m = re.match(r"^'([a-z0-9-]+)\|\d{4}':\{(.*)\},$", line.rstrip())
    if m and 'blend:{' in m.group(2):
        blend.add(m.group(1))

out = []
tot = collections.defaultdict(lambda: [0, 0, 0])
missing = collections.defaultdict(list)
for eid, e in E.items():
    g = group(eid)
    tot[g][0] += 1
    if eid in has:
        tot[g][1] += 1
    else:
        missing[g].append(e.get('name') or eid)
    if eid in blend:
        tot[g][2] += 1

out.append('ESTATES WITH NO TECHNICAL SHEET')
out.append('')
out.append('%-26s %7s %9s %9s %8s' % ('', 'estates', 'w/ fiche', 'w/ blend',
                                      'missing'))
for g in ORDER:
    if g not in tot:
        continue
    n, u, b = tot[g]
    out.append('%-26s %7d %9s %9s %8d'
               % (g, n, '%d (%.0f%%)' % (u, 100.0 * u / n),
                  '%d (%.0f%%)' % (b, 100.0 * b / n), n - u))
cn = sum(tot[g][0] for g in ORDER if g in tot and g in CLASSIFIED)
cu = sum(tot[g][1] for g in ORDER if g in tot and g in CLASSIFIED)
out.append('')
out.append('classified lists together: %d estates, %d with a fiche (%.0f%%), '
           '%d without' % (cn, cu, 100.0 * cu / cn, cn - cu))
out.append('every list together:       %d estates, %d with a fiche (%.0f%%), '
           '%d without'
           % (len(E), len(has), 100.0 * len(has) / len(E), len(E) - len(has)))

for g in ORDER:
    if g not in missing or not missing[g]:
        continue
    if g not in CLASSIFIED and not a.all:
        out.append('')
        out.append('%s: %d missing (pass --all to name them)'
                   % (g, len(missing[g])))
        continue
    out.append('')
    out.append('%s - %d with no sheet:' % (g, len(missing[g])))
    for nm in sorted(missing[g]):
        out.append('   ' + nm)

if not os.path.isdir(ROOT + 'reports'):
    os.makedirs(ROOT + 'reports')
io.open(ROOT + 'reports/missing-fiches.txt', 'w', encoding='utf-8',
        newline='').write('\n'.join(out) + '\n')
print('\n'.join(out))
print('\nwritten to reports/missing-fiches.txt')
