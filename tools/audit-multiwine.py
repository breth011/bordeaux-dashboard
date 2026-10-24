# -*- coding: utf-8 -*-
"""Documents that cover more than one of an estate's wines.

data/sources.json records ONE wine per sheet, and every guard is built
on that: whose_sheet decides whose document this is, and then
everything in it is read as that wine's. A sheet covering two wines
breaks the assumption quietly, because it is correctly attributed and
still wrong about half its contents.

Lynch-Bages' negociant sheet is the case that found it. It opens

    Chateau Lynch-Bages 2017 Blend: 70% Cabernet Sauvignon 24% Merlot
    Ageing: 18 months in French oak barrels (75% new wood)
    Analyses: Alcohol: 13.06% vol...

so it is the grand vin's, and whose_sheet is right to accept it. Then
further down it carries

    Tasting note (March 2018): The Blanc de Lynch-Bages 2017 is a
    pale-yellow colour with green hues...

and the label is real, so the labelled reader offered the white's note
for the grand vin's record. Nothing was looking inside the window.

blend_of has always known about this - it cuts its window at another
wine's mark - and read_prose now refuses a passage that opens by
naming a different wine. But neither of those tells anyone WHICH
documents are like this, which is what makes the next one a surprise
too.

So this counts them: for every document in the manifest, how many of
its estate's wines does it name? The answer is a property of the
document, worth recording once rather than rediscovering.

    python tools/audit-multiwine.py                 the whole archive
    python tools/audit-multiwine.py --estate lynch-bages
    python tools/audit-multiwine.py --write         into sources.json

--write adds `wines_named` to each sheet that names more than one, so
the manifest says so and a reader can ask. It writes nothing else and
leaves every other field alone.
"""
import argparse
import collections
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheetreader as sr


def wines_of(e):
    """The estate's wines, by the names a sheet would use."""
    out = []
    if e.get('name'):
        out.append(('grand', e['name']))
    if e.get('second'):
        out.append(('second', e['second']))
    for c in (e.get('cuvees') or ()):
        out.append(('other', c))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--estate')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--limit', type=int, default=30)
    a = ap.parse_args()

    E = sr.estates(ROOT)
    man = json.load(io.open(ROOT + 'data/sources.json', encoding='utf-8'))
    where = {}
    for root, dirs, files in os.walk(ROOT + 'sources'):
        for f in files:
            where.setdefault(f, os.path.join(root, f))

    hits = []
    byest = collections.Counter()
    read = 0
    for s in man.get('sheets', []):
        eid = s.get('estate')
        if not eid or (a.estate and eid != a.estate):
            continue
        e = E.get(eid) or {}
        wines = wines_of(e)
        if len(wines) < 2:
            continue
        p = where.get(s['file'])
        if not p:
            continue
        try:
            t = ' '.join(sr.flat(p).split())
        except Exception:
            continue
        read += 1
        # The grand vin's name is inside most cuvee names - "Blanc de
        # Lynch-Bages" contains "Lynch-Bages" - so a wine counts as
        # named only where its own name matches and no LONGER wine
        # name matches at the same place. Longest first does that.
        named = []
        for role, nm in sorted(wines, key=lambda w: -len(w[1])):
            if not sr.says(t, nm):
                continue
            if any(nm.lower() in prev.lower() for _r, prev in named):
                continue
            named.append((role, nm))
        if len(named) > 1:
            hits.append((eid, s['file'], s.get('wine') or s.get('role')
                         or '?', named))
            byest[eid] += 1

    print('%d document(s) read at estates that make more than one wine'
          % read)
    print('%d name more than one of them, at %d estate(s)\n'
          % (len(hits), len(byest)))

    print('%-30s %s' % ('estate', 'multi-wine documents'))
    print('-' * 56)
    for eid, n in byest.most_common(a.limit):
        print('   %-30s %d' % (eid[:30], n))
    if len(byest) > a.limit:
        print('   ... and %d more estate(s)' % (len(byest) - a.limit))

    if a.estate:
        print()
        for eid, fn, filed, named in hits[:a.limit]:
            print('   %s' % fn[:66])
            print('      filed as %-10s names: %s'
                  % (filed, ', '.join(nm for _r, nm in named)))

    if a.write:
        n = 0
        idx = {}
        for s in man.get('sheets', []):
            idx[(s.get('estate'), s.get('file'))] = s
        for eid, fn, filed, named in hits:
            s = idx.get((eid, fn))
            if s is None:
                continue
            s['wines_named'] = [nm for _r, nm in named]
            n += 1
        io.open(ROOT + 'data/sources.json', 'w', encoding='utf-8',
                newline='').write(
            json.dumps(man, indent=1, ensure_ascii=False,
                       sort_keys=True) + '\n')
        print('\nwines_named written on %d sheet(s) in data/sources.json'
              % n)
    elif hits:
        print('\nnothing written; pass --write to record wines_named on '
              'these sheets')


if __name__ == '__main__':
    main()
