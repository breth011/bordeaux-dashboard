"""Phase 2.4 section 7: why each surviving v3 second-wine acceptance passed.

Reads documents from sources/ (untrusted data): run with python -I.
Changes nothing.
"""
import glob
import os
import re
import sys
import unicodedata

ROOT = sys.argv[1]
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import sheetreader as sr

E = sr.estates(ROOT + os.sep)

CASES = [
    ('belgrave', 'belgrave-2023-fc11b611.pdf', 2023),
    ('latour-martillac',
     '2020__agrave-martillac-blanc-2020-lacroix-martillac-rouge-2019-min.txt',
     2020),
    ('latour-martillac',
     '2020__agrave-martillac-blanc-2020-lacroix-martillac-rouge-2019-min.txt',
     2019),
    ('caillou', 'Fiche-technique-FR-MURETS-BLANCS-2023-AOC-Bordeaux-Blanc.pdf',
     2023),
    ('pedesclaux', 'FT-PEDESCLAUX-2025_FR_compressed.pdf', 2025),
    ('haut-brion',
     '2019__-mission-haut-brion-la-chapelle-de-la-mission-haut-brion2019.txt',
     2019),
]


def squashed(path):
    head = sr.flat(path, 1)
    s = re.sub(r'\s+', '', head)[:400].lower()
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if not unicodedata.combining(c))


for eid, fn, yr in CASES:
    e = E[eid]
    hits = glob.glob(os.path.join(ROOT, 'sources', '**', fn), recursive=True)
    print('=' * 78)
    print('%s | %s | asked for %s' % (eid, fn, yr))
    print('  estate second wine : %r' % e.get('second'))
    print('  estate cuvees      : %r' % e.get('cuvees'))
    print('  copies on disk     : %s' % [os.path.relpath(h, ROOT) for h in hits])
    if not hits:
        continue
    p = hits[0]
    named = fn
    wines = list(dict.fromkeys([w for w in e['cuvees'] if w] + [e['second']]))
    fnw = sr.named_wines(named, e['name'], wines)
    print('  filename names     : %r' % fnw)
    print('  is_second_wine     : %r' % sr.is_second_wine(p))
    s = squashed(p)
    for ph in ('secondvin', 'deuxiemevin', 'secondwine'):
        i = s.find(ph)
        if i >= 0:
            print('     phrase %-11s at %3d  context %r  3-before %r'
                  % (ph, i, s[max(0, i - 25):i + len(ph) + 12],
                     s[max(0, i - 3):i]))
    sibs = [w for w in wines if w != e['second']]
    try:
        t = sr.names_another_wine(p, fn, e['name'], e['second'], siblings=sibs)
    except Exception as x:
        t = 'error %s' % x
    print('  title names second : %r' % t)
    v = sr.whose_sheet(p, fn, e['name'], e['cuvees'], e['second'], e['cat'],
                       year=yr, is_second=True)
    print('  whose_sheet (2nd)  : %s' % ('ACCEPTED' if v is None else v))
    g = sr.whose_sheet(p, fn, e['name'], e['cuvees'], e['second'], e['cat'],
                       year=yr)
    print('  whose_sheet (grand): %s' % ('ACCEPTED' if g is None else g))
    body = ' '.join(sr.flat(p).split())
    print('  opening            : %s' % body[:420])
    for w in [e['name']] + wines:
        core = re.sub(r'(?i)^(ch[aâ]teau|clos|domaine)\s+', '', w)
        core = re.sub(r'\s*\([^)]*\)', '', core)
        n = len(re.findall(re.escape(core.split()[0]), body, re.I))
        print('     mentions of %-40r first-word count %d' % (w, n))
    yrs = sorted(set(re.findall(r'(?<!\d)(?:19|20)\d\d(?!\d)', body)))
    print('  years in document  : %s' % yrs)
